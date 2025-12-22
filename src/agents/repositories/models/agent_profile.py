"""
智能体Profile模型
对应 agent_profiles 表
"""

from sqlalchemy import Column, String, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from src.agents.base.base_config import BaseConfig

class AgentProfile(BaseConfig):
    """智能体Profile模型"""
    __tablename__ = 'agent_profiles'
    
    agent_config_id = Column(Integer, ForeignKey('agent_configs.id'), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    expertise_domains = Column(JSON, nullable=True)  # 专业领域列表（用途为工具调用路由提供参考）
    language = Column(String(10), default='zh-CN')
    max_context_length = Column(Integer, default=4000)
    is_public = Column(Boolean, server_default='false')
    custom_metadata = Column(JSON, nullable=True)
    is_usable = Column(Boolean, server_default='true', comment="是否可用")
    
    # 新增字段：增强沟通风格配置
    communication_style_id = Column(Integer, ForeignKey('prompt_templates.id'), nullable=True, comment="沟通风格ID")
    personality_tags = Column(JSON, nullable=True, default=[], comment="个性标签列表")
    
    # 关系定义
    agent_config = relationship("AgentConfig", back_populates="profile")
    
    @property
    def communication_style(self):
        from src.agents.prompts.prompt_template import PromptTemplate
        return self._get_relationship(PromptTemplate, "communication_style_id")
    
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
        return f"<AgentProfile(id={self.id}, agent_config_id={self.agent_config_id})>"
    
    @property
    def formatted_expertise(self) -> str:
        """格式化专业领域"""
        if self.expertise_domains:
            return ', '.join(self.expertise_domains)
        return ""
    
    def has_expertise(self, domain: str) -> bool:
        """检查是否具备某个专业领域"""
        if not self.expertise_domains:
            return False
        return any(domain.lower() in d.lower() for d in self.expertise_domains)
    
    @property
    def agent_name(self) -> str:
        """获取关联的Agent名称"""
        if self.agent_config:
            return self.agent_config.name
        return f"Unknown Agent (ID: {self.agent_config_id})"
    
    @property
    def agent_type(self) -> str:
        """获取关联的Agent类型"""
        if self.agent_config:
            return self.agent_config.agent_type
        return "unknown"
    
    def get_avatar_url(self, default_url: str = None) -> str:
        """获取头像URL，提供默认值"""
        if self.avatar_url:
            return self.avatar_url
        if default_url:
            return default_url
        
        # 根据个性标签返回默认头像（优先使用新字段）
        if self.personality_tags and isinstance(self.personality_tags, list):
            tags = [tag.lower() for tag in self.personality_tags]
            if 'friendly' in tags or '友好' in tags:
                return "/assets/avatars/friendly.png"
            elif 'professional' in tags or '专业' in tags:
                return "/assets/avatars/professional.png"
            elif 'creative' in tags or '创意' in tags:
                return "/assets/avatars/creative.png"
        
        # 回退到旧字段
        if self.personality == "friendly":
            return "/assets/avatars/friendly.png"
        elif self.personality == "professional":
            return "/assets/avatars/professional.png"
        else:
            return "/assets/avatars/default.png"