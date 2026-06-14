import time
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from nyuctf.challenge import CTFChallenge

from .logging import logger
from .conversation import Conversation, MessageRole, Message
from .tools import DelegateTool, FinishTaskTool, ToolResult, GenAutoPromptTool
from .utils import AgentError

now = lambda: time.time()
EXECUTOR_LOOP_WARNING_LIMIT = 3
PLANNER_REPEAT_TASK_LIMIT = 3


def _normalize_text(text):
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _candidate_flags(text):
    if not text:
        return []
    return re.findall(r"[A-Za-z0-9_]+\{[^}\n\r]{1,256}\}", str(text))

class BaseAgent:
    """Base class for an Agent"""
    def __init__(self, environment, challenge, prompter, backend):
        self.environment = environment
        self.challenge = challenge
        self.prompter = prompter
        self.backend = backend

        self.conversation = Conversation()
        self.max_rounds = 30
        self.current_cost = 0.0
        self.flag_candidates = []
        self.loop_warnings = 0

    def continue_prompt(self, task_description=None):
        return self.prompter.build_continue(self, task_description=task_description)

    def add_start_prompts(self):
        """
        Adds the system and initial prompts to the conversation.
        This is a separate function to allow adding more params to the prompts.
        """
        self.add_system_message(self.prompter.get("system"))
        self.add_user_message(self.prompter.get("initial"))

    def check_flag_in_response(self, response):
        if response is None:
            return
        stripped_flag = self.challenge.flag
        if "{" in stripped_flag:
            stripped_flag = stripped_flag[stripped_flag.index("{")+1:-1]
        if stripped_flag in str(response):
            self.environment.solved = True
        for candidate in _candidate_flags(str(response)):
            if candidate not in self.flag_candidates:
                self.flag_candidates.append(candidate)

    # Helper functions to add and print messages to the conversation
    def add_system_message(self, message):
        self.conversation.append_system(message)
        logger.system_message(message)
    def add_user_message(self, message):
        self.conversation.append_user(message)
        logger.user_message(message)
        self.check_flag_in_response(message)
    def add_assistant_message(self, message, tool_call):
        self.conversation.append_assistant(content=message, tool_data=tool_call)
        # Only print thought, action is printed after tool_call is parsed
        logger.assistant_thought(message)
        self.check_flag_in_response(message)
        if tool_call is not None:
            self.check_flag_in_response(tool_call.arguments)

    def add_observation_message(self, tool_result):
        self.conversation.append_observation(tool_data=tool_result)
        # Get truncated output from the conversation
        self.check_flag_in_response(str(self.conversation.all_messages[-1].tool_data.result))

    def run_one_round(self):
        raise NotImplementedError

    def print_parsed_call(self, parsed_call):
        self.environment.tools[parsed_call.name].print_tool_call(parsed_call)
    def print_result(self, tool_result):
        if tool_result.name in self.environment.tools:
            self.environment.tools[tool_result.name].print_result(tool_result)
        else:
            logger.observation_message(tool_result.format())

    def recent_assistant_messages(self, count=3):
        messages = []
        for m in reversed(self.conversation.all_messages):
            if m.role == MessageRole.ASSISTANT and m.content:
                messages.append(m.content)
                if len(messages) >= count:
                    break
        return list(reversed(messages))

    def recent_tool_names(self, count=3):
        names = []
        for m in reversed(self.conversation.all_messages):
            if m.role == MessageRole.ASSISTANT and m.tool_data is not None:
                names.append(m.tool_data.name)
                if len(names) >= count:
                    break
        return list(reversed(names))

    def detect_loop(self):
        recent_msgs = self.recent_assistant_messages(3)
        if len(recent_msgs) < 3:
            return False

        normalized = [_normalize_text(msg) for msg in recent_msgs]
        min_similarity = min(
            _similarity(normalized[0], normalized[1]),
            _similarity(normalized[1], normalized[2]),
        )
        repeated_tools = self.recent_tool_names(3)
        same_tool_chain = len(repeated_tools) == 3 and len(set(repeated_tools)) == 1
        no_recent_observation = True
        for m in reversed(self.conversation.all_messages):
            if m.role == MessageRole.OBSERVATION:
                result_text = _normalize_text(str(m.tool_data.result))
                no_recent_observation = result_text in {"none", "", "{}", "[]"} or len(result_text) < 16
                break

        return min_similarity >= 0.72 or (same_tool_chain and no_recent_observation)

    def add_loop_warning(self, message):
        self.loop_warnings += 1
        self.add_user_message(message)


