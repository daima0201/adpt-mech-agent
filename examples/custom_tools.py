#!/usr/bin/env python3
"""
自定义工具使用示例
演示如何创建和使用自定义Agent工具
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.impls.react_agent import ReActAgent
from src.agents.tools.base import Tool
from src.agents.tools.registry import ToolRegistry
from src.shared.config.manager import ConfigManager
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class WeatherTool(Tool):
    """天气查询工具示例"""
    
    def __init__(self):
        super().__init__(
            name="weather",
            description="查询指定城市的天气信息",
            parameters={
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            }
        )
    
    def execute(self, city: str) -> str:
        """执行天气查询"""
        # 这里应该是调用真实天气API的代码
        # 为了示例，我们返回模拟数据
        weather_data = {
            "北京": "晴，25°C",
            "上海": "多云，23°C", 
            "深圳": "小雨，26°C",
            "杭州": "阴，22°C"
        }
        
        if city in weather_data:
            return f"{city}的天气：{weather_data[city]}"
        else:
            return f"抱歉，找不到{city}的天气信息"


class CalculatorTool(Tool):
    """计算器工具示例"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算",
            parameters={
                "expression": {
                    "type": "string", 
                    "description": "数学表达式，如 '2 + 3 * 4'"
                }
            }
        )
    
    def execute(self, expression: str) -> str:
        """执行数学计算"""
        try:
            # 安全地评估数学表达式
            result = eval(expression, {"__builtins__": {}}, {})
            return f"{expression} = {result}"
        except Exception as e:
            return f"计算错误: {e}"


class FileSearchTool(Tool):
    """文件搜索工具示例"""
    
    def __init__(self):
        super().__init__(
            name="file_search",
            description="在项目中搜索包含特定关键词的文件",
            parameters={
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "file_type": {
                    "type": "string", 
                    "description": "文件类型（可选）",
                    "optional": True
                }
            }
        )
    
    def execute(self, keyword: str, file_type: str = None) -> str:
        """执行文件搜索"""
        import glob
        
        # 构建搜索模式
        pattern = f"**/*.{file_type}" if file_type else "**/*"
        
        matches = []
        for file_path in glob.glob(pattern, recursive=True):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if keyword in content:
                        matches.append(file_path)
            except:
                continue
        
        if matches:
            return f"找到包含'{keyword}'的文件:\n" + "\n".join(matches[:10])  # 限制结果数量
        else:
            return f"未找到包含'{keyword}'的文件"


def register_custom_tools():
    """注册自定义工具"""
    registry = ToolRegistry()
    
    # 注册自定义工具
    registry.register(WeatherTool())
    registry.register(CalculatorTool()) 
    registry.register(FileSearchTool())
    
    return registry


def create_custom_agent():
    """创建带有自定义工具的Agent"""
    config = ConfigManager().get_config()
    
    # 注册自定义工具
    tool_registry = register_custom_tools()
    
    # 创建ReAct Agent并注入自定义工具
    agent = ReActAgent(config, tool_registry=tool_registry)
    
    return agent


def run_custom_tool_examples(agent):
    """运行自定义工具示例"""
    examples = [
        "查询北京的天气",
        "计算一下 15 * 8 + 20 / 4 等于多少",
        "搜索项目中包含'knowledge'的文件",
        "帮我找一下Python文件中包含'class Agent'的内容",
        "先查询上海的天气，然后计算 100 - 25 * 3"
    ]
    
    for example in examples:
        print(f"\n{'='*50}")
        print(f"请求: {example}")
        print('-'*50)
        
        try:
            response = agent.process_message(example)
            print(f"响应: {response}")
        except Exception as e:
            print(f"错误: {e}")


def main():
    """主函数"""
    print("=== 自定义工具示例 ===")
    
    try:
        # 1. 创建带有自定义工具的Agent
        print("步骤1: 创建自定义工具Agent...")
        agent = create_custom_agent()
        
        # 2. 显示可用工具
        print("步骤2: 可用工具列表:")
        for tool_name, tool in agent.tool_registry.get_tools().items():
            print(f"  - {tool_name}: {tool.description}")
        
        # 3. 运行示例
        print("步骤3: 运行工具示例...")
        run_custom_tool_examples(agent)
        
        print("\n=== 示例完成 ===")
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"错误: {e}")


if __name__ == "__main__":
    main()