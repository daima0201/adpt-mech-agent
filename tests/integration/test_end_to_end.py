"""
端到端集成测试
测试完整系统的功能和性能
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os
import time
from pathlib import Path

from src.knowledge.core.knowledge_base import KnowledgeBase
from src.knowledge.stores.chroma_store import ChromaStore
from src.knowledge.embedders.local_embedder import LocalEmbedder
from src.knowledge.processors.document_loader import DocumentLoader
from src.knowledge.processors.text_splitter import TextSplitter
from src.knowledge.core.schema.document import Document
from src.agents.impls.react_agent import ReActAgent
from src.shared.config.manager import ConfigManager


class TestEndToEndIntegration:
    """端到端集成测试类"""
    
    @pytest.fixture
    def setup_complete_system(self):
        """设置完整的系统环境"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置
            config = ConfigManager().get_config()
            
            # 设置向量存储
            store_path = os.path.join(temp_dir, "e2e_chroma")
            vector_store = ChromaStore(persist_directory=store_path)
            embedder = LocalEmbedder()
            
            # 创建知识库
            kb = KnowledgeBase(
                vector_store=vector_store,
                embedder=embedder,
                config=config
            )
            
            # 创建文档处理器
            loader = DocumentLoader()
            splitter = TextSplitter(chunk_size=200, chunk_overlap=50)
            
            # 创建Agent
            agent = ReActAgent(config, knowledge_base=kb)
            
            yield {
                'knowledge_base': kb,
                'document_loader': loader,
                'text_splitter': splitter,
                'agent': agent,
                'temp_dir': temp_dir
            }
    
    def test_complete_document_processing_pipeline(self, setup_complete_system):
        """测试完整的文档处理管道"""
        system = setup_complete_system
        
        # 创建测试文档
        test_content = """
        人工智能（AI）是计算机科学的一个分支，旨在创造能够执行通常需要人类智能的任务的机器。
        
        机器学习是AI的一个子集，它使计算机能够在没有明确编程的情况下学习和改进。
        
        深度学习是机器学习的一个子领域，使用神经网络模拟人脑的工作方式。
        """
        
        # 保存文档到临时文件
        doc_path = Path(system['temp_dir']) / "ai_concepts.txt"
        doc_path.write_text(test_content)
        
        # 测试文档加载
        documents = system['document_loader'].load_from_file(str(doc_path))
        assert len(documents) == 1
        assert "人工智能" in documents[0].content
        
        # 测试文本分割
        chunks = system['text_splitter'].split_documents(documents)
        assert len(chunks) > 1  # 应该被分割成多个块
        
        # 测试添加到知识库
        for chunk in chunks:
            system['knowledge_base'].add_document(chunk)
        
        # 验证知识库内容
        results = system['knowledge_base'].search("机器学习", top_k=3)
        assert len(results) > 0
    
    def test_real_world_scenario_tech_consultation(self, setup_complete_system):
        """测试真实世界场景：技术咨询"""
        system = setup_complete_system
        
        # 构建技术知识库
        tech_docs = [
            Document(
                content="云计算提供按需计算资源，包括计算能力、存储和网络",
                metadata={"source": "cloud_computing.txt", "category": "infrastructure"}
            ),
            Document(
                content="AWS提供广泛的云服务，包括EC2、S3、Lambda等",
                metadata={"source": "aws_services.txt", "category": "cloud"}
            ),
            Document(
                content="微服务架构将应用拆分为小型独立服务，提高可维护性",
                metadata={"source": "microservices.txt", "category": "architecture"}
            ),
            Document(
                content="Docker容器化技术实现应用的环境一致性",
                metadata={"source": "docker.txt", "category": "devops"}
            ),
            Document(
                content="Kubernetes是容器编排平台，自动化部署和管理",
                metadata={"source": "kubernetes.txt", "category": "orchestration"}
            )
        ]
        
        for doc in tech_docs:
            system['knowledge_base'].add_document(doc)
        
        # 模拟技术咨询对话
        conversation = [
            {"role": "user", "content": "我们公司想迁移到云原生架构，有什么建议？"}
        ]
        
        with patch.object(system['agent'].llm, 'generate') as mock_generate:
            # 模拟复杂的多步骤咨询过程
            mock_generate.side_effect = [
                # 第一步：理解需求并检索相关信息
                """Thought: 用户询问云原生架构迁移建议，这是一个复杂的技术咨询问题
Action: knowledge_tool
Action Input: {\"query\": \"云原生架构 迁移 最佳实践\", \"top_k\": 5}""",
                # 第二步：基于检索结果提供具体建议
                """Observation: 检索到云原生相关技术：微服务、容器化、Kubernetes、CI/CD
Thought: 基于这些技术，我可以提供具体的迁移建议
Final Answer: 迁移到云原生架构的建议包括：1) 采用微服务架构拆分应用 2) 使用Docker容器化部署 3) 实施Kubernetes进行容器编排 4) 建立CI/CD流水线 5) 考虑服务网格和监控方案"""
            ]
            
            response = system['agent'].process_message(
                conversation[-1]["content"], 
                conversation_history=conversation[:-1]
            )
            
            # 验证回答包含关键技术点
            assert any(keyword in response for keyword in ["微服务", "容器", "Kubernetes", "CI/CD"])
            assert "架构" in response or "迁移" in response
    
    def test_multi_turn_conversation_with_knowledge(self, setup_complete_system):
        """测试多轮对话中的知识连贯性"""
        system = setup_complete_system
        
        # 构建软件开发知识库
        dev_docs = [
            Document(
                content="敏捷开发强调迭代开发和持续交付",
                metadata={"source": "agile.txt", "topic": "methodology"}
            ),
            Document(
                content="Scrum是敏捷开发的一种框架，包含Sprint和站会",
                metadata={"source": "scrum.txt", "topic": "framework"}
            ),
            Document(
                content="测试驱动开发(TDD)先写测试再写实现代码",
                metadata={"source": "tdd.txt", "topic": "practice"}
            ),
            Document(
                content="持续集成要求开发者频繁合并代码到主干",
                metadata={"source": "ci.txt", "topic": "automation"}
            )
        ]
        
        for doc in dev_docs:
            system['knowledge_base'].add_document(doc)
        
        # 模拟多轮对话
        conversation_history = []
        
        # 第一轮：基础概念
        query1 = "什么是敏捷开发？"
        
        with patch.object(system['agent'].llm, 'generate') as mock_generate:
            mock_generate.return_value = """Thought: 用户询问敏捷开发定义
Action: knowledge_tool
Action Input: {\"query\": \"敏捷开发 定义 特点\", \"top_k\": 3}
Observation: 敏捷开发强调迭代开发和持续交付
Final Answer: 敏捷开发是一种强调迭代开发、持续交付和响应变化的软件开发方法论。"""
            
            response1 = system['agent'].process_message(query1, conversation_history)
            conversation_history.extend([
                {"role": "user", "content": query1},
                {"role": "assistant", "content": response1}
            ])
            
            assert "敏捷开发" in response1
            assert "迭代" in response1 or "交付" in response1
        
        # 第二轮：深入探讨（基于上下文）
        query2 = "Scrum和敏捷有什么关系？"
        
        with patch.object(system['agent'].llm, 'generate') as mock_generate:
            mock_generate.return_value = """Thought: 用户之前了解了敏捷开发，现在问Scrum与敏捷的关系
Action: knowledge_tool
Action Input: {\"query\": \"Scrum 敏捷 关系 框架\", \"top_k\": 3}
Observation: Scrum是敏捷开发的一种框架
Final Answer: Scrum是敏捷开发的具体实施框架之一。敏捷是方法论理念，而Scrum是实践这种理念的具体框架，包含Sprint迭代、每日站会等实践。"""
            
            response2 = system['agent'].process_message(query2, conversation_history)
            
            # 验证回答考虑了对话历史
            assert "Scrum" in response2
            assert "敏捷" in response2
            assert "框架" in response2 or "关系" in response2
    
    def test_performance_under_load(self, setup_complete_system):
        """测试负载下的性能表现"""
        system = setup_complete_system
        
        # 添加大量测试文档
        for i in range(50):  # 添加50个文档
            doc = Document(
                content=f"技术概念{i}: 这是第{i}个测试技术概念的描述",
                metadata={"source": f"test_doc_{i}.txt", "index": i}
            )
            system['knowledge_base'].add_document(doc)
        
        # 性能测试：并发查询
        queries = [
            "技术概念",
            "测试描述", 
            "概念解释",
            "技术文档",
            "系统架构"
        ] * 4  # 20个查询
        
        with patch.object(system['agent'].llm, 'generate') as mock_generate:
            mock_generate.return_value = "基于知识库检索的标准回答"
            
            start_time = time.time()
            
            responses = []
            for query in queries:
                response = system['agent'].process_message(query)
                responses.append(response)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 验证所有查询都成功完成
            assert len(responses) == len(queries)
            assert all(response is not None for response in responses)
            
            # 性能要求：平均每个查询<2秒
            avg_time_per_query = total_time / len(queries)
            assert avg_time_per_query < 2.0, f"平均查询时间{avg_time_per_query:.2f}秒超出预期"
            
            print(f"性能测试结果: {len(queries)}个查询，总耗时{total_time:.2f}秒，平均{avg_time_per_query:.2f}秒/查询")
    
    def test_error_handling_and_recovery(self, setup_complete_system):
        """测试错误处理和恢复机制"""
        system = setup_complete_system
        
        # 测试各种边界情况
        edge_cases = [
            "",  # 空查询
            "非常非常长的查询字符串" * 100,  # 超长查询
            "!@#$%^&*()",  # 特殊字符
            "查询不存在的技术概念XYZ123",  # 无匹配内容
        ]
        
        for query in edge_cases:
            try:
                with patch.object(system['agent'].llm, 'generate') as mock_generate:
                    # 模拟优雅的错误处理
                    if not query.strip():
                        mock_generate.return_value = "请提供有效的查询内容"
                    else:
                        mock_generate.return_value = """Thought: 尝试处理用户查询
Action: knowledge_tool
Action Input: {\"query\": \"\"\" + query + \"\"\", \"top_k\": 3}
Observation: 未找到相关信息或处理异常
Final Answer: 抱歉，我无法处理这个查询。请尝试更具体的技术问题。"""
                    
                    response = system['agent'].process_message(query)
                    
                    # 验证系统没有崩溃，返回了合理的响应
                    assert response is not None
                    assert isinstance(response, str)
                    
            except Exception as e:
                pytest.fail(f"边界情况处理失败: {query}, 错误: {e}")
    
    def test_knowledge_freshness_and_updates(self, setup_complete_system):
        """测试知识新鲜度和更新机制"""
        system = setup_complete_system
        
        # 初始知识状态
        initial_doc = Document(
            content="Python 3.8引入了海象运算符 := 和位置参数语法",
            metadata={"source": "python_3.8.txt", "version": "3.8"}
        )
        system['knowledge_base'].add_document(initial_doc)
        
        # 测试初始知识
        with patch.object(system['agent'].llm, 'generate') as mock_generate:
            mock_generate.return_value = """Thought: 查询Python 3.8特性
Action: knowledge_tool
Action Input: {\"query\": \"Python 3.8 新特性\", \"top_k\": 3}
Observation: Python 3.8引入了海象运算符和位置参数语法
Final Answer: Python 3.8的主要新特性包括海象运算符(:=)和位置参数语法(/)。"""
            
            initial_response = system['agent'].process_message("Python 3.8有什么新特性？")
            assert "3.8" in initial_response
            assert "海象" in initial_response or "位置参数" in initial_response
        
        # 更新知识（模拟新版本发布）
        updated_doc = Document(
            content="Python 3.9引入了字典合并运算符 | 和字符串方法removeprefix/removesuffix",
            metadata={"source": "python_3.9.txt", "version": "3.9"}
        )
        system['knowledge_base'].add_document(updated_doc)
        
        # 测试更新后的知识
        with patch.object(system['agent'].llm, 'generate') as mock_generate:
            mock_generate.return_value = """Thought: 查询Python最新版本特性
Action: knowledge_tool
Action Input: {\"query\": \"Python 新版本 特性\", \"top_k\": 5}
Observation: 检索到Python 3.8和3.9的特性信息
Final Answer: Python的最新特性包括：3.8的海象运算符，3.9的字典合并运算符和新的字符串方法。"""
            
            updated_response = system['agent'].process_message("Python最新版本有哪些特性？")
            
            # 验证系统能够访问更新的知识
            assert any(version in updated_response for version in ["3.8", "3.9"])
            assert "特性" in updated_response
    
    def test_integration_with_external_tools(self, setup_complete_system):
        """测试与外部工具的集成"""
        system = setup_complete_system
        
        # 构建包含工具使用知识的知识库
        tool_docs = [
            Document(
                content="Git是分布式版本控制系统，用于代码管理",
                metadata={"source": "git.txt", "tool": "vcs"}
            ),
            Document(
                content="Docker Compose用于定义和运行多容器应用",
                metadata={"source": "docker_compose.txt", "tool": "orchestration"}
            ),
            Document(
                content="JIRA是项目管理工具，支持敏捷开发流程",
                metadata={"source": "jira.txt", "tool": "project_management"}
            )
        ]
        
        for doc in tool_docs:
            system['knowledge_base'].add_document(doc)
        
        # 测试工具相关的复杂查询
        complex_query = "如何结合Git、Docker和JIRA实现DevOps流程？"
        
        with patch.object(system['agent'].llm, 'generate') as mock_generate:
            # 模拟多工具集成建议
            mock_generate.return_value = """Thought: 这是一个关于工具集成的复杂问题
Action: knowledge_tool
Action Input: {\"query\": \"Git Docker JIRA DevOps 集成 流程\", \"top_k\": 5}
Observation: 检索到各工具的功能和集成可能性
Final Answer: 实现DevOps流程的建议：1) 使用Git进行代码版本控制 2) 用Docker容器化应用 3) 通过JIRA管理任务和进度 4) 建立CI/CD流水线连接这些工具 5) 确保团队协作和自动化。"""
            
            response = system['agent'].process_message(complex_query)
            
            # 验证回答涉及多个工具
            tools_mentioned = sum(1 for tool in ["Git", "Docker", "JIRA"] if tool in response)
            assert tools_mentioned >= 2, "回答应该涉及至少两个工具"
            assert "DevOps" in response or "流程" in response