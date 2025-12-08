#!/usr/bin/env python3
"""
智能体系统配置和测试脚本
帮助新手了解如何配置和运行智能体系统
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_imports():
    """测试基本导入功能"""
    logger.info("=== 测试基本导入 ===")
    
    try:
        from src.agents.core.llm import MockLLM, HelloAgentsLLM
        from src.agents.core.agent import AgentConfig
        from src.agents.impls.simple_agent import SimpleAgent
        
        logger.info("✅ 基本导入成功")
        return True
    except ImportError as e:
        logger.error(f"❌ 导入失败: {e}")
        return False

def test_mock_llm():
    """测试Mock LLM"""
    logger.info("\n=== 测试Mock LLM ===")
    
    try:
        from src.agents.core.llm import MockLLM
        
        llm = MockLLM()
        messages = [{"role": "user", "content": "你好，请介绍一下你自己"}]
        
        # 测试同步调用
        response = llm.invoke(messages)
        logger.info(f"✅ Mock LLM响应: {response}")
        
        # 测试流式调用
        stream_response = "".join(llm.stream_invoke(messages))
        logger.info(f"✅ Mock LLM流式响应: {stream_response}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Mock LLM测试失败: {e}")
        return False

def test_simple_agent():
    """测试简单智能体"""
    logger.info("\n=== 测试SimpleAgent ===")
    
    try:
        from src.agents.core.llm import MockLLM
        from src.agents.core.agent import AgentConfig
        from src.agents.impls.simple_agent import SimpleAgent
        
        # 创建配置
        config = AgentConfig(
            name="测试助手",
            description="一个简单的测试智能体",
            system_prompt="你是一个乐于助人的AI助手。请用中文回答用户的问题。"
        )
        
        # 创建LLM实例
        llm = MockLLM()
        
        # 创建智能体
        agent = SimpleAgent(config, llm)
        
        # 测试运行
        response = agent.run("你好，请介绍一下你自己")
        logger.info(f"✅ SimpleAgent响应: {response}")
        
        # 测试带元数据的运行
        metadata_response = agent.run_with_metadata("今天的天气怎么样？", {"source": "test"})
        logger.info(f"✅ SimpleAgent带元数据响应: {metadata_response}")
        
        return True
    except Exception as e:
        logger.error(f"❌ SimpleAgent测试失败: {e}")
        return False

def test_agent_manager():
    """测试智能体管理器"""
    logger.info("\n=== 测试AgentManager ===")
    
    try:
        from src.agents.core.manager import PreconfiguredAgentManager
        from src.agents.core.llm import MockLLM
        
        # 创建LLM实例
        llm = MockLLM()
        
        # 创建预配置的管理器
        manager = PreconfiguredAgentManager(llm)
        
        # 获取智能体列表
        agents = manager.get_agent_list()
        logger.info(f"✅ 可用智能体: {len(agents)}个")
        for agent in agents:
            logger.info(f"   - {agent['name']} ({agent['id']})")
        
        # 测试发送消息
        response = manager.send_message("你好", "test_session")
        logger.info(f"✅ AgentManager响应: {response}")
        
        return True
    except Exception as e:
        logger.error(f"❌ AgentManager测试失败: {e}")
        return False

def test_configuration():
    """测试配置系统"""
    logger.info("\n=== 测试配置系统 ===")
    
    try:
        from src.shared.config.manager import ConfigManager
        
        # 创建配置管理器
        config_manager = ConfigManager("configs")
        
        # 加载测试配置
        test_config = config_manager.load_config("test")
        logger.info(f"✅ 测试配置加载成功")
        logger.info(f"   环境: {test_config.get('environment', 'N/A')}")
        logger.info(f"   LLM提供商: {test_config.get('llm', {}).get('provider', 'N/A')}")
        
        # 获取特定配置值
        llm_provider = config_manager.get_config("test", "llm.provider")
        logger.info(f"   LLM提供商（通过点号访问）: {llm_provider}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 配置系统测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🚀 开始智能体系统配置测试...")
    
    tests = [
        ("基本导入", test_basic_imports),
        ("Mock LLM", test_mock_llm),
        ("简单智能体", test_simple_agent),
        ("智能体管理器", test_agent_manager),
        ("配置系统", test_configuration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    logger.info("\n" + "="*50)
    logger.info("📊 测试结果汇总:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    total = len(results)
    logger.info(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试都通过了！智能体系统配置正确。")
        logger.info("\n📝 下一步建议:")
        logger.info("   1. 运行 pytest tests/unit/test_agents/test_agents.py 进行单元测试")
        logger.info("   2. 查看 examples/ 目录中的示例代码")
        logger.info("   3. 修改 configs/test.yaml 来配置真实的LLM服务")
    else:
        logger.warning("⚠️  部分测试失败，请检查错误信息并修复问题。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)