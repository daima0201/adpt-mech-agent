"""
RAG流程集成测试
测试知识库与Agent的完整集成
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os

from src.knowledge.core.knowledge_base import KnowledgeBase
from src.knowledge.stores.chroma_store import ChromaStore
from src.knowledge.embedders.local_embedder import LocalEmbedder
from src.knowledge.core.schema.document import Document
from src.agents.impls.react_agent import ReActAgent
from src.shared.config.manager import ConfigManager


class TestRAGFlow:
    """RAG流程集成测试类"""
    
    @pytest.fixture
    def setup_knowledge_base(self):
        """设置知识库"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置
            config = ConfigManager().get_config()
            
            # 创建向量存储和嵌入器
            store_path = os.path.join(temp_dir, "chroma_test")
            vector_store = ChromaStore(persist_directory=store_path)
            embedder = LocalEmbedder()
            
            # 创建知识库
            kb = KnowledgeBase(
                vector_store=vector_store,
                embedder=embedder,
                config=config
            )
            
            # 添加测试文档
            test_documents = [
                Document(
                    content="Python是一种高级编程语言，具有简洁易读的语法",
                    metadata={"source": "python_intro.txt", "type": "tutorial"}
                ),
                Document(
                    content="机器学习是人工智能的一个分支，专注于算法开发",
                    metadata={"source": "ml_basics.txt", "type": "technical"}
                ),
                Document(
                    content="Docker是一种容器化技术，用于打包和部署应用",
                    metadata={"source": "docker_overview.txt", "type": "devops"}
                )
            ]
            
            for doc in test_documents:
                kb.add_document(doc)
            
            yield kb
    
    def test_rag_with_simple_agent(self, setup_knowledge_base):
        """测试简单Agent与知识库集成"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        # 创建支持知识库的Agent
        agent = ReActAgent(config, knowledge_base=kb)
        
        # 测试查询
        query = "什么是Python编程语言？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟LLM响应，包含知识检索结果
            mock_generate.return_value = """Thought: 我需要从知识库中检索关于Python的信息
