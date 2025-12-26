# src/core/persona/persona_matrix.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

from .persona_types import PersonaStatus, PersonaSwitchPolicy


@dataclass(frozen=True)
class PersonaMatrix:
    """
    PersonaMatrix（人格矩阵）

    设计定位：
    - 不可变（immutable）
    - 只描述“人格是什么”，不描述“人格做什么”
    - Agent / Session / Memory 都只能“消费”它
    """

    # ==================== 身份 ====================

    persona_id: str  # 全局唯一（如: quantum_consultant_v1）
    name: str  # 展示名称
    version: str = "1.0.0"

    # ==================== 状态 ====================

    status: PersonaStatus = PersonaStatus.ACTIVE
    switch_policy: PersonaSwitchPolicy = PersonaSwitchPolicy.USER_CONFIRM

    # ==================== Prompt 相关 ====================

    """
    prompt_templates:
    - key: prompt_type（role_definition / reasoning_framework / safety_policy ...）
    - value: PromptTemplate.to_dict() 或等价结构
    """
    prompt_templates: Dict[str, Any] = field(default_factory=dict)

    """
    prompt_priority:
    决定 Prompt 拼装顺序（可选）
    """
    prompt_priority: List[str] = field(default_factory=list)

    # ==================== Memory 绑定 ====================

    """
    memory_scope_id:
    - 用于 MemoryManager / MemoryStore
    - 一个 persona = 一个独立记忆视角
    """
    memory_scope_id: str = ""

    # ==================== 行为约束（预留） ====================

    """
    behavior_constraints:
    - 不参与第一版逻辑
    - 作为未来 agent policy / tool routing / safety 的输入
    """
    behavior_constraints: Dict[str, Any] = field(default_factory=dict)

    # ==================== 元数据 ====================

    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ==================== 校验 ====================

    def validate(self) -> None:
        """
        轻量校验（不做 I/O）
        """
        if not self.persona_id:
            raise ValueError("persona_id 不能为空")

        if not self.name:
            raise ValueError("persona name 不能为空")

        if not self.memory_scope_id:
            raise ValueError("memory_scope_id 不能为空")

        if self.status == PersonaStatus.DISABLED:
            raise ValueError("DISABLED persona 不应被加载")

    # ==================== Prompt 消费接口 ====================

    def get_prompt_templates(self) -> Dict[str, Any]:
        """
        返回 prompt 模板（只读）
        """
        return dict(self.prompt_templates)

    def get_prompt_order(self) -> List[str]:
        """
        返回 prompt 拼装顺序
        """
        if self.prompt_priority:
            return list(self.prompt_priority)
        return list(self.prompt_templates.keys())

    # ==================== 行为语义 ====================

    def is_switchable(self) -> bool:
        return self.switch_policy != PersonaSwitchPolicy.FIXED

    def require_user_confirm(self) -> bool:
        return self.switch_policy == PersonaSwitchPolicy.USER_CONFIRM

    # ==================== 序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "switch_policy": self.switch_policy.value,
            "memory_scope_id": self.memory_scope_id,
            "prompt_templates": self.prompt_templates,
            "prompt_priority": self.prompt_priority,
            "behavior_constraints": self.behavior_constraints,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaMatrix":
        return cls(
            persona_id=data["persona_id"],
            name=data["name"],
            version=data.get("version", "1.0.0"),
            status=PersonaStatus(data.get("status", "active")),
            switch_policy=PersonaSwitchPolicy(
                data.get("switch_policy", "user_confirm")
            ),
            memory_scope_id=data["memory_scope_id"],
            prompt_templates=data.get("prompt_templates", {}),
            prompt_priority=data.get("prompt_priority", []),
            behavior_constraints=data.get("behavior_constraints", {}),
            description=data.get("description"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def build_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        消费接口：将 prompt_templates 按顺序拼成 system prompt
        - 只做纯拼装，不做 I/O
        - context 作为模板渲染输入（可选）
        """
        context = context or {}

        parts: List[str] = []
        for key in self.get_prompt_order():
            tpl = self.prompt_templates.get(key)
            if not tpl:
                continue

            # 允许两类结构：
            # 1) 直接字符串
            # 2) dict: {"content": "..."} 或 {"template": "..."} 等
            if isinstance(tpl, str):
                text = tpl
            elif isinstance(tpl, dict):
                text = tpl.get("content") or tpl.get("template") or ""
            else:
                text = str(tpl)

            text = text.strip()
            if text:
                # 可选：简单 format 渲染（你也可以以后换成更强的模板引擎）
                try:
                    text = text.format(**context)
                except Exception:
                    # 渲染失败不阻断（避免 persona 因 context 缺字段崩）
                    pass
                parts.append(text)

        return "\n\n".join(parts).strip()
