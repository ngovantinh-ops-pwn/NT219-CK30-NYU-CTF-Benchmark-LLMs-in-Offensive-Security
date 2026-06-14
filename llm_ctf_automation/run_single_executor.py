import argparse
import yaml
import sys
from pathlib import Path

from nyuctf.dataset import CTFDataset
from nyuctf.challenge import CTFChallenge

from nyuctf_multiagent.environment import CTFEnvironment
from nyuctf_multiagent.backends import MODELS, Role, resolve_backend_cls
from nyuctf_multiagent.prompting import PromptManager
from nyuctf_multiagent.agent import SingleAgent, AutoPromptAgent, CriticAgent
from nyuctf_multiagent.logging import logger
from nyuctf_multiagent.utils import APIKeys, load_common_options, get_log_filename, load_config
from nyuctf_multiagent.config import Config

parser = argparse.ArgumentParser(description="Multi-agent Planner-Executor LLM for CTF solving")

# Loads the dataset and container related common options into parser
load_common_options(parser)
parser.add_argument("--logdir", default="logs_single_executor", type=str, help="Log directory")
parser.add_argument("--config", default=None, help="YAML config for the planner-executor multiagent. If not provided, it picks one automatically based on challenge cateogory.")

# Config overriding options
parser.add_argument("--executor-model", default=None, help="Executor model to use (overrides config)")
parser.add_argument("--autoprompter-model", default=None, help="AutoPrompt model to use (overrides config)")
parser.add_argument("--max-cost", default=0.0, type=float, help="Max cost in $ (overrides config)")
parser.add_argument("--enable-autoprompt", action="store_true", help="Init prompt message auto generated, else use generic base prompt")

args = parser.parse_args()

logger.set(quiet=args.quiet, debug=args.debug)

if args.dataset is not None:
    dataset = CTFDataset(dataset_json=args.dataset)
else:
    dataset = CTFDataset(split=args.split)
challenge = CTFChallenge(dataset.get(args.challenge), dataset.basedir)
logfile = get_log_filename(args, challenge)

logger.print(f"Logging to {str(logfile)}", force=True)
if logfile.exists() and args.skip_existing:
    logger.print("Skipping as log file exists", force=True)
    exit(0)

keys = APIKeys(args.keys)
environment = CTFEnvironment(challenge, args.container_image, args.container_network, tool_profile=args.tool_profile)

if args.config:
    config_f = Path(args.config)
else:
    config_d = Path(sys.argv[0]).parent / "configs" / "single_executor"
    config_f = config_d / f"{challenge.category}_single_executor.yaml"

logger.print(f"Using config: {str(config_f)}", force=True)
config = load_config(config_f, args=args)

autoprompter_backend_cls = resolve_backend_cls(config.autoprompter.model, config)
autoprompter_backend = autoprompter_backend_cls(Role.AUTOPROMPTER, config.autoprompter.model,
                                      environment.get_toolset(config.autoprompter.toolset),
                                      keys.get(autoprompter_backend_cls.NAME.upper()), config)
autoprompter_prompter = PromptManager(config_f.parent / config.autoprompter.prompt, challenge, environment,
                                      verbose_reasoning=False)
autoprompter = AutoPromptAgent(environment, challenge, autoprompter_prompter,
                       autoprompter_backend, max_rounds=config.autoprompter.max_rounds)

if config.experiment.enable_autoprompt:
    autoprompter.enable_autoprompt()

critic = None
if config.experiment.enable_critic:
    critic_backend_cls = resolve_backend_cls(config.critic.model, config)
    critic_backend = critic_backend_cls(Role.CRITIC, config.critic.model,
                                        environment.get_toolset(config.critic.toolset),
                                        keys.get(critic_backend_cls.NAME.upper()), config)
    critic_prompter = PromptManager(config_f.parent / config.critic.prompt, challenge, environment,
                                    verbose_reasoning=False)
    critic = CriticAgent(environment, challenge, critic_prompter, critic_backend)

executor_backend_cls = resolve_backend_cls(config.executor.model, config)
executor_backend = executor_backend_cls(Role.EXECUTOR, config.executor.model,
                                        environment.get_toolset(config.executor.toolset),
                                        keys.get(executor_backend_cls.NAME.upper()), config)
executor_prompter = PromptManager(config_f.parent / config.executor.prompt, challenge, environment,
                                  verbose_reasoning=getattr(config, "verbose_reasoning", False))

with SingleAgent(environment, challenge, executor_prompter, executor_backend, autoprompter,
                 max_rounds=config.executor.max_rounds, max_cost=config.experiment.max_cost,
                 len_observations=config.executor.len_observations, logfile=logfile, critic=critic) as executor:
    executor.run()
