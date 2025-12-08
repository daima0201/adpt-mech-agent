"""
配置模型定义
定义项目使用的配置数据模型
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class VectorStoreType(Enum):
    """向量存储类型"""
    CHROMA = "chroma"
    QDRANT = "qdrant"


class EmbedderType(Enum):
    """嵌入器类型"""
    OPENAI = "openai"
    BGE = "bge"
    LOCAL = "local"


class AgentType(Enum):
    """智能体类型"""
    SIMPLE = "simple"
    REACT = "react"
    PLAN_SOLVE = "plan_solve"
    REFLECTION = "reflection"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str
    port: int = 5432
    username: str = ""
    password: str = ""
    database: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class LLMConfig:
    """LLM配置"""
    model: str
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class KnowledgeBaseConfig:
    """知识库配置"""
    name: str
    vector_store: VectorStoreType = VectorStoreType.CHROMA
    embedder: EmbedderType = EmbedderType.OPENAI
    chunk_size: int = 1000
    chunk_overlap: int = 200
    similarity_threshold: float = 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['vector_store'] = self.vector_store.value
        result['embedder'] = self.embedder.value
        return result


@dataclass
class AgentConfig:
    """智能体配置"""
    agent_type: AgentType
    name: str
    description: str = ""
    system_prompt: str = ""
    tools: List[str] = None
    knowledge_bases: List[str] = None
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = []
        if self.knowledge_bases is None:
            self.knowledge_bases = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['agent_type'] = self.agent_type.value
        return result


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ConfigSchema:
    """完整配置schema"""
    database: Optional[DatabaseConfig] = None
    llm: Optional[LLMConfig] = None
    knowledge_base: Optional[KnowledgeBaseConfig] = None
    agents: List[AgentConfig] = None
    logging: LoggingConfig = None
    
    def __post_init__(self):
        if self.agents is None:
            self.agents = []
        if self.logging is None:
            self.logging = LoggingConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        
        if self.database:
            result['database'] = self.database.to_dict()
        if self.llm:
            result['llm'] = self.llm.to_dict()
        if self.knowledge_base:
            result['knowledge_base'] = self.knowledge_base.to_dict()
        
        result['agents'] = [agent.to_dict() for agent in self.agents]
        result['logging'] = self.logging.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigSchema':
        """从字典创建配置schema"""
        database_data = data.get('database', {})
        llm_data = data.get('llm', {})
        kb_data = data.get('knowledge_base', {})
        agents_data = data.get('agents', [])
        logging_data = data.get('logging', {})
        
        database = DatabaseConfig(**database_data) if database_data else None
        llm = LLMConfig(**llm_data) if llm_data else None
        
        # 处理枚举类型转换
        if kb_data:
            if 'vector_store' in kb_data:
                kb_data['vector_store'] = VectorStoreType(kb_data['vector_store'])
            if 'embedder' in kb_data:
                kb_data['embedder'] = EmbedderType(kb_data['embedder'])
            knowledge_base = KnowledgeBaseConfig(**kb_data)
        else:
            knowledge_base = None
        
        agents = []
        for agent_data in agents_data:
            if 'agent_type' in agent_data:
                agent_data['agent_type'] = AgentType(agent_data['agent_type'])
            agents.append(AgentConfig(**agent_data))
        
        logging = LoggingConfig(**logging_data)
        
        return cls(
            database=database,
            llm=llm,
            knowledge_base=knowledge_base,
            agents=agents,
            logging=logging
        )