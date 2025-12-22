# Adaptive Mechanism Agent (adpt-mech-agent)

一个基于自适应机制的智能Agent框架，集成了知识库RAG功能和工具调用能力。

## 🚀 项目特色

- **自适应协调机制**：根据任务复杂度自动选择合适的Agent策略
- **知识感知能力**：集成RAG（检索增强生成）功能，支持多源知识库
- **工具系统**：可扩展的工具调用框架，支持自定义工具开发
- **模块化架构**：清晰的层次结构，便于定制和扩展
- **多LLM支持**：支持OpenAI、DeepSeek等多种LLM提供商
- **即插即用**：预配置多种智能体类型，开箱即用
- **配置中心**：支持MySQL持久化存储，统一管理智能体配置

## 📦 快速开始

### 一键启动

```bash
# 运行快速启动脚本
python scripts/quick_start.py
```

### MySQL配置中心（推荐）

```bash
# 安装和配置MySQL
python scripts/setup_mysql.py

# 测试MySQL连接
python test_mysql_connection.py

# 测试完整配置系统
python test_mysql_config.py
```

### 手动安装

```bash
# 克隆项目
git clone <repository-url>
cd adpt-mech-agent

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 运行基础测试
python examples/test_basic_functionality.py
```

### 客户经理智能体演示

```bash
# 运行完整的客户经理智能体演示
python examples/final_customer_manager_demo.py
```

## 🎯 核心功能

### 智能体类型

- **SimpleAgent**: 基础对话智能体
- **ReActAgent**: 推理-行动智能体
- **ReflectionAgent**: 反思型智能体
- **PlanSolveAgent**: 规划求解智能体
- **KnowledgeAwareAgent**: 知识感知智能体

### 知识库集成

```python
from src.knowledge.core.knowledge_base import KnowledgeBase
from src.agents.impls.knowledge_aware_agent import KnowledgeAwareAgent

# 创建知识感知智能体
agent = KnowledgeAwareAgent(config, llm, knowledge_base)
response = await agent.run("量子加密产品的技术特点是什么？")
```

### 工具调用

```python
from src.capabilities.tools.registry import ToolRegistry

# 注册和使用工具
ToolRegistry.register(CustomTool())
response = await agent.run("计算一下123 + 456等于多少", use_tools=True)
```

## 🔧 配置指南

详细配置说明请查看 [docs/configuration_guide.md](docs/configuration_guide.md)

### LLM配置

在 `configs/llm_config.yaml` 中配置：

```yaml
llm:
  type: "deepseek"  # mock, deepseek, openai
  model_name: "deepseek-chat"
  api_key: "${DEEPSEEK_API_KEY}"
  base_url: "https://api.deepseek.com"
  temperature: 0.7
  max_tokens: 2048
```

### 环境变量

在 `.env` 文件中设置：

```bash
DEEPSEEK_API_KEY="your-api-key-here"
OPENAI_API_KEY="your-openai-key-here"
DEBUG=true
```

## 📁 项目结构

```
adpt-mech-agent/
├── src/                           # 源代码主目录
│   ├── agents/                   # Agent核心模块
│   ├── knowledge/                # 知识库RAG模块
│   ├── adaptive/                 # 自适应协调层
│   └── shared/                   # 共享模块
├── configs/                      # 配置文件目录
├── data/                         # 数据目录
├── tests/                        # 测试目录
├── examples/                     # 示例代码
├── docs/                         # 项目文档
└── scripts/                      # 管理脚本
```

## 🔧 核心组件

### 🤖 Agent类型

- **SimpleAgent**: 基础对话智能体
- **ReActAgent**: 推理-行动智能体
- **ReflectionAgent**: 反思型智能体
- **PlanSolveAgent**: 规划求解智能体
- **KnowledgeAwareAgent**: 知识感知智能体

### 📚 知识库系统

- **向量存储**: 支持Chroma、Qdrant等
- **嵌入模型**: 支持本地模型和OpenAI API
- **检索器**: 向量检索、BM25、混合检索
- **处理器**: 文档加载、文本切分、元数据提取

### ⚙️ 自适应机制

- **KnowledgeManager**: 知识库协调管理
- **ToolManager**: 工具注册和调用
- **AgentOrchestrator**: Agent选择和调度
- **Evaluator**: 性能评估和优化

## 🛠️ 开发指南

项目使用YAML格式的配置文件，支持多环境配置：

- `configs/default.yaml`: 默认配置
- `configs/development.yaml`: 开发环境
- `configs/production.yaml`: 生产环境
- `configs/test.yaml`: 测试环境

### 🔧 添加自定义工具

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

### 📚 扩展知识库

```python
from src.knowledge.processors.processor_base import ProcessorBase

class CustomProcessor(ProcessorBase):
    def process(self, document):
        # 自定义处理逻辑
        return processed_document
```

## 🧪 测试

运行单元测试：
```bash
pytest tests/unit/
```

运行集成测试：
```bash
pytest tests/integration/
```

## 🚀 部署

### 📦 Docker部署

```bash
cd docker
docker-compose up -d
```

### 💻 本地部署

```bash
python scripts/start_server.py
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 文档: [Documentation]

---

## 🔗 相关资源

- [📚 架构文档](docs/architecture.md) - 详细的项目架构说明
- [⚙️ 配置指南](docs/configuration_guide.md) - 完整的配置和使用说明
- [🎯 客户经理演示](examples/final_customer_manager_demo.py) - 完整的智能体演示案例
- [🚀 快速启动脚本](scripts/quick_start.py) - 一键配置和测试

## 💡 使用提示

1. **首次使用**: 运行 `python scripts/quick_start.py` 进行环境检查和基础测试
2. **配置LLM**: 编辑 `configs/llm_config.yaml` 设置真实的API密钥
3. **自定义智能体**: 参考 `examples/final_customer_manager_demo.py` 创建专业角色智能体
4. **集成知识库**: 查看 `docs/configuration_guide.md` 了解知识库集成方法

*更多详细信息请参考项目文档*