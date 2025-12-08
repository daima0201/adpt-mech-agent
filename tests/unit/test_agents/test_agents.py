"""
Agent单元测试
测试各种Agent的实现和功能
"""

import pytest
from unittest.mock import Mock, patch

from src.agents.impls.simple_agent import SimpleAgent
from src.agents.impls.react_agent import ReActAgent
from src.agents.impls.reflection_agent import ReflectionAgent
from src.agents.impls.plan_solve_agent import PlanAndSolveAgent
from src.shared.config.manager import ConfigManager


class TestSimpleAgent:
    """SimpleAgent测试类"""
    
    @pytest.fixture
    def simple_agent(self):
        """创建SimpleAgent实例"""
        from src.agents.core.agent import AgentConfig
        config = AgentConfig(
            name="test_agent",
            description="测试智能体",
            system_prompt="你是一个测试助手"
        )
        return SimpleAgent(config)
    
    def test_initialization(self, simple_agent):
        """测试初始化"""
        assert simple_agent is not None
        assert hasattr(simple_agent, 'llm')
        assert hasattr(simple_agent, 'config')
        assert hasattr(simple_agent, 'tool_registry')
    
    def test_process_message_basic(self, simple_agent):
        """测试基础消息处理"""
        # 模拟LLM响应
        with patch.object(simple_agent.llm, 'generate') as mock_generate:
            mock_generate.return_value = "这是一个测试响应"
            
            response = simple_agent.process_message("你好")
            
            assert response == "这是一个测试响应"
            mock_generate.assert_called_once()
    
    def test_process_message_with_context(self, simple_agent):
        """测试带上下文的消息处理"""
        conversation_history = [
            {"role": "user", "content": "第一个问题"},
            {"role": "assistant", "content": "第一个回答"}
        ]
        
        with patch.object(simple_agent.llm, 'generate') as mock_generate:
            mock_generate.return_value = "基于上下文的响应"
            
            response = simple_agent.process_message("第二个问题", conversation_history)
            
            # 验证调用时包含了历史记录
            call_args = mock_generate.call_args[0][0]
            assert len(call_args) > 2  # 应该包含历史消息
            mock_generate.assert_called_once()


class TestReActAgent:
    """ReActAgent测试类"""
    
    @pytest.fixture
    def react_agent(self):
        """创建ReActAgent实例"""
        from src.agents.core.agent import AgentConfig
        config = AgentConfig(
            name="test_react_agent",
            description="测试推理智能体",
            system_prompt="你是一个善于推理的测试助手"
        )
        return ReActAgent(config)
    
    def test_initialization(self, react_agent):
        """测试初始化"""
        assert react_agent is not None
        assert hasattr(react_agent, 'max_iterations')
        assert hasattr(react_agent, 'tool_registry')
    
    def test_reasoning_cycle(self, react_agent):
        """测试推理循环"""
        # 模拟工具执行
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"
        mock_tool.execute.return_value = "工具执行结果"
        
        react_agent.tool_registry.register(mock_tool)
        
        # 模拟LLM生成思考过程
        with patch.object(react_agent.llm, 'generate') as mock_generate:
            # 模拟思考-行动-观察循环
            mock_generate.side_effect = [
                "Thought: 我需要使用test_tool\nAction: test_tool\nAction Input: {}",
                "Thought: 工具执行完成，现在可以给出最终答案\nFinal Answer: 最终答案"
            ]
            
            response = react_agent.process_message("请使用test_tool")
            
            assert "最终答案" in response
            assert mock_tool.execute.called
    
    def test_max_iterations_limit(self, react_agent):
        """测试最大迭代次数限制"""
        # 设置较小的最大迭代次数
        react_agent.max_iterations = 2
        
        with patch.object(react_agent.llm, 'generate') as mock_generate:
            # 模拟无限循环的思考
            mock_generate.return_value = "Thought: 继续思考...\nAction: some_action"
            
            response = react_agent.process_message("测试问题")
            
            # 应该达到最大迭代次数限制
            assert "达到最大迭代次数" in response or "无法完成" in response


