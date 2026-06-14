import subprocess

from ..logging import logger
from .tool import Tool


class InspectChallengeFilesTool(Tool):
    NAME = "inspect_challenge_files"
    DESCRIPTION = "Inspect challenge files in the container with file metadata, hashes, and a shallow directory tree for fast initial recon."
    PARAMETERS = {
        "path": ("string", "directory or file path to inspect, default /home/ctfplayer/ctf_files"),
        "max_depth": ("number", "max directory depth to list, default 2"),
    }
    REQUIRED_PARAMETERS = set()

    def __init__(self, environment):
        super().__init__()
        self.environment = environment

    def call(self, path="/home/ctfplayer/ctf_files", max_depth=2):
        script = f"""
set -eu
target="{path}"
depth="{int(max_depth)}"
echo "== pwd =="
pwd
echo
echo "== listing =="
find "$target" -maxdepth "$depth" -mindepth 0 -printf "%y %p\\n" 2>/dev/null | sort
echo
echo "== file info =="
find "$target" -maxdepth "$depth" -type f -print0 2>/dev/null | xargs -0 -r file
echo
echo "== sha256 =="
find "$target" -maxdepth "$depth" -type f -print0 2>/dev/null | xargs -0 -r sha256sum
"""
        p = subprocess.run(
            ["docker", "exec", self.environment.container, "bash", "-lc", script],
            capture_output=True,
            text=True,
        )
        return {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode}

    def print_tool_call(self, tool_call):
        path = tool_call.parsed_arguments.get("path", "/home/ctfplayer/ctf_files")
        logger.assistant_action(f"**{self.NAME}** `{path}`")


class SearchFilesTool(Tool):
    NAME = "search_files"
    DESCRIPTION = "Search text across challenge files with ripgrep when available and grep as fallback."
    PARAMETERS = {
        "pattern": ("string", "regular expression or string to search for"),
        "path": ("string", "directory or file path to search, default /home/ctfplayer/ctf_files"),
    }
    REQUIRED_PARAMETERS = {"pattern"}

    def __init__(self, environment):
        super().__init__()
        self.environment = environment

    def call(self, pattern=None, path="/home/ctfplayer/ctf_files"):
        if pattern is None:
            return {"error": "No pattern provided"}
        script = f"""
set -eu
if command -v rg >/dev/null 2>&1; then
  rg -n --hidden --glob '!*.pyc' --glob '!*.o' --glob '!*.a' --glob '!*.so' "{pattern}" "{path}"
else
  grep -RIn --binary-files=without-match --exclude='*.pyc' --exclude='*.o' --exclude='*.a' --exclude='*.so' "{pattern}" "{path}"
fi
"""
        p = subprocess.run(
            ["docker", "exec", self.environment.container, "bash", "-lc", script],
            capture_output=True,
            text=True,
        )
        return {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode}

    def print_tool_call(self, tool_call):
        pattern = tool_call.parsed_arguments["pattern"]
        logger.assistant_action(f"**{self.NAME}** `{pattern}`")


class CheckRemoteTool(Tool):
    NAME = "check_remote"
    DESCRIPTION = "Perform a quick connectivity check to a remote TCP or HTTP service before spending rounds on exploitation."
    PARAMETERS = {
        "host": ("string", "remote host name or IP address"),
        "port": ("number", "remote port"),
        "scheme": ("string", "tcp or http, default tcp"),
    }
    REQUIRED_PARAMETERS = {"host", "port"}

    def __init__(self, environment):
        super().__init__()
        self.environment = environment

    def call(self, host=None, port=None, scheme="tcp"):
        if host is None or port is None:
            return {"error": "host and port are required"}
        port = int(port)
        scheme = (scheme or "tcp").lower()
        if scheme == "http":
            command = f"curl -I -sS --max-time 8 http://{host}:{port}/"
        else:
            command = f"nc -vz -w 5 {host} {port}"
        p = subprocess.run(
            ["docker", "exec", self.environment.container, "bash", "-lc", command],
            capture_output=True,
            text=True,
        )
        return {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode}

    def print_tool_call(self, tool_call):
        host = tool_call.parsed_arguments["host"]
        port = int(tool_call.parsed_arguments["port"])
        scheme = tool_call.parsed_arguments.get("scheme", "tcp")
        logger.assistant_action(f"**{self.NAME}** `{scheme}://{host}:{port}`")
