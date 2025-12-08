# 智能体知识库RAG体系架构扩展

## 一、整体架构设计原则

**核心原则**：

1. **保持架构一致性** - 延续现有的分层架构模式，遵循核心框架层、Agent实现层、工具系统层分离
2. **非侵入式集成** - RAG系统作为可插拔模块，不影响现有Agent核心逻辑
3. **配置驱动** - 所有RAG组件通过配置文件管理，支持热切换
4. **异步优先** - 整个知识库系统完全异步化，与现有异步工具执行器兼容

## 二、完整的模块结构扩展

### 新的目录结构：

```
adpt-mech-agent/
├── src/                           # 源代码主目录
│   │
│   ├── agents/                    # Agent核心模块
│   │   ├── core/                 # Agent框架层
│   │   │   ├── __init__.py
│   │   │   ├── agent.py          # Agent基类（含KnowledgeAware扩展）
│   │   │   ├── llm.py            # LLM统一接口
│   │   │   ├── message.py        # 消息系统（扩展knowledge_context）
│   │   │   └── config.py         # Agent配置类
│   │   │
│   │   ├── impls/                # Agent实现层
│   │   │   ├── __init__.py
│   │   │   ├── simple_agent.py   # SimpleAgent实现
│   │   │   ├── react_agent.py    # ReActAgent实现（知识感知）
│   │   │   ├── reflection_agent.py # ReflectionAgent实现
│   │   │   └── plan_solve_agent.py # PlanAndSolveAgent实现
│   │   │
│   │   └── tools/                # Agent工具系统
│   │       ├── __init__.py
│   │       ├── base.py           # 工具基类
│   │       ├── registry.py       # 工具注册
│   │       ├── chain.py          # 工具链管理
│   │       └── builtin/          # 内置工具
│   │           ├── __init__.py
│   │           ├── calculator.py # 计算工具
│   │           ├── search.py     # 搜索工具
│   │           └── knowledge_tool.py # 知识检索工具
│   │
│   ├── knowledge/                # 知识库RAG模块
│   │   ├── core/                # 知识库核心
│   │   │   ├── __init__.py
│   │   │   ├── knowledge_base.py # 知识库主类
│   │   │   ├── base.py          # 基础抽象类
│   │   │   └── schema/          # 数据模型
│   │   │       ├── __init__.py
│   │   │       ├── document.py  # Document模型
│   │   │       ├── chunk.py     # Chunk模型
│   │   │       └── query.py     # Query模型
│   │   │
│   │   ├── stores/              # 向量存储实现
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 向量存储接口
│   │   │   ├── qdrant_store.py  # Qdrant实现（生产）
│   │   │   ├── chroma_store.py  # Chroma实现（开发）
│   │   │   └── manager.py       # 多向量库管理
│   │   │
│   │   ├── embedders/           # 嵌入模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 嵌入模型接口
│   │   │   ├── bge_embedder.py  # BGE-M3实现
│   │   │   ├── openai_embedder.py # OpenAI实现
│   │   │   └── local_embedder.py # 本地模型实现
│   │   │
│   │   ├── retrievers/          # 检索器
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 检索器接口
│   │   │   ├── vector_retriever.py # 向量检索
│   │   │   ├── bm25_retriever.py # BM25关键词检索
│   │   │   ├── hybrid_retriever.py # 混合检索（主推）
│   │   │   └── reranker.py      # 重排序器
│   │   │
│   │   └── processors/          # 文档处理器
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── document_loader.py # 文档加载器
│   │       ├── text_splitter.py   # 文本切分器
│   │       ├── code_splitter.py   # 代码感知切分器
│   │       └── metadata_extractor.py # 元数据提取
│   │
│   ├── adaptive/                # 自适应协调层
│   │   ├── __init__.py
│   │   ├── knowledge_manager.py # 知识协调器（重构）
│   │   ├── tool_manager.py      # 工具管理器
│   │   ├── agent_orchestrator.py # Agent协调器
│   │   ├── coordinator.py       # 协调器基类
│   │   └── evaluator.py         # 性能评估器
│   │
│   └── shared/                  # ★新增：共享模块★
│       ├── __init__.py
│       ├── utils/               # 共享工具函数
│       │   ├── __init__.py
│       │   ├── logger.py        # 统一日志系统
│       │   ├── validators.py    # 统一验证器
│       │   ├── file_utils.py    # 文件操作工具
│       │   ├── async_utils.py   # 异步工具
│       │   └── cache.py         # 缓存工具
│       │
│       ├── config/              # 统一配置管理
│       │   ├── __init__.py
│       │   ├── manager.py       # 配置管理器
│       │   ├── schema.py        # 配置模型定义
│       │   └── loader.py        # 配置加载器
│       │
│       └── exceptions/          # 统一异常体系
│           ├── __init__.py
│           ├── base.py          # 异常基类
│           ├── agent_errors.py  # Agent相关异常
│           ├── knowledge_errors.py # 知识库异常
│           └── tool_errors.py   # 工具异常
│
├── configs/                     # 配置文件目录（统一管理）
│   ├── __init__.py
│   ├── default.yaml            # 默认配置
│   ├── development.yaml        # 开发环境
│   ├── production.yaml         # 生产环境
│   └── test.yaml               # 测试环境
│
├── data/                       # ★统一数据目录★
│   ├── knowledge/              # 知识源文档
│   │   ├── code_knowledge/     # 代码知识
│   │   │   ├── python_docs/
│   │   │   ├── api_docs/
│   │   │   └── project_docs/
│   │   ├── general_knowledge/  # 通用知识
│   │   └── processed/          # 处理后的文档
│   │
│   ├── vector_stores/          # 向量数据库文件
│   │   ├── chroma/            # Chroma数据
│   │   ├── qdrant/            # Qdrant数据
│   │   └── indexes/           # 索引文件
│   │
│   ├── caches/                 # 缓存数据
│   │   ├── embeddings/        # 嵌入缓存
│   │   ├── retrieval/         # 检索缓存
│   │   └── temp/              # 临时缓存
│   │
│   └── logs/                   # 日志文件
│       ├── app/               # 应用日志
│       ├── knowledge/         # 知识库日志
│       └── agents/            # Agent日志
│
├── scripts/                    # 管理脚本
│   ├── __init__.py
│   ├── knowledge_cli.py       # 知识库管理CLI
│   ├── build_knowledge_base.py # 知识库构建脚本
│   ├── start_server.py        # 服务启动脚本
│   └── setup_environment.py   # 环境配置脚本
│
├── tests/                      # 测试目录
│   ├── __init__.py
│   ├── unit/                  # 单元测试
│   │   ├── test_agents/
│   │   ├── test_knowledge/
│   │   ├── test_tools/
│   │   └── test_adaptive/
│   │
│   ├── integration/           # 集成测试
│   │   ├── test_rag_flow.py   # RAG流程测试
│   │   ├── test_agent_knowledge.py # Agent+知识库测试
│   │   └── test_end_to_end.py # 端到端测试
│   │
│   └── fixtures/              # 测试夹具
│       ├── test_data/
│       └── mocks/
│
├── examples/                   # 示例代码
│   ├── __init__.py
│   ├── basic_usage.py         # 基础使用示例
│   ├── knowledge_agent.py     # 知识感知Agent示例
│   ├── custom_tools.py        # 自定义工具示例
│   └── advanced_rag.py        # 高级RAG示例
│
├── docs/                       # 项目文档
│   ├── api_reference.md       # API参考
│   ├── user_guide.md          # 用户指南
│   ├── architecture.md        # 架构文档
│   ├── getting_started.md     # 快速开始
│   └── deployment.md          # 部署指南
│
├── docker/                     # Docker配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
│
├── main.py                     # 应用主入口
├── pyproject.toml             # ★推荐：现代Python项目配置★
├── setup.py                   # 传统setup配置（可选）
├── .env.example               # 环境变量示例
├── README.md                  # 项目说明
└── requirements.txt           # 依赖清单（或使用pyproject.toml管理）
```

