"""
FastAPI应用主入口
配置应用、中间件和路由
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.dependencies import (
    get_cache_manager,
    get_agent_service,
    get_session_manager,
    get_connection_manager
)
from src.api.v1.routers import api_router
from src.api.websocket.chat_handler import WebSocketChatHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="多Agent智能体API系统",
    description="基于FastAPI的多Agent智能体API系统，支持WebSocket和HTTP两种通信方式",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix="/api")

# 静态文件服务
import os
from fastapi.responses import FileResponse

# 获取项目根目录的绝对路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_demo_path = os.path.join(project_root, "web_demo")

if os.path.exists(web_demo_path):
    # 根路径重定向到quantum_sales_chat_real.html
    @app.get("/")
    async def read_index():
        return FileResponse(os.path.join(web_demo_path, "quantum_sales_chat_real.html"))
    
    # 静态文件服务
    app.mount("/", StaticFiles(directory=web_demo_path, html=True), name="static")
else:
    logger.warning(f"Web demo directory not found: {web_demo_path}")


# WebSocket端点
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket, session_id: str):
    """WebSocket聊天端点"""
    try:
        # 获取依赖实例
        connection_manager = get_connection_manager()
        agent_service = get_agent_service()
        session_manager = get_session_manager()

        # 创建WebSocket处理器
        handler = WebSocketChatHandler(
            connection_manager=connection_manager,
            agent_service=await agent_service,
            session_manager=session_manager
        )

        await handler.handle_connection(websocket, session_id)

    except Exception as e:
        logger.error(f"WebSocket endpoint error for session {session_id}: {e}")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 初始化缓存管理器（单例模式会自动初始化）
    cache_manager = get_cache_manager()
    
    # 初始化Agent服务
    agent_service = await get_agent_service()
    await agent_service.initialize()
    
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Application shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
