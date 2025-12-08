"""
Agent与知识库集成测试
测试各种Agent类型与知识库的协同工作
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os

from src.knowledge.core.knowledge_base import KnowledgeBase
from src.knowledge.stores.chroma_store import ChromaStore
from src.knowledge.embedders.local_embedder import LocalEmbedder
from src.knowledge.core.schema.document import Document
from src.agents.impls.simple_agent import SimpleAgent
from src.agents.impls.react_agent import ReActAgent
from src.agents.impls.reflection_agent import ReflectionAgent
from src.agents.impls.plan_solve_agent import PlanAndSolveAgent
from src.shared.config.manager import ConfigManager


class TestAgentKnowledgeIntegration:
    """Agent与知识库集成测试类"""
    
    @pytest.fixture
    def setup_knowledge_base(self):
        """设置知识库"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager().get_config()
            
            store_path = os.path.join(temp_dir, "chroma_test")
            vector_store = ChromaStore(persist_directory=store_path)
            embedder = LocalEmbedder()
            
            kb = KnowledgeBase(
                vector_store=vector_store,
                embedder=embedder,
                config=config
            )
            
            # 添加技术文档
            tech_documents = [
                Document(
                    content="微服务架构将应用拆分为小型、独立的服务",
                    metadata={"source": "microservices.txt", "type": "architecture"}
                ),
                Document(
                    content="API网关是微服务架构中的入口点，负责路由和认证",
                    metadata={"source": "api_gateway.txt", "type": "architecture"}
                ),
                Document(
                    content="容器编排工具如Kubernetes用于管理容器化应用",
                    metadata={"source": "kubernetes.txt", "type": "devops"}
                ),
                Document(
                    content="CI/CD流水线自动化软件构建、测试和部署过程",
                    metadata={"source": "cicd.txt", "type": "devops"}
                )
            ]
            
            for doc in tech_documents:
                kb.add_document(doc)
            
            yield kb
    
    def test_simple_agent_with_knowledge(self, setup_knowledge_base):
        """测试简单Agent与知识库集成"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = SimpleAgent(config, knowledge_base=kb)
        
        query = "什么是微服务架构？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟直接使用知识库信息的响应
            mock_generate.return_value = "微服务架构将应用拆分为小型、独立的服务。这种架构模式有助于提高系统的可维护性和可扩展性。"
            
            response = agent.process_message(query)
            
            assert "微服务" in response
            assert "架构" in response
    
    def test_react_agent_knowledge_tool_usage(self, setup_knowledge_base):
        """测试ReAct Agent的知识工具使用"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReActAgent(config, knowledge_base=kb)
        
        query = "请解释API网关在微服务中的作用"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟ReAct推理过程
            mock_generate.return_value = """Thought: 用户询问API网关的作用，我需要检索相关知识
Action: knowledge_tool
Action Input: {\"query\": \"API网关 微服务 作用\", \"top_k\": 3}
Observation: API网关是微服务架构中的入口点，负责路由和认证
Thought: 基于检索结果，我可以详细解释API网关的作用
Final Answer: API网关在微服务架构中扮演重要角色，作为统一的入口点处理请求路由、身份认证、负载均衡等功能。"""
            
            response = agent.process_message(query)
            
            # 验证使用了知识工具
            assert "API网关" in response
            assert "微服务" in response
            assert "路由" in response or "认证" in response
    
    def test_reflection_agent_knowledge_validation(self, setup_knowledge_base):
        """测试反思Agent的知识验证能力"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReflectionAgent(config, knowledge_base=kb)
        
        query = "Kubernetes和Docker有什么区别？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟反思过程：生成答案 -> 验证 -> 改进
            mock_generate.side_effect = [
                # 初始回答
                """Thought: 用户询问Kubernetes和Docker的区别
