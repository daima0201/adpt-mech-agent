# 星辰大模型API调用指南

## API基础信息

### 基本URL
```
https://api.ctyun.cn/stellar/v1
```

### 认证方式
- **API Key认证**：在请求头中携带 `Authorization: Bearer {your_api_key}`

## 核心接口

### 文本生成接口
**端点**: `/completions`
**方法**: POST

#### 请求示例
```java
HttpHeaders headers = new HttpHeaders();
headers.setContentType(MediaType.APPLICATION_JSON);
headers.set("Authorization", "Bearer " + apiKey);

Map<String, Object> requestBody = new HashMap<>();
requestBody.put("prompt", "你的提示文本");
requestBody.put("max_tokens", 1000);
requestBody.put("temperature", 0.7);

HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
ResponseEntity<Map> response = restTemplate.postForEntity(baseUrl + "/completions", request, Map.class);
```

#### 请求参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 输入的提示文本 |
| max_tokens | integer | 否 | 最大生成token数，默认1000 |
| temperature | float | 否 | 温度参数，控制随机性，默认0.7 |
| top_p | float | 否 | 核采样参数，默认0.9 |

### 对话接口
**端点**: `/chat/completions`
**方法**: POST

#### 请求示例
```java
List<Map<String, String>> messages = new ArrayList<>();
messages.add(Map.of("role", "user", "content", "你好"));

Map<String, Object> requestBody = new HashMap<>();
requestBody.put("messages", messages);
requestBody.put("max_tokens", 1000);

HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
ResponseEntity<Map> response = restTemplate.postForEntity(baseUrl + "/chat/completions", request, Map.class);
```

### 嵌入向量接口
**端点**: `/embeddings`
**方法**: POST

#### 请求示例
```java
Map<String, Object> requestBody = new HashMap<>();
requestBody.put("input", "需要嵌入的文本");
requestBody.put("model", "text-embedding-v1");

HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
ResponseEntity<Map> response = restTemplate.postForEntity(baseUrl + "/embeddings", request, Map.class);
```

## Spring Boot集成配置

### application.yml配置
```yaml
stellar:
  api:
    base-url: https://api.ctyun.cn/stellar/v1
    key: ${STELLAR_API_KEY:your-api-key}
    timeout: 30000
```

### 配置类
```java
@Configuration
@ConfigurationProperties(prefix = "stellar.api")
@Data
public class StellarConfig {
    private String baseUrl;
    private String key;
    private int timeout = 30000;
}
```

## 错误码说明

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 401 | 认证失败 | 检查API Key是否正确 |
| 403 | 权限不足 | 确认API Key有相应权限 |
| 429 | 请求频率限制 | 降低请求频率 |
| 500 | 服务器内部错误 | 稍后重试 |

## 最佳实践

1. **安全性**: 使用环境变量管理API Key
2. **性能**: 设置合理的超时时间和连接池
3. **监控**: 记录API调用日志和错误信息
4. **重试**: 实现请求重试机制

## 注意事项

- API调用需要有效的API Key
- 注意请求频率限制
- 建议在生产环境中使用HTTPS
- 及时更新API版本