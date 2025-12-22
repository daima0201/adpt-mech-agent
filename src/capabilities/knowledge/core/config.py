"""
知识库配置定义
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class KnowledgeConfig:
    """知识库配置类"""
    
    # 向量存储配置
    vector_store_config: Dict[str, Any] = field(default_factory=dict)
    
    # 嵌入器配置
    embedder_config: Dict[str, Any] = field(default_factory=dict)
    
    # 处理器配置
    processors_config: Dict[str, Any] = field(default_factory=dict)
    
    # 检索器配置
    retriever_config: Dict[str, Any] = field(default_factory=dict)
    
    # 其他通用配置
    chunk_size: int = 1000
    chunk_overlap: int = 200
    similarity_threshold: float = 0.7
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'KnowledgeConfig':
        """从配置文件加载配置"""
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)