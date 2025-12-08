# Adaptive Mechanism Agent (adpt-mech-agent)

一个基于自适应机制的智能Agent框架，集成了知识库RAG功能和工具调用能力。

## 项目概述

adpt-mech-agent是一个现代化的智能Agent开发框架，具有以下核心特性：

- **自适应协调机制**：根据任务复杂度自动选择合适的Agent策略
- **知识感知能力**：集成RAG（检索增强生成）功能，支持多源知识库
- **工具系统**：可扩展的工具调用框架，支持自定义工具开发
- **模块化架构**：清晰的层次结构，便于定制和扩展

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from src.agents.impls.react_agent import ReActAgent
from src.shared.config.manager import ConfigManager

# 加载配置
config = ConfigManager().get_config()

# 创建Agent
agent = ReActAgent(config)

# 处理消息
response = agent.process_message("你好，请介绍一下Python编程语言")
print(response)
```

### 使用知识库

```python
from src.knowledge.core.knowledge_base import KnowledgeBase
from src.knowledge.stores.chroma_store import ChromaStore
from src.knowledge.embedders.local_embedder import LocalEmbedder

# 创建知识库
vector_store = ChromaStore(persist_directory="./data/vector_stores/chroma")
embedder = LocalEmbedder()
kb = KnowledgeBase(vector_store=vector_store, embedder=embedder)

# 添加文档到知识库
document = Document(
    content="Python是一种高级编程语言...",
    metadata={"source": "python_intro.txt"}
)
kb.add_document(document)

# 创建支持知识库的Agent
agent = ReActAgent(config, knowledge_base=kb)
```

## 项目结构

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

## 核心组件

### Agent类型

- **SimpleAgent**: 基础Agent实现
- **ReActAgent**: 推理+行动模式的Agent
- **ReflectionAgent**: 带反思能力的Agent
- **PlanSolveAgent**: 规划求解型Agent

### 知识库系统

- **向量存储**: 支持Chroma、Qdrant等
- **嵌入模型**: 支持本地模型和OpenAI API
- **检索器**: 向量检索、BM25、混合检索
- **处理器**: 文档加载、文本切分、元数据提取

### 自适应机制

- **KnowledgeManager**: 知识库协调管理
- **ToolManager**: 工具注册和调用
- **AgentOrchestrator**: Agent选择和调度
- **Evaluator**: 性能评估和优化

## 配置说明

项目使用YAML格式的配置文件，支持多环境配置：

- `configs/default.yaml`: 默认配置
- `configs/development.yaml`: 开发环境
- `configs/production.yaml`: 生产环境
- `configs/test.yaml`: 测试环境

## 开发指南

### 添加自定义工具

```python
from src.agents.tools.base import BaseTool

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "自定义工具描述"
    
    def execute(self, input_data):
        # 工具逻辑实现
        return {"result": "处理完成"}
```

### 扩展知识库

```python
from src.knowledge.core.base import BaseProcessor

class CustomProcessor(BaseProcessor):
    def process(self, document):
        # 自定义处理逻辑
        return processed_document
```

## 测试

运行单元测试：
```bash
pytest tests/unit/
```

运行集成测试：
```bash
pytest tests/integration/
```

## 部署

### Docker部署

```bash
cd docker
docker-compose up -d
```

### 本地部署

```bash
python scripts/start_server.py
```

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 文档: [Documentation]

---

*更多详细信息请参考项目文档*