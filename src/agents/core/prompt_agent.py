import logging
from typing import Any, Optional, List, Dict

from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.core.base_agent import BaseAgent
from src.agents.enum.cognitive_state import CognitiveState
from src.agents.models import AgentConfig
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
        from src.managers.template_manager import TemplateManager
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
    
    收到第一张表，我已将其整理为以下结构化的知识点条目，供后续调用。
    -----
    ### **知识库：量子加密文件产品 (表1)**
    **领域：** 产品定义、功能、优势、适用场景与办理条件
    
    ---
    
    **K001: 产品介绍**
    *   **核心描述：** 上海电信推出的商业秘密文件全生命周期安全防护产品。融合量子加密技术，为商业秘密/工作秘密电子文件在存储、流转、外发过程中提供加密防护、分级分类、权限管控、外发安全等全流程管理。
    *   **业务场景：** 产品咨询
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 产品介绍、文件，量子加密、全流程管理
    
    **K002: 产品结构**
    *   **核心描述：** 产品由三部分组成：
        1.  **量子密码服务平台：** 生成文档专属量子密钥，为文件加解密提供密钥支撑。
        2.  **量子加密文件服务端：** 核验用户访问权限；接收量子密钥对文件执行加密/解密操作。
        3.  **量子加密文件客户端：** 用户操作终端入口，实现终端侧文件安全管理，向服务端请求加解密，是用户与后台交互的桥梁。
    *   **业务场景：** 产品咨询
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 产品结构、客户端、服务端、量子密码服务平台、权限
    
    **K003: 文件定密管理**
    *   **核心描述：** 基于目录策略和规则，识别并智能标定商密/工作秘密文件的密级，实现分级分类。
        *   根据秘密事项录入系统目录进行分类管理。
        *   自动识别内容、提取关键词，给出密级建议。
        *   设置不同标密策略和分级权限。
        *   可设置商密权属、保密期限、知悉范围。
    *   **业务场景：** 产品功能介绍
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 标密策略、商密权属、保密期限、知悉范围、分类管理
    
    **K004: 文件显性标识与溯源监控**
    *   **核心描述：** 为加密文件绑定密级标识并添加多类型水印，实现全流程操作审计与泄密追溯。
        *   支持内嵌、浮动、阅读等多种水印。
        *   兼容办公、设计、图片、多媒体等常用格式。
        *   审计应标未标、非法打印、违规解密等操作日志。
        *   泄密时可对解密外发、截屏、拍照等行为进行追溯。
    *   **业务场景：** 产品功能介绍
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 水印、文件格式、溯源监控
    
    **K005: 文件内部流转**
    *   **核心描述：** 支持单位内部商密文件安全流转，提供多样化分享渠道与可控化流转能力。
        *   双方安装客户端后，可通过OA、邮箱等渠道发送加密文件。
        *   借助文档库、密盘进行知识分享与存储。
        *   客户端内置“密件收发”专用通道，支持阅后即焚、再授权等功能。
    *   **业务场景：** 产品功能介绍
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 内部流转、OA、文档库、密盘
    
    **K006: 文件外部流转**
    *   **核心描述：** 支持单位外部商密文件安全流转，实现便捷交付与精细化权限管控。
        *   外部分享可生成文档包或外链。
        *   接收方无需安装客户端即可查阅。
        *   可管控阅读次数、期限、打印权限及下载。
    *   **业务场景：** 产品功能介绍
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 外部流转、文档包，外链、打印权限
    
    **K007: 量子加密文件产品优势**
    *   **核心描述：**
        1.  **政策合规，深度适配：** 拥有国密局、保密局、公安部等权威认证，符合《中央企业商业秘密安全保护技术指引》。
        2.  **量子加持，安全可靠：** 采用SM4国密算法+量子真随机密钥，实现“一文一密”，加密真随机，全流程量子加密。
        3.  **功能全面，灵活策略：** 覆盖文档全生命周期防护，支持阅后即焚、溯源水印等；支持按密级动态调整防护强度，审批流程可自定义。
        4.  **场景丰富，灵活适配：** 支持数据隔离、断网可用等场景；云化部署，由运营商提供专业运维与升级支持。
    *   **业务场景：** 产品竞品比较
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 商秘、SM4国密算法、真随机密钥、一文一密、灵活策略配置、全生命周期防护
    
    **K008: 适用服务场景**
    *   **核心描述：** 面向拥有商业秘密防护需求的各类单位（央企、党政机关、金融机构、交通能源、教育医疗、上市公司等）。
        1.  **单位内部核心商密传递：** 如下发会议纪要、工资明细、营销策略等，保障内部流转不泄露。
        2.  **单位之间核心商密交互：** 如传递部委函件、商务合同、招投标材料等，确保外部流转安全。
    *   **业务场景：** 产品咨询
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 内部商密传递、外部流转、面向行业
    
    **K009: 办理使用条件**
    *   **核心描述：**
        1.  **业务办理：** 企业客户需携带三证等资质文件，联系电信BD或区局客户经理开通业务功能包。
        2.  **终端准备：** 客户端要求运行于Windows系统的PC终端。
    *   **业务场景：** 产品开通
    *   **关联产品：** 量子加密文件产品
    *   **关键词：** 终端、PC、操作系统、使用条件、资质文件、客户经理
    收到第二张表，我已将其整理为以下结构化的对话范例库，供后续调用。
    
    ### **知识库：标准对话范例 (表2)**
    **领域：** 常见客户痛点、客服回应标准话术与流程
    
    ---
    
    #### **范例组D001：文件权限管控**
    *   **用户痛点：** 离职员工还能登录旧账号解密文件，非授权岗位人员误操作核心资料。
    *   **用户意图：** 权限管控漏洞，渴望解决方案。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **共情与安抚：** “这种情况确实很常见，给您推荐一款产品可以解顾虑...”
        2.  **推荐产品：** “量子加密文件产品要求操作人员先完成身份认证，只有通过认证的人员才能开展文件加密、解密相关操作...”
        3.  **阐述效果：** “这样就从权限源头把控文件安全，避免因权限混乱导致的文件安全隐患，这样就解决问题了。”
    *   **业务场景：** 文件权限管控
    *   **对应知识点：** K002 (产品结构中的权限核验)
    
    #### **范例组D002：文件加密防护**
    *   **用户痛点：** 企业核心商密文件在存储或传输中总是被恶意窃取、篡改。
    *   **用户意图：** 文件传输不安全，渴望解决方案。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **共情与安抚：** “这种情况真是防不胜防，但是有一款产品可以从根源上解决该问题...”
        2.  **推荐产品：** “这就是量子加密文件，该产品采用 SM4 国密算法 + 量子真随机密钥，实现一文一密的量子级加密...”
        3.  **阐述效果：** “加密密钥具备真随机特性，能有效抵御传统加密手段无法防范的算力破解，为您的核心商密文件筑牢安全防线。”
    *   **业务场景：** 文件加密防护
    *   **对应知识点：** K007 (产品优势：量子加持，安全可靠)
    
    #### **范例组D003：文件分级管控**
    *   **用户痛点：** 大规模企业，大量文件无法精准判定密级、分类混乱。
    *   **用户意图：** 文件管理混乱，渴望解决方案。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **共情与安抚：** “管理起来太辛苦了，给您推荐一款产品可以解决该问题...”
        2.  **推荐产品：** “量子加密文件产品可基于商密目录制定策略规则，智能识别文件内容并标定密级...”
        3.  **阐述效果：** “实现核心商密、普通商密等分级分类管理，还能明确商密权属、保密期限与知悉范围，让文件密级管控更规范高效。”
    *   **业务场景：** 文件分级管控
    *   **对应知识点：** K003 (文件定密管理)
    
    #### **范例组D004：多类型文件统一管控**
    *   **用户痛点：** 企业业务复杂，存在 Word、Excel、CAD、PSD 等多类型文件，寻求统一管理防护方案。
    *   **用户意图：** 文件类型多样，渴望统一管控。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **共情与安抚：** “有的，我来为您推荐一款产品...”
        2.  **推荐产品：** “量子加密文件，量子加密文件产品支持办公类、设计类、图片类、多媒体类等全品类常用文件格式加密...”
        3.  **阐述效果：** “无需区分文件类型即可一键防护，全面覆盖企业各类文件安全需求。”
    *   **业务场景：** 多类型文件统一管控
    *   **对应知识点：** K004 (文件显性标识与溯源监控：兼容多格式)
    
    #### **范例组D005：违规操作追踪回溯**
    *   **用户痛点：** 出现过文件违规打印、非法解密却无法追责的情况。
    *   **用户意图：** 违规操作无法追责，渴望解决方案。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **共情与安抚：** “这种行为确实很严重，会为企业带来不可逆的消极影响...”
        2.  **推荐产品：** “我来为您推荐一款产品可以解决这个问题，量子加密文件产品支持全生命周期审计...”
        3.  **阐述效果：** “可记录文件阅读、编辑、复制、外发等所有操作日志，一旦出现违规操作能及时预警，若发生泄密还可精准追溯操作源头，杜绝泄密隐患。”
    *   **业务场景：** 违规操作追踪回溯
    *   **对应知识点：** K004 (文件显性标识与溯源监控：审计与追溯)
    
    #### **范例组D006：内外部文件安全流转管控**
    *   **用户痛点：** 商密文件需要内部流转和外发，担心被违规操作。
    *   **用户意图：** 文件流转方式多样，渴望安全防控。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **共情与安抚：** “有的，我来为您推荐一款产品...”
        2.  **推荐产品：** “量子加密文件，量子加密文件产品支持直接使用OA、邮箱、微信等形式发送加密文件...外发文件可打包为 EXE 格式...”
        3.  **阐述效果：** “...实现内外部流转全可控。”
    *   **业务场景：** 内外部文件安全流转管控
    *   **对应知识点：** K005 (文件内部流转), K006 (文件外部流转)
    
    #### **范例组D007：电子公文国产化替代 (特殊场景)**
    *   **用户异议：** 质疑产品能否解决电子公文国产化替代中的保密与分级管理难题。
    *   **用户意图：** 对产品提出异议，需要进一步解释。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **高度共情与认同：** “主任，您说的这个痛点太关键了，也是目前党政机关国产化改造中最受关注的问题。”
        2.  **针对性介绍产品：** “咱们这款量子加密文件产品，刚好能针对性解决您提到的保密和分级管控需求。量子加密文件产品依托于上海电信量子城域网，通过量子加密技术，可实现公文智能定密与分级管控...”
        3.  **阐述合规性效果：** “文件流转可限定知悉范围，搭配水印、溯源审计功能，杜绝政务敏感信息外泄，同时满足党政机关电子政务建设的保密规范。”
    *   **业务场景：** 电子公文国产化替代需求
    *   **对应知识点：** K003 (文件定密管理), K004 (水印与溯源), K008 (适用服务场景：党政机关)
    
    #### **范例组D008：国资委商密保护合规 (特殊场景)**
    *   **用户抱怨：** 国资委商密保护制度落地难，人工标密易出错，操作无法实时掌控。
    *   **用户意图：** 抱怨吐槽现状，渴望解决方案。
    *   **客服标准回应 (话术 & 流程)：**
        1.  **深度共情与强调危害：** “特别理解你的困扰！央国企的商密信息直接关系到企业核心利益，一旦泄露损失确实不可估量。”
        2.  **推荐产品：** “我来为您推荐一款产品，量子加密文件，专门解决制度落地难和数据泄露的痛点。量子加密文件产品通过量子加密技术，可实现商密文件从创建、流转、外发到解密的全生命周期防护...”
        3.  **阐述效果：** “支持智能定密、权限管控和操作溯源，还能按企业商密目录建立标密规范，实时监控商密文件分布与操作情况，为企业筑牢商密安全屏障。”
    *   **业务场景：** 商业秘密文件全流程防护 (符合国资委规定)
    *   **对应知识点：** K003 (文件定密管理), K004 (溯源监控), K007 (产品优势：政策合规), K008 (适用服务场景：央企)
    
    -----
    
    收到第三张表，我已将其整理为以下结构化的场景化话术库，供后续调用。
    
    ### **知识库：场景化专业话术 (表3)**
    **领域：** 针对特定行业或具体功能痛点的专业化销售/客服沟通话术
    
    ---
    
    #### **行业场景话术**
    
    **S001: 党政机关 - 电子公文国产化替代**
    *   **业务场景：** 电子公文国产化替代需求，公文及工作秘密文件的保密传输与合规管控，防止敏感政务信息外泄。
    *   **专业话术：** “据了解咱们党政机关正推进电子公文国产化替代，且对政务秘密文件的保密传输和合规管理有严格要求。量子加密文件产品依托于上海电信量子城域网，通过量子加密技术，可实现公文智能定密与分级管控，支持电子公文全生命周期加密防护。文件流转可限定知悉范围，搭配水印、溯源审计功能，杜绝政务敏感信息外泄，同时满足党政机关电子政务建设的保密规范。”
    *   **使用时机：** 对接党政机关信息化/保密办负责人，客户提及电子公文国产化改造、政务信息保密合规痛点时。
    *   **效果说明：** 精准匹配国产化与保密双重需求，突出合规性与安全性，提升政务场景认可度。
    
    **S002: 央国企 - 商业秘密全流程防护**
    *   **业务场景：** 商业秘密文件的全流程防护，需符合国资委商密保护规定，防范核心经营、技术信息泄露。
    *   **专业话术：** “央国企对商业秘密保护有明确的制度要求，核心经营数据、技术资料一旦泄露会造成重大损失。量子加密文件产品通过量子加密技术，可实现商密文件从创建、流转、外发到解密的全生命周期防护，支持智能定密、权限管控和操作溯源，还能按企业商密目录建立标密规范，实时监控商密文件分布与操作情况，为企业筑牢商密安全屏障。”
    *   **使用时机：** 对接央国企保密管理部门、法务部或信息化负责人，客户阐述商密保护制度落地难、核心数据易泄露的困扰时。
    *   **效果说明：** 紧扣国资委合规要求，解决商密管控痛点，增强央国企客户合作意愿。
    
    **S003: 金融机构 - 金融数据防泄露防篡改**
    *   **业务场景：** 金融数据如客户隐私、交易记录、风控模型的防泄露、防篡改。
    *   **专业话术：** “领导好，金融行业的客户隐私信息、核心交易记录以及风控模型等数据...量子加密文件产品采用 SM4 国密算法 + 量子真随机密钥，可对...实现一文一密的量子级加密，从根源上防止数据被篡改；同时支持文件智能定密和细粒度权限管控...搭配全生命周期操作日志审计，可精准追溯数据操作轨迹，既保障金融核心数据的安全，又符合银保监会等监管部门的数据保密规范。”
    *   **使用时机：** 对接银行、证券、保险等金融机构的信息安全部门、风控部门负责人，客户提及客户隐私保护、监管合规及数据防篡改需求时。
    *   **效果说明：** 结合行业监管要求，突出国密算法+量子密钥、一文一密和全生命周期审计，满足合规并建立安全信任。
    
    **S004: 科研机构 - 学术成果与专利保护**
    *   **业务场景：** 保护学术研究成果、技术专利、实验数据，防范论文的非授权分享或下载。
    *   **专业话术：** “研究成果、技术数据等信息一旦被非法获取，会危及国家利益...量子加密文件产品支持办公、设计、图片、多媒体等多类常用文件格式，为科研文件提供量子加密保护，支持科研数据智能定密和分级存储，还可实现跨团队加密流转，搭配水印等机制，防止科研信息外泄，一旦非授权下载或解密外发等操作，可通过日志审查追溯违规操作。”
    *   **使用时机：** 对接高校科研管理部门、科研院所项目负责人，客户反馈科研成果易被窃取、专利信息难保密的问题时。
    *   **效果说明：** 针对科研文件多格式、跨团队流转特性，突出多格式兼容、分级存储与违规追溯，解决科研成果全链路保密难题。
    
    **S005: 医疗机构 - 患者隐私与临床数据安全**
    *   **业务场景：** 患者病情隐私信息、临床试验数据、新药研发资料的安全存储与研讨，防止医疗敏感数据泄露。
    *   **专业话术：** “医疗行业的患者病情信息属于核心隐私，临床试验数据也需严格保密，科室间研讨还需保障信息传输安全。量子加密文件产品可对患者病历、临床试验数据进行加密存储，支持企业内部科室间加密文件流转研讨，设置阅后即焚、再授权等防护机制，还能实现医疗文件操作溯源，既保护患者隐私，又保障临床试验数据的安全同步，符合医疗行业数据保密规范。”
    *   **使用时机：** 对接医院信息科、医药企业研发部门负责人，客户提及患者隐私保护、临床试验数据同步安全等痛点时。
    *   **效果说明：** 贴合医疗行业隐私与合规要求，突出加密存储、操作溯源，兼顾内部流转便捷性与安全性。
    
    **S006: 法律行业 - 诉讼材料与合同草案保密**
    *   **业务场景：** 保障诉讼材料、合同草案、专利申请书等文件的机密性。
    *   **专业话术：** “法律行业的诉讼材料、合同草案、专利申请书等文件，是案件推进和权益保障的核心依据...量子加密文件产品可对各类法律涉密文件进行量子加密保护，支持按文件重要程度进行分级定密...内部团队间可通过多种渠道实现加密流转研讨，设置阅后即焚权限；对外传递合同草案等文件时，可打包为加密外发包，限定阅读次数和期限且禁止转发，一旦出现非授权操作可精准追溯，全方位保障法律文件的机密性。”
    *   **使用时机：** 接洽律所合伙人、企业法务部门负责人，客户表达诉讼材料泄密影响案件走向、合同草案外发难管控的顾虑时。
    *   **效果说明：** 针对法律文件核心机密属性，强调分级定密、阅后即焚、外发包权限管控，精准解决法律文件保密痛点。
    
    ---
    
    #### **功能痛点应对话术**
    
    **S007: 应对权限混乱**
    *   **业务场景：** 文件权限管控
    *   **专业话术：** “量子加密文件产品要求操作人员先完成身份认证，只有通过认证的人员才能开展文件加密、解密相关操作，从权限源头把控文件安全，避免因权限混乱导致的文件安全隐患。”
    *   **使用时机：** 客户提出内部权限混乱易引发数据泄露的问题时。
    *   **效果说明：** 解决对内部人员操作权限不可控的担忧，夯实对产品基础安全能力的认知。
    
    **S008: 应对加密强度质疑**
    *   **业务场景：** 文件加密防护
    *   **专业话术：** “量子加密文件产品采用 SM4 国密算法 + 量子真随机密钥，实现一文一密的量子级加密，加密密钥具备真随机特性，能有效抵御传统加密手段无法防范的算力破解，为您的核心商密文件筑牢安全防线。”
    *   **使用时机：** 客户质疑传统加密手段抵御算力破解能力不足时。
    *   **效果说明：** 输出国密算法与量子真随机密钥结合的技术优势，建立产品在加密技术层面的权威地位。
    
    **S009: 应对密级管理不规范**
    *   **业务场景：** 文件分级管控
    *   **专业话术：** “量子加密文件产品可基于商密目录制定策略规则，智能识别文件内容并标定密级，实现核心商密、普通商密等分级分类管理，还能明确商密权属、保密期限与知悉范围，让文件密级管控更规范高效。”
    *   **使用时机：** 客户提及商密文件分类不清晰、密级管控不规范的痛点时。
    *   **效果说明：** 帮助客户建立标准化商密管理体系，提升产品在海量文件管控场景的适配价值。
    
    **S010: 应对多格式文件防护繁琐**
    *   **业务场景：** 多类型文件统一管控
    *   **专业话术：** “量子加密文件产品支持办公类、设计类、图片类、多媒体类等全品类常用文件格式加密，无需区分文件类型即可一键防护，全面覆盖企业各类文件安全需求。”
    *   **使用时机：** 客户反馈企业文件格式繁杂、防护需区分类型且操作繁琐时。
    *   **效果说明：** 突出全品类文件一键防护的便捷性，解决多格式文件防护的效率痛点，体现通用性与易用性。
    
    **S011: 应对泄密溯源困难**
    *   **业务场景：** 违规操作追踪回溯
    *   **专业话术：** “量子加密文件产品支持全生命周期审计，可记录文件阅读、编辑、复制、外发等所有操作日志，一旦出现违规操作能及时预警，若发生泄密还可精准追溯操作源头，杜绝泄密隐患。”
    *   **使用时机：** 客户关注泄密后无法追溯源头的风险时。
    *   **效果说明：** 强调全生命周期审计与违规预警能力，解决泄密溯源难的核心诉求，强化事后追溯与风险管控价值。
    
    **S012: 应对流转渠道多样难管控**
    *   **业务场景：** 内外部文件安全流转管控
    *   **专业话术：** “量子加密文件产品支持直接使用OA、邮箱、微信等形式发送加密文件，也可通过文档库、密盘进行知识分享与存储，客户端内置‘密件收发’专用通道，可设置阅后即焚、再授权等权限；外发文件可打包为 EXE 格式，无需安装客户端即可查阅，还能限定阅读次数、期限及打印权限，实现内外部流转全可控。”
    *   **使用时机：** 客户提出文件流转渠道多样、权限难管控的问题时。
    *   **效果说明：** 解决客户内外部文件交互的保密难题，提升产品在协作场景的综合价值。
    
    ---
    
    ### **知识库整合完成**
    
    我已根据您提供的三张表，为您生成了完整的硬编码知识库，共包含三个核心部分：
    1.  **产品知识点（表1）：** 9个核心知识点（K001-K009），涵盖产品定义、功能、优势、场景与办理。
    2.  **对话范例库（表2）：** 8组标准对话范例（D001-D008），展示针对不同痛点的标准回应流程与话术。
    3.  **场景化话术库（表3）：** 12条场景化专业话术（S001-S012），包括6大行业场景和6大功能痛点应对策略。
    
    **调用说明：**
    *   您可以直接要求我基于此知识库回答关于“量子加密文件产品”的问题。
    *   您可以指定场景（如“客户是银行，担心数据被篡改”）或痛点（如“客户抱怨文件格式太多不好管”），我会调用对应的话术和知识点进行回应。
    *   您可以询问具体功能（如“文件外发怎么控制”），我会引用对应的知识点（K006）和话术（S012）进行解答。
    
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
