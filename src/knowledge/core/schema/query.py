"""
查询数据模型定义
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
from enum import Enum


class QueryType(Enum):
    """查询类型枚举"""
    SEMANTIC = "semantic"      # 语义查询
    KEYWORD = "keyword"        # 关键词查询
    HYBRID = "hybrid"          # 混合查询
    STRUCTURED = "structured"  # 结构化查询


@dataclass
class Query:
    """查询模型"""
    
    text: str
    query_type: QueryType = QueryType.SEMANTIC
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5
    similarity_threshold: float = 0.7
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.filters:
            self.filters = {}
    
    def add_filter(self, field: str, value: Any, operator: str = "eq") -> None:
        """添加过滤器"""
        if 'filters' not in self.metadata:
            self.metadata['filters'] = {}
        
        self.metadata['filters'][field] = {
            'value': value,
            'operator': operator
        }
    
    def set_top_k(self, top_k: int) -> None:
        """设置返回结果数量"""
        self.top_k = top_k
    
    def set_similarity_threshold(self, threshold: float) -> None:
        """设置相似度阈值"""
        self.similarity_threshold = threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'text': self.text,
            'query_type': self.query_type.value,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'filters': self.filters,
            'top_k': self.top_k,
            'similarity_threshold': self.similarity_threshold
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Query':
        """从字典创建查询"""
        # 处理时间戳
        created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        
        # 处理查询类型
        query_type = QueryType(data.get('query_type', 'semantic'))
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            text=data['text'],
            query_type=query_type,
            metadata=data.get('metadata', {}),
            created_at=created_at,
            filters=data.get('filters'),
            top_k=data.get('top_k', 5),
            similarity_threshold=data.get('similarity_threshold', 0.7)
        )


@dataclass
class QueryResult:
    """查询结果模型"""
    
    query: Query
    chunks: list[Any]  # Chunk对象列表
    total_count: int = 0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __len__(self) -> int:
        return len(self.chunks)
    
    def get_top_chunks(self, top_k: Optional[int] = None) -> list[Any]:
        """获取前top_k个结果"""
        if top_k is None:
            top_k = self.query.top_k
        
        # 按相似度排序（假设chunks有similarity_score属性）
        sorted_chunks = sorted(self.chunks, key=lambda x: getattr(x, 'similarity_score', 0), reverse=True)
        return sorted_chunks[:top_k]
    
    def filter_by_threshold(self, threshold: Optional[float] = None) -> list[Any]:
        """根据阈值过滤结果"""
        if threshold is None:
            threshold = self.query.similarity_threshold
        
        return [chunk for chunk in self.chunks if getattr(chunk, 'similarity_score', 0) >= threshold]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'query': self.query.to_dict(),
            'chunks': [chunk.to_dict() if hasattr(chunk, 'to_dict') else chunk for chunk in self.chunks],
            'total_count': self.total_count,
            'execution_time': self.execution_time,
            'metadata': self.metadata
        }


@dataclass
class QueryBatch:
    """批量查询模型"""
    
    queries: list[Query]
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __len__(self) -> int:
        return len(self.queries)
    
    def add_query(self, query: Query) -> None:
        """添加查询到批次"""
        self.queries.append(query)
    
    def get_queries_by_type(self, query_type: QueryType) -> list[Query]:
        """根据类型筛选查询"""
        return [query for query in self.queries if query.query_type == query_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'batch_id': self.batch_id,
            'queries': [query.to_dict() for query in self.queries],
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata
        }