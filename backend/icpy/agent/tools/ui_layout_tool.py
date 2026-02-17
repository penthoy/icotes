"""
UI Layout Agent Tool
Allows AI agents to manipulate the UI layout at runtime via WebSocket messages
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class UILayoutToolInput(BaseModel):
    """Input schema for UI layout operations"""
    action: str = Field(..., description="Action to perform: switch_layout, activate_panel, toggle_area, resize_area, add_panel, remove_panel, save_layout, get_layout, set_split")
    layout_name: Optional[str] = Field(None, description="Layout name for switch_layout or save_layout")
    panel_id: Optional[str] = Field(None, description="Panel ID for activate_panel or remove_panel")
    panel_type: Optional[str] = Field(None, description="Panel type for add_panel (explorer, editor, terminal, chat, etc.)")
    area_id: Optional[str] = Field(None, description="Area ID for actions (left, center, right, bottom, main)")
    visible: Optional[bool] = Field(None, description="Visibility for toggle_area")
    size: Optional[int] = Field(None, description="Size percentage for resize_area (0-100)")
    split_key: Optional[str] = Field(None, description="Split config key (mainHorizontalSplit, rightVerticalSplit, centerVerticalSplit)")
    percentage: Optional[int] = Field(None, description="Split percentage (0-100)")


async def _ui_layout_implementation(
    action: str,
    layout_name: Optional[str] = None,
    panel_id: Optional[str] = None,
    panel_type: Optional[str] = None,
    area_id: Optional[str] = None,
    visible: Optional[bool] = None,
    size: Optional[int] = None,
    split_key: Optional[str] = None,
    percentage: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    UI Layout control tool for agents.
    
    Available actions:
    - switch_layout(layout_name): Load a named YAML preset
    - activate_panel(area_id, panel_id): Switch to a specific panel tab
    - toggle_area(area_id, visible): Show/hide sidebar
    - resize_area(area_id, size): Change area percentage
    - add_panel(panel_type, area_id): Add a new panel
    - remove_panel(panel_id): Remove a panel
    - save_layout(layout_name): Save current layout as preset
    - get_layout(): Return current layout state to agent
    - set_split(split_key, percentage): Update split percentage
    
    Args:
        action: The layout action to perform
        layout_name: Name of layout for switch/save operations
        panel_id: ID of panel for activate/remove operations
        panel_type: Type of panel to add (explorer, editor, terminal, chat, etc.)
        area_id: Area ID (left, center, right, bottom, main)
        visible: Boolean for toggle_area
        size: Size percentage for resize_area
        split_key: Split configuration key
        percentage: Split percentage value
        
    Returns:
        Dict with success status and any relevant data
    """
    try:
        from icpy.gateway.api_gateway import get_api_gateway
        
        gateway = await get_api_gateway()
        
        # Validate action
        valid_actions = ['switch_layout', 'activate_panel', 'toggle_area', 'resize_area', 
                        'add_panel', 'remove_panel', 'save_layout', 'get_layout', 'set_split']
        
        if action not in valid_actions:
            return {
                'success': False,
                'error': f'Invalid action: {action}. Valid actions: {", ".join(valid_actions)}'
            }
        
        # Build WebSocket message based on action
        message_data: Dict[str, Any] = {}
        
        if action == 'switch_layout':
            if not layout_name:
                return {'success': False, 'error': 'layout_name required for switch_layout'}
            message_data = {'name': layout_name}
            ws_action = 'switch'
            
        elif action == 'activate_panel':
            if not area_id or not panel_id:
                return {'success': False, 'error': 'area_id and panel_id required for activate_panel'}
            message_data = {'areaId': area_id, 'panelId': panel_id}
            ws_action = 'activate_panel'
            
        elif action == 'toggle_area':
            if not area_id or visible is None:
                return {'success': False, 'error': 'area_id and visible required for toggle_area'}
            message_data = {'areaId': area_id, 'visible': visible}
            ws_action = 'toggle_area'
            
        elif action == 'resize_area':
            if not area_id or size is None:
                return {'success': False, 'error': 'area_id and size required for resize_area'}
            if not 0 <= size <= 100:
                return {'success': False, 'error': 'size must be between 0 and 100'}
            message_data = {'areaId': area_id, 'size': size}
            ws_action = 'resize_area'
            
        elif action == 'add_panel':
            if not panel_type or not area_id:
                return {'success': False, 'error': 'panel_type and area_id required for add_panel'}
            message_data = {'panelType': panel_type, 'areaId': area_id}
            ws_action = 'add_panel'
            
        elif action == 'remove_panel':
            if not panel_id:
                return {'success': False, 'error': 'panel_id required for remove_panel'}
            message_data = {'panelId': panel_id}
            ws_action = 'remove_panel'
            
        elif action == 'save_layout':
            if not layout_name:
                return {'success': False, 'error': 'layout_name required for save_layout'}
            message_data = {'name': layout_name}
            ws_action = 'save_layout'
            
        elif action == 'set_split':
            if not split_key or percentage is None:
                return {'success': False, 'error': 'split_key and percentage required for set_split'}
            if not 0 <= percentage <= 100:
                return {'success': False, 'error': 'percentage must be between 0 and 100'}
            message_data = {'splitKey': split_key, 'percentage': percentage}
            ws_action = 'set_split'
            
        elif action == 'get_layout':
            # This would need to query current state - for now return instruction
            return {
                'success': True,
                'message': 'Layout state is maintained on frontend. Use switch_layout to change layouts.',
                'available_layouts': ['H', 'IDE', 'mobile']
            }
        
        else:
            return {'success': False, 'error': f'Action {action} not implemented'}
        
        # Broadcast layout command to all connected WebSocket clients
        layout_message = {
            'type': 'layout',
            'action': ws_action,
            'data': message_data
        }
        
        import json
        message_str = json.dumps(layout_message)
        await gateway.broadcast_message(message_str)
        
        logger.info(f"[UI Layout Tool] Sent {action} command to frontend")
        
        return {
            'success': True,
            'action': action,
            'message': f'Layout command {action} sent to frontend',
            'data': message_data
        }
        
    except Exception as e:
        logger.error(f"[UI Layout Tool] Error executing {action}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Tool metadata for agent registration
UI_LAYOUT_TOOL_METADATA = {
    "name": "ui_layout",
    "description": """Control the IDE's user interface layout programmatically.
    
Available actions:
- switch_layout: Load a preset layout (H, IDE, mobile, or custom name)
- activate_panel: Activate a specific panel in an area
- toggle_area: Show or hide a sidebar area
- resize_area: Change the size of an area (0-100 percentage)
- add_panel: Add a new panel to an area
- remove_panel: Remove a panel
- save_layout: Save current layout as a named preset
- set_split: Update split pane percentage
- get_layout: Get available layouts

Examples:
- Switch to H layout: action='switch_layout', layout_name='H'
- Show chat panel: action='activate_panel', area_id='right', panel_id='chat'
- Hide left sidebar: action='toggle_area', area_id='left', visible=False
- Resize editor: action='resize_area', area_id='center', size=60
""",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["switch_layout", "activate_panel", "toggle_area", "resize_area", 
                        "add_panel", "remove_panel", "save_layout", "get_layout", "set_split"],
                "description": "The layout action to perform"
            },
            "layout_name": {
                "type": "string",
                "description": "Layout name (for switch_layout or save_layout)"
            },
            "panel_id": {
                "type": "string",
                "description": "Panel ID (for activate_panel or remove_panel)"
            },
            "panel_type": {
                "type": "string",
                "enum": ["explorer", "editor", "terminal", "chat", "chat-history", "git", "preview", "hop"],
                "description": "Panel type (for add_panel)"
            },
            "area_id": {
                "type": "string",
                "enum": ["left", "center", "right", "bottom", "main"],
                "description": "Area ID"
            },
            "visible": {
                "type": "boolean",
                "description": "Visibility (for toggle_area)"
            },
            "size": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Size percentage (for resize_area)"
            },
            "split_key": {
                "type": "string",
                "enum": ["mainHorizontalSplit", "mainVerticalSplit", "rightVerticalSplit", "centerVerticalSplit"],
                "description": "Split configuration key (for set_split)"
            },
            "percentage": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Split percentage (for set_split)"
            }
        },
        "required": ["action"]
    }
}


class UILayoutTool(BaseTool):
    """Tool for controlling UI layout from agents"""
    
    def __init__(self):
        super().__init__()
        self.name = "ui_layout"
        self.description = UI_LAYOUT_TOOL_METADATA["description"]
        self.parameters = UI_LAYOUT_TOOL_METADATA["parameters"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute UI layout control"""
        try:
            result = await _ui_layout_implementation(**kwargs)
            
            if result.get('success'):
                payload = dict(result)
                payload.pop('success', None)
                return ToolResult(success=True, data=payload)
            else:
                payload = dict(result)
                payload.pop('success', None)
                error = payload.pop('error', None) or 'Unknown error'
                return ToolResult(success=False, error=error, data=payload)
                
        except Exception as e:
            logger.error(f"UILayoutTool error: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )
