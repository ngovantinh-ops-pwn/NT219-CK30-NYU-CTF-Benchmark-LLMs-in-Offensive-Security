from .tool import Tool, ToolCall, ToolResult

# Tools
from .misc import SubmitFlagTool, GiveupTool, DelegateTool, FinishTaskTool, GenAutoPromptTool
from .run_command import RunCommandTool
from .editing import CreateFileTool
from .reversing import DisassembleTool, DecompileTool
from .helpers import InspectChallengeFilesTool, SearchFilesTool, CheckRemoteTool

ALLTOOLS = {RunCommandTool, SubmitFlagTool, GiveupTool, CreateFileTool, GenAutoPromptTool,
            DelegateTool, FinishTaskTool, DisassembleTool, DecompileTool,
            InspectChallengeFilesTool, SearchFilesTool, CheckRemoteTool}

TOOL_PROFILES = {
    "extended_recon": {
        InspectChallengeFilesTool.NAME,
        SearchFilesTool.NAME,
        CheckRemoteTool.NAME,
    },
    "pwn_extended": {
        InspectChallengeFilesTool.NAME,
        SearchFilesTool.NAME,
        CheckRemoteTool.NAME,
        DisassembleTool.NAME,
        DecompileTool.NAME,
    },
    "web_extended": {
        InspectChallengeFilesTool.NAME,
        SearchFilesTool.NAME,
        CheckRemoteTool.NAME,
    },
    "rev_extended": {
        InspectChallengeFilesTool.NAME,
        SearchFilesTool.NAME,
        DisassembleTool.NAME,
        DecompileTool.NAME,
    },
}