class SingleAgent(BaseAgent):
    """Single Executor Agent implementation"""
    def __init__(self, environment, challenge, prompter, backend, autoprompter,
                 max_rounds=30, max_cost=1.0, len_observations=5, logfile=None, critic=None):
        super().__init__(environment, challenge, prompter, backend)
        self.autoprompter = autoprompter
        self.critic = critic
        self.max_rounds = max_rounds
        self.max_cost = max_cost
        self.conversation.len_observations = len_observations
        self.logfile = logfile
        self.last_loop_round = -1

    def __enter__(self):
        self.challenge.start_challenge_container()
        self.environment.setup()
        self.start_time = now()
        logger.start_progress()
        return self

    def __exit__(self, ex_type, ex_val, tb):
        self.environment.teardown(ex_type, ex_val, tb)
        self.challenge.stop_challenge_container()
        self.end_time = now()

        error = f"{ex_type.__name__}: {str(ex_val)}" if ex_type is not None else None
        self.dump_log(error=error)
        logger.stop_progress()

    def get_exit_reason(self):
        if self.environment.solved:
            return "solved"
        elif self.environment.giveup:
            return "giveup"
        elif self.total_cost() > self.max_cost:
            return "cost"
        elif self.conversation.round > self.max_rounds:
            return "max_rounds"
        else:
            return "unknown"

    def dump_log(self, error=None):
        if self.logfile is None:
            return

        exit_reason = "error" if error is not None else self.get_exit_reason()
        cost = self.total_cost()
        with self.logfile.open("w") as lf:
            json.dump({
                "start_time": self.start_time,
                "end_time": self.end_time,
                "time_taken": (self.end_time - self.start_time),
                "autoprompter_model": None if not self.autoprompter.enabled else self.autoprompter.backend.model,
                "executor_model": self.backend.model,
                "total_cost": cost,
                "success": self.environment.solved,
                "exit_reason": exit_reason,
                "error": error,
                "autoprompter": [] if not self.autoprompter.enabled else self.autoprompter.conversation.dump(),
                "critic": [] if self.critic is None else self.critic.critiques,
                "executor": self.conversation.dump(),
                "flag_candidates": self.flag_candidates,
                "loop_warnings": self.loop_warnings,
                "debug_log": logger.debug_log,
            }, lf, indent=2)
        if exit_reason == "solved":
            logger.print("[green bold]Challenge Solved![/green bold]", force=True, markup=True)
        else:
            logger.print("[red bold]Challenge Not Solved![/red bold]", force=True, markup=True)
        logger.print(f"exit: {exit_reason} cost: ${cost:.3f} rounds: {self.conversation.round}", force=True)

    def total_cost(self):
        cost = self.current_cost
        if self.autoprompter.enabled:
            cost += self.autoprompter.current_cost
        if self.critic is not None:
            cost += self.critic.current_cost
        logger.progress_message(f"${cost:.3f} / ${self.max_cost:.3f}")
        return cost

    def run_one_round(self):
        response = self.backend.send(self.conversation.messages) 
        if response.error is not None:
            raise AgentError(response.error)

        self.current_cost += response.cost
        self.add_assistant_message(response.content, response.tool_call)

        if not response.tool_call:
            self.add_user_message(self.continue_prompt())
            return

        parsed, parsed_call = self.backend.parse_tool_arguments(response.tool_call)
        if not parsed:
            # Print unparsed tool_call
            logger.assistant_action(response.tool_call.format())
            # Contains the ToolResult with error
            self.print_result(parsed_call)
            self.add_observation_message(parsed_call)
            return

        # Print parsed tool_call
        self.print_parsed_call(parsed_call)

        tool_result = self.environment.run_tool(parsed_call)
        self.print_result(tool_result)
        self.add_observation_message(tool_result)

    def run_autoprompter(self):
        """Run the autoprompter to set the autoprompt for single agent"""
        # Assumes autoprompter is not None
        while not self.environment.solved and not self.autoprompter.finished \
                and self.autoprompter.conversation.round <= self.autoprompter.max_rounds \
                and self.total_cost() <= self.max_cost:
            self.autoprompter.conversation.next_round()
            self.autoprompter.run_one_round()

        if not self.environment.solved and self.total_cost() <= self.max_cost \
                and self.autoprompter.autoprompt is None:
            # Prompt last time for the autoprompt
            self.autoprompter.run_for_autoprompt()

    def run(self):
        """
        Basic loop to run the agent for fixed number of rounds.
        Calls run_one_round() for each iteration.
        """
        initial_prompt = self.prompter.get("initial")
        if self.autoprompter.enabled:
            # Run the autoprompter if provided
            self.run_autoprompter()
            if self.autoprompter.autoprompt is not None:
                # Only set if autoprompter successfully generates a prompt
                initial_prompt = self.autoprompter.autoprompt
            elif not self.environment.solved:
                logger.print("WARNING! Autoprompter failed to generate a prompt, using the hardcoded one", force=True, style="dark_orange bold")

        logger.print("============= EXECUTOR ===============", style="bold")
        self.add_system_message(self.prompter.get("system"))
        self.add_user_message(initial_prompt)

        while not self.environment.giveup and not self.environment.solved \
                and self.conversation.round <= self.max_rounds \
                and self.total_cost() <= self.max_cost:
            self.conversation.next_round()
            if self.conversation.round != self.last_loop_round and self.detect_loop():
                if self.critic is not None:
                    critique = self.critic.critique(
                        scope="single_executor",
                        task_description="Solve the challenge end-to-end as a single agent.",
                        transcript=self.conversation.dump()[-8:],
                    )
                    if critique:
                        self.add_user_message(f"Critic feedback: {critique}")
                self.add_loop_warning(
                    "Loop control: your last steps repeated the same hypothesis. "
                    "Do not retry the same payload or same analysis path. "
                    "State one disproved hypothesis, one missing fact, and then take a materially different next action."
                )
                self.last_loop_round = self.conversation.round
            self.run_one_round()


