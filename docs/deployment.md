# 部署指南

## 本地部署

### 1. 环境准备
```bash
# 安装Python 3.11+
python --version

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\\Scripts\\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置生产环境
```yaml
# configs/production.yaml
environment: production
log_level: INFO

llm:
  provider: "openai"
  model: "gpt-4"
  api_key: ${OPENAI_API_KEY}

knowledge:
  vector_store:
    type: "qdrant"
    host: "localhost"
    port: 6333
```

### 3. 启动服务
```bash
python main.py
```

## Docker部署

### 1. 构建镜像
```bash
docker build -t adpt-mech-agent:latest .
```

### 2. 运行容器
```bash
docker run -d \
  --name adpt-mech-agent \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_api_key \
  -e ENVIRONMENT=production \
  -v /host/path/data:/app/data \
  adpt-mech-agent:latest
```

### 3. 使用docker-compose
```bash
# 编辑docker-compose.yml，配置环境变量
docker-compose up -d
```

## Kubernetes部署

### 1. 创建ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: adpt-mech-agent-config
data:
  config.yaml: |
    environment: production
    log_level: INFO
```

### 2. 创建Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adpt-mech-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: adpt-mech-agent
  template:
    metadata:
      labels:
        app: adpt-mech-agent
    spec:
      containers:
      - name: adpt-mech-agent
        image: adpt-mech-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: openai-api-key
        volumeMounts:
        - name: config-volume
          mountPath: /app/configs
      volumes:
      - name: config-volume
        configMap:
          name: adpt-mech-agent-config
```

### 3. 创建Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: adpt-mech-agent-service
spec:
  selector:
    app: adpt-mech-agent
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: LoadBalancer
```

## 云平台部署

### AWS ECS部署
```bash
# 推送镜像到ECR
aws ecr create-repository --repository-name adpt-mech-agent
aws ecr get-login-password | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
docker tag adpt-mech-agent:latest YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/adpt-mech-agent:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/adpt-mech-agent:latest
```

### Azure Container Instances
```bash
az container create \
  --resource-group myResourceGroup \
  --name adpt-mech-agent \
  --image adpt-mech-agent:latest \
  --ports 8000 \
  --environment-variables OPENAI_API_KEY=your_key
```

## 监控和日志

### 日志配置
```python
# 使用内置日志系统
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Application started")
```

### 健康检查
```bash
# 健康检查端点
curl http://localhost:8000/health
```

## 备份和恢复

### 知识库备份
```bash
# 备份向量数据库
docker exec qdrant-db tar -czf /backup/qdrant_backup.tar.gz /qdrant/storage

# 备份配置文件
cp -r configs/ backup/configs/
cp -r data/ backup/data/
```

### 恢复
```bash
# 恢复向量数据库
docker exec qdrant-db tar -xzf /backup/qdrant_backup.tar.gz -C /

# 恢复配置和数据
cp -r backup/configs/ configs/
cp -r backup/data/ data/
```