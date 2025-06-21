from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from contextlib import asynccontextmanager

from .models import (
    SessionCreate, 
    SessionResponse, 
    ChatMessage, 
    ChatRequest,
    ToolResult,
    VNCConnection
)
from .database import DatabaseManager
from .session_manager import SessionManager
from .computer_loop import ComputerLoopManager
from .vnc_manager import VNCManager

# Global managers
db_manager: Optional[DatabaseManager] = None
session_manager: Optional[SessionManager] = None
computer_loop_manager: Optional[ComputerLoopManager] = None
vnc_manager: Optional[VNCManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_manager, session_manager, computer_loop_manager, vnc_manager
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialize session manager
    session_manager = SessionManager(db_manager)
    
    # Initialize computer loop manager
    computer_loop_manager = ComputerLoopManager()
    
    # Initialize VNC manager
    vnc_manager = VNCManager()
    
    yield
    
    # Shutdown
    if db_manager:
        await db_manager.close()
    if vnc_manager:
        await vnc_manager.close()

app = FastAPI(
    title="Computer Use Demo API",
    description="FastAPI backend for Claude Computer Use Demo",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency to get managers
def get_db_manager() -> DatabaseManager:
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")
    return db_manager

def get_session_manager() -> SessionManager:
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    return session_manager

def get_computer_loop_manager() -> ComputerLoopManager:
    if not computer_loop_manager:
        raise HTTPException(status_code=500, detail="Computer loop manager not initialized")
    return computer_loop_manager

def get_vnc_manager() -> VNCManager:
    if not vnc_manager:
        raise HTTPException(status_code=500, detail="VNC manager not initialized")
    return vnc_manager

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    """Serve the main frontend HTML page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Create a new chat session"""
    try:
        session = await session_mgr.create_session(
            api_key=session_data.api_key,
            provider=session_data.provider,
            model=session_data.model,
            system_prompt=session_data.system_prompt
        )
        return SessionResponse(
            session_id=session["session_id"],
            created_at=session["created_at"],
            status="active"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Get session details"""
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        session_id=session["session_id"],
        created_at=session["created_at"],
        status=session["status"]
    )

@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Get all messages for a session"""
    messages = await session_mgr.get_session_messages(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": messages}

@app.post("/api/sessions/{session_id}/chat")
async def send_message(
    session_id: str,
    chat_request: ChatRequest,
    session_mgr: SessionManager = Depends(get_session_manager),
    computer_mgr: ComputerLoopManager = Depends(get_computer_loop_manager)
):
    """Send a message to a session and start processing"""
    try:
        # Add user message to session
        await session_mgr.add_message(session_id, "user", chat_request.message)
        
        # Start computer loop processing
        await computer_mgr.start_processing(
            session_id=session_id,
            message=chat_request.message,
            session_mgr=session_mgr
        )
        
        return {"status": "processing", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    computer_mgr: ComputerLoopManager = Depends(get_computer_loop_manager)
):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    
    try:
        # Register this WebSocket connection for the session
        await computer_mgr.register_websocket(session_id, websocket)
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "session_id": session_id,
            "status": "connected"
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                if message_data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": str(e)
                }))
                
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "error": str(e)
        }))
    finally:
        # Clean up WebSocket registration
        await computer_mgr.unregister_websocket(session_id, websocket)

@app.get("/api/vnc/status")
async def get_vnc_status(
    vnc_mgr: VNCManager = Depends(get_vnc_manager)
):
    """Get VNC connection status"""
    status = await vnc_mgr.get_status()
    return status

@app.post("/api/vnc/connect")
async def connect_vnc(
    vnc_mgr: VNCManager = Depends(get_vnc_manager)
):
    """Start VNC server and return connection details"""
    try:
        connection = await vnc_mgr.start_vnc()
        return connection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Delete a session and all its messages"""
    success = await session_mgr.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 