import subprocess
import json
import re
import tempfile
import os
from pathlib import Path
from typing_extensions import Annotated

from .modules import Tool, CTFCategories
from ..ctflogging import status

SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
GHIDRA_TIMEOUT_SECONDS = 90

def _find_ghidra():
    candidates = [
        SCRIPT_DIR / "ghidra_11.0.1_PUBLIC/support",
        SCRIPT_DIR / "docker/baseline/ghidra_11.0.1_PUBLIC/support",
    ]
    executable = "analyzeHeadless.bat" if os.name == "nt" else "analyzeHeadless"
    fallback = "analyzeHeadless"
    for support_dir in candidates:
        preferred = support_dir / executable
        if preferred.exists():
            return preferred
        alt = support_dir / fallback
        if alt.exists():
            return alt
    return candidates[0] / executable

GHIDRA = _find_ghidra()

def _clean_process_output(text):
    if text is None:
        return ""
    if isinstance(text, bytes):
        return text.decode("utf-8", errors="replace").replace("\r\n", "\n")
    return str(text).replace("\r\n", "\n")

def _truncate_error(message, max_lines=8, max_chars=1200):
    lines = [line.rstrip() for line in message.splitlines() if line.strip()]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append("...truncated...")
    compact = "\n".join(lines)
    if len(compact) > max_chars:
        compact = compact[:max_chars].rstrip() + "\n...truncated..."
    return compact

def _format_ghidra_error(binary, stdout="", stderr="", returncode=None, timeout=None):
    details = []
    if timeout is not None:
        details.append(f"Ghidra timed out after {timeout}s")
    elif returncode is not None:
        details.append(f"Ghidra exited with code {returncode}")
    if stderr.strip():
        details.append(f"stderr:\n{stderr.strip()}")
    if stdout.strip():
        details.append(f"stdout:\n{stdout.strip()}")
    if not details:
        details.append("Unknown Ghidra failure")
    return f"Failed to run Ghidra for {binary}: {_truncate_error(chr(10).join(details))}"