class AutoPromptAgent(BaseAgent):
    """The AutoPrompt will gnerate a prompt and pass it to the Planner-Executor system"""
    def __init__(self, environment, challenge, prompter, backend, max_rounds=10):
        super().__init__(environment, challenge, prompter, backend)
        self.max_rounds = max_rounds
        self.autoprompt = None
        self.finished = False
        self.enabled = False
        self.add_start_prompts()

    def enable_autoprompt(self):
        self.enabled = True

    def run_one_round(self):
        response = self.backend.send(self.conversation.messages)
        if response.error is not None:
            raise AgentError(response.error)
            
        self.current_cost += response.cost
        self.add_assistant_message(response.content, response.tool_call)

        if not response.tool_call:
            self.add_user_message(self.continue_prompt())
            return

        parsed, parsed_call = self.backend.parse_tool_arguments(response.tool_call)
        if not parsed:
            # Print unparsed tool_call
            logger.assistant_action(response.tool_call.format())
            # Contains the ToolResult with error
            self.print_result(parsed_call)
            self.add_observation_message(parsed_call)
            return

        # Print parsed tool_call
        self.print_parsed_call(parsed_call)

        if parsed_call.name == GenAutoPromptTool.NAME:
            self.autoprompt = parsed_call.parsed_arguments.get("prompt", None)
            self.finished = True
        else:
            tool_result = self.environment.run_tool(parsed_call)
            self.print_result(tool_result)
            self.add_observation_message(tool_result)

    def run_for_autoprompt(self):
        """
        Prompt the autoprompted last time if it did not already generate a prompt
        """
        self.add_user_message(self.prompter.get("finish_autoprompt"))
        response = self.backend.send(self.conversation.messages)
        self.current_cost += response.cost

        if response.error is not None:
            # Return None if it still errors
            return
        if not response.tool_call:
            # Even if model did not call the tool, we can return any thought content generated.
            self.autoprompt = response.content
            return

        parsed, parsed_call = self.backend.parse_tool_arguments(response.tool_call)
        if not parsed:
            # Return unparsed call with content
            logger.assistant_action(response.tool_call.format())
            self.autoprompt = response.content + "\n\n" + response.tool_call.arguments
            return
        # Print parsed tool_call
        self.print_parsed_call(parsed_call)
        if parsed_call.name == GenAutoPromptTool.NAME:
            # Set the task summary
            self.autoprompt = parsed_call.parsed_arguments.get("prompt", None)
        # If any other tool is called, model still does not generate summary.


