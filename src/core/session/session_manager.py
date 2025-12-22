"""
会话管理器
管理用户会话和消息历史
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from src.infrastructure.cache.cache_manager import UnifiedCacheManager

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """消息数据类"""
    id: str
    content: str
    role: str  # user, assistant, system
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class Session(BaseModel):
    """会话数据类"""
    id: str
    agent_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = []
    metadata: Dict[str, Any] = {}


class SessionManager:
    """会话管理器"""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.default_agent_id = "default_agent"
    
    async def create_session(self, agent_id: Optional[str] = None) -> Session:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        if agent_id is None:
            agent_id = self.default_agent_id
        
        session = Session(
            id=session_id,
            agent_id=agent_id,
            created_at=now,
            updated_at=now
        )
        
        # 保存到缓存
        await self._save_session(session)
        logger.info(f"Session created: {session_id} with agent: {agent_id}")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        try:
            session_data = await self.cache_manager.get_config("session", session_id)
            if session_data:
                return Session(**session_data)
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
        return None
    
    async def get_or_create_session(
        self, 
        session_id: Optional[str] = None, 
        agent_id: Optional[str] = None
    ) -> Session:
        """获取或创建会话"""
        if session_id:
            session = await self.get_session(session_id)
            if session:
                # 如果提供了新的agent_id，更新会话
                if agent_id and session.agent_id != agent_id:
                    session.agent_id = agent_id
                    session.updated_at = datetime.now()
                    await self._save_session(session)
                return session
        
        # 创建新会话
        return await self.create_session(agent_id)
    
    async def add_message(
        self, 
        session_id: str, 
        user_message: str, 
        assistant_response: str,
        user_role: str = "user",
        assistant_role: str = "assistant"
    ) -> bool:
        """添加消息到会话"""
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return False
            
            now = datetime.now()
            
            # 添加用户消息
            session.messages.append(Message(
                id=str(uuid.uuid4()),
                content=user_message,
                role=user_role,
                timestamp=now
            ))
            
            # 添加助手响应
            session.messages.append(Message(
                id=str(uuid.uuid4()),
                content=assistant_response,
                role=assistant_role,
                timestamp=now
            ))
            
            session.updated_at = now
            await self._save_session(session)
            
            logger.info(f"Messages added to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            return False
    
    async def get_message_history(self, session_id: str, limit: int = 10) -> List[Message]:
        """获取消息历史"""
        session = await self.get_session(session_id)
        if session:
            # 返回最新的limit条消息
            return session.messages[-limit:]
        return []
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            await self.cache_manager.delete_config("session", session_id)
            logger.info(f"Session deleted: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    async def _save_session(self, session: Session):
        """保存会话到缓存"""
        try:
            session_dict = session.dict()
            # 转换datetime为字符串以便序列化
            session_dict["created_at"] = session.created_at.isoformat()
            session_dict["updated_at"] = session.updated_at.isoformat()
            for msg in session_dict["messages"]:
                msg["timestamp"] = msg["timestamp"].isoformat()
            
            await self.cache_manager.set_config(
                "session", session.id, session_dict, ttl=86400  # 24小时
            )
        except Exception as e:
            logger.error(f"Error saving session {session.id}: {e}")
            raise