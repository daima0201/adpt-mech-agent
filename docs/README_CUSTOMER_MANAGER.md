# 客户经理智能体演示

## 概述

本演示展示了如何使用Adaptive Mechanism Agent框架构建一个专业的量子加密文件产品客户经理智能体。该智能体具备以下特点：

- **角色定位**：毕业1-2年的专业客户经理，专注于量子加密产品销售
- **学习能力**：能够在一周内掌握量子加密技术的基本概念
- **销售目标**：一个月内实现100个license的销售目标
- **专业领域**：为金融、政府、医疗等敏感数据行业提供安全解决方案

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd adpt-mech-agent

# 安装依赖
pip install -r requirements.txt
```

### 2. LLM配置

创建配置文件 `configs/llm_config.yaml`：

```yaml
default_provider: deepseek
providers:
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    base_url: https://api.deepseek.com
    model: deepseek-chat
```

设置环境变量：

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

### 3. 运行演示

```bash
python examples/run_customer_manager_demo.py
```

## 核心功能演示

### 智能体管理

演示展示了如何：

1. **创建预配置的管理器**：自动加载默认智能体
2. **注册自定义智能体**：创建专门的客户经理角色
3. **智能体切换**：在不同智能体之间无缝切换
4. **会话管理**：维护独立的对话历史

### 客户经理专业能力测试

演示包含以下测试场景：

1. **自我介绍**：验证角色定位和专业知识
2. **技术优势介绍**：展示量子加密相比传统加密的优势
3. **具体场景应用**：针对金融机构的数据安全需求
4. **销售策略咨询**：提供达成销售目标的建议

## 代码结构说明

### 核心模块

```python
# 智能体配置
from src.shared.config.schemas.agent import AgentConfig

# 智能体实现
from src.agents.impls.agent.simple_agent import SimpleAgent

# 智能体服务
from src.services.agent_service import AgentService
from src.infrastructure.cache.cache_manager import get_cache_manager

# LLM服务
from src.services.llm_service import LLMService
```

### 客户经理配置示例

```python
customer_manager_prompt = """你是一名专注于量子加密文件产品销售的专业客户经理。你有以下特点：
- 毕业1-2年，有基础销售经验但需要快速学习新技术产品
- 能够在一周内掌握量子加密技术的基本概念和应用场景
- 一个月内可以实现100个license的销售目标
- 擅长为金融、政府、医疗等敏感数据行业提供安全解决方案

请基于以上角色定位，为客户提供专业的量子加密产品咨询服务。"""

config = AgentConfig(
    name="量子加密客户经理",
    description="专注于量子加密文件产品销售的专业客户经理",
    system_prompt=customer_manager_prompt
)
```

## 推荐的工具和平台

### AI开发平台               
- **OpenAI API**：提供强大的GPT模型支持
- **DeepSeek API**：国产优秀的大语言模型服务
- **百度文心一言**：中文理解能力优秀的AI平台

### 向量数据库
- **ChromaDB**：轻量级开源向量数据库
- **Qdrant**：高性能向量搜索引擎

### 知识库管理
- **LangChain**：AI应用开发框架
- **LlamaIndex**：数据连接和检索框架

## 扩展功能

### 知识库集成

可以集成知识库功能，让客户经理智能体能够：

1. **检索产品文档**：快速获取量子加密产品的技术规格
2. **学习销售案例**：分析成功的销售案例和经验
3. **了解竞争对手**：掌握市场竞品信息

### 多智能体协作

可以扩展为多智能体系统：

- **技术专家智能体**：负责解答深层次的技术问题
- **销售策略智能体**：提供销售技巧和市场策略
- **客户关系智能体**：管理客户信息和跟进记录

## 故障排除

### 常见问题

1. **ModuleNotFoundError: No module named 'src'**
   - 确保在项目根目录下运行脚本
   - 检查PYTHONPATH设置

2. **LLM API连接失败**
   - 验证API密钥是否正确设置
   - 检查网络连接和API端点

3. **异步事件循环错误**
   - 确保所有异步方法正确使用await
   - 避免在异步环境中嵌套asyncio.run()

### 调试技巧

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 下一步

1. **集成真实API**：配置真实的DeepSeek或其他LLM API
2. **添加知识库**：集成量子加密产品的技术文档
3. **优化提示工程**：根据实际业务需求调整角色提示
4. **部署到生产**：考虑性能优化和监控方案

## 联系我们

如有问题或建议，请通过项目Issue页面提交反馈。