## 三、核心组件详细设计

### 1. 知识库基础模型（`knowledge/schema/`）

```python
# knowledge/schema/chunk.py
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class KnowledgeChunk(BaseModel):
    """知识片段模型"""
    id: str = Field(description="唯一标识符")
    content: str = Field(description="文本内容")
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    score: float = Field(0.0, description="检索相关性得分")
    source: str = Field(description="来源文档")
    chunk_index: int = Field(description="在文档中的位置")

    class Config:
        arbitrary_types_allowed = True
```

### 2. 知识库主类（`knowledge/knowledge_base.py`）

```python
# knowledge/knowledge_base.py
from src.agents.core import KnowledgeConfig
from src.knowledge.vector_store.base import VectorStore
from src.knowledge.embedder.base import Embedder
from src.knowledge.retriever.hybrid_retriever import HybridRetriever


class KnowledgeBase:
    """知识库主类 - 统一管理RAG全流程"""

    def __init__(self, name: str, config: KnowledgeConfig):
        self.name = name
        self.config = config
        self.vector_store: VectorStore = None
        self.embedder: Embedder = None
        self.retriever: HybridRetriever = None
        self.is_initialized = False

    async def initialize(self):
        """初始化知识库组件"""
        # 1. 初始化向量存储
        vector_store_class = self._get_vector_store_class()
        self.vector_store = vector_store_class(self.config.vector_store)
        await self.vector_store.initialize()

        # 2. 初始化嵌入模型
        embedder_class = self._get_embedder_class()
        self.embedder = embedder_class(self.config.embedding)

        # 3. 初始化检索器
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            embedder=self.embedder,
            config=self.config.retrieval
        )

        self.is_initialized = True
        logger.info(f"知识库 '{self.name}' 初始化完成")

    async def add_documents(self, documents: List[Document]):
        """添加文档到知识库"""
        if not self.is_initialized:
            await self.initialize()

        # 1. 文档处理（加载、切分、提取元数据）
        processor = DocumentProcessor(self.config.processing)
        chunks = await processor.process_documents(documents)

        # 2. 生成向量嵌入
        embeddings = await self.embedder.embed_chunks(chunks)
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        # 3. 存储到向量数据库
        await self.vector_store.add_chunks(chunks)

        logger.info(f"已添加 {len(chunks)} 个知识片段到知识库 '{self.name}'")

    async def retrieve(
            self,
            query: str,
            top_k: int = 5,
            score_threshold: float = 0.7,
            **kwargs
    ) -> List[KnowledgeChunk]:
        """检索相关知识"""
        if not self.is_initialized:
            await self.initialize()

        # 执行检索
        results = await self.retriever.retrieve(
            query=query,
            top_k=top_k * 2,  # 检索更多以便重排序
            **kwargs
        )

        # 过滤和重排序
        filtered_results = [
                               chunk for chunk in results
                               if chunk.score >= score_threshold
                           ][:top_k]

        return filtered_results

    def _get_vector_store_class(self):
        """根据配置获取向量存储类"""
        store_type = self.config.vector_store.type
        if store_type == "qdrant":
            from .vector_store.qdrant_store import QdrantVectorStore
            return QdrantVectorStore
        elif store_type == "chroma":
            from .vector_store.chroma_store import ChromaVectorStore
            return ChromaVectorStore
        else:
            raise ValueError(f"不支持的向量存储类型: {store_type}")
```

