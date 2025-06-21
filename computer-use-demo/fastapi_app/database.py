import sqlite3
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import aiosqlite

class DatabaseManager:
    def __init__(self, db_path: str = "computer_use_demo.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    api_key TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    system_prompt TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Create messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tool_name TEXT,
                    tool_input TEXT,
                    tool_result TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages (session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)")
            
            await db.commit()
    
    async def close(self):
        """Close database connections"""
        pass  # aiosqlite handles connection cleanup automatically
    
    async def create_session(self, session_id: str, api_key: str, provider: str, 
                           model: str, system_prompt: str = "") -> bool:
        """Create a new session"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO sessions (session_id, api_key, provider, model, system_prompt)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, api_key, provider, model, system_prompt))
                await db.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM sessions WHERE session_id = ?
            """, (session_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        async with aiosqlite.connect(self.db_path) as db:
            result = await db.execute("""
                UPDATE sessions SET status = ? WHERE session_id = ?
            """, (status, session_id))
            await db.commit()
            return result.rowcount > 0
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        async with aiosqlite.connect(self.db_path) as db:
            result = await db.execute("""
                DELETE FROM sessions WHERE session_id = ?
            """, (session_id,))
            await db.commit()
            return result.rowcount > 0
    
    async def add_message(self, session_id: str, message_id: str, role: str, 
                         content: str, tool_name: Optional[str] = None,
                         tool_input: Optional[Dict[str, Any]] = None,
                         tool_result: Optional[Dict[str, Any]] = None) -> bool:
        """Add a message to a session"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO messages (id, session_id, role, content, tool_name, tool_input, tool_result)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    message_id,
                    session_id,
                    role,
                    content,
                    tool_name,
                    json.dumps(tool_input) if tool_input else None,
                    json.dumps(tool_result) if tool_result else None
                ))
                await db.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    async def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM messages 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """, (session_id,)) as cursor:
                rows = await cursor.fetchall()
                messages = []
                for row in rows:
                    message = dict(row)
                    # Parse JSON fields
                    if message['tool_input']:
                        message['tool_input'] = json.loads(message['tool_input'])
                    if message['tool_result']:
                        message['tool_result'] = json.loads(message['tool_result'])
                    messages.append(message)
                return messages
    
    async def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT session_id, created_at, status, model, provider
                FROM sessions 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Clean up sessions older than specified days"""
        async with aiosqlite.connect(self.db_path) as db:
            result = await db.execute("""
                DELETE FROM sessions 
                WHERE created_at < datetime('now', '-{} days')
            """.format(days))
            await db.commit()
            return result.rowcount 