import yaml
from dataclasses import dataclass

@dataclass
class ExperimentConfig:
    max_cost: float
    enable_autoprompt: bool
    enable_critic: bool

@dataclass
class AgentConfig:
    max_rounds: int
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    prompt: str
    toolset: list
    strict: bool
    len_observations: int = None

class Config:
    def __init__(self, config_path = None):
        self.config_yaml = {} if not config_path else yaml.safe_load(config_path.open("r"))
        self.experiment = ExperimentConfig(
            max_cost=self.config_yaml.get("experiment", {}).get("max_cost", 1.0),
            enable_autoprompt=self.config_yaml.get("experiment", {}).get("enable_autoprompt", True),
            enable_critic=self.config_yaml.get("experiment", {}).get("enable_critic", False),
        )

        self.planner = AgentConfig(
            max_rounds=self.config_yaml.get("planner", {}).get("max_rounds", 30),
            model=self.config_yaml.get("planner", {}).get("model", "gpt-4o-2024-11-20"),
            temperature=self.config_yaml.get("planner", {}).get("temperature", 0.95),
            top_p=self.config_yaml.get("planner", {}).get("top_p", 1.0),
            max_tokens=self.config_yaml.get("planner", {}).get("max_tokens", 4096),
            prompt=self.config_yaml.get("planner", {}).get("prompt", "prompt/base_planner_prompt.yaml"),
            toolset=self.config_yaml.get("planner", {}).get("toolset", ["run_command", "submit_flag", "giveup", "delegate"]),
            strict=self.config_yaml.get("planner", {}).get("strict", False)
        )

        self.executor = AgentConfig(
            max_rounds=self.config_yaml.get("executor", {}).get("max_rounds", 30),
            model=self.config_yaml.get("executor", {}).get("model", "gpt-4o-2024-11-20"),
            temperature=self.config_yaml.get("executor", {}).get("temperature", 0.95),
            top_p=self.config_yaml.get("executor", {}).get("top_p", 1.0),
            max_tokens=self.config_yaml.get("executor", {}).get("max_tokens", 4096),
            len_observations=self.config_yaml.get("executor", {}).get("len_observations", 5),
            prompt=self.config_yaml.get("executor", {}).get("prompt", "prompt/base_executor_prompt.yaml"),
            toolset=self.config_yaml.get("executor", {}).get("toolset", ["run_command", "finish_task", "disassemble", "decompile", "create_file"]),
            strict=self.config_yaml.get("executor", {}).get("strict", False)
        )

        self.autoprompter = AgentConfig(
            max_rounds=self.config_yaml.get("autoprompter", {}).get("max_rounds", 30),
            model=self.config_yaml.get("autoprompter", {}).get("model", "gpt-4o-2024-11-20"),
            temperature=self.config_yaml.get("autoprompter", {}).get("temperature", 0.95),
            top_p=self.config_yaml.get("autoprompter", {}).get("top_p", 1.0),
            max_tokens=self.config_yaml.get("autoprompter", {}).get("max_tokens", 4096),
            prompt=self.config_yaml.get("autoprompter", {}).get("prompt", "prompt/autoprompt_prompt.yaml"),
            toolset=self.config_yaml.get("autoprompter", {}).get("toolset", ["run_command", "generate_prompt"]),
            strict=self.config_yaml.get("autoprompter", {}).get("strict", False)
        )

        self.critic = AgentConfig(
            max_rounds=self.config_yaml.get("critic", {}).get("max_rounds", 1),
            model=self.config_yaml.get("critic", {}).get("model", self.config_yaml.get("executor", {}).get("model", "gpt-4o-2024-11-20")),
            temperature=self.config_yaml.get("critic", {}).get("temperature", 0.2),
            top_p=self.config_yaml.get("critic", {}).get("top_p", 1.0),
            max_tokens=self.config_yaml.get("critic", {}).get("max_tokens", 512),
            prompt=self.config_yaml.get("critic", {}).get("prompt", "prompts/critic_prompt.yaml"),
            toolset=self.config_yaml.get("critic", {}).get("toolset", []),
            strict=self.config_yaml.get("critic", {}).get("strict", False)
        )
