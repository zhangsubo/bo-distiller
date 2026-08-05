# Bo-Distiller Docker 镜像
# 多阶段构建：前端构建 + Python 后端

# ============ 阶段 1: 构建前端 ============
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# 先复制依赖文件，利用 Docker 缓存
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# 复制源码并构建
COPY frontend/ .
RUN npm run build

# ============ 阶段 2: Python 运行时 ============
FROM python:3.11-slim

# 安装系统依赖（包括 Node.js）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 安装 Cubox CLI
RUN npm install -g cubox-cli

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目源码
COPY distill.py web_ui.py config.example.yaml sources.example.yaml prompts.example.yaml topics.yaml ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 复制配置文件（如果存在）
COPY config.example.yaml config.yaml
COPY sources.example.yaml sources.yaml
COPY prompts.example.yaml prompts.yaml

# 创建数据目录
RUN mkdir -p data output .cache

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令（绑定到 0.0.0.0 以允许外部访问）
CMD ["python", "-c", "import uvicorn; from src.web.app import create_app; uvicorn.run(create_app(), host='0.0.0.0', port=8000)"]
