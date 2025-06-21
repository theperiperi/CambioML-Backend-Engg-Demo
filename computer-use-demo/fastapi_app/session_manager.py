import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from .database import DatabaseManager
from .models import ChatMessage, APIProvider

class SessionManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def create_session(self, api_key: str, provider: APIProvider, 
                           model: str, system_prompt: str = "") -> Dict[str, Any]:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        
        # Create session in database
        success = await self.db_manager.create_session(
            session_id=session_id,
            api_key=api_key,
            provider=provider.value,
            model=model,
            system_prompt=system_prompt
        )
        
        if not success:
            raise Exception("Failed to create session")
        
        # Create session object
        session = {
            "session_id": session_id,
            "api_key": api_key,
            "provider": provider,
            "model": model,
            "system_prompt": system_prompt,
            "created_at": datetime.now(),
            "status": "active",
            "messages": []
        }
        
        # Store in memory
        async with self._lock:
            self._active_sessions[session_id] = session
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details"""
        # First check memory
        async with self._lock:
            if session_id in self._active_sessions:
                return self._active_sessions[session_id]
        
        # Fall back to database
        session_data = await self.db_manager.get_session(session_id)
        if session_data:
            # Convert to session object format
            session = {
                "session_id": session_data["session_id"],
                "api_key": session_data["api_key"],
                "provider": APIProvider(session_data["provider"]),
                "model": session_data["model"],
                "system_prompt": session_data["system_prompt"],
                "created_at": datetime.fromisoformat(session_data["created_at"]),
                "status": session_data["status"],
                "messages": []
            }
            
            # Load messages
            messages = await self.db_manager.get_session_messages(session_id)
            session["messages"] = messages
            
            # Cache in memory
            async with self._lock:
                self._active_sessions[session_id] = session
            
            return session
        
        return None
    
    async def add_message(self, session_id: str, role: str, content: str,
                         tool_name: Optional[str] = None,
                         tool_input: Optional[Dict[str, Any]] = None,
                         tool_result: Optional[Dict[str, Any]] = None) -> str:
        """Add a message to a session"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Add to database
        success = await self.db_manager.add_message(
            session_id=session_id,
            message_id=message_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_result=tool_result
        )
        
        if not success:
            raise Exception("Failed to add message to database")
        
        # Create message object
        message = {
            "id": message_id,
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_result": tool_result
        }
        
        # Add to memory cache
        async with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id]["messages"].append(message)
        
        return message_id
    
    async def get_session_messages(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get all messages for a session"""
        # Check if session exists
        session = await self.get_session(session_id)
        if not session:
            return None
        
        # Return messages from memory cache
        async with self._lock:
            if session_id in self._active_sessions:
                return self._active_sessions[session_id]["messages"]
        
        # Fall back to database
        return await self.db_manager.get_session_messages(session_id)
    
    async def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        success = await self.db_manager.update_session_status(session_id, status)
        
        if success:
            # Update memory cache
            async with self._lock:
                if session_id in self._active_sessions:
                    self._active_sessions[session_id]["status"] = status
        
        return success
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        success = await self.db_manager.delete_session(session_id)
        
        if success:
            # Remove from memory cache
            async with self._lock:
                if session_id in self._active_sessions:
                    del self._active_sessions[session_id]
        
        return success
    
    async def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions"""
        return await self.db_manager.get_recent_sessions(limit)
    
    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Clean up old sessions"""
        deleted_count = await self.db_manager.cleanup_old_sessions(days)
        
        # Also clean up memory cache for deleted sessions
        if deleted_count > 0:
            async with self._lock:
                # This is a simple cleanup - in production you might want to be more sophisticated
                current_time = datetime.now()
                sessions_to_remove = []
                
                for session_id, session in self._active_sessions.items():
                    if (current_time - session["created_at"]).days > days:
                        sessions_to_remove.append(session_id)
                
                for session_id in sessions_to_remove:
                    del self._active_sessions[session_id]
        
        return deleted_count
    
    async def get_session_config(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session configuration for API calls"""
        # First check memory
        async with self._lock:
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                return {
                    "api_key": session["api_key"],
                    "provider": session["provider"],
                    "model": session["model"],
                    "system_prompt": session["system_prompt"]
                }
        
        # Fall back to database
        session = await self.get_session(session_id)
        if session:
            return {
                "api_key": session["api_key"],
                "provider": session["provider"],
                "model": session["model"],
                "system_prompt": session["system_prompt"]
            }
        
        return None 