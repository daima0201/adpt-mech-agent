# 政企客户经理智能体前端需求规格说明书

## 📋 项目概述

### 1.1 项目背景
为ADPT-MECH智能体系统开发一个专业的政企客户经理交互界面，支持多角色切换、工具调用和知识反馈功能。

### 1.2 目标用户
- 企业决策者（CEO、CTO、CIO）
- 业务部门负责人
- IT管理人员
- 项目协调人员

### 1.3 核心价值
- **专业形象**: 通过角色面具提供专业顾问体验
- **高效协作**: 多角色智能体协同工作
- **知识沉淀**: 自动从对话中提取有价值知识
- **工具集成**: 丰富的业务工具支持

## 🎯 功能需求

### 2.1 角色管理模块

#### 2.1.1 角色切换功能
**需求描述**: 用户可以在不同专业角色间切换，每个角色具有不同的专长和工具权限

**功能点**:
- [ ] 角色选择界面展示
- [ ] 角色状态指示（在线/忙碌/离线）
- [ ] 角色专长标签显示
- [ ] 一键切换角色
- [ ] 切换确认对话框
- [ ] 角色切换动画效果

**技术实现**:
```javascript
// 角色数据结构
const roles = {
  manager: {
    id: 'manager',
    name: '高级客户经理',
    avatar: '👤',
    expertise: ['战略规划', '客户关系', '商务谈判'],
    tools: ['strategy', 'communication', 'document'],
    status: 'online'
  },
  expert: {
    id: 'expert', 
    name: '产品专家',
    avatar: '🛠️',
    expertise: ['产品功能', '技术方案', '实施细节'],
    tools: ['analysis', 'demo', 'technical'],
    status: 'offline'
  }
};
```

### 2.2 对话交互模块

#### 2.2.1 消息展示
**需求描述**: 清晰展示用户与智能体的对话内容，包含丰富的元信息

**功能点**:
- [ ] 消息气泡设计
- [ ] 头像和角色标识
- [ ] 时间戳显示
- [ ] 思维链展开/收起
- [ ] 工具调用标记
- [ ] 消息状态指示（发送中/已发送/已读）

#### 2.2.2 输入控制
**需求描述**: 提供多种输入方式，支持富文本和文件上传

**功能点**:
- [ ] 文本输入框
- [ ] 语音输入支持
- [ ] 文件上传功能
- [ ] 表情符号选择
- [ ] 快捷回复模板
- [ ] 输入验证和过滤

### 2.3 工具调用模块

#### 2.3.1 工具面板
**需求描述**: 分类展示可用的业务工具，支持快速调用

**功能点**:
- [ ] 工具分类展示
- [ ] 工具搜索功能
- [ ] 权限控制显示
- [ ] 工具状态指示
- [ ] 最近使用工具
- [ ] 工具收藏功能

#### 2.3.2 工具执行
**需求描述**: 提供工具参数配置和执行结果展示

**功能点**:
- [ ] 工具参数表单
- [ ] 执行进度显示
- [ ] 结果可视化展示
- [ ] 错误处理界面
- [ ] 执行历史记录

### 2.4 知识反馈模块

#### 2.4.1 知识提取
**需求描述**: 自动从对话中识别和提取有价值的知识点

**功能点**:
- [ ] 实时知识检测
- [ ] 知识重要性评分
- [ ] 自动标签生成
- [ ] 知识摘要生成
- [ ] 相似知识推荐

#### 2.4.2 知识确认
**需求描述**: 用户确认和编辑提取的知识点

**功能点**:
- [ ] 知识预览界面
- [ ] 内容编辑功能
- [ ] 标签管理
- [ ] 重要性调整
- [ ] 确认保存流程

## 🎨 非功能需求

### 3.1 性能要求
- **页面加载时间**: 首屏加载 < 3秒
- **响应时间**: 用户操作响应 < 100ms
- **并发支持**: 支持1000+同时在线用户
- **数据缓存**: 合理使用本地存储缓存

### 3.2 可用性要求
- **易学性**: 新用户10分钟内掌握基本操作
- **效率性**: 常用操作3步内完成
- **容错性**: 提供清晰的错误提示和恢复路径
- **一致性**: 界面风格和交互逻辑统一

### 3.3 兼容性要求
- **浏览器支持**: Chrome 90+, Firefox 88+, Safari 14+
- **移动端适配**: iOS Safari, Android Chrome
- **屏幕尺寸**: 支持320px - 3840px宽度
- **网络环境**: 支持离线基础功能

## 🔧 技术架构

### 4.1 前端技术栈
```yaml
框架: Vue 3 + TypeScript
构建工具: Vite
UI组件库: Element Plus
样式方案: Tailwind CSS + SCSS
状态管理: Pinia
路由管理: Vue Router
HTTP客户端: Axios
实时通信: WebSocket
图标库: Font Awesome / Material Icons
```

### 4.2 项目结构
```
src/
├── components/          # 通用组件
│   ├── layout/         # 布局组件
│   ├── ui/            # UI基础组件
│   └── business/      # 业务组件
├── views/             # 页面组件
│   ├── chat/          # 对话页面
│   ├── tools/         # 工具页面
│   └── knowledge/     # 知识页面
├── stores/            # 状态管理
├── services/          # API服务
├── utils/             # 工具函数
├── types/             # TypeScript类型定义
└── assets/            # 静态资源
```

### 4.3 组件设计规范

