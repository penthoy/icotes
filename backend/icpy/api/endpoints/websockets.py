"""
WebSocket endpoint handlers.

This module contains WebSocket endpoint implementations for real-time
communication with various services.
"""

import asyncio
import json
import logging
import time
import uuid

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

try:
    from icpy.services import get_agent_service, get_chat_service
    from icpy.api import get_websocket_api
    ICPY_AVAILABLE = True
except ImportError:
    logger.warning("icpy WebSocket services not available")
    ICPY_AVAILABLE = False
    get_agent_service = lambda: None
    get_chat_service = lambda: None
    get_websocket_api = lambda: None


async def agent_stream_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent output streaming."""
    if not ICPY_AVAILABLE:
        await websocket.close(code=1011, reason="icpy services not available")
        return
    
    try:
        await websocket.accept()
        
        # Get agent service
        agent_service = await get_agent_service()
        
        # Verify agent session exists
        session = agent_service.get_agent_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Agent session not found")
            return
        
        # Connect to message broker for agent stream events
        websocket_api = await get_websocket_api()
        connection_id = await websocket_api.connect_websocket(websocket)
        
        # Subscribe to agent stream topic
        # Lazy import to avoid startup errors when messaging is unavailable
        from icpy.core.message_broker import get_message_broker
        message_broker = await get_message_broker()
        await message_broker.subscribe(f"agent.{session_id}.stream", 
                                     lambda msg: websocket_api.send_to_connection(connection_id, msg.payload))
        
        # Send initial session info
        await websocket.send_json({
            "type": "agent_session_info",
            "session": session.to_dict()
        })
        
        # Keep connection alive
        while True:
            try:
                # Wait for ping/pong or other control messages
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "get_status":
                    # Send current session status
                    updated_session = agent_service.get_agent_session(session_id)
                    if updated_session:
                        await websocket.send_json({
                            "type": "agent_status",
                            "session": updated_session.to_dict()
                        })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Agent stream WebSocket error: {e}")
                break
        
        # Cleanup
        await websocket_api.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"Agent stream WebSocket initialization error: {e}")
        await websocket.close(code=1011, reason="Internal server error")


async def workflow_monitor_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time workflow monitoring."""
    if not ICPY_AVAILABLE:
        await websocket.close(code=1011, reason="icpy services not available")
        return
    
    try:
        await websocket.accept()
        
        # Get agent service
        agent_service = await get_agent_service()
        
        # Verify workflow session exists
        session = agent_service.get_workflow_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Workflow session not found")
            return
        
        # Connect to message broker for workflow events
        websocket_api = await get_websocket_api()
        connection_id = await websocket_api.connect_websocket(websocket)
        
        # Subscribe to workflow events
        # Lazy import to avoid startup errors when messaging is unavailable
        from icpy.core.message_broker import get_message_broker
        message_broker = await get_message_broker()
        await message_broker.subscribe(f"workflow.{session_id}.*", 
                                     lambda msg: websocket_api.send_to_connection(connection_id, msg.payload))
        
        # Send initial session info
        await websocket.send_json({
            "type": "workflow_session_info",
            "session": session.to_dict()
        })
        
        # Keep connection alive and handle control messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "get_status":
                    # Send current workflow status
                    updated_session = agent_service.get_workflow_session(session_id)
                    if updated_session:
                        await websocket.send_json({
                            "type": "workflow_status",
                            "session": updated_session.to_dict()
                        })
                elif data.get("type") == "control":
                    # Handle workflow control commands
                    action = data.get("action")
                    if action == "pause":
                        await agent_service.pause_workflow(session_id)
                    elif action == "resume":
                        await agent_service.resume_workflow(session_id)
                    elif action == "cancel":
                        await agent_service.cancel_workflow(session_id)
                    
                    # Send updated status
                    updated_session = agent_service.get_workflow_session(session_id)
                    if updated_session:
                        await websocket.send_json({
                            "type": "workflow_status",
                            "session": updated_session.to_dict()
                        })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Workflow monitor WebSocket error: {e}")
                break
        
        # Cleanup
        await websocket_api.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"Workflow monitor WebSocket initialization error: {e}")
        await websocket.close(code=1011, reason="Internal server error")


async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with AI agents."""
    if not ICPY_AVAILABLE:
        await websocket.close(code=1011, reason="icpy services not available")
        return
    
    connection_id = None
    
    try:
        await websocket.accept()
        
        # Get chat service
        chat_service = get_chat_service()
        
        # Generate connection ID for this chat session
        connection_id = str(uuid.uuid4())
        
        # Store the WebSocket in chat service for this connection
        chat_service.websocket_connections[connection_id] = websocket
        
        # Connect to chat service
        session_id = await chat_service.connect_websocket(connection_id)
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "timestamp": time.time()
        })
        
        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                message_type = data.get("type")
                
                if message_type == "message":
                    # Handle user message
                    content = data.get("content", "")
                    metadata = data.get("metadata", {})
                    
                    if content.strip():
                        await chat_service.handle_user_message(
                            connection_id, 
                            content, 
                            metadata
                        )
                
                elif message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": time.time()
                    })
                
                elif message_type == "get_status":
                    # Send current agent status
                    status = await chat_service.get_agent_status()
                    await websocket.send_json({
                        "type": "status",
                        "agent": status.to_dict(),
                        "timestamp": time.time()
                    })
                
                elif message_type == "get_config":
                    # Send current chat configuration
                    await websocket.send_json({
                        "type": "config",
                        "config": chat_service.config.to_dict(),
                        "timestamp": time.time()
                    })
                
                elif message_type == "update_config":
                    # Update chat configuration
                    config_updates = data.get("config", {})
                    await chat_service.update_config(config_updates)
                    
                    await websocket.send_json({
                        "type": "config_updated",
                        "config": chat_service.config.to_dict(),
                        "timestamp": time.time()
                    })
                
                elif message_type == "stop":
                    # Stop/interrupt current streaming response
                    # Derive session_id from the connection mapping; don't trust client override
                    mapped_session_id = chat_service.chat_sessions.get(connection_id)
                    requested_session_id = data.get("session_id")
                    if mapped_session_id and requested_session_id and requested_session_id != mapped_session_id:
                        logger.warning(
                            f"Stop requested with mismatched session_id "
                            f"(requested={requested_session_id}, mapped={mapped_session_id}); ignoring client override."
                        )
                    session_id_to_stop = mapped_session_id or requested_session_id
                    if not session_id_to_stop:
                        await websocket.send_json({
                            "type": "stop_response",
                            "success": False,
                            "error": "no_session_for_connection",
                            "timestamp": time.time()
                        })
                        continue

                    success = await chat_service.stop_streaming(session_id_to_stop)
                    
                    await websocket.send_json({
                        "type": "stop_response",
                        "success": success,
                        "session_id": session_id_to_stop,
                        "timestamp": time.time()
                    })
                
                else:
                    logger.warning(f"Unknown chat message type: {message_type}")
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.error("Invalid JSON received in chat WebSocket")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Chat WebSocket message error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": time.time()
                })
        
        # Cleanup
        if connection_id:
            # Remove WebSocket from chat service
            chat_service.websocket_connections.pop(connection_id, None)
            await chat_service.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"Chat WebSocket initialization error: {e}")
        if connection_id:
            chat_service.websocket_connections.pop(connection_id, None)
        await websocket.close(code=1011, reason="Internal server error")