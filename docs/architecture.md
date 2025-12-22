# adpt-mech-agent 自适应机制智能体框架架构文档

## 一、整体架构设计原则

**核心设计理念**：

1. **分层架构** - 清晰的模块边界，遵循单一职责原则
2. **插件化设计** - 各组件可独立替换和扩展
3. **配置驱动** - 通过配置文件管理不同环境和部署场景
4. **异步优先** - 全链路异步处理，提升并发性能
5. **知识感知** - 深度集成RAG能力，使智能体具备持续学习能力

## 二、实际项目架构结构

### 实际项目目录结构（基于当前代码）：

```
adpt-mech-agent/
├── src/                           # 源代码主目录
│   ├── agents/                    # Agent核心模块
│   │   ├── impls/                # Agent实现层
│   │   │   ├── llm/              # LLM实现
│   │   │   │   ├── __init__.py
│   │   │   │   ├── mock_llm.py     # MockLLM实现
│   │   │   │   ├── openai_llm.py   # OpenAI客户端实现
│   │   │   │   ├── deepseek_llm.py # DeepSeek客户端实现
│   │   │   │   └── llm_factory.py  # LLM工厂类
│   │   │   └── __init__.py
│   │   │
│   │   ├── models/               # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── agent_config.py   # Agent配置模型
│   │   │   ├── agent_profile.py  # Agent配置文件
│   │   │   ├── llm_config.py     # LLM配置模型
│   │   │   ├── message_config.py # 消息配置模型
│   │   │   └── config_change_log.py # 配置变更日志
│   │   │
│   │   ├── prompts/              # Prompt模板管理
│   │   │   ├── __init__.py
│   │   │   └── prompt_template.py # Prompt模板类
│   │   │
│   │   ├── repositories/         # 数据访问层
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py # 基础仓储类
│   │   │   ├── agent_repository.py # Agent仓储
│   │   │   └── llm_repository.py # LLM仓储
│   │   │
│   │   ├── tools/                # Agent工具系统
│   │   │   ├── __init__.py
│   │   │   ├── tool_base.py      # 工具基类
│   │   │   ├── registry.py       # 工具注册
│   │   │   ├── chain.py          # 工具链管理
│   │   │   ├── async_executor.py # 异步执行器
│   │   │   └── builtin/          # 内置工具
│   │   │       ├── __init__.py
│   │   │       ├── calculator.py # 计算工具
│   │   │       ├── search.py     # 搜索工具
│   │   │       ├── knowledge_tool.py # 知识检索工具
│   │   │       └── validator.py  # 验证工具
│   │   │
│   │   ├── utils/                # Agent工具函数
│   │   │   └── llm_stream_helper.py # LLM流式助手
│   │   │
│   │   └── managers_DEL/         # 旧版管理器（待重构）
│   │       ├── __init__.py
│   │       ├── agent_manager.py  # 旧版Agent管理器
│   │       └── llm_manager.py    # 旧版LLM管理器
│   │
│   ├── knowledge/                # 知识库RAG模块
│   │   ├── core/                # 知识库核心
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # 知识库配置类
│   │   │   ├── knowledge_base.py # 知识库主类
│   │   │   ├── knowledge_base_interface.py # 知识库接口
│   │   │   └── schema/          # 数据模型
│   │   │       ├── __init__.py
│   │   │       ├── document.py  # Document模型
│   │   │       ├── chunk.py     # Chunk模型
│   │   │       └── query.py     # Query模型
│   │   │
│   │   ├── stores/              # 向量存储实现
│   │   │   ├── __init__.py
│   │   │   ├── store_base.py    # 向量存储接口
│   │   │   ├── qdrant_store.py  # Qdrant实现
│   │   │   ├── chroma_store.py  # Chroma实现
│   │   │   └── manager.py       # 多向量库管理
│   │   │
│   │   ├── embedders/           # 嵌入模型
│   │   │   ├── __init__.py
│   │   │   ├── embedder_base.py # 嵌入模型接口
│   │   │   ├── bge_embedder.py  # BGE-M3实现
│   │   │   ├── openai_embedder.py # OpenAI实现
│   │   │   └── local_embedder.py # 本地模型实现
│   │   │
│   │   ├── retrievers/          # 检索器
│   │   │   ├── __init__.py
│   │   │   ├── retriever_base.py # 检索器接口
│   │   │   ├── vector_retriever.py # 向量检索
│   │   │   ├── bm25_retriever.py # BM25关键词检索
│   │   │   ├── hybrid_retriever.py # 混合检索
│   │   │   └── reranker.py      # 重排序器
│   │   │
│   │   └── processors/          # 文档处理器
│   │       ├── __init__.py
│   │       ├── processor_base.py # 处理器接口
│   │       ├── document_loader.py # 文档加载器
│   │       ├── text_splitter.py   # 文本切分器
│   │       ├── code_splitter.py   # 代码感知切分器
│   │       └── metadata_extractor.py # 元数据提取
│   │
│   ├── managers/                # 新版管理器
│   │   ├── __init__.py
│   │   ├── agent_manager.py     # Agent管理器
│   │   ├── agent_state_manager.py # Agent状态管理器
│   │   ├── cache_manager.py     # 缓存管理器
│   │   └── config_manager.py    # 配置管理器
│   │
│   ├── services/                # 业务服务层
│   │   ├── __init__.py
│   │   ├── agent_service.py     # Agent服务
│   │   ├── agent_config_service.py # Agent配置服务
│   │   ├── llm_service.py       # LLM服务
│   │   ├── prompt_template_service.py # Prompt模板服务
│   │   ├── prompt_template_service_v2.py # Prompt模板服务V2
│   │   └── async_prompt_template_service.py # 异步Prompt模板服务
│   │
│   └── shared/                  # 共享模块
│       ├── __init__.py
│       ├── utils/               # 共享工具函数
│       │   ├── __init__.py
│       │   ├── logger.py        # 统一日志系统
│       │   ├── validators.py    # 统一验证器
│       │   ├── file_utils.py    # 文件操作工具
│       │   ├── async_utils.py   # 异步工具
│       │   ├── db_utils.py      # 数据库工具
│       │   ├── redis_utils.py   # Redis工具
│       │   ├── log_config.py    # 日志配置
│       │   └── tracing.py       # 链路追踪
│       │
│       └── exceptions/          # 统一异常体系
│           ├── __init__.py
│           ├── base_errors.py   # 异常基类
│           ├── agent_errors.py  # Agent相关异常
│           ├── knowledge_errors.py # 知识库异常
│           └── tool_errors.py   # 工具异常
│
├── configs/                     # 配置文件目录
│   └── config.yaml              # 主配置文件
│
├── tests/                       # 测试目录
│   └── test_logging.py          # 日志测试
│
├── docs/                        # 项目文档
│   └── architecture.md          # 架构文档
│
├── main.py                      # 应用主入口
├── pyproject.toml               # Python项目配置
├── .env.example                 # 环境变量示例
├── README.md                    # 项目说明
└── requirements.txt             # 依赖清单
```
## 三、核心架构组件详解