#### 4.3.1 角色卡片组件 (RoleCard)
```vue
<template>
  <div class="role-card" :class="{ active: isActive }" @click="selectRole">
    <div class="avatar">{{ role.avatar }}</div>
    <div class="info">
      <div class="name">{{ role.name }}</div>
      <div class="status" :class="role.status">
        {{ statusText[role.status] }}
      </div>
      <div class="expertise">
        <span v-for="exp in role.expertise.slice(0, 2)" :key="exp">
          {{ exp }}
        </span>
      </div>
    </div>
    <button class="switch-btn" v-if="!isActive">切换</button>
  </div>
</template>
```

#### 4.3.2 消息气泡组件 (MessageBubble)
```vue
<template>
  <div class="message-bubble" :class="[type, { thinking: isThinking }]">
    <div class="header">
      <span class="avatar">{{ avatar }}</span>
      <span class="sender">{{ sender }}</span>
      <span class="timestamp">{{ time }}</span>
    </div>
    <div class="content">
      <div v-if="thinkingChain" class="thinking-chain">
        <button @click="toggleThinking">💭 思维链 {{ isExpanded ? '收起' : '展开' }}</button>
        <div v-if="isExpanded" class="chain-content">
          {{ thinkingChain }}
        </div>
      </div>
      <div class="text">{{ content }}</div>
      <div v-if="toolsUsed" class="tools-used">
        🔧 使用了: {{ toolsUsed.join(', ') }}
      </div>
    </div>
  </div>
</template>
```

## 📊 数据流设计

### 5.1 状态管理架构
```typescript
interface AppState {
  // 用户相关
  user: UserInfo;
  
  // 角色管理
  currentRole: Role;
  availableRoles: Role[];
  
  // 对话管理
  conversations: Conversation[];
  currentConversation: Conversation;
  
  // 工具管理
  tools: Tool[];
  activeTool: Tool | null;
  
  // 知识管理
  extractedKnowledge: Knowledge[];
  knowledgeBase: Knowledge[];
}
```

### 5.2 API接口设计

#### 5.2.1 对话相关接口
```typescript
// 发送消息
POST /api/chat/send-message
{
  roleId: string;
  message: string;
  attachments?: File[];
}

// 接收消息流
GET /api/chat/message-stream
WebSocket连接，实时推送消息

// 获取对话历史
GET /api/chat/conversations/:id/history
```

#### 5.2.2 工具相关接口
```typescript
// 获取可用工具
GET /api/tools/available

// 执行工具
POST /api/tools/execute
{
  toolId: string;
  parameters: Record<string, any>;
}

// 获取工具执行结果
GET /api/tools/results/:executionId
```

#### 5.2.3 知识相关接口
```typescript
// 提取知识
POST /api/knowledge/extract
{
  conversationId: string;
  text: string;
}

// 确认知识
POST /api/knowledge/confirm
{
  knowledgeId: string;
  confirmed: boolean;
  edits?: Partial<Knowledge>;
}

// 查询知识库
GET /api/knowledge/search?query=关键词
```

## 🎯 交互设计规范

### 6.1 动效设计原则
- **入场动画**: 淡入 + 轻微缩放
- **切换动画**: 滑动过渡
- **反馈动画**: 按钮按压效果
- **加载动画**: 脉冲呼吸效果

### 6.2 微交互设计
- **悬停效果**: 轻微阴影提升
- **点击反馈**: 缩小动画
- **滚动指示**: 渐隐渐现
- **状态变化**: 平滑过渡

## 📱 响应式设计

### 7.1 断点策略
```scss
// 移动端优先
$breakpoint-sm: 640px;   // 小屏幕手机
$breakpoint-md: 768px;   // 平板竖屏
$breakpoint-lg: 1024px;  // 平板横屏/小桌面
$breakpoint-xl: 1280px;  // 标准桌面
$breakpoint-2xl: 1536px; // 大桌面
```

### 7.2 布局适配
| 设备类型 | 布局模式 | 主要特性 |
|---------|---------|---------|
| 手机 (<768px) | 单列垂直 | 底部输入栏，角色条水平滚动 |
| 平板 (768-1024px) | 两栏布局 | 固定侧边栏，自适应主区域 |
| 桌面 (>1024px) | 三栏布局 | 完整功能展示，工具面板常驻 |

## 🔒 安全考虑

### 8.1 数据安全
- 敏感信息加密传输
- 用户权限验证
- XSS攻击防护
- CSRF令牌保护

### 8.2 隐私保护
- 对话数据本地存储加密
- 知识提取用户确认机制
- 数据清理和匿名化

## 📈 性能优化策略

### 9.1 前端优化
- 代码分割和懒加载
- 图片和资源压缩
- 缓存策略优化
- 虚拟滚动长列表

### 9.2 网络优化
- HTTP/2多路复用
- 请求合并和批处理
- 离线缓存策略
- 预加载关键资源

## 🚀 部署和运维

### 10.1 构建配置
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          ui: ['element-plus'],
          utils: ['axios', 'dayjs']
        }
      }
    }
  }
});
```

### 10.2 监控指标
- 页面加载性能
- 用户交互响应时间
- 错误率和异常监控
- 用户行为分析

---

## 📋 验收标准

### 功能验收清单
- [ ] 角色切换功能完整可用
- [ ] 对话交互流畅自然
- [ ] 工具调用准确可靠
- [ ] 知识反馈机制有效
- [ ] 响应式适配完善

### 性能验收清单
- [ ] 页面加载时间达标
- [ ] 操作响应及时
- [ ] 内存使用合理
- [ ] 网络请求优化

### 用户体验验收清单
- [ ] 界面美观易用
- [ ] 交互逻辑清晰
- [ ] 错误处理友好
- [ ] 帮助文档完整

**文档版本**: v1.0  
**最后更新**: 2024-12-07  
**编写者**: ADPT-MECH Development Team