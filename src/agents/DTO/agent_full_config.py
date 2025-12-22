"""
Agent完整配置 - 数据传输对象（DTO）
只在内存中使用，不持久化到数据库
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class AgentFullConfig:
    """
    Agent完整配置 - 数据传输对象

    特点：
    1. 只在内存中存在
    2. 从多个数据库表数据组合而成
    3. 用于在服务层传递完整的Agent配置
    4. 支持序列化/反序列化用于缓存

    不持久化到数据库！
    """

    # ==================== 核心数据 ====================
    agent_config: Any  # AgentConfig对象（数据库模型）
    agent_profile: Optional[Any] = None  # AgentProfile对象（可选）
    llm_config: Optional[Any] = None  # LLMConfig对象（可选）

    # Prompt模板字典（key: 模板类型, value: PromptTemplate对象）
    prompt_templates: Dict[str, Any] = field(default_factory=dict)

    # ==================== 元数据 ====================
    source_db_id: Optional[int] = None  # 来源数据库ID
    loaded_at: datetime = field(default_factory=datetime.now)  # 加载时间
    is_valid: bool = True  # 配置是否有效
    validation_errors: List[str] = field(default_factory=list)  # 验证错误

    # ==================== 便捷属性 ====================
    @property
    def agent_id(self) -> Optional[int]:
        """获取Agent数据库ID"""
        return getattr(self.agent_config, 'id', None) if self.agent_config else None

    @property
    def agent_name(self) -> str:
        """获取Agent名称"""
        if self.agent_config:
            return getattr(self.agent_config, 'name', 'Unknown')
        return 'Unknown'

    @property
    def agent_type(self) -> str:
        """获取Agent类型"""
        if self.agent_config:
            return getattr(self.agent_config, 'agent_type', 'unknown')
        return 'unknown'

    @property
    def display_name(self) -> str:
        """获取显示名称"""
        if self.agent_profile and hasattr(self.agent_profile, 'display_name'):
            return self.agent_profile.display_name
        return self.agent_name

    # ==================== 模板相关方法 ====================
    def get_template(self, template_type: str) -> Optional[Any]:
        """获取指定类型模板"""
        return self.prompt_templates.get(template_type)

    def has_template(self, template_type: str) -> bool:
        """检查是否有指定类型模板"""
        return template_type in self.prompt_templates

    def get_required_template(self) -> Optional[Any]:
        """获取必需的角色定义模板"""
        return self.get_template('role_definition')

    def has_required_templates(self) -> bool:
        """检查是否有必需的模板"""
        required_types = ['role_definition']
        return all(self.has_template(t) for t in required_types)

    # ==================== 验证方法 ====================
    def validate(self) -> bool:
        """验证配置是否完整有效"""
        self.validation_errors.clear()

        # 1. 检查AgentConfig
        if not self.agent_config:
            self.validation_errors.append("缺少AgentConfig")
            self.is_valid = False

        # 2. 检查必需模板
        if not self.has_required_templates():
            self.validation_errors.append("缺少必需的角色定义模板")
            self.is_valid = False

        # 3. 检查LLM配置（如果配置中指定了）
        if self.agent_config and hasattr(self.agent_config, 'llm_config_id'):
            if self.agent_config.llm_config_id and not self.llm_config:
                self.validation_errors.append("配置了LLM但未找到LLM配置")
                self.is_valid = False

        return self.is_valid

    # ==================== 序列化方法 ====================
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于缓存/传输）

        注意：对象引用转换为字典，便于序列化
        """
        result = {
            "meta": {
                "source_db_id": self.source_db_id,
                "loaded_at": self.loaded_at.isoformat(),
                "is_valid": self.is_valid,
                "validation_errors": self.validation_errors
            }
        }

        # 转换AgentConfig
        if self.agent_config and hasattr(self.agent_config, 'to_dict'):
            result["agent_config"] = self.agent_config.to_dict()

        # 转换Profile
        if self.agent_profile and hasattr(self.agent_profile, 'to_dict'):
            result["agent_profile"] = self.agent_profile.to_dict()

        # 转换LLMConfig
        if self.llm_config and hasattr(self.llm_config, 'to_dict'):
            result["llm_config"] = self.llm_config.to_dict()

        # 转换模板
        if self.prompt_templates:
            result["prompt_templates"] = {
                key: template.to_dict() if hasattr(template, 'to_dict') else template
                for key, template in self.prompt_templates.items()
            }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentFullConfig':
        """
        从字典创建实例（用于从缓存恢复）

        注意：这里需要导入具体的模型类
        """
        from src.agents.repositories.models import AgentConfig
        from src.agents.repositories.models import AgentProfile
        from src.agents.repositories.models.llm_config import LLMConfig
        from src.agents.prompts.prompt_template import PromptTemplate

        meta = data.get("meta", {})

        # 解析AgentConfig
        agent_config = None
        if "agent_config" in data:
            agent_config = AgentConfig.from_dict(data["agent_config"])

        # 解析Profile
        agent_profile = None
        if "agent_profile" in data:
            agent_profile = AgentProfile.from_dict(data["agent_profile"])

        # 解析LLMConfig
        llm_config = None
        if "llm_config" in data:
            llm_config = LLMConfig.from_dict(data["llm_config"])

        # 解析模板
        prompt_templates = {}
        if "prompt_templates" in data:
            for key, template_data in data["prompt_templates"].items():
                try:
                    template = PromptTemplate.from_dict(template_data)
                    prompt_templates[key] = template
                except Exception as e:
                    logger.warning(f"反序列化模板失败 {key}: {e}")

        # 创建实例
        instance = cls(
            agent_config=agent_config,
            agent_profile=agent_profile,
            llm_config=llm_config,
            prompt_templates=prompt_templates,
            source_db_id=meta.get("source_db_id"),
            loaded_at=datetime.fromisoformat(meta.get("loaded_at")) if meta.get("loaded_at") else datetime.now(),
            is_valid=meta.get("is_valid", True),
            validation_errors=meta.get("validation_errors", [])
        )

        return instance

    # ==================== 工厂方法 ====================
    @classmethod
    async def create_from_database(
            cls,
            repository: 'AgentRepository',
            db_agent_id: int
    ) -> Optional['AgentFullConfig']:
        """
        从数据库创建AgentFullConfig（工厂方法）

        Args:
            repository: AgentRepository实例
            db_agent_id: 数据库Agent ID

        Returns:
            AgentFullConfig: 配置对象，失败返回None
        """
        try:
            # 通过Repository获取数据
            agent = await repository.get_agent(db_agent_id)
            if not agent:
                logger.error(f"Agent配置不存在: {db_agent_id}")
                return None

            profile = await repository.profile_repo.get_by(agent_config_id=db_agent_id)

            llm_config = None
            if agent.llm_config_id:
                # 这里简化，实际需要查询LLMConfig
                pass

            # 获取所有模板
            prompt_templates = {}
            template_fields = [
                ("role_definition_id", "role_definition"),
                ("reasoning_framework_id", "reasoning_framework"),
                ("retrieval_strategy_id", "retrieval_strategy"),
                ("safety_policy_id", "safety_policy"),
                ("process_guide_id", "process_guide"),
            ]

            for field_id, template_key in template_fields:
                if hasattr(agent, field_id):
                    template_id = getattr(agent, field_id)
                    if template_id:
                        # 这里需要查询PromptTemplate
                        pass

            # 创建DTO实例
            full_config = cls(
                agent_config=agent,
                agent_profile=profile,
                llm_config=llm_config,
                prompt_templates=prompt_templates,
                source_db_id=db_agent_id
            )

            # 验证
            full_config.validate()

            return full_config

        except Exception as e:
            logger.error(f"创建AgentFullConfig失败 {db_agent_id}: {e}")
            return None
