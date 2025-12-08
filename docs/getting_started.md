# 快速开始指南

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境配置

1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 配置必要的环境变量：
```bash
# OpenAI API密钥
OPENAI_API_KEY=your_openai_api_key_here

# 环境设置
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

## 构建知识库

```bash
# 构建初始知识库
python scripts/build_knowledge_base.py

# 或者使用CLI工具
python scripts/knowledge_cli.py build
```

## 运行示例

### 基础使用
```python
from src.agents.core.agent import SimpleAgent
from src.shared.config.manager import ConfigManager

# 加载配置
config = ConfigManager().get_config()

# 创建Agent
agent = SimpleAgent(config)

# 发送消息
response = agent.process_message("你好，请介绍一下这个项目")
print(response)
```

### 知识感知Agent
```python
from src.agents.impls.react_agent import ReActAgent
from src.knowledge.core.knowledge_base import KnowledgeBase

# 初始化知识库
kb = KnowledgeBase(config)

# 创建知识感知Agent
agent = ReActAgent(config, knowledge_base=kb)

# 处理复杂查询
response = agent.process_message("根据项目文档，解释一下RAG架构的工作原理")
print(response)
```

## Docker运行

```bash
# 构建镜像
docker build -t adpt-mech-agent .

# 运行容器
docker run -p 8000:8000 adpt-mech-agent

# 使用docker-compose
docker-compose up -d
```

## 测试

```bash
# 运行单元测试
python -m pytest tests/unit/

# 运行集成测试
python -m pytest tests/integration/

# 运行所有测试
python -m pytest
```