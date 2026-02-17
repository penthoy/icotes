"""
Agent tools package

Lazy-loading tool registry to minimize memory footprint.
Tools are only imported and instantiated when the registry is first accessed.
"""

import threading

# Only import lightweight types, not heavyweight tool classes
from .base_tool import BaseTool, ToolResult
from .tool_registry import ToolRegistry, get_tool_registry as _get_raw_registry

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "get_tool_registry",
]

# Track whether tools have been registered (guarded by lock for thread safety)
_tools_registered = False
_tools_register_lock = threading.Lock()

def _register_default_tools_lazy():
    """Lazy-load and register all default tools with the registry.
    
    This function is called only when get_tool_registry() is first accessed,
    avoiding heavyweight imports until tools are actually needed.
    Uses double-checked locking to prevent duplicate registration under
    concurrent access.
    """
    global _tools_registered
    if _tools_registered:
        return
    with _tools_register_lock:
        if _tools_registered:
            return
        
        registry = _get_raw_registry()
        
        # Import and register tools lazily - only when this function is called
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
        from .youtube_download_tool import YouTubeDownloadTool
        from .ui_layout_tool import UILayoutTool
        
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
        registry.register(YouTubeDownloadTool())
        registry.register(UILayoutTool())
        
        _tools_registered = True


def get_tool_registry() -> ToolRegistry:
    """Get the tool registry, lazily loading tools on first access.
    
    This wrapper ensures tools are only imported when actually needed,
    significantly reducing memory footprint for tests and imports.
    """
    _register_default_tools_lazy()
    return _get_raw_registry() 