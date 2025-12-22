# 配置指南

## 快速开始

### 1. 环境设置

```bash
# 克隆项目
git clone <repository-url>
cd adpt-mech-agent

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env
```

### 2. LLM API配置

#### 方法一：使用配置文件

在 `configs/llm_config.yaml` 中配置：

```yaml
# configs/llm_config.yaml
llm:
  type: "deepseek"  # 或 "openai", "mock"
  model_name: "deepseek-chat"
  api_key: "${DEEPSEEK_API_KEY}"  # 从环境变量读取
  base_url: "https://api.deepseek.com"
  temperature: 0.7
  max_tokens: 2048
```

#### 方法二：使用环境变量

```bash
# 在 .env 文件中设置
export DEEPSEEK_API_KEY="your-api-key-here"
export OPENAI_API_KEY="your-openai-key-here"
```

### 3. 基础测试

运行基础功能测试确保一切正常：

```bash
python examples/test_basic_functionality.py
```

## 智能体配置

### 创建自定义智能体

```python
from src.shared.config.schemas.agent import AgentConfig
from src.agents.impls.agent.simple_agent import SimpleAgent
from src.agents.base.base_llm import MockLLM, DeepSeekClient

# 1. 创建智能体配置
config = AgentConfig(
   name="专业客户经理",
   description="专注于量子加密产品销售的专业顾问",
   system_prompt="你是一名专业的量子加密产品客户经理...",
   temperature=0.7,
   max_tokens=2048
)

# 2. 创建LLM实例（选择一种）
# 使用Mock LLM（测试用）
llm = MockLLM()

# 或使用真实LLM
# llm = DeepSeekClient()

# 3. 创建智能体
agent = SimpleAgent(config, llm)

# 4. 运行智能体
response = await agent.run("你好，请介绍一下你的服务")
print(response)
```

### 预配置智能体管理器

```python
from src.services.agent_service import AgentService
from src.infrastructure.cache.cache_manager import get_cache_manager

# 创建服务
agent_service = AgentService(get_cache_manager())
await agent_service.initialize()

# 获取可用智能体列表
agents = agent_service.agent_manager.list_agents()
print("可用智能体:")
for agent in agents:
   print(f"- {agent['name']} ({agent['id']})")

# 发送消息
response = await manager.send_message("你好", "simple_assistant")
print(response)
```

## 知识库集成

### 1. 配置知识库存储

```python
from src.knowledge.stores.chroma_store import ChromaStore
from src.knowledge.core.knowledge_base import KnowledgeBase

# 创建向量数据库存储
store = ChromaStore(
    collection_name="product_docs",
    persist_directory="./data/chroma"
)

# 创建知识库
knowledge_base = KnowledgeBase(store)
```

### 2. 加载文档

```python
from src.knowledge.processors.document_loader import DocumentLoader

# 加载文档
loader = DocumentLoader()
documents = loader.load_from_directory("./docs/products/")

# 添加到知识库
await knowledge_base.add_documents(documents)
```

### 3. 智能体集成知识库

```python
from src.agents.impls.knowledge_aware_agent import KnowledgeAwareAgent

# 创建知识感知智能体
agent = KnowledgeAwareAgent(config, llm, knowledge_base)

# 智能体会自动检索相关知识来回答问题
response = await agent.run("量子加密产品的技术特点是什么？")
```

## 工具集成

### 内置工具

项目提供以下内置工具：
- `CalculatorTool`: 数学计算
- `SearchTool`: 网络搜索
- `KnowledgeTool`: 知识库查询

### 自定义工具

```python
from src.capabilities.tools.base import Tool


class CustomTool(Tool):
   """自定义工具示例"""

   def __init__(self):
      super().__init__(
         name="custom_tool",
         description="自定义工具描述"
      )

   async def execute(self, **kwargs) -> str:
      """执行工具逻辑"""
      return "工具执行结果"


# 注册工具
from src.capabilities.tools.registry import ToolRegistry

ToolRegistry.register(CustomTool())
```

## 调试和监控

### 日志配置

```python
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 性能监控

```python
from src.shared.utils.tracing import Tracing

# 启用追踪
Tracing.enable()

# 查看追踪数据
Tracing.get_traces()
```

## 部署配置

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "scripts/start_server.py"]
```

### 生产环境配置

```yaml
# configs/production.yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4

logging:
  level: "INFO"
  file: "/var/log/agent-service.log"

cache:
  enabled: true
  ttl: 3600
```

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查环境变量是否正确设置
   - 验证API密钥是否有效

2. **导入错误**
   - 确保Python路径包含项目根目录
   - 检查依赖是否完整安装

3. **内存不足**
   - 减少max_tokens参数
   - 使用流式响应

### 调试技巧

```python
# 启用详细调试
import os
os.environ["DEBUG"] = "true"

# 检查智能体状态
print(f"智能体状态: {agent.state}")
print(f"可用工具: {agent.available_tools}")
```

这个配置指南提供了完整的项目配置和使用说明，帮助用户快速上手并定制自己的智能体系统。