class CriticAgent(BaseAgent):
    """A lightweight reflection agent that suggests pivots when another agent starts looping."""
    def __init__(self, environment, challenge, prompter, backend):
        super().__init__(environment, challenge, prompter, backend)
        self.critiques = []

    def critique(self, scope, task_description, transcript):
        convo = Conversation()
        convo.append_system(self.prompter.get("system"))
        convo.append_user(self.prompter.get(
            "initial",
            scope=scope,
            task_description=task_description,
            transcript=json.dumps(transcript, indent=2),
        ))

        response = self.backend.send(convo.messages)
        if response.error is not None:
            logger.debug_message(f"Critic error: {response.error}")
            return None

        self.current_cost += response.cost
        critique = (response.content or "").strip()
        if not critique:
            return None

        self.critiques.append({
            "scope": scope,
            "task_description": task_description,
            "critique": critique,
        })
        return critique

class PlannerAgent(BaseAgent):
    """The Planner Agent of a multi-agent Planner-Executor system"""
    def __init__(self, environment, challenge, prompter, backend, max_rounds=30):
        super().__init__(environment, challenge, prompter, backend)
        self.max_rounds = max_rounds
        self.delegated_task = None
        self.delegation_history = []
        self.blocked_task_signatures = set()

    def run_one_round(self):
        response = self.backend.send(self.conversation.messages)
        if response.error is not None:
            raise AgentError(response.error)
            
        self.current_cost += response.cost
        self.add_assistant_message(response.content, response.tool_call)

        if not response.tool_call:
            self.add_user_message(self.continue_prompt())
            return

        parsed, parsed_call = self.backend.parse_tool_arguments(response.tool_call)
        if not parsed:
            # Print unparsed tool_call
            logger.assistant_action(response.tool_call.format())
            # Contains the ToolResult with error
            self.print_result(parsed_call)
            self.add_observation_message(parsed_call)
            return

        # Print parsed tool_call
        self.print_parsed_call(parsed_call)

        if parsed_call.name == DelegateTool.NAME:
            self.delegated_task = parsed_call
            # MultiAgent system is responsible to add observation to the conversation.
        else:
            tool_result = self.environment.run_tool(parsed_call)
            self.print_result(tool_result)
            self.add_observation_message(tool_result)

