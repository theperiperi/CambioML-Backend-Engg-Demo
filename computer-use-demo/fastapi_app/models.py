from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class APIProvider(str, Enum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    VERTEX = "vertex"

class SessionCreate(BaseModel):
    api_key: str = Field(..., description="API key for the chosen provider")
    provider: APIProvider = Field(default=APIProvider.ANTHROPIC, description="API provider")
    model: str = Field(default="claude-3-5-sonnet-20241022-v2:0", description="Model to use")
    system_prompt: Optional[str] = Field(default="", description="Custom system prompt")

class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    status: str

class ChatMessage(BaseModel):
    id: str
    role: str  # "user", "assistant", "tool"
    content: str
    timestamp: datetime
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to send")

class ToolResult(BaseModel):
    tool_id: str
    tool_name: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class VNCConnection(BaseModel):
    host: str
    port: int
    password: Optional[str] = None
    status: str
    websocket_url: Optional[str] = None

class WebSocketMessage(BaseModel):
    type: str  # "message", "tool_result", "error", "status"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class ProcessingStatus(BaseModel):
    session_id: str
    status: str  # "processing", "completed", "error"
    current_step: Optional[str] = None
    progress: Optional[float] = None
    error: Optional[str] = None 