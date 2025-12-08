"""
知识库核心功能测试
测试KnowledgeBase类和基础功能
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os

from src.knowledge.core.knowledge_base import KnowledgeBase
from src.knowledge.core.schema.document import Document
from src.knowledge.core.schema.chunk import Chunk
from src.knowledge.stores.base import VectorStore
from src.knowledge.embedders.base import Embedder
from src.shared.config.manager import ConfigManager


class TestKnowledgeBase:
    """知识库测试类"""
    
    @pytest.fixture
    def mock_components(self):
        """创建模拟组件"""
        # 模拟向量存储
        mock_store = Mock(spec=VectorStore)
        mock_store.add_documents.return_value = ["doc1", "doc2"]
        mock_store.search.return_value = [
            Mock(content="搜索结果1", score=0.9, metadata={}),
            Mock(content="搜索结果2", score=0.8, metadata={})
        ]
        
        # 模拟嵌入器
        mock_embedder = Mock(spec=Embedder)
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        
        return mock_store, mock_embedder
    
    @pytest.fixture
    def knowledge_base(self, mock_components):
        """创建知识库实例"""
        mock_store, mock_embedder = mock_components
        config = ConfigManager().get_config()
        
        return KnowledgeBase(
            vector_store=mock_store,
            embedder=mock_embedder,
            config=config
        )
    
    def test_initialization(self, knowledge_base, mock_components):
        """测试初始化"""
        mock_store, mock_embedder = mock_components
        
        assert knowledge_base.vector_store == mock_store
        assert knowledge_base.embedder == mock_embedder
        assert hasattr(knowledge_base, 'config')
    
    def test_add_document(self, knowledge_base, mock_components):
        """测试添加文档"""
        mock_store, _ = mock_components
        
        # 创建测试文档
        document = Document(
            content="这是一个测试文档",
            metadata={"source": "test.txt", "type": "text"}
        )
        
        # 添加文档
        result = knowledge_base.add_document(document)
        
        # 验证向量存储被调用
        mock_store.add_documents.assert_called_once()
        assert len(result) > 0
    
    def test_search_documents(self, knowledge_base, mock_components):
        """测试文档搜索"""
        mock_store, mock_embedder = mock_components
        
        query = "测试查询"
        top_k = 5
        
        # 执行搜索
        results = knowledge_base.search(query, top_k=top_k)
        
        # 验证嵌入器被调用
        mock_embedder.embed.assert_called_with(query)
        
        # 验证向量存储被调用
        mock_store.search.assert_called()
        
        # 验证结果格式
        assert len(results) == 2
        assert results[0].content == "搜索结果1"
        assert results[0].score == 0.9
    
    def test_batch_add_documents(self, knowledge_base, mock_components):
        """测试批量添加文档"""
        mock_store, _ = mock_components
        
        # 创建多个文档
        documents = [
            Document(content=f"文档{i}", metadata={"id": i}) 
            for i in range(3)
        ]
        
        # 批量添加
        results = knowledge_base.batch_add_documents(documents)
        
        # 验证批量操作
        mock_store.add_documents.assert_called_once()
        assert len(results) == 3
    
    def test_delete_document(self, knowledge_base, mock_components):
        """测试删除文档"""
        mock_store, _ = mock_components
        
        doc_id = "test_doc_123"
        
        # 删除文档
        knowledge_base.delete_document(doc_id)
        
        # 验证删除操作
        mock_store.delete_document.assert_called_with(doc_id)
    
    def test_get_document_count(self, knowledge_base, mock_components):
        """测试获取文档数量"""
        mock_store, _ = mock_components
        mock_store.get_document_count.return_value = 100
        
        count = knowledge_base.get_document_count()
        
        assert count == 100
        mock_store.get_document_count.assert_called_once()


class TestDocumentProcessing:
    """文档处理测试类"""
    
    def test_document_creation(self):
        """测试文档创建"""
        content = "测试文档内容"
        metadata = {"source": "test.txt", "author": "tester"}
        
        doc = Document(content=content, metadata=metadata)
        
        assert doc.content == content
        assert doc.metadata == metadata
        assert doc.id is not None  # 应该自动生成ID
    
    def test_document_equality(self):
        """测试文档相等性"""
        doc1 = Document(content="相同内容", metadata={"id": 1})
        doc2 = Document(content="相同内容", metadata={"id": 1})
        doc3 = Document(content="不同内容", metadata={"id": 2})
        
        # 相同内容的文档应该相等
        assert doc1 == doc2
        assert doc1 != doc3
    
    def test_chunk_creation(self):
        """测试分块创建"""
        content = "这是一个较长的文本，需要被分割成多个块"
        metadata = {"source": "long_text.txt"}
        chunk_index = 0
        
        chunk = Chunk(
            content=content,
            metadata=metadata,
            chunk_index=chunk_index
        )
        
        assert chunk.content == content
        assert chunk.metadata == metadata
        assert chunk.chunk_index == chunk_index
        assert chunk.parent_doc_id is None


class TestKnowledgeBaseIntegration:
    """知识库集成测试类"""
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 使用临时目录进行测试
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置
            config = ConfigManager().get_config()
            
            # 创建真实的知识库实例（使用Chroma存储）
            from src.knowledge.stores.chroma_store import ChromaStore
            from src.knowledge.embedders.local_embedder import LocalEmbedder
            
            store_path = os.path.join(temp_dir, "chroma_test")
            vector_store = ChromaStore(persist_directory=store_path)
            embedder = LocalEmbedder()
            
            kb = KnowledgeBase(
                vector_store=vector_store,
                embedder=embedder,
                config=config
            )
            
            # 添加文档
            doc = Document(
                content="Python是一种高级编程语言",
                metadata={"source": "python_intro.txt"}
            )
            
            kb.add_document(doc)
            
            # 搜索文档
            results = kb.search("Python编程", top_k=1)
            
            # 验证搜索结果
            assert len(results) > 0
            assert "Python" in results[0].content
    
    def test_error_handling(self, knowledge_base, mock_components):
        """测试错误处理"""
        mock_store, mock_embedder = mock_components
        
        # 模拟嵌入失败
        mock_embedder.embed.side_effect = Exception("嵌入服务不可用")
        
        with pytest.raises(Exception) as exc_info:
            knowledge_base.search("测试查询")
        
        assert "嵌入服务不可用" in str(exc_info.value)
        
        # 模拟存储失败
        mock_store.add_documents.side_effect = Exception("存储写入失败")
        
        doc = Document(content="测试文档")
        
        with pytest.raises(Exception) as exc_info:
            knowledge_base.add_document(doc)
        
        assert "存储写入失败" in str(exc_info.value)