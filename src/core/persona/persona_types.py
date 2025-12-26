# src/core/persona/persona_types.py

from enum import Enum


class PersonaStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class PersonaSwitchPolicy(str, Enum):
    """
    人格是否允许在 Session 中被切换
    """
    FIXED = "fixed"            # 不允许切换
    SESSION = "session"        # 允许 session 内切换
    USER_CONFIRM = "user_confirm"  # 必须用户确认