### 1. Agent系统架构

#### Agent管理器（src/managers/agent_manager.py）

```python
class AgentManager:
    """Agent实例管理器 - 只管理内存中的Agent实例"""
    
    def __init__(self):
        self.agents: Dict[str, object] = {}  # 使用object类型以支持任何Agent实现
        self.active_agent_id: Optional[str] = None
        self._lock = asyncio.Lock()
    
    async def register(self, agent_id: str, agent: object) -> bool:
        """注册Agent实例"""
        async with self._lock:
            if agent_id in self.agents:
                logger.warning(f"Agent {agent_id} already registered")
                return False
            
            self.agents[agent_id] = agent
            
            # 如果没有活跃Agent，设置为活跃
            if self.active_agent_id is None:
                self.active_agent_id = agent_id
            
            logger.info(f"Agent registered: {agent_id}")
            return True
    
    async def unregister(self, agent_id: str) -> bool:
        """注销Agent实例"""
        async with self._lock:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # 如果注销的是活跃Agent，重新选择
            if self.active_agent_id == agent_id:
                self.active_agent_id = next(
                    (id_ for id_ in self.agents.keys() if id_ != agent_id),
                    None
                )
            
            # 关闭Agent
            agent = self.agents.pop(agent_id)
            await self._close_agent(agent)
            
            logger.info(f"Agent unregistered: {agent_id}")
            return True
```

