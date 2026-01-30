"""
Agent tools package
"""

from .base_tool import BaseTool, ToolResult
from .tool_registry import ToolRegistry, get_tool_registry
from .read_file_tool import ReadFileTool
from .create_file_tool import CreateFileTool
from .replace_string_tool import ReplaceStringTool
from .run_terminal_tool import RunTerminalTool
from .semantic_search_tool import SemanticSearchTool
from .websearch_tools import WebSearchTool
from .imagen_tool import ImagenTool
from .web_fetch_tool import WebFetchTool
from .read_doc_tool import ReadDocTool
from .write_doc_tool import WriteDocTool
from .elevenlabs_tts_tool import ElevenLabsTTSTool
from .elevenlabs_stt_tool import ElevenLabsSTTTool
from .elevenlabs_music_tool import ElevenLabsMusicTool
from .elevenlabs_sfx_tool import ElevenLabsSoundEffectsTool
from .atlascloud.ttv_tool import AtlasCloudTextToVideoTool
from .atlascloud.itv_tool import AtlasCloudImageToVideoTool
from .atlascloud.v2v_sound_tool import AtlasCloudVideoToVideoSoundTool

__all__ = [
    "BaseTool",
    "ToolResult", 
    "ToolRegistry",
    "get_tool_registry",
    "ReadFileTool",
    "CreateFileTool", 
    "ReplaceStringTool",
    "RunTerminalTool",
    "SemanticSearchTool",
    "WebSearchTool",
    "ImagenTool",
    "WebFetchTool",
    "ReadDocTool",
    "WriteDocTool",
    "ElevenLabsTTSTool",
    "ElevenLabsSTTTool",
    "ElevenLabsMusicTool",
    "ElevenLabsSoundEffectsTool",
    "AtlasCloudTextToVideoTool",
    "AtlasCloudImageToVideoTool",
    "AtlasCloudVideoToVideoSoundTool",
]

# Auto-register all tools when module is imported
def _register_default_tools():
    """
    Register the package's predefined tool instances with the global tool registry.
    
    This makes the module's default tools available for discovery and use by registering them with the global ToolRegistry.
    """
    registry = get_tool_registry()
    
    # Register each tool
    registry.register(ReadFileTool())
    registry.register(CreateFileTool())
    registry.register(ReplaceStringTool())
    registry.register(RunTerminalTool())
    registry.register(SemanticSearchTool())
    registry.register(WebSearchTool())
    registry.register(ImagenTool())
    registry.register(WebFetchTool())
    registry.register(ReadDocTool())
    registry.register(WriteDocTool())
    registry.register(ElevenLabsTTSTool())
    registry.register(ElevenLabsSTTTool())
    registry.register(ElevenLabsMusicTool())
    registry.register(ElevenLabsSoundEffectsTool())
    registry.register(AtlasCloudTextToVideoTool())
    registry.register(AtlasCloudImageToVideoTool())
    registry.register(AtlasCloudVideoToVideoSoundTool())

# Register tools on import
_register_default_tools() 