class CommandExec(Tool):
    NAME = "run_command"
    def __init__(self, environment: "CTFEnvironment"):
        super().__init__()
        self.environment = environment

    @staticmethod
    def _clean(text):
        if text is None:
            return None
        return text.decode('utf-8', errors='backslashreplace').replace('\r\n', '\n')

    def run_cmd(self, command, timeout):
        """Run a command in the docker container and return
        {"stdout": stdout, "stderr": stderr, "returncode": returncode, "timed_out": timed_out}
        """
        p = subprocess.Popen(
            ['docker', 'exec', self.environment.container, 'bash', '-c', command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            stdout, stderr = p.communicate(timeout=timeout)
            out = self._clean(stdout)
            err = self._clean(stderr)
            return {"stdout": out, "stderr": err, "returncode": p.returncode, "timed_out": False}
        except subprocess.TimeoutExpired as e:
            p.kill()
            stdout, stderr = p.communicate(timeout=timeout)     
            out = self._clean(stdout)
            err = self._clean(stderr) 
            # out = self._clean(e.stdout)
            # err = self._clean(e.stderr)
            return {"stdout": out, "stderr": err, "returncode": None, "timed_out": True}
        except subprocess.CalledProcessError as e:
            out = self._clean(e.stdout)
            err = self._clean(e.stderr)
            return {"stdout": out, "stderr": err, "returncode": e.returncode, "timed_out": False}

    def __call__(self, command: Annotated[str, "the command to run"],
                       timeout: Annotated[float, "the maximum number of seconds to run the command"] = 10.0):
        """Execute a command in an Ubuntu container (persistent across calls)"""
        if command is None:
            return {"error": "No command provided"}
        return self.run_cmd(command, timeout)

class CheckFlag(Tool):
    NAME = "check_flag"
    def __init__(self, environment: "CTFEnvironment"):
        super().__init__()
        self.environment = environment
        self.real_flag = environment.challenge.flag

    def __call__(self, flag: Annotated[str,"the flag to check"]):
        """Check if a flag is correct."""
        if flag is None:
            return {"error": "No flag provided"}
        status.print(f"Checking flag:")
        status.print(f"  Provided: [blue]{flag}[/blue]", markup=True)
        status.print(f"    Actual: [green]{self.real_flag}[/green]", markup=True)
        if flag == self.real_flag:
            status.print(f"[red bold]Correct flag![/red bold]", markup=True)
            self.environment.solved = True
            return {"correct": True}
        else:
            status.print(f"[red bold]Incorrect flag.[/red bold]", markup=True)
            return {"correct": False}

class CreateFile(Tool):
    NAME = "createfile"
    def __init__(self, environment: "CTFEnvironment"):
        super().__init__()
        self.environment = environment

    def __call__(self,
                 path: Annotated[str,"path where the file should be created; relative paths will be relative to /home/ctfplayer/"],
                 contents: Annotated[str,"contents of the file"],
                 decode_escapes: Annotated[bool,"whether to decode escape sequences in the contents"] = False):
        """Create a file in the container with the given contents"""
        if path is None:
            return {"error": "No path provided"}
        if contents is None:
            return {"error": "No contents provided"}
        if decode_escapes is None:
            decode_escapes = False
        return self.createfile(path, contents)

    @staticmethod
    def _expanduser(path, home):
        """Expand ~ and ~user constructs in the given path"""
        strpath = str(path)
        if strpath.startswith('~'):
            strpath = strpath.replace('~', str(home), 1)
        return Path(strpath)

    def createfile(self, path, contents, decode_escapes=False):
        if decode_escapes:
            # Decode escape sequences to get a bytes object
            try:
                contents = bytes(contents, 'utf-8').decode('unicode_escape').encode('latin-1')
            except UnicodeDecodeError as e:
                return {"error": f"Invalid escape sequence in contents: {e}"}
        else:
            contents = contents.encode()
        path = Path(self._expanduser(path, self.environment.container_home))
        if not path.is_absolute():
            path = self.environment.container_home / path
        with tempfile.NamedTemporaryFile(mode="wb") as f:
            f.write(contents)
            f.flush()
            try:
                path = self.environment.copy_into_container(f.name, path)
                return {"success": True, "path": str(path)}
            except subprocess.CalledProcessError as e:
                return {"error": f"Error copying file into container: {e.stderr.decode('utf-8', errors='backslashreplace')}"}

class GiveUp(Tool):
    NAME = "give_up"
    def __init__(self, environment: "CTFEnvironment"):
        super().__init__()
        self.environment = environment

    def __call__(self, confirm: Annotated[bool,"a boolean flag to confirm that you want to give up"]):
        """Give up on the challenge"""
        if not confirm:
            return {"error": "You must confirm that you want to give up"}
        self.environment.giveup = True
        return {"success": True}

class Decompile(Tool):
    NAME = "decompile_function"
    CATEGORIES = {CTFCategories.rev, CTFCategories.pwn, CTFCategories.crypto}
    def __init__(self, environment: "CTFEnvironment"):
        super().__init__()
        self.environment = environment
        self.challenge = self.environment.challenge
        self._decomp_cache = {}
        self._last_ghidra_error = None

    def __call__(self,
                 path: Annotated[str,"path to the binary to decompile"],
                 function: Annotated[str,"the function to decompile"] = 'main'):
        """Decompile a function from a binary using Ghidra."""
        if path is None:
            return {"error": "No binary provided"}
        if function is None:
            function = "main"
        return self.decompile(path, function)

    def find_function(self, dis, function):
        if function in dis["functions"]:
            return dis["functions"][function]
        # Looking for main entry point, so try other names also
        if function == "main":
            if "_start" in dis["functions"]:
                return dis["functions"]["_start"]
            if "invoke_main" in dis["functions"]:
                return dis["functions"]["invoke_main"]
        # Check if requesting radare2 unnamed function with address
        if re.match(r"fcn\.[0-9a-f]+$", function):
            addr = function[4:]
            if addr in dis["addresses"]:
                return dis["functions"][dis["addresses"][addr]]
        # Nothing found
        return None

    def decompile(self, binary, function):
        # Look for the decompilation output in "decomp"
        basename = Path(binary).name
        if basename not in self._decomp_cache:
            decomp_output = SCRIPT_DIR / f"decomp/{self.challenge.category}/{self.challenge.challenge_dir.name}/{basename}.decomp.json"
            if decomp_output.exists():
                self._decomp_cache[basename] = json.loads(decomp_output.read_text())
            else:
                if not self.run_ghidra(basename, decomp_output):
                    return {"error": self._last_ghidra_error or f"Decompilation for {binary} not available"}
                self._decomp_cache[basename] = json.loads(decomp_output.read_text())

        if found := self.find_function(self._decomp_cache[basename], function):
            return {"decompilation": found}
        else:
            return {"error": f"Function {function} not found in {binary}"}

    def run_ghidra(self, binary, output):
        self._last_ghidra_error = None
        status.debug_message(f"Running Ghidra to decompile {binary}...")
        binary_paths = self.challenge.challenge_dir.glob(f'**/{binary}')
        real_binary = next(binary_paths, None)
        if not real_binary or not real_binary.exists():
            self._last_ghidra_error = f"Binary not found for Ghidra: {binary}"
            return False
        status.debug_message(f"Real binary path: {real_binary}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            cmd = [
                str(GHIDRA), str(tmpdir), "DummyProj",
                "-scriptpath", str(SCRIPT_DIR / "nyuctf_baseline/ghidra_scripts"),
                "-import", str(real_binary),
                "-postscript", "DecompileToJson.java", str(output)
            ]
            try:
                res = subprocess.run(
                    cmd,
                    check=False,
                    capture_output=True,
                    timeout=GHIDRA_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as e:
                stdout = _clean_process_output(e.stdout)
                stderr = _clean_process_output(e.stderr)
                self._last_ghidra_error = _format_ghidra_error(
                    binary, stdout=stdout, stderr=stderr, timeout=GHIDRA_TIMEOUT_SECONDS
                )
                status.debug_message(self._last_ghidra_error)
                return False
            stdout = _clean_process_output(res.stdout)
            stderr = _clean_process_output(res.stderr)
            if res.returncode != 0:
                self._last_ghidra_error = _format_ghidra_error(
                    binary, stdout=stdout, stderr=stderr, returncode=res.returncode
                )
                status.debug_message(self._last_ghidra_error)
                return False
            if not output.exists():
                self._last_ghidra_error = _format_ghidra_error(
                    binary, stdout=stdout, stderr=stderr, returncode=res.returncode
                )
                status.debug_message(self._last_ghidra_error)
                return False
            return output.exists()

class Disassemble(Tool):
    NAME = "disassemble_function"
    CATEGORIES = {CTFCategories.rev, CTFCategories.pwn, CTFCategories.crypto}
    def __init__(self, environment: "CTFEnvironment"):
        super().__init__()
        self.environment = environment
        self.challenge = self.environment.challenge
        self._disasm_cache = {}
        self._last_ghidra_error = None

    def __call__(self,
                 path: Annotated[str,"path to the binary to disassemble"],
                 function: Annotated[str,"the function to disassemble"] = 'main'):
        """Disassemble a function from a binary using Ghidra."""
        if function is None:
            function = "main"
        if path is None:
            return {"error": "No binary provided"}
        return self.disassemble(path, function)

    def find_function(self, dis, function):
        if function in dis["functions"]:
            return dis["functions"][function]
        # Looking for main entry point, so try other names also
        if function == "main":
            if "_start" in dis["functions"]:
                return dis["functions"]["_start"]
            if "invoke_main" in dis["functions"]:
                return dis["functions"]["invoke_main"]
        # Check if requesting radare2 unnamed function with address
        if re.match(r"fcn\.[0-9a-f]+$", function):
            addr = function[4:]
            if addr in dis["addresses"]:
                return dis["functions"][dis["addresses"][addr]]
        # Nothing found
        return None

    def disassemble(self, binary, function):
        # Look for the disassembly output in "decomp"
        basename = Path(binary).name
        disasm_output = SCRIPT_DIR / f"decomp/{self.challenge.category}/{self.challenge.challenge_dir.name}/{basename}.disas.json"

        if basename not in self._disasm_cache:
            if disasm_output.exists():
                self._disasm_cache[basename] = json.loads(disasm_output.read_text())
            else:
                if not self.run_ghidra(basename, disasm_output):
                    return {"error": self._last_ghidra_error or f"Disassembly for {binary} not available"}
                self._disasm_cache[basename] = json.loads(disasm_output.read_text())

        if found := self.find_function(self._disasm_cache[basename], function):
            return {"disassembly": found}
        else:
            return {"error": f"Function {function} not found in {binary}"}

    def run_ghidra(self, binary, output):
        self._last_ghidra_error = None
        status.debug_message(f"Running Ghidra to disassemble {binary}...")
        binary_paths = self.challenge.challenge_dir.glob(f'**/{binary}')
        real_binary = next(binary_paths, None)
        if not real_binary or not real_binary.exists():
            self._last_ghidra_error = f"Binary not found for Ghidra: {binary}"
            return False
        status.debug_message(f"Real binary path: {real_binary}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            cmd = [
                str(GHIDRA), str(tmpdir), "DummyProj",
                "-scriptpath", str(SCRIPT_DIR / "nyuctf_baseline/ghidra_scripts"),
                "-import", str(real_binary),
                "-postscript", "DisassembleToJson.java", str(output)
            ]
            try:
                res = subprocess.run(
                    cmd,
                    check=False,
                    capture_output=True,
                    timeout=GHIDRA_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as e:
                stdout = _clean_process_output(e.stdout)
                stderr = _clean_process_output(e.stderr)
                self._last_ghidra_error = _format_ghidra_error(
                    binary, stdout=stdout, stderr=stderr, timeout=GHIDRA_TIMEOUT_SECONDS
                )
                status.debug_message(self._last_ghidra_error)
                return False
            stdout = _clean_process_output(res.stdout)
            stderr = _clean_process_output(res.stderr)
            if res.returncode != 0:
                self._last_ghidra_error = _format_ghidra_error(
                    binary, stdout=stdout, stderr=stderr, returncode=res.returncode
                )
                status.debug_message(self._last_ghidra_error)
                return False
            if not output.exists():
                self._last_ghidra_error = _format_ghidra_error(
                    binary, stdout=stdout, stderr=stderr, returncode=res.returncode
                )
                status.debug_message(self._last_ghidra_error)
                return False
            return output.exists()