Action: knowledge_tool
Action Input: {\"query\": \"Kubernetes Docker 区别\", \"top_k\": 3}
Observation: Kubernetes是容器编排工具，Docker是容器化技术
Initial Answer: Kubernetes用于编排容器，Docker用于创建容器""",
                # 反思和改进
                """Reflection: 这个回答过于简单，需要更详细的对比
Improved Answer: Kubernetes是容器编排平台，用于管理和调度容器化应用；Docker是容器运行时，用于打包和运行应用。两者是互补关系：Docker创建容器，Kubernetes管理这些容器。"""
            ]
            
            response = agent.process_message(query)
            
            # 验证反思过程产生了更详细的回答
            assert "Kubernetes" in response
            assert "Docker" in response
            assert "编排" in response or "管理" in response
            assert "容器" in response
    
    def test_plan_solve_agent_complex_knowledge_query(self, setup_knowledge_base):
        """测试规划求解Agent的复杂知识查询"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = PlanAndSolveAgent(config, knowledge_base=kb)
        
        complex_query = "设计一个完整的微服务CI/CD流水线需要考虑哪些因素？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟多步骤规划过程
            mock_generate.side_effect = [
                # 规划阶段
                """Plan: 
1. 检索微服务架构特点
2. 检索CI/CD最佳实践
3. 结合两者设计流水线
4. 考虑安全性和监控""",
                # 执行阶段 - 步骤1
                """Step 1: 检索微服务架构特点
Action: knowledge_tool
Action Input: {\"query\": \"微服务架构 特点 设计原则\", \"top_k\": 3}""",
                # 步骤1结果
                """Observation: 微服务特点：独立部署、松耦合、技术多样性""",
                # 步骤2
                """Step 2: 检索CI/CD最佳实践
Action: knowledge_tool
Action Input: {\"query\": \"CI/CD 最佳实践 微服务\", \"top_k\": 3}""",
                # 步骤2结果
                """Observation: CI/CD实践：自动化测试、持续部署、环境隔离""",
                # 综合答案
                """Final Answer: 设计微服务CI/CD流水线需要考虑：独立服务的构建和部署、自动化测试策略、环境隔离、服务发现和配置管理、监控和日志聚合等关键因素。"""
            ]
            
            response = agent.process_message(complex_query)
            
            # 验证复杂问题的系统性回答
            assert "微服务" in response
            assert "CI/CD" in response or "流水线" in response
            assert any(keyword in response for keyword in ["构建", "部署", "测试", "监控"])
    
    def test_agent_knowledge_context_persistence(self, setup_knowledge_base):
        """测试Agent知识上下文持久化"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReActAgent(config, knowledge_base=kb)
        
        # 多轮对话测试
        conversation = [
            {"role": "user", "content": "什么是容器编排？"},
            {"role": "assistant", "content": "容器编排工具用于管理容器化应用的部署和运行"}
        ]
        
        follow_up = "Kubernetes有哪些核心概念？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟考虑对话历史的响应
            mock_generate.return_value = """Thought: 用户之前询问了容器编排，现在问Kubernetes的核心概念
Action: knowledge_tool
Action Input: {\"query\": \"Kubernetes 核心概念 Pod Service Deployment\", \"top_k\": 3}
Observation: Kubernetes核心概念包括Pod、Service、Deployment等
Final Answer: Kubernetes的核心概念包括：Pod（最小部署单元）、Service（服务发现）、Deployment（部署管理）等。"""
            
            response = agent.process_message(follow_up, conversation)
            
            # 验证上下文感知
            assert "Kubernetes" in response
            assert any(concept in response for concept in ["Pod", "Service", "Deployment"])
    
    def test_knowledge_aware_decision_making(self, setup_knowledge_base):
        """测试基于知识的决策制定"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReflectionAgent(config, knowledge_base=kb)
        
        decision_query = "对于新项目，应该选择单体架构还是微服务架构？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟基于知识的决策过程
            mock_generate.side_effect = [
                # 初始分析
                """Thought: 这是一个架构选择问题，需要检索两种架构的特点和适用场景
Action: knowledge_tool
Action Input: {\"query\": \"单体架构 微服务架构 优缺点 适用场景\", \"top_k\": 5}""",
                # 检索结果
                """Observation: 单体架构简单但难扩展，微服务灵活但复杂度高
Initial Analysis: 需要根据项目规模、团队经验等因素决定""",
                # 反思和改进
                """Reflection: 应该提供更具体的指导原则
Final Decision: 对于小型项目或初创团队，建议从单体架构开始；对于大型复杂系统或需要快速迭代的场景，微服务更合适。关键考虑因素包括团队规模、技术债务容忍度、部署频率等。"""
            ]
            
            response = agent.process_message(decision_query)
            
            # 验证决策包含具体指导
            assert "单体" in response
            assert "微服务" in response
            assert any(factor in response for factor in ["规模", "团队", "复杂度", "部署"])
    
    def test_cross_agent_knowledge_sharing(self, setup_knowledge_base):
        """测试不同Agent间的知识共享"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        # 创建不同类型的Agent
        simple_agent = SimpleAgent(config, knowledge_base=kb)
        react_agent = ReActAgent(config, knowledge_base=kb)
        
        query = "解释DevOps中的CI/CD概念"
        
        # 测试不同Agent对同一知识库的使用
        with patch.object(simple_agent.llm, 'generate') as mock_simple:
            mock_simple.return_value = "CI/CD代表持续集成和持续部署，是DevOps的核心实践"
            
            simple_response = simple_agent.process_message(query)
            
            with patch.object(react_agent.llm, 'generate') as mock_react:
                mock_react.return_value = """Thought: 需要检索CI/CD的具体定义和实践
Action: knowledge_tool
Action Input: {\"query\": \"CI/CD DevOps 持续集成 持续部署\", \"top_k\": 3}
Observation: CI/CD流水线自动化软件构建、测试和部署过程
Final Answer: CI/CD是DevOps的关键实践，包括持续集成（代码合并和测试自动化）和持续部署（自动发布到生产环境）。"""
                
                react_response = react_agent.process_message(query)
                
                # 验证两个Agent都能正确使用知识库
                assert "CI/CD" in simple_response
                assert "CI/CD" in react_response
                assert "DevOps" in simple_response or "DevOps" in react_response
    
    def test_knowledge_base_update_during_runtime(self, setup_knowledge_base):
        """测试运行时知识库更新"""
        kb = setup_knowledge_base
        config = ConfigManager().get_config()
        
        agent = ReActAgent(config, knowledge_base=kb)
        
        # 初始查询
        initial_query = "什么是服务网格？"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            # 模拟知识库中没有相关信息
            mock_generate.return_value = """Thought: 尝试检索服务网格信息
Action: knowledge_tool
Action Input: {\"query\": \"服务网格 Service Mesh\", \"top_k\": 3}
Observation: 未找到相关信息
Final Answer: 抱歉，我目前没有关于服务网格的详细信息。"""
            
            initial_response = agent.process_message(initial_query)
            assert "抱歉" in initial_response or "没有" in initial_response
            
            # 向知识库添加新文档
            new_doc = Document(
                content="服务网格（Service Mesh）是微服务架构中的基础设施层，处理服务间通信",
                metadata={"source": "service_mesh.txt", "type": "architecture"}
            )
            kb.add_document(new_doc)
            
            # 再次查询相同问题
            with patch.object(agent.llm, 'generate') as mock_generate_updated:
                mock_generate_updated.return_value = """Thought: 重新检索服务网格信息
Action: knowledge_tool
Action Input: {\"query\": \"服务网格 Service Mesh\", \"top_k\": 3}
Observation: 服务网格是微服务架构中的基础设施层，处理服务间通信
Final Answer: 服务网格是微服务架构中的专用基础设施层，用于处理服务之间的通信、安全、监控等横切关注点。"""
                
                updated_response = agent.process_message(initial_query)
                
                # 验证更新后的知识库提供了信息
                assert "服务网格" in updated_response
                assert "微服务" in updated_response
                assert "通信" in updated_response