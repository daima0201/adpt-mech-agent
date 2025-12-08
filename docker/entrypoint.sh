#!/bin/bash

# 等待数据库就绪（如果使用外部数据库）
if [ "$WAIT_FOR_DB" = "true" ]; then
    echo "Waiting for database to be ready..."
    while ! nc -z $DB_HOST $DB_PORT; do
        sleep 1
    done
    echo "Database is ready!"
fi

# 初始化知识库（如果需要）
if [ "$INIT_KNOWLEDGE_BASE" = "true" ]; then
    echo "Initializing knowledge base..."
    python scripts/build_knowledge_base.py
fi

# 启动应用
exec python main.py