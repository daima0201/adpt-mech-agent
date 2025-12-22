
## 概述

本项目支持通过配置文件管理多种LLM提供商，包括 DeepSeek、OpenAI 和 MockLLM（用于测试）。

## 快速开始

### 1. 设置 API 密钥

#### 方法一：环境变量（推荐）

```bash
# Linux/MacOS
export DEEPSEEK_API_KEY="your_deepseek_api_key_here"

# Windows PowerShell
$env:DEEPSEEK_API_KEY="your_deepseek_api_key_here"
```

#### 方法二：创建 .env 文件

在项目根目录创建 `.env` 文件：

```bash
# 复制 .env.example 为 .env
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 配置 LLM

主配置文件位于 `configs/llm_config.yaml`：

```yaml
# configs/llm_config.yaml
llm:
  llm_type: "deepseek"
  model: "deepseek-chat"
  api_key: "${DEEPSEEK_API_KEY}"  # 从环境变量读取
  base_url: "https://api.deepseek.com/v1"
  temperature: 0.7
  max_tokens: 2048
  timeout: 30
```

### 3. 运行演示

```bash
# 测试 LLM 工厂功能
python ../examples/test_llm_factory.py

# 运行完整的配置集成演示
python ../examples/llm_config_demo.py
```

## 支持的 LLM 类型

### DeepSeek
- **类型**: `deepseek`
- **模型**: `deepseek-chat`, `deepseek-coder`
- **API 端点**: `https://api.deepseek.com/v1`
- **特点**: 性价比高，适合中文场景

### OpenAI
- **类型**: `openai`
- **模型**: `gpt-3.5-turbo`, `gpt-4`
- **API 端点**: `https://api.openai.com/v1`
- **特点**: 稳定性好，功能丰富

### MockLLM
- **类型**: `mock`
- **用途**: 测试和开发环境
- **特点**: 无需 API 密钥，返回预设响应

## 高级配置

### 多 LLM 配置

可以同时配置多个 LLM 实例：

```yaml
llms:
  default:
    llm_type: "deepseek"
    model: "deepseek-chat"
    api_key: "${DEEPSEEK_API_KEY}"
  
  openai_backup:
    llm_type: "openai"
    model: "gpt-3.5-turbo"
    api_key: "${OPENAI_API_KEY}"
  
  mock_test:
    llm_type: "mock"
    model: "mock-model"
```

### 智能体配置

```yaml
agents:
  - agent_type: "simple"
    name: "简单助手"
    description: "一个简单的对话助手"
    system_prompt: "你是一个乐于助人的AI助手。"

  - agent_type: "react"
    name: "推理助手"
    description: "一个善于推理的助手"
    system_prompt: "你是一个善于推理和解决问题的AI助手。"
```

## 代码使用示例

### 基本用法

```python
from src.services.llm_service import LLMService
from src.infrastructure.cache.cache_manager import get_cache_manager
from src.agents.repositories.models.llm_config import LLMConfig, LLMType

# 创建LLM服务
llm_service = LLMService(get_cache_manager())

# 方式一：使用默认配置ID
llm = await llm_service.get_or_create_llm(1)  # 假设默认配置ID为1

# 方式二：自定义配置
config = LLMConfig(
   llm_type=LLMType.DEEPSEEK,
   model="deepseek-chat",
   api_key="your_api_key"
)
llm = create_llm_from_config(config)

# 方式三：使用智能体管理器（自动加载配置）
from src.agents.base.manager import PreconfiguredAgentManager

manager = PreconfiguredAgentManager()
agent = manager.get_agent("simple_assistant")
```

### 多 LLM 管理

```python
from src.services.llm_service import LLMService
from src.infrastructure.cache.cache_manager import get_cache_manager

llm_service = LLMService(get_cache_manager())

# 注册多个 LLM
manager.create_llm_from_config(deepseek_config, "deepseek")
manager.create_llm_from_config(openai_config, "openai")

# 切换默认 LLM
manager.set_default_llm("openai")

# 获取特定 LLM
llm = manager.get_llm("deepseek")
```

## 故障排除

### 常见问题

1. **API 密钥错误**
   - 检查环境变量是否正确设置
   - 确认 API 密钥是否有效
   - 验证网络连接

2. **配置加载失败**
   - 检查 YAML 文件语法
   - 确认文件路径正确
   - 查看日志输出

3. **LLM 创建失败**
   - 检查 LLM 类型是否支持
   - 验证配置参数完整性
   - 尝试使用 MockLLM 测试

### 调试模式

启用详细日志：

```bash
export LOG_LEVEL=DEBUG
python your_script.py
```

## 扩展新的 LLM 提供商

要添加新的 LLM 提供商：

1. 在 `src/shared/config/schema.py` 中添加新的 `LLMType` 枚举值
2. 在 `src/agents/core/llm.py` 中实现对应的客户端类
3. 在 `LLMFactory` 中注册新的 LLM 类型
4. 更新配置文件支持

## 安全注意事项

- 🔒 **不要将 API 密钥提交到版本控制**
- 🔒 **使用环境变量或 .env 文件管理敏感信息**
- 🔒 **定期轮换 API 密钥**
- 🔒 **监控 API 使用量，避免意外费用**