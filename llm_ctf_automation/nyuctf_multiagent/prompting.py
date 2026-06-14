import yaml
from pathlib import Path

class PromptManager:
    """Handles formatting of the prompts"""
    def __init__(self, promptyaml, challenge, environment, verbose_reasoning=False):
        
        self.promptyaml = Path(promptyaml)
        with open(self.promptyaml, "r") as c:
            self.templates = yaml.safe_load(c)
        self.challenge = challenge
        self.environment = environment
        self.verbose_reasoning = verbose_reasoning

        # FIXME need to hotplug server description
        if challenge.server_type == "web":
            self.server_description = self.get("web_server_description")
        elif challenge.server_type == "nc":
            self.server_description = self.get("nc_server_description")
        else:
            self.server_description = ""

    def get(self, key, **kwargs):
        # TODO check if templating done properly
        tmpl = self.templates.get(key, "")
        prompt = tmpl.format(challenge=self.challenge, environment=self.environment, 
                             prompter=self, **kwargs)
        prompt = self._append_contextual_guidance(prompt, key)
        if self.verbose_reasoning and self._should_append_reasoning(key):
            prompt = f"{prompt.rstrip()}\n\n{self._reasoning_suffix(key)}"
        return prompt

    def build_continue(self, agent, task_description=None):
        base = self.templates.get("continue", "").format(
            challenge=self.challenge,
            environment=self.environment,
            prompter=self,
            task_description=task_description or "",
        ).rstrip()

        guidance = self._dynamic_navigation_guidance(agent, task_description=task_description)
        if guidance:
            return f"{base}\n\n{guidance}"
        return base

    def _should_append_reasoning(self, key):
        if "autoprompt" in self.promptyaml.name:
            return False
        return key in {"system", "initial", "continue"}

    def _reasoning_suffix(self, key):
        if key == "system":
            return (
                "Before every tool call, briefly explain your current hypothesis, "
                "what you learned from the previous step, and why the next action is useful. "
                "Keep this visible reasoning concise: 1 to 3 short sentences."
            )
        if key == "initial":
            return (
                "Before each command, delegation, or tool use, first provide a short reasoning "
                "update that explains the exploit direction, vulnerability check, or plan adjustment. "
                "Make your workflow visible with concise step-by-step notes."
            )
        return (
            "Please explain your current reasoning in 1 to 3 short sentences, then proceed with the next action."
        )

    def _append_contextual_guidance(self, prompt, key):
        if key == "initial":
            suffix = self._initial_navigation_suffix()
            if suffix:
                return f"{prompt.rstrip()}\n\n{suffix}"
        return prompt

    def _initial_navigation_suffix(self):
        lines = [
            "Navigation strategy:",
            self._phase_strategy_line(),
        ]

        category_line = self._category_strategy_line()
        if category_line:
            lines.append(category_line)

        source_files = self._source_files()
        if source_files:
            lines.append(
                f"- Source-first hint: relevant source-like files exist ({', '.join(source_files[:4])}). "
                "If they are readable, prefer extracting ground-truth behavior from them before heavy reversing."
            )

        if self.challenge.server_type == "nc":
            lines.append(
                "- Remote-first caution: if the challenge has a remote service, verify connectivity once before spending many rounds on exploit retries."
            )
        elif self.challenge.server_type == "web":
            lines.append(
                "- Web-first caution: map routes, auth state, and trust boundaries before attempting deeper exploitation."
            )

        helper_line = self._helper_tool_line()
        if helper_line:
            lines.append(helper_line)

        return "\n".join(lines)

    def _phase_strategy_line(self):
        return (
            "- Work in phases: recon -> identify primitive -> verify one hypothesis with one decisive fact -> exploit or solve -> validate the flag."
        )

    def _category_strategy_line(self):
        category = self.challenge.category
        if category == "pwn":
            return (
                "- Pwn focus: establish binary properties, input surface, crash or control primitive, exact offset or argument control, then only move to local and remote payload construction."
            )
        if category == "rev":
            return (
                "- Rev focus: recover program logic first with strings, source, decompile, or disassembly, then reconstruct the check or transform before writing a solver."
            )
        if category == "web":
            return (
                "- Web focus: enumerate endpoints, parameters, sessions, roles, and response differences before choosing one exploit path."
            )
        if category == "crypto":
            return (
                "- Crypto focus: identify the algorithm family, leakage, malformed parameter, or oracle, then validate the mathematical weakness with a small script."
            )
        if category == "forensics":
            return (
                "- Forensics focus: choose a disciplined analysis chain, such as metadata -> extraction -> carving -> decoded artifact, instead of trying tools at random."
            )
        return ""

    def _helper_tool_line(self):
        tool_names = set(self.environment.tools.keys())
        helpful = [name for name in ("inspect_challenge_files", "search_files", "check_remote") if name in tool_names]
        if not helpful:
            return ""
        return f"- Helper tools available in this repo include: {', '.join(helpful)}."

    def _source_files(self):
        exts = {".c", ".cc", ".cpp", ".py", ".php", ".js", ".ts", ".java", ".go", ".rs", ".cs"}
        return [f for f in self.challenge.files if Path(f).suffix.lower() in exts]

    def _dynamic_navigation_guidance(self, agent, task_description=None):
        suggestions = []
        tool_names = set(agent.backend.tools.keys())
        transcript = agent.conversation.dump()
        recent = transcript[-8:]
        recent_text = "\n".join(str(item) for item in recent).lower()

        if not any(item.get("role") == "MessageRole.OBSERVATION" for item in transcript):
            suggestions.append(self._first_step_guidance(tool_names, task_description))

        if self._has_dns_or_remote_failure(recent_text):
            suggestions.append(
                "- Remote blocker detected: do not keep retrying the same remote command. Record that connectivity is failing, gather local evidence instead, and only retry remote after a materially different check."
            )

        if "ghidra" in recent_text and ("failed to run ghidra" in recent_text or "function" in recent_text and "not found" in recent_text):
            suggestions.append(
                "- Reversing tool pivot: decompile or disassemble did not give ground truth. Switch to source files, strings, file metadata, objdump, checksec, or symbol listing instead of repeating the same request."
            )

        if self.challenge.category == "pwn":
            pwn_hint = self._pwn_continue_hint(tool_names, recent_text)
            if pwn_hint:
                suggestions.append(pwn_hint)
        elif self.challenge.category == "web":
            suggestions.append(
                "- Choose one web hypothesis next: route discovery, auth bypass, input validation flaw, or session misuse. Gather one response difference that can confirm or reject it."
            )
        elif self.challenge.category == "crypto":
            suggestions.append(
                "- Choose one crypto hypothesis next: algorithm identification, parameter weakness, oracle behavior, or decoding step. Write a short script to test only that hypothesis."
            )
        elif self.challenge.category == "rev":
            suggestions.append(
                "- Choose one rev hypothesis next: where the flag is checked, transformed, or reconstructed. Prefer a small extract-and-test script over another broad scan."
            )
        elif self.challenge.category == "forensics":
            suggestions.append(
                "- Choose one forensic artifact path next: metadata, embedded file, stream, packet, or archive member. Do not branch into multiple carving directions at once."
            )

        if "no command" in recent_text or "no tool" in recent_text:
            suggestions.append(
                "- Do not think abstractly for another round. Pick one concrete tool call that can produce a new fact."
            )

        suggestions = [s for s in suggestions if s]
        unique = []
        for suggestion in suggestions:
            if suggestion not in unique:
                unique.append(suggestion)
        return "\n".join(unique[:4])

    def _first_step_guidance(self, tool_names, task_description=None):
        source_files = self._source_files()
        if source_files:
            return (
                f"- Early navigation: start with ground truth from source-like files ({', '.join(source_files[:3])}) or a shallow file inspection before complex exploitation."
            )
        if "inspect_challenge_files" in tool_names:
            return "- Early navigation: start with `inspect_challenge_files` to map the available artifacts and metadata."
        return "- Early navigation: start with one high-yield recon step such as listing files, checking binary or file type, or reading the most relevant artifact."

    def _pwn_continue_hint(self, tool_names, recent_text):
        if self.challenge.server_type == "nc" and "check_remote" in tool_names and "check_remote" not in recent_text:
            return "- Pwn navigation: verify remote reachability once before spending more rounds on payload retries."
        if self._source_files():
            return "- Pwn navigation: if source is available, derive the exact primitive and argument constraints from source before refining the payload."
        return "- Pwn navigation: pick exactly one next primitive to verify, such as control of RIP, exact offset, leak source, or required calling convention."

    def _has_dns_or_remote_failure(self, text):
        markers = [
            "could not resolve hostname",
            "name or service not known",
            "temporary failure in name resolution",
            "socket.gaierror",
            "connection refused",
            "failed to connect",
            "timed out",
        ]
        return any(marker in text for marker in markers)
