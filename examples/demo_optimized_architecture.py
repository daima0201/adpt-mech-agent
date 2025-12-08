"""
HelloAgents优化架构演示脚本
展示基于参考架构重构后的智能体框架功能
"""

import asyncio
import logging
from src.agents import (
    SimpleAgent, ReActAgent, ReflectionAgent, PlanAndSolveAgent,
    HelloAgentsLLM, AgentManager, PreconfiguredAgentManager,
    ToolRegistry, CalculatorTool, SearchTool
)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def demo_simple_agents():
    """演示简单智能体功能"""
    print("\n=== 简单智能体演示 ===")
    
    # 创建LLM实例
    llm = HelloAgentsLLM()
    
    # 创建不同类型的智能体
    simple_agent = SimpleAgent("简单助手", llm, "你是一个乐于助人的AI助手。")
    react_agent = ReActAgent("推理助手", llm, "你是一个善于推理和解决问题的AI助手。")
    reflection_agent = ReflectionAgent("反思助手", llm, "你是一个严谨、善于自我反思的AI助手。")
    plan_agent = PlanAndSolveAgent("规划助手", llm, "你是一个擅长制定计划和解决问题的AI助手。")
    
    agents = [simple_agent, react_agent, reflection_agent, plan_agent]
    
    # 测试每个智能体
    test_messages = [
        "你好，请介绍一下你自己",
        "请帮我分析一个复杂问题",
        "对于这个解决方案，你有什么反思和建议？",
        "请帮我制定一个项目计划"
    ]
    
    for i, agent in enumerate(agents):
        if i < len(test_messages):
            response = agent.run(test_messages[i])
            print(f"\n{agent.name} 响应: {response}")

async def demo_tool_integration():
    """演示工具集成功能"""
    print("\n=== 工具集成演示 ===")
    
    # 创建工具注册表
    tool_registry = ToolRegistry()
    
    # 注册内置工具
    calculator = CalculatorTool()
    search_tool = SearchTool()
    
    tool_registry.register_tool(calculator, category="math", tags=["calculation", "arithmetic"])
    tool_registry.register_tool(search_tool, category="search", tags=["information", "web"])
    
    # 显示可用工具
    tools_info = tool_registry.list_tools()
    print(f"可用工具: {tools_info}")
    
    # 测试工具
    result1 = calculator.execute(expression="2 + 3 * 4")
    print(f"计算器结果: {result1}")
    
    # 创建支持工具的智能体
    llm = HelloAgentsLLM()
    react_agent = ReActAgent("工具助手", llm, "你是一个可以使用工具来帮助用户的AI助手。", tool_registry=tool_registry)
    
    # 测试工具调用（模拟）
    response = react_agent.run("请帮我计算一下15乘以28等于多少？")
    print(f"工具助手响应: {response}")

async def demo_agent_manager():
    """演示智能体管理器功能"""
    print("\n=== 智能体管理器演示 ===")
    
    # 创建LLM实例
    llm = HelloAgentsLLM()
    
    # 创建预配置的管理器
    manager = PreconfiguredAgentManager(llm)
    
    # 显示可用智能体
    agents_list = manager.get_agent_list()
    print("可用智能体:")
    for agent in agents_list:
        status = "活跃" if agent['is_active'] else "非活跃"
        print(f"- {agent['name']} ({agent['id']}) - {status}")
    
    # 发送消息给当前活跃智能体
    response1 = await manager.send_message("你好，请介绍一下你自己", "demo_session_1")
    print(f"\n当前活跃智能体响应: {response1}")
    
    # 切换到推理助手
    await manager.switch_active_agent("reasoning_assistant")
    
    # 再次发送消息
    response2 = await manager.send_message("请帮我分析一个复杂问题", "demo_session_1")
    print(f"\n推理助手响应: {response2}")
    
    # 获取会话信息
    active_agent_info = manager.get_active_agent_info()
    print(f"\n活跃智能体信息: {active_agent_info}")
    
    # 提取知识
    knowledge = await manager.extract_knowledge_from_session("demo_session_1")
    print(f"\n从会话中提取的知识项数量: {len(knowledge)}")
    
    if knowledge:
        for item in knowledge[:2]:  # 显示前两个知识项
            print(f"知识项: {item['content'][:100]}... (重要性: {item['importance']:.2f})")

async def demo_advanced_features():
    """演示高级功能"""
    print("\n=== 高级功能演示 ===")
    
    # 创建自定义智能体管理器
    llm = HelloAgentsLLM()
    manager = AgentManager()
    
    # 创建并注册自定义智能体
    custom_agent = SimpleAgent("专业顾问", llm, "你是一个专业的商业顾问，擅长提供战略建议。")
    manager.register_agent("business_advisor", custom_agent)
    
    # 设置自定义智能体为活跃
    await manager.switch_active_agent("business_advisor")
    
    # 测试专业咨询
    business_query = "我们公司想要进入新市场，你有什么建议？"
    response = await manager.send_message(business_query, "business_session")
    print(f"专业顾问响应: {response}")
    
    # 显示会话统计
    session_count = manager.get_session_count()
    print(f"\n当前会话数量: {session_count}")
    
    # 清空会话
    manager.clear_session("business_session")
    print("已清空业务会话")

def demo_configuration():
    """演示配置管理功能"""
    print("\n=== 配置管理演示 ===")
    
    from src.agents.core import ConfigManager
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    # 添加多个配置源
    config_manager.add_source('dict', config_dict={
        'max_history_length': 200,
        'temperature': 0.8,
        'model_name': 'gpt-4'
    })
    
    # 加载配置
    config = config_manager.load_config()
    
    # 显示配置
    print("当前配置:")
    for key in ['max_history_length', 'temperature', 'model_name', 'timeout']:
        value = config.get(key)
        print(f"  {key}: {value}")
    
    # 动态更新配置
    config.set('temperature', 0.9)
    print(f"\n更新后的温度配置: {config.get('temperature')}")

async def main():
    """主演示函数"""
    print("HelloAgents优化架构演示")
    print("=" * 50)
    
    try:
        # 演示各个功能模块
        await demo_simple_agents()
        await demo_tool_integration()
        await demo_agent_manager()
        await demo_advanced_features()
        demo_configuration()
        
        print("\n" + "=" * 50)
        print("演示完成！HelloAgents优化架构运行正常。")
        
    except Exception as e:
        logger.error(f"演示过程中出现错误: {e}")
        print(f"错误详情: {e}")

if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())