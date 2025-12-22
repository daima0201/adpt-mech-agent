"""
文档数据模型定义
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import uuid
from datetime import datetime


@dataclass
class Document:
    """文档模型"""
    
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    language: str = "zh"  # 默认中文
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.source and 'source' in self.metadata:
            self.source = self.metadata['source']
        if not self.title and 'title' in self.metadata:
            self.title = self.metadata['title']
        if not self.author and 'author' in self.metadata:
            self.author = self.metadata['author']
    
    def update_content(self, new_content: str) -> None:
        """更新文档内容"""
        self.content = new_content
        self.updated_at = datetime.now()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'source': self.source,
            'title': self.title,
            'author': self.author,
            'language': self.language
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """从字典创建文档"""
        # 处理时间戳
        created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        updated_at = datetime.fromisoformat(data['updated_at']) if isinstance(data['updated_at'], str) else data['updated_at']
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            content=data['content'],
            metadata=data.get('metadata', {}),
            created_at=created_at,
            updated_at=updated_at,
            source=data.get('source'),
            title=data.get('title'),
            author=data.get('author'),
            language=data.get('language', 'zh')
        )


@dataclass
class DocumentBatch:
    """文档批次处理模型"""
    
    documents: list[Document]
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __len__(self) -> int:
        return len(self.documents)
    
    def add_document(self, document: Document) -> None:
        """添加文档到批次"""
        self.documents.append(document)
    
    def get_documents_by_source(self, source: str) -> list[Document]:
        """根据来源筛选文档"""
        return [doc for doc in self.documents if doc.source == source]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'batch_id': self.batch_id,
            'documents': [doc.to_dict() for doc in self.documents],
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata
        }