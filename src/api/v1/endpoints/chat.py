"""
聊天相关端点 - HTTP接口
提供非流式和流式聊天接口
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.services.agent_service import AgentService, ChatResponse
from src.api.dependencies import get_agent_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None
    agent_id: str = "quantum_sales_manager"


class APIResponse(BaseModel):
    """API响应模型"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/message", response_model=APIResponse)
async def send_message(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """发送消息（非流式）"""
    try:
        # 处理消息
        result = await agent_service.process_message(
            agent_id=request.agent_id,
            message=request.message,
            session_id=request.session_id
        )
        
        return APIResponse(
            success=True,
            data={
                "response": result.response,
                "session_id": result.session_id,
                "processing_time": result.processing_time
            }
        )
        
    except Exception as e:
        logger.error(f"处理聊天消息失败: {e}")
        return APIResponse(
            success=False,
            error=str(e)
        )


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """流式聊天接口"""
    
    async def generate_stream():
        """生成流式响应"""
        try:
            # 发送流开始事件
            yield f"data: {json.dumps({'type': 'stream_start', 'session_id': request.session_id or 'new_session'})}\n\n"
            
            # 流式处理消息
            full_response = ""
            async for chunk in agent_service.process_message_stream(
                agent_id=request.agent_id,
                message=request.message,
                session_id=request.session_id
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # 发送流结束事件
            yield f"data: {json.dumps({'type': 'stream_end', 'session_id': request.session_id or 'new_session'})}\n\n"
            
        except Exception as e:
            logger.error(f"流式聊天错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )