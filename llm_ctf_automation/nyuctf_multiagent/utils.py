from pathlib import Path
from datetime import datetime
from .config import Config
import getpass
from nyuctf_multiagent.backends import MODELS

class APIKeys(dict):
    """Loads and holds API keys"""
    def __init__(self, key_cfg):
        keys = Path(key_cfg).open("r")
        for line in keys:
            if line.startswith("#"):
                continue
            tag, k = line.strip().split("=")
            self[tag] = k

def load_common_options(parser):
    parser.add_argument("--challenge", required=True, help="Name of the challenge")
    parser.add_argument("--dataset", help="Dataset JSON path. Only provide if not using the NYUCTF dataset at default path")
    parser.add_argument("-n", "--experiment-name", default="default", type=str, help="Experiment name (creates subdir in logdir)")
    parser.add_argument("-s", "--split", default="development", choices=["test", "development"], help="Dataset split to select. Only used when --dataset not provided.")
    parser.add_argument("--keys", default="keys.cfg", help="Path to keys.cfg file for loading API keys")
    parser.add_argument("--openai-base-url", default=None, help="Override the OpenAI-compatible API base URL, e.g. http://127.0.0.1:8000/v1")
    parser.add_argument("--openai-api-key", default=None, help="Override the OpenAI API key. For local compatible endpoints you can pass a dummy value.")
    parser.add_argument("--verbose-reasoning", default=False, action="store_true",
                        help="Ask planner/executor prompts to emit short visible reasoning before each tool step. Off by default to keep benchmark prompts unchanged.")
    parser.add_argument("--enable-critic", default=False, action="store_true",
                        help="Enable a lightweight critic agent that suggests pivots when planner or executor starts looping.")
    parser.add_argument("--critic-model", default=None,
                        help="Critic model to use (overrides config).")
    parser.add_argument("--tool-profile", default=None,
                        help="Optional named tool profile to append to the configured toolsets, e.g. extended_recon or pwn_extended.")

    parser.add_argument("--container-image", default="ctfenv:multiagent", help="Image tag of docker container")
    parser.add_argument("--container-network", default="ctfnet", help="Network name of docker container")

    # Logging options
    parser.add_argument("-d", "--debug", default=False, action="store_true", help="Print debug messages")
    parser.add_argument("-q", "--quiet", default=False, action="store_true", help="Do not print messages to console")
    parser.add_argument("--overwrite-existing", default=False, action="store_true", help="Overwrite existing log")
    parser.add_argument("--skip-existing", default=False, action="store_true", help="Skip if log exists")

def load_config(config_path: str, args) -> Config:
    # TODO this is specific to planner-executor, cleanup later
    config = Config(config_path=config_path)
    config.openai_base_url = getattr(args, "openai_base_url", None)
    config.openai_api_key = getattr(args, "openai_api_key", None)
    config.verbose_reasoning = getattr(args, "verbose_reasoning", False)
    if getattr(args, "planner_model", None):
        config.planner.model = args.planner_model
    if getattr(args, "executor_model", None):
        config.executor.model = args.executor_model
    if getattr(args, "autoprompter_model", None):
        config.autoprompter.model = args.autoprompter_model
    if getattr(args, "critic_model", None):
        config.critic.model = args.critic_model
    if getattr(args, "max_cost", 0) > 0:
        config.experiment.max_cost = args.max_cost

    allow_openai_compatible = bool(getattr(config, "openai_base_url", None))

    if config.planner.model not in MODELS and not allow_openai_compatible:
        raise KeyError(f"Model {config.planner.model} not in options. Select from {', '.join(MODELS.keys())}")
    if config.executor.model not in MODELS and not allow_openai_compatible:
        raise KeyError(f"Model {config.executor.model} not in options. Select from {', '.join(MODELS.keys())}")
    if config.autoprompter.model not in MODELS and not allow_openai_compatible:
        raise KeyError(f"Model {config.autoprompter.model} not in options. Select from {', '.join(MODELS.keys())}")
    if config.critic.model not in MODELS and not allow_openai_compatible:
        raise KeyError(f"Model {config.critic.model} not in options. Select from {', '.join(MODELS.keys())}")

    config.experiment.enable_autoprompt = True if getattr(args, "enable_autoprompt", False) else config.experiment.enable_autoprompt
    config.experiment.enable_critic = True if getattr(args, "enable_critic", False) else config.experiment.enable_critic

    tool_profile = getattr(args, "tool_profile", None)
    if tool_profile:
        profile_ref = f"profile:{tool_profile}"
        for agent_cfg in (config.planner, config.executor, config.autoprompter):
            if profile_ref not in agent_cfg.toolset:
                agent_cfg.toolset.append(profile_ref)

    return config

def get_log_filename(args, challenge):
    chalname = challenge.canonical_name
    logdir = Path(args.logdir) / getpass.getuser() / args.experiment_name
    logdir.mkdir(parents=True, exist_ok=True)

    if args.overwrite_existing or args.skip_existing:
        # Keep consistent name if overwriting same or skipping
        return logdir / f"{chalname}.json"
    else:
        # Append datetime to make unique name
        now = datetime.now().strftime("%y%m%d%H%M%S")
        return logdir / f"{chalname}-{now}.json"

class AgentError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
