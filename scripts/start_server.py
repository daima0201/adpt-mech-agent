#!/usr/bin/env python3
"""
服务启动脚本
启动Adaptive Mechanism Agent服务
"""

import os
import sys
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.shared.config.manager import ConfigManager
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def create_fastapi_app():
    """创建FastAPI应用（待实现）"""
    from fastapi import FastAPI
    
    app = FastAPI(
        title="Adaptive Mechanism Agent",
        description="智能Agent系统，支持知识检索和工具调用",
        version="1.0.0"
    )
    
    @app.get("/")
    async def root():
        return {"message": "Adaptive Mechanism Agent API"}
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    # TODO: 添加更多的API端点
    
    return app


def start_uvicorn_server():
    """启动Uvicorn服务器"""
    config = ConfigManager().get_config()
    
    # 获取服务器配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    # 创建FastAPI应用
    app = create_fastapi_app()
    
    # 启动服务器
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=config.log_level.lower(),
        reload=config.environment == "development"
    )


def start_cli_mode():
    """启动CLI模式"""
    print("=== Adaptive Mechanism Agent CLI模式 ===")
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'help' 查看帮助")
    
    from src.agents.core.agent import SimpleAgent
    from src.shared.config.manager import ConfigManager
    
    config = ConfigManager().get_config()
    agent = SimpleAgent(config)
    
    while True:
        try:
            user_input = input("\n>>> ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("再见！")
                break
            elif user_input.lower() == 'help':
                print("可用命令:")
                print("  help - 显示帮助")
                print("  quit/exit - 退出")
                print("  其他任何输入将被发送给Agent处理")
                continue
            
            if user_input:
                response = agent.process_message(user_input)
                print(f"Agent: {response}")
                
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            logger.error(f"处理用户输入时出错: {e}")
            print(f"错误: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adaptive Mechanism Agent")
    parser.add_argument(
        "--mode", 
        choices=["server", "cli"], 
        default="server",
        help="运行模式: server (API服务) 或 cli (命令行交互)"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="服务器主机地址"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="服务器端口"
    )
    
    args = parser.parse_args()
    
    # 设置环境变量
    os.environ["HOST"] = args.host
    os.environ["PORT"] = str(args.port)
    
    try:
        if args.mode == "server":
            print(f"启动API服务器: http://{args.host}:{args.port}")
            start_uvicorn_server()
        else:
            start_cli_mode()
            
    except Exception as e:
        logger.error(f"启动失败: {e}")
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()