#### Agent服务（src/services/agent_service.py）

```python
class AgentService:
    """Agent服务 - 集成创建、管理、缓存"""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.agent_manager = AgentManager()
        self._initialized = False
    
    async def create_agent(
        self,
        config: AgentConfig,
        agent_id: Optional[str] = None,
        use_cache: bool = True
    ) -> BaseAgent:
        """
        创建Agent实例
        
        Args:
            config: Agent配置
            agent_id: 自定义Agent ID，如果为None则使用配置名
            use_cache: 是否使用缓存
            
        Returns:
            BaseAgent实例
        """
        if agent_id is None:
            agent_id = f"{config.name}_{config.agent_type}"
        
        # 1. 检查缓存中的配置
        if use_cache:
            cached_config = await self._get_cached_config(agent_id)
            if cached_config:
                config = cached_config
        
        # 2. 创建或获取LLM
        llm = await self._get_or_create_llm(config)
        
        # 3. 创建Agent实例
        agent = await self._create_agent_instance(config, llm)
        
        # 4. 注册到管理器
        await self.agent_manager.register(agent_id, agent)
        
        # 5. 缓存配置
        if use_cache:
            await self._cache_config(agent_id, config)
        
        logger.info(f"Agent created: {agent_id}")
        return agent
```

### 2. 知识库系统架构

#### 知识库基础模型（src/knowledge/core/schema/）

```python
# src/knowledge/base/schema/chunk.py
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class Chunk(BaseModel):
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

#### 知识库主类（src/knowledge/core/knowledge_base.py）

```python
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
```
            raise ValueError(f"不支持的向量存储类型: {store_type}")

### 3. LLM系统架构

#### LLM工厂（src/agents/impls/llm/llm_factory.py）

```python
class LLMFactory:
    """LLM工厂类 - 根据配置创建不同类型的LLM实例"""

    @staticmethod
    def create_llm(config: LLMConfig) -> BaseLLM:
        """
        根据配置创建LLM实例
        
        Args:
            config: LLM配置对象
            
        Returns:
            BaseLLM实例
        """
        provider = config.provider.lower()

        if provider == "openai":
            from src.infrastructure.llm.impls.openai_llm import OpenAIClient
            return OpenAIClient(config)
        elif provider == "deepseek":
            from src.infrastructure.llm.impls.deepseek_llm import DeepSeekClient
            return DeepSeekClient(config)
        elif provider == "mock":
            from src.infrastructure.llm.impls.mock_llm import MockLLM
            return MockLLM(config)
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")
```

#### LLM服务（src/services/llm_service.py）

```python
class LLMService:
    """LLM服务 - 提供LLM实例的管理和缓存"""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.llm_repository = LLMRepository()
        self._llm_cache: Dict[str, BaseLLM] = {}
    
    async def get_or_create_llm(self, llm_config_id: str) -> BaseLLM:
        """
        获取或创建LLM实例
        
        Args:
            llm_config_id: LLM配置ID
            
        Returns:
            BaseLLM实例
        """
        # 1. 检查内存缓存
        if llm_config_id in self._llm_cache:
            return self._llm_cache[llm_config_id]
        
        # 2. 从数据库获取配置
        llm_config = await self.llm_repository.get_by_id(llm_config_id)
        if not llm_config:
            raise ValueError(f"LLM配置不存在: {llm_config_id}")
        
        # 3. 创建LLM实例
        llm = LLMFactory.create_llm(llm_config)
        
        # 4. 缓存到内存
        self._llm_cache[llm_config_id] = llm
        
        logger.info(f"LLM实例创建成功: {llm_config_id}")
        return llm