### 3. 智能文档处理器（`knowledge/processor/`）

```python
# knowledge/processor/code_splitter.py
class CodeAwareTextSplitter:
    """代码感知的文本切分器 - 针对编程知识优化"""

    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_code(self, content: str, language: str = "python") -> List[DocumentChunk]:
        """智能切分代码文件"""
        chunks = []

        if language == "python":
            # Python特定切分逻辑
            chunks = self._split_python_code(content)
        elif language == "javascript":
            # JavaScript特定切分逻辑
            chunks = self._split_javascript_code(content)
        else:
            # 通用代码切分
            chunks = self._split_general_code(content)

        # 确保不超过chunk_size
        return self._adjust_chunk_sizes(chunks)

    def _split_python_code(self, content: str) -> List[DocumentChunk]:
        """切分Python代码，按函数/类边界"""
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_metadata = {}

        for i, line in enumerate(lines):
            # 检测函数定义
            if line.strip().startswith('def '):
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, current_metadata))
                    current_chunk = current_chunk[-self.chunk_overlap:]  # 保留重叠

                # 提取函数信息
                func_name = line.split('def ')[1].split('(')[0].strip()
                current_metadata = {
                    'type': 'function',
                    'name': func_name,
                    'line_start': i
                }

            # 检测类定义
            elif line.strip().startswith('class '):
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, current_metadata))
                    current_chunk = current_chunk[-self.chunk_overlap:]
```