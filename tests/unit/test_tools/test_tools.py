"""
工具系统单元测试
测试工具注册、执行和链式调用功能
"""

import pytest
from unittest.mock import Mock, patch

from src.agents.tools.base import BaseTool
from src.agents.tools.registry import ToolRegistry
from src.agents.tools.chain import ToolChain
from src.agents.tools.builtin.calculator import CalculatorTool
from src.agents.tools.builtin.search import SearchTool
from src.agents.tools.builtin.knowledge_tool import KnowledgeTool


class TestBaseTool:
    """基础工具测试类"""
    
    def test_base_tool_interface(self):
        """测试基础工具接口"""
        # 创建具体实现
        class TestTool(BaseTool):
            name = "test_tool"
            description = "测试工具"
            
            def execute(self, **kwargs):
                return f"执行结果: {kwargs}"
        
        tool = TestTool()
        
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert tool.execute(test="value") == "执行结果: {'test': 'value'}"
    
    def test_tool_validation(self):
        """测试工具参数验证"""
        class ValidatedTool(BaseTool):
            name = "validated_tool"
            description = "带验证的工具"
            required_params = ["required_field"]
            
            def execute(self, **kwargs):
                self._validate_params(kwargs)
                return "验证通过"
        
        tool = ValidatedTool()
        
        # 测试缺少必需参数
        with pytest.raises(ValueError) as exc_info:
            tool.execute()
        assert "缺少必需参数" in str(exc_info.value)
        
        # 测试参数验证通过
        result = tool.execute(required_field="value")
        assert result == "验证通过"


class TestToolRegistry:
    """工具注册表测试类"""
    
    @pytest.fixture
    def registry(self):
        """创建工具注册表"""
        return ToolRegistry()
    
    @pytest.fixture
    def sample_tools(self):
        """创建示例工具"""
        tools = []
        
        for i in range(3):
            tool = Mock()
            tool.name = f"tool_{i}"
            tool.description = f"测试工具{i}"
            tools.append(tool)
        
        return tools
    
    def test_register_and_get_tool(self, registry, sample_tools):
        """测试工具注册和获取"""
        # 注册工具
        for tool in sample_tools:
            registry.register(tool)
        
        # 验证工具存在
        for tool in sample_tools:
            retrieved_tool = registry.get_tool(tool.name)
            assert retrieved_tool == tool
    
    def test_duplicate_registration(self, registry, sample_tools):
        """测试重复注册"""
        tool = sample_tools[0]
        
        # 第一次注册
        registry.register(tool)
        
        # 第二次注册应该失败
        with pytest.raises(ValueError) as exc_info:
            registry.register(tool)
        assert "已存在" in str(exc_info.value)
    
    def test_list_tools(self, registry, sample_tools):
        """测试工具列表"""
        # 注册多个工具
        for tool in sample_tools:
            registry.register(tool)
        
        # 获取工具列表
        tools_list = registry.list_tools()
        
        assert len(tools_list) == len(sample_tools)
        for tool in sample_tools:
            assert tool.name in tools_list
    
    def test_unregister_tool(self, registry, sample_tools):
        """测试工具注销"""
        tool = sample_tools[0]
        
        # 注册然后注销
        registry.register(tool)
        assert registry.get_tool(tool.name) == tool
        
        registry.unregister(tool.name)
        
        # 验证工具已不存在
        with pytest.raises(KeyError):
            registry.get_tool(tool.name)


class TestCalculatorTool:
    """计算器工具测试类"""
    
    @pytest.fixture
    def calculator(self):
        """创建计算器工具"""
        return CalculatorTool()
    
    def test_basic_calculation(self, calculator):
        """测试基础计算"""
        test_cases = [
            ("2 + 3", "5"),
            ("10 - 4", "6"),
            ("3 * 7", "21"),
            ("15 / 3", "5.0"),
            ("2 ** 8", "256"),
        ]
        
        for expression, expected in test_cases:
            result = calculator.execute(expression=expression)
            assert result == expected
    
    def test_complex_expressions(self, calculator):
        """测试复杂表达式"""
        complex_cases = [
            ("(2 + 3) * 4", "20"),
            ("sqrt(16)", "4.0"),
            ("sin(pi/2)", "1.0"),
            ("log(100, 10)", "2.0"),
        ]
        
        for expression, expected in complex_cases:
            result = calculator.execute(expression=expression)
            assert result == expected
    
    def test_error_handling(self, calculator):
        """测试错误处理"""
        error_cases = [
            "10 / 0",  # 除零错误
            "undefined_function()",  # 未定义函数
            "invalid syntax",  # 语法错误
        ]
        
        for expression in error_cases:
            result = calculator.execute(expression=expression)
            assert "错误" in result or "无法计算" in result


