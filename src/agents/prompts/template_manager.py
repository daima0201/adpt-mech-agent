"""
模板管理器 - 提取自BaseAgent
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any

from src.agents.prompts.prompt_template import PromptTemplate
from src.shared.exceptions.agent_errors import AgentTemplateError

logger = logging.getLogger(__name__)


@dataclass
class TemplateStats:
    """模板使用统计"""
    name: str
    render_count: int = 0
    last_rendered_at: Optional[str] = None


class TemplateManager:
    """
    模板管理器 - 专门负责模板的存储、渲染和管理
    """

    def __init__(self):
        self.PromptTemplate = PromptTemplate
        self.templates: Dict[str, PromptTemplate] = {}
        self.template_stats: Dict[str, TemplateStats] = {}

        # 预定义的标准模板类型
        self.STANDARD_TEMPLATES = {
            '角色定义': 'role_definition',
            '推理框架': 'reasoning_framework',
            '检索策略': 'retrieval_strategy',
            '安全策略': 'safety_policy',
            '流程指导': 'process_guide'
        }

        # 必需模板配置
        self.REQUIRED_TEMPLATES = ['角色定义']

        logger.debug("模板管理器初始化完成")

    def add_template(self, name: str, template: PromptTemplate) -> None:
        """添加PromptTemplate对象"""
        if not isinstance(template, PromptTemplate):
            raise TypeError(f"Expected PromptTemplate, got {type(template)}")

        old_template = self.templates.get(name)
        self.templates[name] = template

        # 初始化统计
        if name not in self.template_stats:
            self.template_stats[name] = TemplateStats(name=name)

        if old_template:
            logger.info(f"模板已更新: {name}")
        else:
            logger.info(f"模板已添加: {name}")

    def add_template_from_dict(self, name: str, template_dict: dict) -> None:
        """从字典添加模板"""
        try:
            template = PromptTemplate(**template_dict)
            self.add_template(name, template)
        except Exception as e:
            raise AgentTemplateError(f"Failed to create template from dict: {e}")

    def add_template_from_string(self, name: str, template_string: str,
                                 description: str = "") -> None:
        """从字符串添加模板"""
        template = PromptTemplate(
            name=name,
            template=template_string,
            description=description
        )
        self.add_template(name, template)

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """获取指定名称的模板"""
        template = self.templates.get(name)
        if not template:
            logger.debug(f"模板不存在: {name}")
        return template

    def render_template(self, template_name: str, **kwargs) -> str:
        """渲染指定模板"""
        template = self.get_template(template_name)
        if not template:
            raise AgentTemplateError(f"模板 '{template_name}' 不存在")

        try:
            # 更新统计信息
            stats = self.template_stats.get(template_name)
            if stats:
                stats.render_count += 1
                from datetime import datetime
                stats.last_rendered_at = datetime.now().isoformat()

            # 渲染模板
            rendered = template.render(**kwargs)
            logger.debug(f"模板渲染成功: {template_name} (渲染次数: {stats.render_count if stats else 'N/A'})")
            return rendered

        except Exception as e:
            logger.error(f"渲染模板 '{template_name}' 失败: {e}")
            raise AgentTemplateError(f"Failed to render template '{template_name}': {e}") from e

    def format_prompt(self, template_name: str, **kwargs) -> str:
        """
        格式化prompt模板（包含验证）
        """
        # 验证模板变量
        if not self.validate_template_variables(template_name, **kwargs):
            logger.warning(f"模板变量验证失败: {template_name}")

        try:
            return self.render_template(template_name, **kwargs)
        except Exception as e:
            logger.error(f"模板格式化失败: {template_name}, 错误: {e}")
            raise AgentTemplateError(f"模板格式化失败: {template_name}") from e

    def build_full_prompt(self, user_input: str,
                          include_templates: Optional[list] = None,
                          include_system_prompt: bool = True) -> str:
        """
        构建完整prompt - 增强版本

        Args:
            user_input: 用户输入
            include_templates: 要包含的模板列表，默认为['角色定义', '安全策略']
            include_system_prompt: 是否包含系统提示前缀
        """
        if include_templates is None:
            include_templates = ['角色定义', '安全策略']

        template_parts = []
        for template_name in include_templates:
            if template_name in self.templates:
                try:
                    rendered = self.render_template(template_name)
                    if rendered and rendered.strip():
                        template_parts.append(rendered.strip())
                except Exception as e:
                    logger.warning(f"渲染模板 '{template_name}' 失败: {e}")

        # 组合所有模板部分
        system_prompt = "\n\n".join(template_parts)

        # 添加用户输入
        if system_prompt:
            if include_system_prompt:
                return f"{system_prompt}\n\n用户输入: {user_input}"
            else:
                return f"{system_prompt}\n\n{user_input}"
        return user_input

    def validate_template_variables(self, template_name: str, **kwargs) -> bool:
        """验证模板变量是否匹配"""
        template = self.get_template(template_name)
        if not template:
            return False

        # 简单检查：如果模板中有变量，则必须提供
        if "{{" in template.template and "}}" in template.template and not kwargs:
            logger.warning(f"模板 '{template_name}' 需要变量但未提供")
            return False

        return True

    def list_templates(self, include_stats: bool = True) -> Dict[str, Dict[str, Any]]:
        """列出所有模板的详细信息"""
        result = {}
        for name, template in self.templates.items():
            template_info = {
                "name": template.name,
                "description": getattr(template, 'description', ''),
                "template_preview": template.template[:100] + "..."
                if len(template.template) > 100 else template.template,
                "is_standard": name in self.STANDARD_TEMPLATES,
                "is_required": name in self.REQUIRED_TEMPLATES,
                "has_variables": "{{" in template.template and "}}" in template.template
            }

            # 添加统计信息
            if include_stats and name in self.template_stats:
                stats = self.template_stats[name]
                template_info.update({
                    "render_count": stats.render_count,
                    "last_rendered_at": stats.last_rendered_at
                })

            result[name] = template_info

        return result

    def validate_required_templates(self) -> bool:
        """验证必需模板是否存在"""
        missing_templates = []
        for required in self.REQUIRED_TEMPLATES:
            if required not in self.templates:
                missing_templates.append(required)

        if missing_templates:
            logger.warning(f"缺少必需模板: {missing_templates}")
            return False

        return True

    def get_template_stats(self, template_name: str) -> Optional[TemplateStats]:
        """获取模板统计信息"""
        return self.template_stats.get(template_name)

    def clear_templates(self) -> None:
        """清空所有模板"""
        template_count = len(self.templates)
        self.templates.clear()
        self.template_stats.clear()
        logger.info(f"已清空所有模板 ({template_count} 个)")

    def remove_template(self, name: str) -> bool:
        """删除指定模板"""
        if name in self.templates:
            self.templates.pop(name)
            self.template_stats.pop(name, None)
            logger.info(f"已删除模板: {name}")
            return True
        return False

    def export_templates(self) -> Dict[str, dict]:
        """导出所有模板为字典格式"""
        result = {}
        for name, template in self.templates.items():
            try:
                if hasattr(template, 'to_dict'):
                    result[name] = template.to_dict()
                else:
                    result[name] = {
                        'name': template.name,
                        'template': template.template,
                        'description': getattr(template, 'description', '')
                    }
            except Exception as e:
                logger.error(f"导出模板 '{name}' 失败: {e}")

        return result

    def import_templates(self, templates_dict: Dict[str, dict]) -> int:
        """从字典导入模板"""
        imported_count = 0
        for name, template_data in templates_dict.items():
            try:
                if isinstance(template_data, PromptTemplate):
                    self.add_template(name, template_data)
                elif isinstance(template_data, dict):
                    self.add_template_from_dict(name, template_data)
                elif isinstance(template_data, str):
                    self.add_template_from_string(name, template_data)
                else:
                    logger.warning(f"跳过无法识别的模板数据格式: {name}")
                    continue

                imported_count += 1
                logger.debug(f"导入模板成功: {name}")

            except Exception as e:
                logger.error(f"导入模板 '{name}' 失败: {e}")

        logger.info(f"模板导入完成: 成功 {imported_count}/{len(templates_dict)}")
        return imported_count