```

### 4. 智能文档处理器（`knowledge/processors/`）

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

## 四、架构现状分析与改进建议

### 1. 当前架构优势

**服务层架构**：
- 新增了清晰的服务层（services/），实现了业务逻辑与数据访问的分离
- AgentService和LLMService提供了统一的管理接口
- 支持缓存机制，提升性能表现

**数据访问层**：
- 引入了仓储模式（repositories/），封装了数据访问细节
- 支持多种数据源，便于扩展
- 提供了基础仓储类，减少重复代码

**配置驱动**：
- 完善的配置模型体系（models/）
- 支持配置变更日志记录
- 灵活的配置管理机制

### 2. 当前架构特点

#### 分层架构更加清晰
- **表示层**: main.py作为应用入口
- **服务层**: services/目录下的各类服务
- **业务层**: managers/目录下的管理器
- **数据层**: repositories/目录下的仓储类
- **基础设施层**: shared/目录下的共享组件

#### 异步处理完善
- 全链路异步支持
- 内置异步执行器和流式助手
- 完善的错误处理和重试机制

### 3. 待改进方面

#### 旧版代码清理
- `managers_DEL/`目录中的旧版管理器需要重构或移除
- 统一新旧版本的接口差异
- 清理过时的依赖和引用

#### 测试覆盖不足
- 目前只有基础的日志测试
- 需要增加单元测试和集成测试
- 完善测试框架和CI/CD流程

#### 文档不完整
- 缺少详细的API文档
- 用户指南和快速开始文档需要补充
- 部署和运维文档需要完善

### 4. 架构演进方向

#### 微服务化改造
- 考虑将Agent、Knowledge、LLM等服务拆分为独立微服务
- 引入消息队列进行服务间通信
- 实现服务的水平扩展能力

#### 监控和可观测性
- 集成链路追踪系统
- 增加性能监控指标
- 实现健康检查和熔断机制

#### 配置中心集成
- 引入外部配置中心（如Consul、Apollo）
- 支持配置的热更新
- 实现配置的版本管理和回滚

## 五、部署与运维

### 1. 环境配置
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件设置API密钥等配置
```

### 2. 项目结构说明
```bash
# 主要入口文件
main.py                    # 应用主入口

# 核心模块
src/agents/               # Agent系统
src/knowledge/            # 知识库RAG系统
src/managers/             # 管理器层
src/services/             # 服务层
src/shared/               # 共享组件

# 配置文件
configs/config.yaml       # 主配置文件
.env.example              # 环境变量模板
```

### 3. 运行方式
```python
# 直接运行主程序
python main.py

# 或通过模块方式运行
python -m src.main
```

### 4. 监控与调试
- 使用内置日志系统进行调试（已集成log_config.py）
- 查看tests/test_logging.py了解日志配置
- 监控Agent状态和知识库健康状况

## 六、总结

本项目采用分层架构设计，构建了一个功能完善的智能体系统。通过引入服务层和仓储模式，实现了业务逻辑与数据访问的清晰分离。架构设计充分考虑了生产环境的实际需求，包括异步处理、缓存机制、配置管理等关键特性。

当前架构已具备以下特点：
- **分层清晰**：表示层、服务层、业务层、数据层、基础设施层
- **异步支持**：全链路异步处理，提升系统吞吐量
- **配置驱动**：完善的配置模型体系，支持灵活配置
- **知识集成**：深度集成了RAG技术，支持多种向量数据库

未来发展方向包括清理旧版代码、完善测试覆盖、增加监控可观测性，以及考虑微服务化改造。