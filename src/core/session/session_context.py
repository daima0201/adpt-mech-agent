from typing import Optional, Dict, Any, List


class SessionContext:
    """封装会话状态的上下文类"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.active_agent_id: Optional[str] = None  # 当前激活的 Agent
        self.speaking_agent_id: Optional[str] = None  # 当前发言的 Agent
        self.shared_memory: List[Dict[str, Any]] = []  # 会话共享记忆
        self.user_interruptible: bool = False  # 是否允许用户打断
