"""
Base tool interface for agent tools
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# Optional imports for namespace-aware helpers (lazy to avoid heavy deps at import time)
try:
    from icpy.services.context_router import get_context_router
    from icpy.services.path_utils import get_display_path_info
except Exception:  # pragma: no cover - tools may import in environments without backend wiring
    get_context_router = None  # type: ignore
    get_display_path_info = None  # type: ignore


@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Base class for all agent tools"""
    
    def __init__(self):
        """Initialize tool with required properties"""
        self.name: str = ""
        self.description: str = ""
        self.parameters: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

    # -----------------------------
    # Phase 4: Namespace path parsing helper
    # -----------------------------
    async def _parse_path_parameter(self, raw_path: str) -> Tuple[str, str]:
        """
        Parse a tool path parameter that may include a namespace prefix.

        Returns:
            (context_id, absolute_path)

        Notes:
            - If the backend context router is not available, fall back to
              treating the input as a local absolute path.
            - Windows drive-letter paths like C:/foo are treated as paths, not namespaces.
        """
        if not raw_path:
            return ("local", "/")
        try:
            if get_context_router is None:
                # Minimal normalization
                path = raw_path if raw_path.startswith('/') or (len(raw_path) >= 3 and raw_path[1:3] == ':/') else '/' + raw_path
                return ("local", path)
            router = await get_context_router()  # type: ignore[misc]
            ctx, abs_path = await router.parse_namespaced_path(raw_path)  # type: ignore[attr-defined]
            return (ctx, abs_path)
        except Exception:
            # Safe fallback
            path = raw_path if raw_path.startswith('/') or (len(raw_path) >= 3 and raw_path[1:3] == ':/') else '/' + raw_path
            return ("local", path)

    async def _format_path_info(self, path: str) -> Dict[str, Any]:
        """Return display path info dict for a given absolute or namespaced path.

        Falls back to a minimal structure when path_utils is unavailable.
        """
        try:
            if get_display_path_info is not None:
                return await get_display_path_info(path)  # type: ignore[misc]
        except Exception:
            pass
        # Minimal fallback
        abs_path = path if path.startswith('/') or (len(path) >= 3 and path[1:3] == ':/') else '/' + path
        return {
            "formatted_path": f"local:{abs_path}",
            "namespace": "local",
            "context_id": "local",
            "absolute_path": abs_path,
            "is_remote": False,
            "display_name": f"local:{abs_path}",
        }