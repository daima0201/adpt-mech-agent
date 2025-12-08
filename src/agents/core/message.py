"""
消息系统
定义消息格式和对话历史管理
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM = "system"
    ERROR = "error"


@dataclass
class Message:
    """消息数据类"""
    content: str
    role: str  # user, assistant, system, tool
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'content': self.content,
            'role': self.role,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息实例"""
        return cls(
            content=data['content'],
            role=data['role'],
            message_type=MessageType(data.get('message_type', 'text')),
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.role}] {self.content}"


class ConversationHistory:
    """对话历史管理器"""
    
    def __init__(self, max_length: int = 100):
        self.max_length = max_length
        self._messages: List[Message] = []
    
    def add_message(self, message: Message) -> None:
        """添加消息到历史记录"""
        self._messages.append(message)
        
        # 如果超过最大长度，移除最早的消息
        if len(self._messages) > self.max_length:
            self._messages = self._messages[-self.max_length:]
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """获取消息列表"""
        if limit:
            return self._messages[-limit:]
        return self._messages.copy()
    
    def get_last_n_messages(self, n: int) -> List[Message]:
        """获取最后n条消息"""
        return self._messages[-n:] if n > 0 else []
    
    def get_messages_by_role(self, role: str) -> List[Message]:
        """按角色筛选消息"""
        return [msg for msg in self._messages if msg.role == role]
    
    def clear(self) -> None:
        """清空历史记录"""
        self._messages.clear()
    
    def size(self) -> int:
        """获取消息数量"""
        return len(self._messages)
    
    def is_empty(self) -> bool:
        """检查是否为空"""
        return len(self._messages) == 0
    
    def to_list(self) -> List[Dict[str, Any]]:
        """转换为字典列表"""
        return [msg.to_dict() for msg in self._messages]
    
    def from_list(self, messages_data: List[Dict[str, Any]]) -> None:
        """从字典列表加载消息"""
        self._messages = [Message.from_dict(data) for data in messages_data]
    
    def get_conversation_summary(self) -> str:
        """生成对话摘要"""
        if not self._messages:
            return "对话历史为空"
        
        # 简单的摘要逻辑
        user_messages = self.get_messages_by_role('user')
        assistant_messages = self.get_messages_by_role('assistant')
        
        summary = f"对话包含 {len(user_messages)} 条用户消息和 {len(assistant_messages)} 条助手回复"
        
        if user_messages:
            last_user_msg = user_messages[-1].content[:50] + "..." if len(user_messages[-1].content) > 50 else user_messages[-1].content
            summary += f"，最近用户消息：{last_user_msg}"
        
        return summary


class MessageBuilder:
    """消息构建器"""
    
    @staticmethod
    def create_user_message(content: str, metadata: Optional[Dict] = None) -> Message:
        """创建用户消息"""
        return Message(content, "user", MessageType.TEXT, metadata=metadata or {})
    
    @staticmethod
    def create_assistant_message(content: str, metadata: Optional[Dict] = None) -> Message:
        """创建助手消息"""
        return Message(content, "assistant", MessageType.TEXT, metadata=metadata or {})
    
    @staticmethod
    def create_system_message(content: str, metadata: Optional[Dict] = None) -> Message:
        """创建系统消息"""
        return Message(content, "system", MessageType.SYSTEM, metadata=metadata or {})
    
    @staticmethod
    def create_tool_call_message(tool_name: str, parameters: str, metadata: Optional[Dict] = None) -> Message:
        """创建工具调用消息"""
        content = f"调用工具 {tool_name}，参数：{parameters}"
        metadata = metadata or {}
        metadata.update({'tool_name': tool_name, 'parameters': parameters})
        return Message(content, "assistant", MessageType.TOOL_CALL, metadata=metadata)
    
    @staticmethod
    def create_tool_result_message(tool_name: str, result: str, metadata: Optional[Dict] = None) -> Message:
        """创建工具结果消息"""
        content = f"工具 {tool_name} 执行结果：{result}"
        metadata = metadata or {}
        metadata.update({'tool_name': tool_name, 'result': result})
        return Message(content, "tool", MessageType.TOOL_RESULT, metadata=metadata)
    
    @staticmethod
    def create_error_message(error_msg: str, metadata: Optional[Dict] = None) -> Message:
        """创建错误消息"""
        metadata = metadata or {}
        metadata.update({'error': True})
        return Message(error_msg, "system", MessageType.ERROR, metadata=metadata)


class MessageFormatter:
    """消息格式化器"""
    
    @staticmethod
    def format_for_llm(messages: List[Message]) -> List[Dict[str, str]]:
        """将消息列表格式化为LLM输入格式"""
        formatted_messages = []
        
        for msg in messages:
            # 根据消息类型和角色进行格式化
            if msg.message_type == MessageType.TOOL_CALL:
                # 工具调用消息通常不需要发送给LLM
                continue
            elif msg.message_type == MessageType.TOOL_RESULT:
                # 工具结果作为用户消息发送
                formatted_messages.append({
                    "role": "user",
                    "content": f"工具执行结果：{msg.content}"
                })
            else:
                # 普通消息直接转换
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return formatted_messages
    
    @staticmethod
    def format_for_display(messages: List[Message], include_timestamps: bool = False) -> str:
        """将消息列表格式化为可读文本"""
        lines = []
        
        for msg in messages:
            timestamp_str = f"[{msg.timestamp.strftime('%H:%M:%S')}] " if include_timestamps else ""
            
            if msg.message_type == MessageType.TOOL_CALL:
                lines.append(f"{timestamp_str}🔧 {msg.role}: {msg.content}")
            elif msg.message_type == MessageType.TOOL_RESULT:
                lines.append(f"{timestamp_str}📊 {msg.role}: {msg.content}")
            elif msg.message_type == MessageType.ERROR:
                lines.append(f"{timestamp_str}❌ {msg.role}: {msg.content}")
            else:
                lines.append(f"{timestamp_str}{msg.role}: {msg.content}")
        
        return "\n".join(lines)