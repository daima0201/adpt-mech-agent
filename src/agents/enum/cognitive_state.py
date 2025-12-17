from enum import Enum


class CognitiveState(Enum):
    """
    Agent 认知 / 逻辑状态
    active 的语义：是否仍然拥有当前 session 的发言权
    """

    # ========= 非 active =========

    NONE = "none"  # 尚未进入会话（未绑定 session / 未参与本轮）
    ERROR = "error"  # 本轮失败，退出发言权

    # ========= active（拥有发言权） =========

    READY = "ready"  # 本轮已完成，但仍是当前会话的 active agent

    # 运行中（active）
    THINKING = "thinking"
    PROCESSING = "processing"

    # 高级态（仍 active）
    PLANNING = "planning"
    REFLECTING = "reflecting"

    # 等待外部（仍 active）
    WAITING_TOOL = "waiting_tool"

    # ========= 语义方法 =========

    def is_active(self) -> bool:
        """
        是否仍然拥有 session 的发言权
        """
        return self not in {
            CognitiveState.NONE,
            CognitiveState.ERROR,
        }

    def is_running(self) -> bool:
        """
        是否正在执行中（子集语义）
        """
        return self in {
            CognitiveState.THINKING,
            CognitiveState.PROCESSING,
            CognitiveState.PLANNING,
            CognitiveState.REFLECTING,
            CognitiveState.WAITING_TOOL,
        }