class TestReflectionAgent:
    """ReflectionAgent测试类"""
    
    @pytest.fixture
    def reflection_agent(self):
        """创建ReflectionAgent实例"""
        from src.agents.core.agent import AgentConfig
        config = AgentConfig(
            name="test_reflection_agent",
            description="测试反思智能体",
            system_prompt="你是一个善于反思的测试助手"
        )
        return ReflectionAgent(config)
    
    def test_reflection_process(self, reflection_agent):
        """测试反思过程"""
        initial_response = "这是一个初步的回答"
        
        with patch.object(reflection_agent.llm, 'generate') as mock_generate:
            # 模拟反思和改进
            mock_generate.side_effect = [
                initial_response,
                "这个回答可以改进的地方是...",
                "改进后的最终回答"
            ]
            
            response = reflection_agent.process_message("测试问题")
            
            assert response == "改进后的最终回答"
            assert mock_generate.call_count == 3  # 初始回答 + 反思 + 改进
    
    def test_reflection_quality_threshold(self, reflection_agent):
        """测试反思质量阈值"""
        high_quality_response = "这是一个高质量的回答，不需要反思"
        
        with patch.object(reflection_agent.llm, 'generate') as mock_generate:
            # 模拟高质量回答（跳过反思）
            mock_generate.return_value = high_quality_response
            
            # 模拟质量评估返回高分
            with patch.object(reflection_agent, '_evaluate_response_quality') as mock_eval:
                mock_eval.return_value = 0.9  # 高质量
                
                response = reflection_agent.process_message("测试问题")
                
                assert response == high_quality_response
                # 应该只调用一次（没有反思）
                assert mock_generate.call_count == 1


class TestPlanAndSolveAgent:
    """PlanAndSolveAgent测试类"""
    
    @pytest.fixture
    def plan_solve_agent(self):
        """创建PlanAndSolveAgent实例"""
        from src.agents.core.agent import AgentConfig
        config = AgentConfig(
            name="test_plan_agent",
            description="测试规划智能体",
            system_prompt="你是一个善于规划的测试助手"
        )
        return PlanAndSolveAgent(config)
    
    def test_planning_phase(self, plan_solve_agent):
        """测试规划阶段"""
        complex_query = "请帮我分析这个项目的架构设计，并给出改进建议"
        
        with patch.object(plan_solve_agent.llm, 'generate') as mock_generate:
            # 模拟规划过程
            mock_generate.side_effect = [
                "计划: 1. 分析当前架构 2. 识别问题 3. 提出改进建议",
                "步骤1分析结果",
                "步骤2分析结果",
                "步骤3分析结果",
                "综合所有步骤的最终回答"
            ]
            
            response = plan_solve_agent.process_message(complex_query)
            
            assert "最终回答" in response
            assert mock_generate.call_count == 5  # 计划 + 3个步骤 + 综合
    
    def test_plan_execution(self, plan_solve_agent):
        """测试计划执行"""
        # 模拟多步骤计划的执行
        plan = ["第一步", "第二步", "第三步"]
        
        with patch.object(plan_solve_agent.llm, 'generate') as mock_generate:
            mock_generate.side_effect = [
                "第一步结果",
                "第二步结果",
                "第三步结果",
                "综合结果"
            ]
            
            result = plan_solve_agent._execute_plan(plan, "原始问题")
            
            assert "综合结果" in result
            assert mock_generate.call_count == 4


class TestAgentIntegration:
    """Agent集成测试类"""
    
    def test_agent_factory_pattern(self):
        """测试Agent工厂模式"""
        from src.agents.core.manager import PreconfiguredAgentManager
        from src.agents.core.llm import HelloAgentsLLM
        
        llm = HelloAgentsLLM()
        manager = PreconfiguredAgentManager(llm)
        
        # 测试创建不同类型的Agent
        agents = [
            ("simple_agent", SimpleAgent),
            ("react_agent", ReActAgent),
            ("reflection_agent", ReflectionAgent),
            ("plan_solve_agent", PlanAndSolveAgent)
        ]
        
        for agent_type, expected_class in agents:
            agent = manager.create_agent(agent_type)
            assert isinstance(agent, expected_class)
    
    def test_agent_with_knowledge_base(self):
        """测试Agent与知识库集成"""
        from src.agents.core.agent import AgentConfig
        
        config = AgentConfig(
            name="test_kb_agent",
            description="测试知识库智能体",
            system_prompt="你是一个使用知识库的测试助手"
        )
        
        # 模拟知识库
        mock_kb = Mock()
        mock_kb.search.return_value = [
            Mock(content="相关知识内容", score=0.8, metadata={})
        ]
        
        # 创建支持知识库的Agent
        agent = ReActAgent(config, knowledge_base=mock_kb)
        
        # 测试知识检索集成
        query = "技术问题"
        
        with patch.object(agent.llm, 'generate') as mock_generate:
            mock_generate.return_value = "基于知识的回答"
            
            response = agent.process_message(query)
            
            # 验证知识库被调用
            mock_kb.search.assert_called_with(query, top_k=5)
            assert "基于知识的回答" in response