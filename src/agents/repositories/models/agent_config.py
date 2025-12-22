"""
智能体配置模型
对应 agent_configs 表
"""
from typing import Dict, Optional, List

from sqlalchemy import Column, String, Text, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship

from src.agents.base.base_config import BaseConfig


class AgentConfig(BaseConfig):
    """智能体配置模型"""
    __tablename__ = 'agent_configs'

    name = Column(String(100), nullable=False, unique=True, comment="角色模板名称")
    agent_type = Column(String(50), nullable=False)  # simple, react, reflection, plan_solve
    llm_config_id = Column(Integer, ForeignKey('llm_configs.id'), nullable=False)
    max_iterations = Column(Integer, default=10)
    timeout = Column(Integer, default=300)
    extra_params = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_usable = Column(Boolean, server_default='true', comment="是否可用")

    # 新增字段：重构Prompt引用方式
    role_definition_id = Column(Integer, ForeignKey('prompt_templates.id'), nullable=False, comment="角色定义ID")
    reasoning_framework_id = Column(Integer, ForeignKey('prompt_templates.id'), nullable=True, comment="推理框架ID")
    retrieval_strategy_id = Column(Integer, ForeignKey('prompt_templates.id'), nullable=True, comment="检索策略ID")
    safety_policy_id = Column(Integer, ForeignKey('prompt_templates.id'), nullable=True, comment="安全策略ID")
    process_guide_id = Column(Integer, ForeignKey('prompt_templates.id'), nullable=True, comment="流程指导ID")

    # 工具系统集成
    enabled_tools = Column(JSON, nullable=True, default=[], comment="启用工具列表")
    # tool_selection_strategy = Column(String(50), nullable=True, default='static', comment="工具选择策略")
    tool_call_strategy = Column(String(50), nullable=True, default='conservative', comment="工具调用策略")

    # 关系定义
    llm_config = relationship("LLMConfig", backref="agents")
    profile = relationship("AgentProfile", back_populates="agent_config", uselist=False, cascade="all, delete-orphan")

    # 新增Prompt模板关系（使用延迟导入避免循环依赖）
    @property
    def role_definition(self):
        from src.agents.prompts.prompt_template import PromptTemplate
        return self._get_relationship(PromptTemplate, "role_definition_id")

    @property
    def reasoning_framework(self):
        from src.agents.prompts.prompt_template import PromptTemplate
        return self._get_relationship(PromptTemplate, "reasoning_framework_id")

    @property
    def retrieval_strategy(self):
        from src.agents.prompts.prompt_template import PromptTemplate
        return self._get_relationship(PromptTemplate, "retrieval_strategy_id")

    @property
    def safety_policy(self):
        from src.agents.prompts.prompt_template import PromptTemplate
        return self._get_relationship(PromptTemplate, "safety_policy_id")

    @property
    def process_guide(self):
        from src.agents.prompts.prompt_template import PromptTemplate
        return self._get_relationship(PromptTemplate, "process_guide_id")

    # 延迟导入以避免循环依赖（保留旧字段兼容性）
    @property
    def prompt_template(self):
        from src.agents.prompts.prompt_template import PromptTemplate
        return self._get_relationship(PromptTemplate, "default_prompt_template_id")

    def _get_relationship(self, model_class, foreign_key_field):
        """获取关系对象"""
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if session is None:
            return None
        foreign_key_value = getattr(self, foreign_key_field)
        if foreign_key_value is None:
            return None
        return session.query(model_class).filter_by(id=foreign_key_value).first()

    def __repr__(self):
        return f"<AgentConfig(id={self.id}, name='{self.name}', type='{self.agent_type}')>"

    @property
    def full_config(self) -> dict:
        """获取完整配置信息"""
        config = self.to_dict()
        if self.llm_config:
            config['llm_config'] = self.llm_config.to_dict()

        # 新增Prompt模板配置
        if self.role_definition:
            config['role_definition'] = self.role_definition.to_dict()
        if self.reasoning_framework:
            config['reasoning_framework'] = self.reasoning_framework.to_dict()
        if self.retrieval_strategy:
            config['retrieval_strategy'] = self.retrieval_strategy.to_dict()
        if self.safety_policy:
            config['safety_policy'] = self.safety_policy.to_dict()
        if self.process_guide:
            config['process_guide'] = self.process_guide.to_dict()

        return config

    @property
    def display_name(self) -> str:
        """获取显示名称（优先使用profile中的display_name）"""
        if self.profile and self.profile.display_name:
            return self.profile.display_name
        return self.name

    @property
    def is_public(self) -> bool:
        """检查是否公开"""
        if self.profile:
            return self.profile.is_public
        return False

    def has_expertise(self, domain: str) -> bool:
        """检查是否具备某个专业领域"""
        if self.profile:
            return self.profile.has_expertise(domain)
        return False

    def get_all_template_ids(self) -> Dict[str, Optional[int]]:
        """
        获取所有模板ID

        Returns:
            Dict格式: {
                "role_definition": id,
                "reasoning_framework": id,
                "retrieval_strategy": id,
                "safety_policy": id,
                "process_guide": id
            }
        """
        template_ids = {}

        fields = [
            "role_definition_id",
            "reasoning_framework_id",
            "retrieval_strategy_id",
            "safety_policy_id",
            "process_guide_id"
        ]

        for field in fields:
            if hasattr(self, field):
                value = getattr(self, field)
                # 从field名去掉_id，作为key
                key = field.replace("_id", "")
                template_ids[key] = value

        return template_ids

    def has_template(self, template_type: str) -> bool:
        """检查是否有指定类型的模板"""
        field_name = f"{template_type}_id"
        if hasattr(self, field_name):
            return bool(getattr(self, field_name))
        return False

    @staticmethod
    def get_template_field_names() -> List[str]:
        """获取所有模板字段名"""
        return [
            "role_definition_id",
            "reasoning_framework_id",
            "retrieval_strategy_id",
            "safety_policy_id",
            "process_guide_id"
        ]
