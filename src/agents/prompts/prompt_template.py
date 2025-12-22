"""
Prompt模板数据模型
存储和管理各种Agent的Prompt模板 - 数据库存储版本
"""

from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean, Enum as SQLEnum, text

from src.agents.enum.prompt_type import PromptType
from src.agents.base.base_config import BaseConfig


class PromptTemplate(BaseConfig):
    """Prompt模板模型"""
    __tablename__ = 'prompt_templates'


    # 基本信息
    name = Column(String(100), nullable=False, unique=True, comment="模板名称")
    version = Column(String(20), nullable=False, default="1.0.0", comment="版本号")
    template = Column(Text, nullable=False, comment="Prompt模板内容")
    description = Column(Text, nullable=True, comment="模板描述")

    # 分类信息
    category = Column(String(50), nullable=True, default="general", comment="模板分类")
    variables = Column(JSON, nullable=True, comment="模板变量定义")

    # 新增字段：Prompt类型分类
    prompt_type = Column(String(50), nullable=False, default='role_definition', comment="Prompt类型")
    usage_guidance = Column(Text, nullable=True, comment="使用指导说明")
    is_required = Column(Boolean, server_default='false', comment="是否必需类型")

    # 配置选项
    is_usable = Column(Boolean, server_default='true', comment="是否可用")

    def render(self, **kwargs) -> str:
        """渲染模板"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"缺少必要的模板变量: {e}")
        except Exception as e:
            raise ValueError(f"模板渲染失败: {e}")

    def validate_variables(self, provided_vars: Dict[str, Any]) -> bool:
        """验证提供的变量是否完整"""
        if not self.variables:
            return True

        required_vars = set(self.variables.keys())
        provided_vars_set = set(provided_vars.keys())

        missing_vars = required_vars - provided_vars_set
        if missing_vars:
            raise ValueError(f"缺少必要的模板变量: {missing_vars}")

        return True

    def get_required_variables(self) -> List[str]:
        """获取必需的变量列表"""
        return list(self.variables.keys()) if self.variables else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            'name': self.name,
            'version': self.version,
            'template': self.template,
            'description': self.description,
            'category': self.category,
            'variables': self.variables or {},
            'prompt_type': self.prompt_type if self.prompt_type else 'role_definition',
            'usage_guidance': self.usage_guidance,
            'is_required': self.is_required,
            'is_usable': self.is_usable
        })
        return result

    @classmethod
    def create_from_yaml(cls, yaml_data: Dict[str, Any], created_by: str = "system") -> List['PromptTemplate']:
        """从YAML数据创建模板列表"""
        templates = []

        for prompt_data in yaml_data.get('prompts', []):
            # 解析prompt_type
            prompt_type = prompt_data.get('prompt_type', 'role_definition')

            template = cls(
                name=prompt_data['name'],
                version=prompt_data.get('version', '1.0.0'),
                template=prompt_data['template'],
                description=prompt_data.get('description', ''),
                category=prompt_data.get('category', 'general'),
                variables=prompt_data.get('variables', {}),
                prompt_type=prompt_type,
                usage_guidance=prompt_data.get('usage_guidance'),
                is_required=prompt_data.get('is_required', False),
                is_usable=True
            )
            templates.append(template)

        return templates


class PromptVersion(BaseConfig):
    """Prompt版本历史"""
    __tablename__ = 'prompt_versions'

    prompt_id = Column(Integer, nullable=False, comment="模板ID")
    version = Column(String(20), nullable=False, comment="版本号")

    # 模板内容快照
    template = Column(Text, nullable=False, comment="模板内容")
    variables = Column(JSON, nullable=True, comment="模板变量")

    # 变更信息
    change_reason = Column(Text, nullable=True, comment="变更原因")
    changed_by = Column(String(100), nullable=False, comment="变更者")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            'prompt_id': self.prompt_id,
            'version': self.version,
            'template': self.template,
            'variables': self.variables or {},
            'change_reason': self.change_reason,
            'changed_by': self.changed_by
        })
        return result
