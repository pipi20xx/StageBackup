# Stage 1: Build Frontend (Node.js)
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend
# 利用 Docker 缓存，仅当 package.json 变化时才重新 install
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Final Runtime Image (Python + Nginx)
FROM python:3.11-slim

# 安装运行时依赖: Nginx, 7zip (备份核心), 以及清理缓存
RUN apt-get update && apt-get install -y \
    nginx \
    p7zip-full \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 设置后端环境
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝后端代码
COPY backend/app ./app

# 拷贝前端构建产物到 Nginx 目录
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# 配置 Nginx
COPY nginx_unified.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# 初始化持久化目录
RUN mkdir -p /data

# 启动脚本
COPY start.sh /start.sh
RUN chmod +x /start.sh

# 环境变量默认值
ENV DATABASE_URL=sqlite:////data/backup_system.db
ENV TZ=Asia/Shanghai
ENV DEBUG=false

EXPOSE 80

CMD ["/start.sh"]