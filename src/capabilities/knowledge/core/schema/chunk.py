"""
文档块数据模型定义
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime


@dataclass
class Chunk:
    """文档块模型"""
    
    content: str
    document_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    embedding: Optional[List[float]] = None
    start_position: int = 0
    end_position: int = 0
    similarity_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.end_position == 0 and self.content:
            self.end_position = len(self.content)
    
    @property
    def size(self) -> int:
        """获取块大小（字符数）"""
        return len(self.content)
    
    @property
    def position_range(self) -> tuple[int, int]:
        """获取位置范围"""
        return (self.start_position, self.end_position)
    
    def set_embedding(self, embedding: List[float]) -> None:
        """设置嵌入向量"""
        self.embedding = embedding
    
    def set_similarity_score(self, score: float) -> None:
        """设置相似度分数"""
        self.similarity_score = score
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'content': self.content,
            'document_id': self.document_id,
            'metadata': self.metadata,
            'embedding': self.embedding,
            'start_position': self.start_position,
            'end_position': self.end_position,
            'similarity_score': self.similarity_score,
            'created_at': self.created_at.isoformat(),
            'size': self.size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chunk':
        """从字典创建块"""
        # 处理时间戳
        created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            content=data['content'],
            document_id=data['document_id'],
            metadata=data.get('metadata', {}),
            embedding=data.get('embedding'),
            start_position=data.get('start_position', 0),
            end_position=data.get('end_position', 0),
            similarity_score=data.get('similarity_score', 0.0),
            created_at=created_at
        )


@dataclass
class ChunkBatch:
    """块批次处理模型"""
    
    chunks: list[Chunk]
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __len__(self) -> int:
        return len(self.chunks)
    
    def add_chunk(self, chunk: Chunk) -> None:
        """添加块到批次"""
        self.chunks.append(chunk)
    
    def get_chunks_with_embeddings(self) -> list[Chunk]:
        """获取有嵌入向量的块"""
        return [chunk for chunk in self.chunks if chunk.embedding is not None]
    
    def get_top_chunks_by_score(self, top_k: int = 5) -> list[Chunk]:
        """根据相似度分数获取前top_k个块"""
        sorted_chunks = sorted(self.chunks, key=lambda x: x.similarity_score, reverse=True)
        return sorted_chunks[:top_k]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'batch_id': self.batch_id,
            'document_id': self.document_id,
            'chunks': [chunk.to_dict() for chunk in self.chunks],
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata
        }