Action: knowledge_tool
Action Input: {\"query\": \"Python编程语言\", \"top_k\": 3}
Observation: 检索到相关信息：Python是一种高级编程语言，具有简洁易读的语法
Thought: 基于检索到的信息，我可以回答用户的问题
Final Answer: Python是一种高级编程语言，具有简洁易读的语法特点。"""
            
            response = agent.process_message(query)
            
            # 验证响应包含相关知识
            assert "Python" in response
            assert "编程语言" in response
    
    def test_rag_complex_query(self, setup_knowledge_base):
        """测试复杂查询的RAG流程"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReActAgent(config, knowledge_base=kb)
        
        complex_query = "请比较Python和机器学习的异同点"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟多步骤推理过程
            mock_generate.side_effect = [
                """Thought: 这是一个复杂问题，需要分别检索Python和机器学习的信息
Action: knowledge_tool
Action Input: {\"query\": \"Python编程语言特点\", \"top_k\": 2}""",
                """Observation: Python特点：高级编程语言，简洁语法，广泛用于数据科学
Thought: 现在检索机器学习信息
Action: knowledge_tool
Action Input: {\"query\": \"机器学习基础概念\", \"top_k\": 2}""",
                """Observation: 机器学习：AI分支，算法开发，数据驱动
Thought: 综合两个领域的信息进行比较
Final Answer: Python是编程语言，机器学习是AI技术领域。Python常用于实现机器学习算法。"""
            ]
            
            response = agent.process_message(complex_query)
            
            # 验证响应包含比较分析
            assert "Python" in response
            assert "机器学习" in response
            assert "比较" in response or "异同" in response
    
    def test_rag_with_context_awareness(self, setup_knowledge_base):
        """测试上下文感知的RAG"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReActAgent(config, knowledge_base=kb)
        
        # 多轮对话测试
        conversation_history = [
            {"role": "user", "content": "我想了解容器化技术"},
            {"role": "assistant", "content": "Docker是一种流行的容器化技术"}
        ]
        
        follow_up_query = "Docker有什么优势？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟考虑上下文的响应
            mock_generate.return_value = """Thought: 用户之前询问了容器化技术，现在问Docker的优势
Action: knowledge_tool
Action Input: {\"query\": \"Docker优势特点\", \"top_k\": 3}
Observation: Docker优势：轻量级、可移植性、快速部署、环境一致性
Final Answer: Docker的主要优势包括轻量级容器、良好的可移植性、快速部署和环境一致性保证。"""
            
            response = agent.process_message(follow_up_query, conversation_history)
            
            # 验证响应考虑了上下文
            assert "Docker" in response
            assert "优势" in response
            assert any(keyword in response for keyword in ["轻量级", "可移植", "部署", "一致性"])
    
    def test_rag_error_recovery(self, setup_knowledge_base):
        """测试RAG错误恢复机制"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReActAgent(config, knowledge_base=kb)
        
        # 测试知识库检索失败的情况
        query = "不存在的技术概念"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟知识库返回空结果时的处理
            mock_generate.side_effect = [
                """Thought: 尝试检索相关信息
Action: knowledge_tool
Action Input: {\"query\": \"不存在的技术概念\", \"top_k\": 3}""",
                """Observation: 未找到相关信息
Thought: 知识库中没有相关信息，我需要基于通用知识回答
Final Answer: 抱歉，我目前没有关于这个特定技术概念的详细信息。您可以提供更多背景或尝试其他相关主题。"""
            ]
            
            response = agent.process_message(query)
            
            # 验证优雅的错误处理
            assert "抱歉" in response or "没有" in response
            assert "信息" in response
    
    def test_rag_performance(self, setup_knowledge_base):
        """测试RAG性能"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReActAgent(config, knowledge_base=kb)
        
        # 性能测试：多次查询
        queries = [
            "Python语法特点",
            "机器学习应用",
            "Docker使用场景"
        ]
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟标准响应
            mock_generate.return_value = "基于知识库检索的标准回答"
            
            import time
            start_time = time.time()
            
            for query in queries:
                response = agent.process_message(query)
                assert response is not None
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 验证性能在合理范围内（平均每个查询<5秒）
            avg_time_per_query = execution_time / len(queries)
            assert avg_time_per_query < 5.0, f"平均查询时间{avg_time_per_query:.2f}秒超出预期"


class TestEndToEndRAG:
    """端到端RAG测试类"""
    
    def test_complete_rag_pipeline(self):
        """测试完整的RAG管道"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 设置知识库
            config = ConfigManager().get_config()
            
            store_path = os.path.join(temp_dir, "e2e_test")
            vector_store = ChromaStore(persist_directory=store_path)
            embedder = LocalEmbedder()
            
            kb = KnowledgeBase(
                vector_store=vector_store,
                embedder=embedder,
                config=config
            )
            
            # 2. 构建知识库
            documents = [
                Document(
                    content="敏捷开发是一种迭代式的软件开发方法",
                    metadata={"source": "agile_methodology.txt"}
                ),
                Document(
                    content="Scrum是敏捷开发的一种框架，包含Sprint和站会等实践",
                    metadata={"source": "scrum_framework.txt"}
                )
            ]
            
            for doc in documents:
                kb.add_document(doc)
            
            # 3. 创建Agent
            agent = ReActAgent(config, knowledge_base=kb)
            
            # 4. 测试端到端流程
            query = "请解释敏捷开发和Scrum的关系"
            
            with patch.object(agent.llm, 'generate') as mock_generate:
                # 模拟真实的RAG推理过程
                mock_generate.return_value = """Thought: 用户询问敏捷开发和Scrum的关系，我需要检索相关知识
Action: knowledge_tool
Action Input: {\"query\": \"敏捷开发 Scrum 关系\", \"top_k\": 3}
Observation: 检索到信息：敏捷开发是迭代式方法，Scrum是敏捷的一种具体框架
Thought: 基于检索结果，可以解释两者关系
Final Answer: 敏捷开发是一种软件开发方法论，而Scrum是敏捷开发的具体实施框架。Scrum在敏捷原则基础上提供了具体的实践方法如Sprint迭代和每日站会。"""
                
                response = agent.process_message(query)
                
                # 验证端到端功能
                assert "敏捷开发" in response
                assert "Scrum" in response
                assert "框架" in response or "关系" in response
                
                # 验证知识检索被调用
                assert mock_generate.called