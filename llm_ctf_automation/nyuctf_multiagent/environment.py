import subprocess
import json
from pathlib import Path, PurePosixPath
from nyuctf.challenge import CTFChallenge

from .tools import ToolCall, ToolResult, ALLTOOLS, TOOL_PROFILES
from .logging import logger

class CTFEnvironment:
    """Manages the docker env for the agent, and the challenge container."""
    def __init__(self, challenge: CTFChallenge, container_image: str, network: str, tool_profile: str | None=None):
        self.challenge = challenge
        self.container_image = container_image
        self.network = network
        self.tool_profile = tool_profile
        self.tools = {}
        for tool in ALLTOOLS:
            tool_instance = tool(self)
            self.tools[tool.NAME] = tool_instance

        # The SubmitFlagTool can set this to indicated if flag is found
        self.solved = False
        # The GiveupTool can set this to give up the challenge
        self.giveup = False

    def get_toolset(self, toolset):
        """Return a set of initialized tools"""
        requested = []
        if self.tool_profile:
            requested.append(f"profile:{self.tool_profile}")
        requested.extend(toolset)

        resolved = []
        for name in requested:
            if name.startswith("profile:"):
                profile_name = name.split(":", 1)[1]
                if profile_name not in TOOL_PROFILES:
                    raise KeyError(f"Unknown tool profile: {profile_name}. Available: {sorted(TOOL_PROFILES)}")
                resolved.extend(sorted(TOOL_PROFILES[profile_name]))
            else:
                resolved.append(name)

        unique_names = []
        for name in resolved:
            if name not in unique_names:
                unique_names.append(name)

        return {name: self.tools[name] for name in unique_names}

    def setup(self):
        self.start_docker()
        for tool in self.tools.values():
            tool.setup()
        # Copy files
        for file in self.challenge.files:
            hostpath = self.challenge.challenge_dir / file
            self.copy_into_container(hostpath, f"ctf_files/{file}")

    def teardown(self, exc_type, exc_value, traceback):
        # Tear down the tools first so they can clean up
        for tool in self.tools.values():
            tool.teardown(exc_type, exc_value, traceback)
        self.stop_docker()

    def start_docker(self):
        logger.print(f"Starting environment container {self.container_image}...", force=True)
        cmd = ["docker", "run", "-d", "--rm", 
               "--network", self.network, "--platform", "linux/amd64",
               self.container_image]
        output = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.container = output.stdout.strip()
        logger.debug_message(f"...started {self.container}")

    def copy_into_container(self, hostpath, filename):
        filename_posix = PurePosixPath(str(filename).replace("\\", "/"))
        if filename_posix.is_absolute():
            containerpath = filename_posix
        else:
            containerpath = self.container_home / filename_posix
            # Make parent path (only locals)
            cmd = ["docker", "exec", self.container, "mkdir", "-p", str(containerpath.parent)]
            mkdir_res = subprocess.run(cmd, capture_output=True, text=True)
            if mkdir_res.returncode != 0:
                raise RuntimeError(
                    f"Failed to create container directory {containerpath.parent}: "
                    f"{mkdir_res.stderr.strip() or mkdir_res.stdout.strip()}"
                )
        # Copy file
        logger.debug_message(f"Copying file {hostpath} into container {self.container} at {containerpath}")
        cmd = ["docker", "cp", "-aq", str(hostpath), f"{self.container}:{containerpath}"]
        cp_res = subprocess.run(cmd, capture_output=True, text=True)
        if cp_res.returncode != 0:
            raise RuntimeError(
                f"Failed to copy {hostpath} into container at {containerpath}: "
                f"{cp_res.stderr.strip() or cp_res.stdout.strip()}"
            )
        return containerpath

    def stop_docker(self):
        logger.print(f"Stopping environment container {self.container_image} {self.container}...", force=True)
        subprocess.run(["docker", "stop", self.container], check=True, capture_output=True)

    def run_tool(self, tool_call):
        # Should have been checked by backend if correct tool or not
        tool = self.tools[tool_call.name]
        res = tool.call(**tool_call.parsed_arguments)
        return ToolResult(name=tool_call.name, id=tool_call.id, result=res)

    @property
    def container_home(self):
        return PurePosixPath("/home/ctfplayer")

