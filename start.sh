#!/bin/bash

# 确保 Nginx 以非守护进程模式运行以便 Popen 能捕获或脚本继续
# 或者以后台模式运行，但让 Python 作为主进程
nginx

# 检查数据库路径是否存在，如果不存在则创建（可选，SQLAlchemy 会自动处理，但这样更显式）
mkdir -p /data

echo "===================================================="
echo "   StageBackup Unified Server is Starting..."
echo "   Frontend: http://localhost:80"
echo "   Backend:  http://localhost:80/api/"
echo "===================================================="

# 启动后端 (Uvicorn)
# 我们将 Python 进程设为 exec，这样它会接收 Docker 的系统信号 (SIGTERM)，实现优雅关闭
LOG_LEVEL="warning"
ACCESS_LOG_FLAG="--no-access-log"

if [ "$DEBUG" = "true" ]; then
    LOG_LEVEL="info"
    ACCESS_LOG_FLAG=""
fi

exec uvicorn app.main:app --host 127.0.0.1 --port 6996 --log-level $LOG_LEVEL $ACCESS_LOG_FLAG