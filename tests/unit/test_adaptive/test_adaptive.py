"""
自适应模块单元测试
"""

import pytest
from unittest.mock import Mock, patch

from src.adaptive.knowledge_manager import KnowledgeManager
from src.adaptive.tool_manager import ToolManager
from src.adaptive.agent_orchestrator import AgentOrchestrator
from src.adaptive.evaluator import Evaluator
from src.shared.config.manager import ConfigManager


class TestKnowledgeManager:
    """知识管理器测试"""
    
    def test_knowledge_manager_initialization(self):
        """测试知识管理器初始化"""
        config = ConfigManager().get_config()
        knowledge_manager = KnowledgeManager(config)
        
        assert knowledge_manager is not None
        assert hasattr(knowledge_manager, 'knowledge_bases')
        assert isinstance(knowledge_manager.knowledge_bases, dict)
    
    def test_add_knowledge_base(self):
        """测试添加知识库"""
        config = ConfigManager().get_config()
        knowledge_manager = KnowledgeManager(config)
        
        mock_kb = Mock()
        mock_kb.name = "test_kb"
        
        knowledge_manager.add_knowledge_base(mock_kb)
        
        assert "test_kb" in knowledge_manager.knowledge_bases
        assert knowledge_manager.knowledge_bases["test_kb"] == mock_kb
    
    def test_get_knowledge_base(self):
        """测试获取知识库"""
        config = ConfigManager().get_config()
        knowledge_manager = KnowledgeManager(config)
        
        mock_kb = Mock()
        mock_kb.name = "test_kb"
        knowledge_manager.knowledge_bases["test_kb"] = mock_kb
        
        result = knowledge_manager.get_knowledge_base("test_kb")
        
        assert result == mock_kb
    
    def test_remove_knowledge_base(self):
        """测试移除知识库"""
        config = ConfigManager().get_config()
        knowledge_manager = KnowledgeManager(config)
        
        mock_kb = Mock()
        mock_kb.name = "test_kb"
        knowledge_manager.knowledge_bases["test_kb"] = mock_kb
        
        knowledge_manager.remove_knowledge_base("test_kb")
        
        assert "test_kb" not in knowledge_manager.knowledge_bases


class TestToolManager:
    """工具管理器测试"""
    
    def test_tool_manager_initialization(self):
        """测试工具管理器初始化"""
        config = ConfigManager().get_config()
        tool_manager = ToolManager(config)
        
        assert tool_manager is not None
        assert hasattr(tool_manager, 'tools')
        assert isinstance(tool_manager.tools, dict)
    
    def test_register_tool(self):
        """测试注册工具"""
        config = ConfigManager().get_config()
        tool_manager = ToolManager(config)
        
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        
        tool_manager.register_tool(mock_tool)
        
        assert "test_tool" in tool_manager.tools
        assert tool_manager.tools["test_tool"] == mock_tool
    
    def test_get_tool(self):
        """测试获取工具"""
        config = ConfigManager().get_config()
        tool_manager = ToolManager(config)
        
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        tool_manager.tools["test_tool"] = mock_tool
        
        result = tool_manager.get_tool("test_tool")
        
        assert result == mock_tool
    
    def test_list_tools(self):
        """测试列出工具"""
        config = ConfigManager().get_config()
        tool_manager = ToolManager(config)
        
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        
        tool_manager.tools = {"tool1": mock_tool1, "tool2": mock_tool2}
        
        tools = tool_manager.list_tools()
        
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools


class TestAgentOrchestrator:
    """Agent协调器测试"""
    
    def test_agent_orchestrator_initialization(self):
        """测试Agent协调器初始化"""
        config = ConfigManager().get_config()
        orchestrator = AgentOrchestrator(config)
        
        assert orchestrator is not None
        assert hasattr(orchestrator, 'agents')
        assert isinstance(orchestrator.agents, dict)
    
    def test_register_agent(self):
        """测试注册Agent"""
        config = ConfigManager().get_config()
        orchestrator = AgentOrchestrator(config)
        
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        
        orchestrator.register_agent(mock_agent)
        
        assert "test_agent" in orchestrator.agents
        assert orchestrator.agents["test_agent"] == mock_agent
    
    def test_select_agent_for_task(self):
        """测试为任务选择Agent"""
        config = ConfigManager().get_config()
        orchestrator = AgentOrchestrator(config)
        
        # 创建不同类型的Agent
        simple_agent = Mock()
        simple_agent.name = "simple"
        simple_agent.capabilities = ["basic_query"]
        
        complex_agent = Mock()
        complex_agent.name = "complex"
        complex_agent.capabilities = ["reasoning", "planning"]
        
        orchestrator.agents = {"simple": simple_agent, "complex": complex_agent}
        
        # 测试简单任务选择
        simple_task = "简单查询"
        selected_agent = orchestrator.select_agent_for_task(simple_task)
        
        assert selected_agent is not None
        
        # 测试复杂任务选择
        complex_task = "需要推理和规划的复杂问题"
        selected_agent = orchestrator.select_agent_for_task(complex_task)
        
        assert selected_agent is not None


class TestEvaluator:
    """评估器测试"""
    
    def test_evaluator_initialization(self):
        """测试评估器初始化"""
        config = ConfigManager().get_config()
        evaluator = Evaluator(config)
        
        assert evaluator is not None
        assert hasattr(evaluator, 'metrics')
        assert isinstance(evaluator.metrics, list)
    
    def test_evaluate_response_quality(self):
        """测试响应质量评估"""
        config = ConfigManager().get_config()
        evaluator = Evaluator(config)
        
        query = "什么是Python？"
        response = "Python是一种高级编程语言，具有简洁易读的语法。"
        
        quality_score = evaluator.evaluate_response_quality(query, response)
        
        assert isinstance(quality_score, float)
        assert 0 <= quality_score <= 1
    
    def test_evaluate_knowledge_relevance(self):
        """测试知识相关性评估"""
        config = ConfigManager().get_config()
        evaluator = Evaluator(config)
        
        query = "机器学习算法"
        retrieved_docs = [
            Mock(content="监督学习算法包括线性回归和决策树"),
            Mock(content="无监督学习用于聚类分析")
        ]
        
        relevance_score = evaluator.evaluate_knowledge_relevance(query, retrieved_docs)
        
        assert isinstance(relevance_score, float)
        assert 0 <= relevance_score <= 1
    
    def test_track_performance_metrics(self):
        """测试性能指标跟踪"""
        config = ConfigManager().get_config()
        evaluator = Evaluator(config)
        
        # 模拟一些性能数据
        performance_data = {
            "response_time": 1.5,
            "accuracy": 0.85,
            "relevance": 0.92
        }
        
        evaluator.track_performance_metrics("test_agent", performance_data)
        
        # 验证指标被记录
        assert len(evaluator.metrics) > 0