#!/usr/bin/env python3
"""
环境设置脚本
自动化设置开发和生产环境
"""

import subprocess
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        raise RuntimeError(f"需要Python 3.8+，当前版本: {version.major}.{version.minor}")

    print(f"✓ Python版本检查通过: {version.major}.{version.minor}.{version.micro}")


def install_dependencies():
    """安装项目依赖"""
    print("安装项目依赖...")

    # 优先使用pyproject.toml
    if Path("pyproject.toml").exists():
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], capture_output=True, text=True)
    else:
        # 回退到requirements.txt
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"依赖安装失败: {result.stderr}")

    print("✓ 依赖安装完成")


def setup_data_directories():
    """设置数据目录结构"""
    directories = [
        "data/knowledge/code_knowledge/python_docs",
        "data/knowledge/code_knowledge/api_docs",
        "data/knowledge/code_knowledge/project_docs",
        "data/knowledge/general_knowledge",
        "data/knowledge/processed",
        "data/vector_stores/chroma",
        "data/vector_stores/qdrant",
        "data/vector_stores/indexes",
        "data/caches/embeddings",
        "data/caches/retrieval",
        "data/caches/temp",
        "data/logs/app",
        "data/logs/knowledge",
        "data/logs/agents"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {directory}")


def create_env_file():
    """创建环境变量文件"""
    env_example = Path(".env.example")
    env_file = Path(".env")

    if not env_file.exists():
        if env_example.exists():
            env_file.write_text(env_example.read_text())
            print("✓ 已创建 .env 文件（请编辑配置）")
        else:
            # 创建基础的环境变量模板
            env_content = """# Adaptive Mechanism Agent 环境配置

# LLM配置
OPENAI_API_KEY=your_openai_api_key_here

# 环境设置
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# 数据库配置（如果使用外部数据库）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=adpt_mech_agent
DB_USER=postgres
DB_PASSWORD=password

# 向量数据库配置
QDRANT_HOST=localhost
QDRANT_PORT=6333

# 缓存配置
REDIS_URL=redis://localhost:6379
"""
            env_file.write_text(env_content)
            print("✓ 已创建 .env 文件模板（请编辑配置）")
    else:
        print("✓ .env 文件已存在")


def setup_test_environment():
    """设置测试环境"""
    test_dirs = [
        "tests/fixtures/test_data",
        "tests/fixtures/mocks",
        "tests/logs"
    ]

    for directory in test_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建测试目录: {directory}")


def run_initial_tests():
    """运行初始测试"""
    print("运行初始测试...")

    try:
        # 运行基础导入测试
        test_script = """
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试核心模块导入
try:
    from src.shared.config.manager import ConfigManager
    from src.shared.utils.logger import get_logger
    from src.agents.core.agent import SimpleAgent
    print("✓ 核心模块导入成功")
except ImportError as e:
    print(f"✗ 模块导入失败: {e}")
    sys.exit(1)

# 测试配置加载
try:
    config = ConfigManager().get_config()
    print("✓ 配置加载成功")
except Exception as e:
    print(f"✗ 配置加载失败: {e}")
    sys.exit(1)

print("✓ 所有测试通过")
"""

        result = subprocess.run([
            sys.executable, "-c", test_script
        ], capture_output=True, text=True, cwd=project_root)

        if result.returncode == 0:
            print("✓ 初始测试通过")
        else:
            print(f"✗ 初始测试失败: {result.stderr}")

    except Exception as e:
        print(f"✗ 测试执行失败: {e}")


def display_next_steps():
    """显示后续步骤"""
    print("\n" + "=" * 50)
    print("环境设置完成！下一步：")
    print("=" * 50)
    print("1. 编辑 .env 文件，配置API密钥和其他设置")
    print("2. 构建知识库: python scripts/build_knowledge_base.py")
    print("3. 运行示例: python examples/basic_usage.py")
    print("4. 启动服务: python scripts/start_server.py")
    print("5. 运行测试: python -m pytest tests/")
    print("\n快速开始命令:")
    print("  source venv/bin/activate  # 激活虚拟环境")
    print("  python scripts/setup_environment.py  # 设置环境")
    print("  python scripts/build_knowledge_base.py  # 构建知识库")
    print("  python scripts/start_server.py --mode cli  # 启动CLI")
    print("=" * 50)


def main():
    """主函数"""
    print("=== Adaptive Mechanism Agent 环境设置 ===")

    try:
        # 1. 检查Python版本
        check_python_version()

        # 2. 安装依赖
        install_dependencies()

        # 3. 设置数据目录
        setup_data_directories()

        # 4. 创建环境变量文件
        create_env_file()

        # 5. 设置测试环境
        setup_test_environment()

        # 6. 运行初始测试
        run_initial_tests()

        # 7. 显示后续步骤
        display_next_steps()

        print("\n✓ 环境设置完成！")

    except Exception as e:
        logger.error(f"环境设置失败: {e}")
        print(f"✗ 环境设置失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
