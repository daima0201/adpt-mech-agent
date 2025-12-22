"""
模拟LLM实现 - 用于测试和开发
"""

from typing import List, Dict, Any, Optional, Iterator, AsyncIterable
from src.agents.base.base_llm import BaseLLM, LLMConfig


class MockLLM(BaseLLM):
    """模拟LLM - 用于测试和开发"""
    
    async def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """异步模拟调用"""
        last_message = messages[-1]['content'] if messages else ""
        
        # 检查是否是ReAct格式的提示词
        if "请开始思考这个问题" in last_message or "请继续思考" in last_message:
            return """思考：用户提出了一个问题，我需要分析这个问题并给出专业回答。
行动：FINISH
观察：这是一个关于量子加密产品销售的问题，我可以直接提供相关信息。"""
        
        # 根据不同的输入内容返回不同的响应
        if "你好" in last_message or "hello" in last_message.lower():
            return """思考：用户在打招呼，我应该礼貌回应并介绍自己。
行动：FINISH
观察：您好！我是量子加密产品销售经理，很高兴为您服务。请问有什么可以帮助您的吗？"""
        elif "价格" in last_message or "多少钱" in last_message:
            return """思考：用户在询问价格信息，我需要提供详细的价格方案。
行动：FINISH
观察：我们的量子加密产品有多种规格和价格方案，基础版起价10万元，企业版50万元起，具体价格取决于您的需求规模。"""
        elif "功能" in last_message or "特点" in last_message:
            return """思考：用户在询问产品功能和特点。
行动：FINISH
观察：我们的量子加密产品具有以下核心特点：量子密钥分发、抗量子攻击、端到端加密、高性能处理能力，支持多种应用场景。"""
        elif "退出" in last_message or "quit" in last_message.lower() or "exit" in last_message.lower():
            return """思考：用户想要结束对话。
行动：FINISH
观察：感谢您的咨询！如有任何问题，随时联系我们。祝您有美好的一天！"""
        else:
            return f"""思考：用户说'{last_message}'，我需要理解用户的具体需求并提供专业建议。
行动：FINISH
观察：我理解了您的需求。作为量子加密产品销售经理，我可以为您提供产品介绍、价格咨询、技术方案等服务。请告诉我您具体关心什么方面？"""
    
    def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterable[str]:
        """模拟流式调用"""
        last_message = messages[-1]['content'] if messages else ""
        response = f"这是对'{last_message}'的模拟流式回答。"
        for char in response:
            yield char
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模拟模型信息"""
        return {
            'provider': 'Mock',
            'model': 'mock-model',
            'capabilities': ['chat', 'completion', 'streaming']
        }