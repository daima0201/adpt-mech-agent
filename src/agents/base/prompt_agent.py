import logging
from typing import Any, Optional, List, Dict

from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.base.base_agent import BaseAgent
from src.agents.enum.cognitive_state import CognitiveState
from src.agents.repositories.models import AgentConfig
from src.agents.prompts.prompt_template import PromptTemplate
from src.shared.exceptions import AgentInitializationError

logger = logging.getLogger(__name__)


# ==================== PromptAgent ====================

class PromptAgent(BaseAgent):
    """
    PromptAgent
    - 增强认知/Prompt管理能力
    """

    def __init__(self, agent_id: str, config: AgentFullConfig, max_history: int = 10):
        super().__init__(agent_id, max_history)
        self.config = config
        self.cognitive_state: Optional[CognitiveState] = CognitiveState.NONE
        self.template_manager = None

    async def customized_initialize(self):
        # 延迟导入以避免循环依赖
        from src.shared.prompts.template_manager import TemplateManager
        if self.template_manager is None:
            self.template_manager = TemplateManager()
        """
        初始化Agent
        """
        try:
            # 1. 验证配置
            self._validate_config(self.config)

            # 2. 初始化模板
            success = self._initialize_templates(self.config)
            if not success:
                logger.error(f"Agent模板初始化失败: {self.agent_id}")
                raise RuntimeError
            logger.info(f"Agent初始化成功: {self.agent_id}")

        except Exception as e:
            logger.error(f"Agent初始化失败 {self.agent_id}: {e}", exc_info=True)

    # ========= 认知状态管理 =========

    def _enter_cognitive_state(self, state: CognitiveState):
        old_state = self.cognitive_state
        self.cognitive_state = state
        # 发言状态联动
        if state in (
                CognitiveState.THINKING,
                CognitiveState.PROCESSING,
                CognitiveState.PLANNING,
                CognitiveState.WAITING_TOOL,
                CognitiveState.REFLECTING):
            self.speaking = True
        else:
            self.speaking = False

        logger.debug(f"{self.agent_id} CognitiveState {old_state} -> {state}, speaking={self.speaking}")

    def get_cognitive_state(self) -> Optional[CognitiveState]:
        return self.cognitive_state

    # ========= Template 代理 =========

    def add_template(self, name: str, template: Any):
        self.template_manager.add_template(name, template)

    def build_full_prompt(self, user_input: str, include_templates: Optional[list] = None) -> str:
        return self.template_manager.build_full_prompt(user_input, include_templates)

    # ========= 核心处理接口 =========

    async def _process(self, input_data: Any, *, stream: bool, **kwargs):
        if input_data is None:
            raise ValueError("输入数据不能为空")

        self._enter_cognitive_state(CognitiveState.NONE)
        try:
            result = await self._do_process(input_data, stream=stream, **kwargs)
            return result
        except Exception:
            self._enter_cognitive_state(CognitiveState.ERROR)
            raise

    async def _do_process(self, input_data: Any, *, stream: bool, **kwargs):
        """
        子类必须实现，负责实际业务逻辑
        """
        raise NotImplementedError

    # ========= TODO:以下待重构 =========

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词（包含所有可用模板和量子计算知识点）

        Returns:
            str: 系统提示词

        设计说明:
            1. 使用角色定义模板构建系统身份
            2. 整合推理框架、检索策略等模板
            3. 添加硬编码的量子计算知识点
            4. 保持简洁，避免在系统提示中包含对话历史
        """
        try:
            prompt_parts = []

            # 1. 角色定义模板（必需）
            role_template = self.template_manager.get_template('角色定义')
            if role_template:
                role_prompt = self.template_manager.render_template('角色定义')
                if role_prompt and role_prompt.strip():
                    prompt_parts.append(role_prompt.strip())

            if not prompt_parts:
                prompt_parts.append("你是一个有帮助的AI助手。请根据用户的输入提供准确、有用的回答。")

            # 2. 推理框架模板（可选）
            reasoning_template = self.template_manager.get_template('推理框架')
            if reasoning_template:
                reasoning_prompt = self.template_manager.render_template('推理框架')
                if reasoning_prompt and reasoning_prompt.strip():
                    prompt_parts.append(f"\n## 思考框架\n{reasoning_prompt.strip()}")

            # 3. 检索策略模板（可选）
            retrieval_template = self.template_manager.get_template('检索策略')
            if retrieval_template:
                retrieval_prompt = self.template_manager.render_template('检索策略')
                if retrieval_prompt and retrieval_prompt.strip():
                    prompt_parts.append(f"\n## 信息检索策略\n{retrieval_prompt.strip()}")

            # 4. 安全策略模板（可选）
            safety_template = self.template_manager.get_template('安全策略')
            if safety_template:
                safety_prompt = self.template_manager.render_template('安全策略')
                if safety_prompt and safety_prompt.strip():
                    prompt_parts.append(f"\n## 安全策略\n{safety_prompt.strip()}")

            # 5. 流程指导模板（可选）
            process_template = self.template_manager.get_template('流程指导')
            if process_template:
                process_prompt = self.template_manager.render_template('流程指导')
                if process_prompt and process_prompt.strip():
                    prompt_parts.append(f"\n## 工作流程指导\n{process_prompt.strip()}")

            # 6. 添加量子计算知识点
            quantum_knowledge = self._get_quantum_computing_knowledge()
            prompt_parts.append(f"\n## 量子专业知识库\n{quantum_knowledge}")

            full_prompt = "\n\n".join(prompt_parts)
            return full_prompt

        except Exception as e:
            logger.error(f"构建系统提示失败: {e}")
            return "你是一个有帮助的AI助手。请根据用户的输入提供准确、有用的回答。"

    @staticmethod
    def _get_quantum_computing_knowledge() -> str:
        """
        获取量子计算专业知识库（硬编码）

        Returns:
            str: 量子计算知识点
        """
        quantum_knowledge = """
    ## 量子计算核心概念
    1. **量子比特 (Qubit)**: 与传统比特不同，量子比特可以同时处于0和1的叠加态
    2. **叠加态 (Superposition)**: 量子系统可以同时存在于多个状态
    3. **纠缠 (Entanglement)**: 两个或多个量子比特之间存在强关联性
    4. **量子门 (Quantum Gates)**: 对量子比特进行操作的基本单元
    
    ## 量子计算优势领域
    1. **优化问题**: 旅行商问题、物流优化、投资组合优化
    2. **机器学习**: 量子神经网络、量子支持向量机
    3. **化学模拟**: 分子结构模拟、药物发现
    4. **密码学**: 量子密钥分发、后量子密码学
    
    ## 量子硬件类型
    1. **超导量子计算机**: IBM、Google使用的主流技术
    2. **离子阱量子计算机**: IonQ等公司采用的技术
    3. **光子量子计算机**: 基于光子的量子计算方案
    4. **拓扑量子计算机**: Microsoft研究的未来方向
    
    ## 实际应用案例
    1. **金融行业**: 风险分析、期权定价、投资组合优化
    2. **制药行业**: 分子模拟、药物设计、蛋白质折叠
    3. **物流行业**: 路径优化、供应链管理、车辆调度
    4. **能源行业**: 材料科学、电池优化、电网管理
    
    ## 实施注意事项
    1. **技术成熟度**: 当前仍处于早期阶段，需要专业团队支持
    2. **成本投入**: 硬件采购和维护成本较高
    3. **人才需求**: 需要量子物理和计算机科学的复合型人才
    4. **集成难度**: 与现有IT系统的集成需要专门规划
    
    ## 典型解决方案时间线
    1. **咨询阶段**: 1-2个月（需求分析、可行性评估）
    2. **原型开发**: 3-6个月（算法设计、小规模测试）
    3. **系统集成**: 6-12个月（与现有系统对接）
    4. **全面部署**: 12-24个月（规模化应用、持续优化）
    
    ## 成本范围参考
    1. **咨询服务**: 10-50万元/项目
    2. **原型开发**: 50-200万元/项目
    3. **完整解决方案**: 200-1000万元/项目
    4. **企业级部署**: 1000万元以上/项目
    
    注意：以上信息仅供参考，具体实施方案需根据客户实际情况定制。
         
    **知识库已准备就绪，可以开始为客户服务。**
    
    """

        return quantum_knowledge.strip()

    def _build_messages(self, system_prompt: str, user_input: str) -> List[Dict[str, str]]:
        """
        构建完整的消息列表

        Args:
            system_prompt: 系统提示词
            user_input: 用户输入

        Returns:
            List[Dict[str, str]]: 完整的消息列表

        消息格式:
            [
                {"role": "system", "content": "系统提示"},
                {"role": "user", "content": "历史用户消息1"},
                {"role": "assistant", "content": "历史助手消息1"},
                {"role": "user", "content": "当前用户输入"}
            ]
        """
        messages = []

        # 1. 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 2. 添加历史对话
        for history_item in self.conversation_history[-self.max_history * 2:]:  # 每条对话包含user和assistant
            messages.append(history_item)

        # 3. 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    @staticmethod
    def _extract_llm_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取LLM相关参数

        Args:
            kwargs: 所有参数

        Returns:
            Dict[str, Any]: 过滤后的LLM参数

        设计说明:
            1. 移除Agent特定的参数
            2. 保留LLM相关参数如temperature、max_tokens等
            3. 设置合理的默认值
        """
        llm_kwargs = kwargs.copy()

        # 移除Agent特定参数
        llm_kwargs.pop('stream', None)  # 由process/process_stream决定
        llm_kwargs.pop('include_templates', None)  # Agent模板参数
        llm_kwargs.pop('preprocess', None)  # 预处理参数
        llm_kwargs.pop('postprocess', None)  # 后处理参数
        llm_kwargs.pop('conversation_history', None)  # 对话历史参数
        llm_kwargs.pop('session_id', None)  # 会话ID参数（LLM API不支持）

        # 设置合理的默认值
        llm_kwargs.setdefault('temperature', 0.7)
        llm_kwargs.setdefault('max_tokens', 2000)

        return llm_kwargs

    def _validate_config(self, full_config: AgentFullConfig):
        """
        验证配置完整性 - 简洁版本
        """
        if not full_config:
            raise AgentInitializationError("Agent配置不能为空")

        # 检查是否有角色定义模板
        has_role_definition = self._has_required_template(full_config, 'role_definition')

        if not has_role_definition:
            logger.warning("Agent配置缺少必需的'角色定义'模板")

        return has_role_definition

    def _has_required_template(self, full_config: AgentFullConfig, template_key: str) -> bool:
        """检查是否包含指定模板"""
        template = self._extract_template(full_config, template_key)
        return template is not None

    @staticmethod
    def _extract_template(full_config: AgentFullConfig, template_key: str) -> Optional[dict]:
        """提取指定模板"""
        # 获取模板数据
        templates_data = None

        if isinstance(full_config, AgentFullConfig):
            # 从AgentFullConfig获取
            if hasattr(full_config, 'prompt_templates') and full_config.prompt_templates:
                templates_data = full_config.prompt_templates
            elif (hasattr(full_config, 'agent_config') and
                  hasattr(full_config.agent_config, 'extra_params')):
                extra_params = full_config.agent_config.extra_params
                if extra_params and 'prompt_templates' in extra_params:
                    templates_data = extra_params['prompt_templates']

        elif isinstance(full_config, AgentConfig):
            # 从AgentConfig获取
            if hasattr(full_config, 'extra_params') and full_config.extra_params:
                extra_params = full_config.extra_params
                if 'prompt_templates' in extra_params:
                    templates_data = extra_params['prompt_templates']

        # 提取指定模板
        if templates_data:
            if isinstance(templates_data, dict):
                return templates_data.get(template_key)
            elif hasattr(templates_data, '__dict__'):
                return getattr(templates_data, template_key, None)

        return None

    def _initialize_templates(self, full_config: AgentFullConfig | AgentConfig) -> bool:
        """
        初始化模板 - 简洁版本
        """
        # 定义要加载的模板
        TEMPLATES_TO_LOAD = [
            ('role_definition', '角色定义', True),
            ('reasoning_framework', '推理框架', False),
            ('retrieval_strategy', '检索策略', False),
            ('safety_policy', '安全策略', False),
            ('process_guide', '流程指导', False),
        ]

        loaded_count = 0

        for template_key, template_name, is_required in TEMPLATES_TO_LOAD:
            try:
                # 提取模板数据
                template_data = self._extract_template(full_config, template_key)

                if not template_data:
                    if is_required:
                        logger.error(f"缺少必需模板: {template_name}")
                        return False
                    continue

                # 创建并加载模板
                prompt_template = self._create_prompt_template(template_data, template_name)
                if prompt_template:
                    self.template_manager.add_template(template_name, prompt_template)
                    loaded_count += 1
                    logger.debug(f"加载模板: {template_name}")
                elif is_required:
                    logger.error(f"无法创建必需模板: {template_name}")
                    return False

            except Exception as e:
                logger.warning(f"加载模板'{template_name}'失败: {e}")
                if is_required:
                    return False

        # 最终验证
        if loaded_count > 0:
            logger.info(f"成功加载 {loaded_count} 个模板")
            return self.template_manager.validate_required_templates()

        return False

    @staticmethod
    def _create_prompt_template(template_data, template_name: str) -> Optional[PromptTemplate]:
        """创建PromptTemplate对象（支持多种格式）"""
        if isinstance(template_data, PromptTemplate):
            return template_data

        return None