class TestSearchTool:
    """搜索工具测试类"""
    
    @pytest.fixture
    def search_tool(self):
        """创建搜索工具"""
        return SearchTool()
    
    def test_search_execution(self, search_tool):
        """测试搜索执行"""
        query = "Python编程"
        
        with patch('requests.get') as mock_get:
            # 模拟API响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"title": "Python教程", "url": "https://example.com"},
                    {"title": "Python文档", "url": "https://docs.python.org"}
                ]
            }
            mock_get.return_value = mock_response
            
            result = search_tool.execute(query=query)
            
            # 验证请求参数
            mock_get.assert_called_once()
            assert "Python编程" in result
    
    def test_search_error_handling(self, search_tool):
        """测试搜索错误处理"""
        with patch('requests.get') as mock_get:
            # 模拟网络错误
            mock_get.side_effect = Exception("网络连接失败")
            
            result = search_tool.execute(query="测试查询")
            
            assert "搜索失败" in result
            assert "网络连接失败" in result


class TestKnowledgeTool:
    """知识检索工具测试类"""
    
    @pytest.fixture
    def knowledge_tool(self):
        """创建知识检索工具"""
        # 模拟知识库
        mock_kb = Mock()
        mock_kb.search.return_value = [
            Mock(content="相关知识内容1", score=0.9, metadata={"source": "doc1"}),
            Mock(content="相关知识内容2", score=0.8, metadata={"source": "doc2"})
        ]
        
        return KnowledgeTool(knowledge_base=mock_kb)
    
    def test_knowledge_retrieval(self, knowledge_tool):
        """测试知识检索"""
        query = "技术问题"
        
        result = knowledge_tool.execute(query=query, top_k=2)
        
        # 验证知识库被调用
        knowledge_tool.knowledge_base.search.assert_called_with(query, top_k=2)
        
        # 验证结果格式
        assert "相关知识内容1" in result
        assert "相关知识内容2" in result
        assert "相似度" in result
    
    def test_knowledge_tool_without_kb(self):
        """测试没有知识库的情况"""
        tool = KnowledgeTool()
        
        result = tool.execute(query="测试查询")
        
        assert "知识库未配置" in result


class TestToolChain:
    """工具链测试类"""
    
    @pytest.fixture
    def tool_chain(self):
        """创建工具链"""
        return ToolChain()
    
    @pytest.fixture
    def mock_tools(self):
        """创建模拟工具"""
        tools = []
        
        for i in range(3):
            tool = Mock()
            tool.name = f"tool_{i}"
            tool.description = f"测试工具{i}"
            tool.execute.return_value = f"工具{i}执行结果"
            tools.append(tool)
        
        return tools
    
    def test_add_and_execute_tools(self, tool_chain, mock_tools):
        """测试添加和执行工具"""
        # 添加工具到链中
        for tool in mock_tools:
            tool_chain.add_tool(tool)
        
        # 执行工具链
        results = tool_chain.execute()
        
        # 验证所有工具都被执行
        assert len(results) == len(mock_tools)
        for i, (tool, result) in enumerate(zip(mock_tools, results)):
            tool.execute.assert_called_once()
            assert result == f"工具{i}执行结果"
    
    def test_sequential_execution(self, tool_chain, mock_tools):
        """测试顺序执行"""
        # 设置工具执行顺序
        execution_order = []
        
        def record_execution(tool_name):
            def execute(**kwargs):
                execution_order.append(tool_name)
                return f"{tool_name}结果"
            return execute
        
        for i, tool in enumerate(mock_tools):
            tool.execute.side_effect = record_execution(f"tool_{i}")
            tool_chain.add_tool(tool)
        
        # 执行并验证顺序
        tool_chain.execute()
        
        assert execution_order == ["tool_0", "tool_1", "tool_2"]
    
    def test_tool_chain_with_parameters(self, tool_chain, mock_tools):
        """测试带参数的链式执行"""
        # 设置工具间参数传递
        mock_tools[0].execute.return_value = {"data": "中间结果"}
        mock_tools[1].execute.return_value = {"processed": "处理后的数据"}
        
        for tool in mock_tools[:2]:
            tool_chain.add_tool(tool)
        
        # 执行并验证参数传递
        results = tool_chain.execute(initial_param="初始值")
        
        # 验证第一个工具接收初始参数
        mock_tools[0].execute.assert_called_with(initial_param="初始值")
        
        # 验证第二个工具接收第一个工具的结果
        mock_tools[1].execute.assert_called_with(data="中间结果")
    
    def test_error_handling_in_chain(self, tool_chain, mock_tools):
        """测试链中的错误处理"""
        # 设置一个工具失败
        mock_tools[1].execute.side_effect = Exception("工具执行失败")
        
        for tool in mock_tools:
            tool_chain.add_tool(tool)
        
        # 执行并验证错误处理
        results = tool_chain.execute()
        
        # 第一个工具应该成功执行
        mock_tools[0].execute.assert_called_once()
        
        # 第二个工具应该失败
        mock_tools[1].execute.assert_called_once()
        
        # 第三个工具不应该执行（取决于错误处理策略）
        # 这里假设错误后停止执行
        mock_tools[2].execute.assert_not_called()
        
        # 结果应该包含错误信息
        assert len(results) >= 1
        assert "工具执行失败" in str(results[-1])