"""
WebSocket聊天处理器
处理WebSocket连接和消息路由
"""

import json
import logging
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from src.services.agent_service import AgentService
from src.core.session.session_manager import SessionManager
from src.api.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class WebSocketChatHandler:
    """WebSocket聊天处理器"""
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        agent_service: AgentService,
        session_manager: SessionManager
    ):
        self.connection_manager = connection_manager
        self.agent_service = agent_service
        self.session_manager = session_manager
    
    async def handle_connection(self, websocket: WebSocket, session_id: str):
        """处理WebSocket连接"""
        await self.connection_manager.connect(websocket, session_id)
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                await self._handle_message(session_id, data)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket handler for {session_id}: {e}")
        finally:
            await self.connection_manager.disconnect(session_id)
    
    async def _handle_message(self, session_id: str, message_data: str):
        """处理收到的消息"""
        try:
            # 解析消息
            message = json.loads(message_data)
            message_type = message.get("type", "chat")
            
            if message_type == "chat":
                await self._handle_chat_message(session_id, message)
            elif message_type == "ping":
                await self._handle_ping(session_id, message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message from {session_id}: {message_data}")
            await self._send_error(session_id, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message from {session_id}: {e}")
            await self._send_error(session_id, str(e))
    
    async def _handle_chat_message(self, session_id: str, message: Dict[str, Any]):
        """处理聊天消息"""
        try:
            text = message.get("text", "")
            agent_id = message.get("agent_id")
            
            if not text:
                await self._send_error(session_id, "Message text is required")
                return
            
            # 获取或创建会话
            session = await self.session_manager.get_or_create_session(session_id, agent_id)
            
            # 获取Agent
            agent = await self.agent_service.get_or_create_agent(session.agent_id)
            
            # 发送开始响应
            await self._send_message(session_id, {
                "type": "response_start",
                "session_id": session.id,
                "agent_id": session.agent_id
            })
            
            # 流式处理消息
            full_response = ""
            async for chunk in agent.process_stream(text):
                full_response += chunk
                await self._send_message(session_id, {
                    "type": "response_chunk",
                    "chunk": chunk,
                    "session_id": session.id
                })
            
            # 发送结束响应
            await self._send_message(session_id, {
                "type": "response_end",
                "session_id": session.id,
                "full_response": full_response
            })
            
            # 保存消息历史
            await self.session_manager.add_message(
                session.id, text, full_response, "user", "assistant"
            )
            
        except Exception as e:
            logger.error(f"Error processing chat message for {session_id}: {e}")
            await self._send_error(session_id, f"Processing error: {str(e)}")
    
    async def _handle_ping(self, session_id: str, message: Dict[str, Any]):
        """处理ping消息"""
        await self._send_message(session_id, {
            "type": "pong",
            "timestamp": message.get("timestamp")
        })
    
    async def _send_message(self, session_id: str, message: Dict[str, Any]):
        """发送消息到指定会话"""
        await self.connection_manager.send_message(session_id, message)
    
    async def _send_error(self, session_id: str, error_message: str):
        """发送错误消息"""
        await self._send_message(session_id, {
            "type": "error",
            "message": error_message,
            "session_id": session_id
        })