class ExecutorAgent(BaseAgent):
    """The Executor Agent of a multi-agent Planner-Executor system"""
    def __init__(self, environment, challenge, prompter, backend, max_rounds=30, len_observations=5):
        super().__init__(environment, challenge, prompter, backend)
        self.max_rounds = max_rounds
        self.conversation.len_observations = len_observations
        self.finished = False
        self.finish_summary = None
        self.error = None
        self.last_loop_round = -1
        self.stop_due_to_loop = False
        self.current_task = None

    def new(self):
        """Create new executor with same settings but new conversation"""
        return ExecutorAgent(self.environment, self.challenge, self.prompter,
                             self.backend, max_rounds=self.max_rounds,
                             len_observations=self.conversation.len_observations)

    def run_one_round(self):
        response = self.backend.send(self.conversation.messages)
        if response.error is not None:
            self.finished = True
            self.error = response.error
            # Do not set finish summary
            return

        self.current_cost += response.cost
        self.add_assistant_message(response.content, response.tool_call)

        if not response.tool_call:
            self.add_user_message(self.continue_prompt(task_description=self.current_task))
            return

        parsed, parsed_call = self.backend.parse_tool_arguments(response.tool_call)
        if not parsed:
            # Print unparsed tool_call
            logger.assistant_action(response.tool_call.format())
            # Contains the ToolResult with error
            self.print_result(parsed_call)
            self.add_observation_message(parsed_call)
            return
        # Print parsed tool_call
        self.print_parsed_call(parsed_call)

        if parsed_call.name == FinishTaskTool.NAME:
            self.finish_summary = parsed_call.parsed_arguments.get("summary", None)
            self.finished = True
            # Executor is done here.
        else:
            tool_result = self.environment.run_tool(parsed_call)
            self.print_result(tool_result)
            self.add_observation_message(tool_result)

    def run_for_finish_summary(self):
        """
        Prompt the executor last time to ask for task summary
        """
        self.add_user_message(self.prompter.get("finish_summary"))
        response = self.backend.send(self.conversation.messages)
        self.current_cost += response.cost

        if response.error is not None:
            # Return None if it still errors
            return
        if not response.tool_call:
            # Even if model did not call the tool, we can return any thought content generated.
            self.finish_summary = response.content
            return

        parsed, parsed_call = self.backend.parse_tool_arguments(response.tool_call)
        if not parsed:
            # Return unparsed call with content
            logger.assistant_action(response.tool_call.format())
            self.finish_summary = response.content + "\n\n" + response.tool_call.arguments
            return
        # Print parsed tool_call
        self.print_parsed_call(parsed_call)
        if parsed_call.name == FinishTaskTool.NAME:
            # Set the task summary
            self.finish_summary = parsed_call.parsed_arguments.get("summary", None)
        # If any other tool is called, model still does not generate summary.

