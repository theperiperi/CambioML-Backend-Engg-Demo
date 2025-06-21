import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from fastapi import WebSocket
import sys
import os

# Add the computer_use_demo path to sys.path to import the existing tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'computer_use_demo'))

from computer_use_demo.loop import sampling_loop, APIProvider
from computer_use_demo.tools import ToolResult, ToolVersion
from .session_manager import SessionManager
from .models import WebSocketMessage, ProcessingStatus

class ComputerLoopManager:
    def __init__(self):
        self._active_websockets: Dict[str, List[WebSocket]] = {}
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def register_websocket(self, session_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a session"""
        async with self._lock:
            if session_id not in self._active_websockets:
                self._active_websockets[session_id] = []
            self._active_websockets[session_id].append(websocket)
    
    async def unregister_websocket(self, session_id: str, websocket: WebSocket):
        """Unregister a WebSocket connection"""
        async with self._lock:
            if session_id in self._active_websockets:
                try:
                    self._active_websockets[session_id].remove(websocket)
                    if not self._active_websockets[session_id]:
                        del self._active_websockets[session_id]
                except ValueError:
                    pass  # WebSocket already removed
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast a message to all WebSocket connections for a session"""
        async with self._lock:
            websockets = self._active_websockets.get(session_id, [])
        
        # Send to all connected WebSockets
        for websocket in websockets:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                # Remove failed WebSocket connections
                await self.unregister_websocket(session_id, websocket)
    
    async def start_processing(self, session_id: str, message: str, session_mgr: SessionManager):
        """Start processing a message using the computer loop"""
        # Cancel any existing processing task for this session
        if session_id in self._processing_tasks:
            self._processing_tasks[session_id].cancel()
        
        # Create new processing task
        task = asyncio.create_task(
            self._process_message(session_id, message, session_mgr)
        )
        self._processing_tasks[session_id] = task
        
        # Send processing started notification
        await self.broadcast_to_session(session_id, {
            "type": "processing_started",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _process_message(self, session_id: str, message: str, session_mgr: SessionManager):
        """Process a message using the computer loop"""
        try:
            # Get session configuration
            session_config = await session_mgr.get_session_config(session_id)
            if not session_config:
                raise Exception("Session not found")
            
            # Get existing messages for the session
            messages = await session_mgr.get_session_messages(session_id)
            
            # Convert messages to the format expected by the sampling loop
            api_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    api_messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
                elif msg["role"] == "assistant":
                    # For assistant messages, we need to reconstruct the content blocks
                    content_blocks = []
                    if msg.get("tool_name"):
                        # This was a tool use message
                        content_blocks.append({
                            "type": "tool_use",
                            "id": msg["id"],
                            "name": msg["tool_name"],
                            "input": msg.get("tool_input", {})
                        })
                    else:
                        # This was a text message
                        content_blocks.append({
                            "type": "text",
                            "text": msg["content"]
                        })
                    
                    api_messages.append({
                        "role": "assistant",
                        "content": content_blocks
                    })
                elif msg["role"] == "tool":
                    # Tool result messages
                    content_blocks = []
                    if msg.get("tool_result"):
                        content_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_name", ""),  # Using tool_name as tool_use_id
                            "content": msg["tool_result"]
                        })
                    
                    if content_blocks:
                        api_messages.append({
                            "role": "user",
                            "content": content_blocks
                        })
            
            # Add the new user message
            api_messages.append({
                "role": "user",
                "content": message
            })
            
            # Create callbacks for real-time updates
            async def output_callback(content_block):
                """Callback for assistant output"""
                message_id = str(uuid.uuid4())
                print(f"DEBUG: output_callback called with: {content_block}")
                
                if content_block["type"] == "text":
                    await session_mgr.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=content_block["text"]
                    )
                    
                    await self.broadcast_to_session(session_id, {
                        "type": "assistant_message",
                        "message_id": message_id,
                        "content": content_block["text"],
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif content_block["type"] == "tool_use":
                    await session_mgr.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=f"Using tool: {content_block['name']}",
                        tool_name=content_block["id"],
                        tool_input=content_block["input"]
                    )
                    
                    await self.broadcast_to_session(session_id, {
                        "type": "tool_use",
                        "tool_id": content_block["id"],
                        "tool_name": content_block["name"],
                        "tool_input": content_block["input"],
                        "timestamp": datetime.now().isoformat()
                    })
            
            async def tool_output_callback(tool_result: ToolResult, tool_id: str):
                """Callback for tool execution results"""
                message_id = str(uuid.uuid4())
                print(f"DEBUG: tool_output_callback called with tool: {tool_result.name}, result: {tool_result.success}")
                
                # Add tool result to session
                await session_mgr.add_message(
                    session_id=session_id,
                    role="tool",
                    content=f"Tool {tool_result.name} completed",
                    tool_name=tool_id,
                    tool_result={
                        "success": tool_result.success,
                        "output": tool_result.output,
                        "error": tool_result.error
                    }
                )
                
                await self.broadcast_to_session(session_id, {
                    "type": "tool_result",
                    "tool_id": tool_id,
                    "tool_name": tool_result.name,
                    "success": tool_result.success,
                    "output": tool_result.output,
                    "error": tool_result.error,
                    "timestamp": datetime.now().isoformat()
                })
            
            def api_response_callback(request, response, error):
                """Callback for API responses"""
                if error:
                    # Schedule the async broadcast operation
                    asyncio.create_task(self.broadcast_to_session(session_id, {
                        "type": "api_error",
                        "error": str(error),
                        "timestamp": datetime.now().isoformat()
                    }))
                else:
                    # Schedule the async broadcast operation
                    asyncio.create_task(self.broadcast_to_session(session_id, {
                        "type": "api_response",
                        "status_code": response.status_code if response else None,
                        "timestamp": datetime.now().isoformat()
                    }))
            
            # Determine tool version based on model
            tool_version = "computer_use_20241022"  # Default
            if "claude-3-7" in session_config["model"] or "claude-opus-4" in session_config["model"]:
                tool_version = "computer_use_20250124"
            
            # Start the sampling loop
            print(f"DEBUG: Starting sampling_loop with {len(api_messages)} messages")
            await sampling_loop(
                model=session_config["model"],
                provider=session_config["provider"],
                system_prompt_suffix=session_config["system_prompt"],
                messages=api_messages,
                output_callback=output_callback,
                tool_output_callback=tool_output_callback,
                api_response_callback=api_response_callback,
                api_key=session_config["api_key"],
                max_tokens=4096,
                tool_version=tool_version,
                thinking_budget=2048
            )
            print("DEBUG: sampling_loop completed")
            
            # Send processing completed notification
            await self.broadcast_to_session(session_id, {
                "type": "processing_completed",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
            
        except asyncio.CancelledError:
            # Task was cancelled
            await self.broadcast_to_session(session_id, {
                "type": "processing_cancelled",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
            raise
        except Exception as e:
            # Send error notification
            await self.broadcast_to_session(session_id, {
                "type": "processing_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            raise
        finally:
            # Clean up task reference
            async with self._lock:
                if session_id in self._processing_tasks:
                    del self._processing_tasks[session_id]
    
    async def stop_processing(self, session_id: str):
        """Stop processing for a session"""
        if session_id in self._processing_tasks:
            self._processing_tasks[session_id].cancel()
            try:
                await self._processing_tasks[session_id]
            except asyncio.CancelledError:
                pass
            del self._processing_tasks[session_id]
    
    async def get_processing_status(self, session_id: str) -> ProcessingStatus:
        """Get processing status for a session"""
        is_processing = session_id in self._processing_tasks
        websocket_count = len(self._active_websockets.get(session_id, []))
        
        return ProcessingStatus(
            session_id=session_id,
            status="processing" if is_processing else "idle",
            current_step=None,
            progress=None,
            error=None
        ) 