class PlannerExecutorSystem:
    """Holds all the agents of the multi-agent system."""
    def __init__(self, environment, challenge, autoprompter, planner, executor, max_cost=1.0, logfile=None, critic=None):
        self.environment = environment
        self.challenge = challenge
        self.autoprompter = autoprompter
        self.planner = planner
        self.executor = executor
        self.critic = critic

        self.max_cost = max_cost
        self.logfile = logfile

        self.all_executors = []
        self.last_planner_loop_round = -1

    def __enter__(self):
        self.challenge.start_challenge_container()
        self.environment.setup()
        self.start_time = now()
        logger.start_progress()
        return self

    def __exit__(self, ex_type, ex_val, tb):
        self.environment.teardown(ex_type, ex_val, tb)
        self.challenge.stop_challenge_container()
        self.end_time = now()

        error = f"{ex_type.__name__}: {str(ex_val)}" if ex_type is not None else None
        self.dump_log(error=error)
        logger.stop_progress()

    def get_exit_reason(self):
        if self.environment.solved:
            return "solved"
        elif self.environment.giveup:
            return "giveup"
        elif self.total_cost() > self.max_cost:
            return "cost"
        elif self.planner.conversation.round > self.planner.max_rounds:
            return "planner_rounds"
        else:
            return "unknown"

    def dump_log(self, error=None):
        if self.logfile is None:
            return

        exit_reason = "error" if error is not None else self.get_exit_reason()
        cost = self.total_cost()
        with self.logfile.open("w") as lf:
            json.dump({
                "start_time": self.start_time,
                "end_time": self.end_time,
                "time_taken": (self.end_time - self.start_time),
                "autoprompter_model": None if not self.autoprompter.enabled else self.autoprompter.backend.model,
                "planner_model": self.planner.backend.model,
                "executor_model": self.executor.backend.model,
                "total_cost": cost,
                "success": self.environment.solved,
                "exit_reason": exit_reason,
                "error": error,
                "autoprompter": [] if not self.autoprompter.enabled else self.autoprompter.conversation.dump(),
                "planner": self.planner.conversation.dump(),
                "executors": [e.conversation.dump() for e in self.all_executors],
                "critic": [] if self.critic is None else self.critic.critiques,
                "executor_errors": [e.error for e in self.all_executors],
                "planner_loop_warnings": self.planner.loop_warnings,
                "executor_loop_warnings": [e.loop_warnings for e in self.all_executors],
                "flag_candidates": {
                    "planner": self.planner.flag_candidates,
                    "executors": [e.flag_candidates for e in self.all_executors],
                },
                "debug_log": logger.debug_log,
            }, lf, indent=2)
        if exit_reason == "solved":
            logger.print("[green bold]Challenge Solved![/green bold]", force=True, markup=True)
        else:
            logger.print("[red bold]Challenge Not Solved![/red bold]", force=True, markup=True)
        logger.print(f"exit: {exit_reason} cost: ${cost:.3f} planner-rounds: {self.planner.conversation.round} num-executors: {len(self.all_executors)}", force=True)

    def total_cost(self):
        cost = self.planner.current_cost + sum(e.current_cost for e in self.all_executors)
        if self.autoprompter != None:
            cost += self.autoprompter.current_cost
        if self.critic is not None:
            cost += self.critic.current_cost
        logger.progress_message(f"${cost:.3f} / ${self.max_cost:.3f}")
        return cost

    def run_autoprompter(self):
        """Run the autoprompter to set the autoprompt for planner"""
        # Assumes autoprompter is not None
        while not self.environment.solved and not self.autoprompter.finished \
                and self.autoprompter.conversation.round <= self.autoprompter.max_rounds \
                and self.total_cost() <= self.max_cost:
            self.autoprompter.conversation.next_round()
            self.autoprompter.run_one_round()

        if not self.environment.solved and self.total_cost() <= self.max_cost \
                and self.autoprompter.autoprompt is None:
            # Prompt last time for the autoprompt
            self.autoprompter.run_for_autoprompt()

    def run(self):
        # Use the hardcoded prompt if no autoprompter
        planner_initial = self.planner.prompter.get("initial")

        if self.autoprompter.enabled:
            # Run the autoprompter if provided
            self.run_autoprompter()
            if self.autoprompter.autoprompt is not None:
                # Only set if autoprompter successfully generates a prompt
                planner_initial = self.autoprompter.autoprompt
            elif not self.environment.solved:
                logger.print("WARNING! Autoprompter failed to generate a prompt, using the hardcoded one", force=True, style="dark_orange bold")

        logger.print("============= PLANNER ===============", style="bold")
        self.planner.add_system_message(self.planner.prompter.get("system"))
        self.planner.add_user_message(planner_initial)

        while not self.environment.solved and not self.environment.giveup and \
                self.planner.conversation.round <= self.planner.max_rounds and \
                self.total_cost() <= self.max_cost:
            self.planner.conversation.next_round()
            if self.planner.conversation.round != self.last_planner_loop_round and self.planner.detect_loop():
                if self.critic is not None:
                    critique = self.critic.critique(
                        scope="planner",
                        task_description="Plan the next delegation for the current challenge.",
                        transcript=self.planner.conversation.dump()[-8:],
                    )
                    if critique:
                        self.planner.add_user_message(f"Critic feedback: {critique}")
                self.planner.add_loop_warning(
                    "Loop control: your recent planner steps are repeating. "
                    "Do not re-delegate the same exploit direction without a new falsifiable fact. "
                    "Name the last concrete fact learned, the current blocker, and delegate a narrower task that can confirm or reject one specific hypothesis."
                )
                self.last_planner_loop_round = self.planner.conversation.round
            self.planner.run_one_round()

            if self.planner.delegated_task is not None:
                delegated_task = self.planner.delegated_task
                task_description = delegated_task.parsed_arguments.get("task", "")
                if self._is_blocked_task(task_description):
                    result = (
                        "Task blocked by loop control: this task family has already been delegated "
                        f"{PLANNER_REPEAT_TASK_LIMIT} times without meaningful progress. "
                        "Do not delegate the same approach again. Change strategy, gather a different kind of evidence, submit the flag if proven, or give up."
                    )
                else:
                    result = self.run_executor(delegated_task)
                # No need to print this
                tool_result = ToolResult(name=DelegateTool.NAME, id=delegated_task.id, result=result)
                self.planner.add_observation_message(tool_result)
                self._record_delegation(delegated_task, result)
                self.planner.delegated_task = None
            
    def run_executor(self, task):
        logger.print("============= EXECUTOR ==============", style="bold")
        executor = self.executor.new() # Create new executor with empty conversation
        self.all_executors.append(executor)

        # Add executor prompts
        task_description = task.parsed_arguments["task"]
        executor.current_task = task_description
        executor_task = task_description
        if self._is_repeated_task(task_description):
            executor_task = (
                f"{task_description}\n\n"
                "Loop control: this task is too similar to a previous failed delegation. "
                "Do not repeat the same workflow. First summarize what the previous attempt disproved, "
                "then gather one new decisive fact using a different diagnostic path."
            )
        executor.add_system_message(executor.prompter.get("system"))
        executor.add_user_message(executor.prompter.get("initial", task_description=executor_task))

        while not self.environment.solved and not executor.finished \
                and executor.conversation.round <= executor.max_rounds \
                and self.total_cost() <= self.max_cost:
            executor.conversation.next_round()
            if executor.conversation.round != executor.last_loop_round and executor.detect_loop():
                if self.critic is not None:
                    critique = self.critic.critique(
                        scope="executor",
                        task_description=task_description,
                        transcript=executor.conversation.dump()[-8:],
                    )
                    if critique:
                        executor.add_user_message(f"Critic feedback: {critique}")
                executor.add_loop_warning(
                    "Loop control: your recent steps are repeating without decisive evidence. "
                    "Do not rerun the same payload or same helper analysis. "
                    "Write one rejected hypothesis, one required fact, and then switch to a different verification method."
                )
                executor.last_loop_round = executor.conversation.round
                if executor.loop_warnings >= EXECUTOR_LOOP_WARNING_LIMIT:
                    executor.finished = True
                    executor.stop_due_to_loop = True
                    break
            executor.run_one_round()

        if not self.environment.solved and self.total_cost() <= self.max_cost \
                and executor.finish_summary is None:
            # Prompt last time for finish_summary
            executor.run_for_finish_summary()

        logger.print("============= EXECUTOR DONE =========", style="bold")
        if executor.finished and executor.finish_summary is not None:
            # Send the executor finish summary to the planner.
            return executor.finish_summary
        elif executor.error is not None:
            logger.print(f"Executor Error: {executor.error}", style="red bold")
            return self.executor.prompter.get("finish_error", error=executor.error)
        else:
            # Executor did not complete the task, send empty result
            return self.executor.prompter.get("finish_empty")

    def _task_signature(self, task_description):
        normalized = _normalize_text(task_description)
        return normalized[:400]

    def _record_delegation(self, task, result):
        task_description = task.parsed_arguments.get("task", "")
        task_signature = self._task_signature(task_description)
        meaningful_progress = self._has_meaningful_progress(result)
        self.planner.delegation_history.append({
            "task": task_description,
            "task_signature": task_signature,
            "result": result,
            "meaningful_progress": meaningful_progress,
        })
        if self._count_recent_failed_repeats(task_signature) >= PLANNER_REPEAT_TASK_LIMIT:
            self.planner.blocked_task_signatures.add(task_signature)

    def _is_repeated_task(self, task_description):
        signature = self._task_signature(task_description)
        for previous in reversed(self.planner.delegation_history[-3:]):
            if _similarity(signature, previous["task_signature"]) >= 0.82:
                return True
        return False

    def _is_blocked_task(self, task_description):
        signature = self._task_signature(task_description)
        if signature in self.planner.blocked_task_signatures:
            return True
        return self._count_recent_failed_repeats(signature) >= PLANNER_REPEAT_TASK_LIMIT

    def _count_recent_failed_repeats(self, signature):
        count = 0
        for previous in reversed(self.planner.delegation_history):
            if _similarity(signature, previous["task_signature"]) < 0.82:
                continue
            if previous.get("meaningful_progress"):
                break
            count += 1
            if count >= PLANNER_REPEAT_TASK_LIMIT:
                break
        return count

    def _has_meaningful_progress(self, result):
        text = _normalize_text(str(result))
        if not text or text in {"none", "{}", "[]"}:
            return False
        negative_markers = [
            "task blocked by loop control",
            "executor error",
            "no progress",
            "no new",
            "same workflow",
            "still failed",
            "still need",
            "could not",
            "unable to",
            "not enough",
            "no marker",
            "no output",
            "finish_empty",
        ]
        if any(marker in text for marker in negative_markers):
            return False
        return len(text) >= 80

