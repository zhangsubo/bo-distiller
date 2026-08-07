#!/bin/bash

# Bo-Distiller 开发服务管理脚本
# 用法: ./dev.sh [start|stop|restart|status]

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$PROJECT_DIR/logs"

# 加载 .env 配置（安全方式：逐行解析，正确处理引号和值中的 =）
if [ -f "$PROJECT_DIR/.env" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # 去除行首尾空白
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        # 提取 key（第一个 = 之前）
        key="${line%%=*}"
        # 提取 value（第一个 = 之后的全部内容）
        value="${line#*=}"
        # 去除 key 的空白
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        # 去除值两端的引号
        if [[ "$value" =~ ^\".*\"$ ]] || [[ "$value" =~ ^\'.*\'$ ]]; then
            value="${value:1:${#value}-2}"
        fi
        # 去除值首尾空白
        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"
        export "$key=$value"
    done < "$PROJECT_DIR/.env"
    echo -e "${GREEN}✓${NC} 已加载 .env 配置"
fi

# 端口配置（从环境变量读取，默认值）
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

# 显示使用说明
show_usage() {
    echo -e "${BLUE}用法:${NC}"
    echo -e "  ./dev.sh start    # 启动前后端服务"
    echo -e "  ./dev.sh stop     # 停止前后端服务"
    echo -e "  ./dev.sh restart  # 重启前后端服务"
    echo -e "  ./dev.sh status   # 查看服务状态"
    echo ""
}

# 启动服务
start_services() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Bo-Distiller 启动服务${NC}"
    echo -e "${BLUE}================================${NC}\n"

    # 检查服务是否已在运行，已运行则阻止重复启动
    ALREADY_RUNNING=false
    if [ -f "$LOGS_DIR/backend.pid" ] && ps -p $(cat "$LOGS_DIR/backend.pid") > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} 后端服务已在运行 (PID: $(cat "$LOGS_DIR/backend.pid"))"
        ALREADY_RUNNING=true
    fi
    if [ -f "$LOGS_DIR/frontend.pid" ] && ps -p $(cat "$LOGS_DIR/frontend.pid") > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} 前端服务已在运行 (PID: $(cat "$LOGS_DIR/frontend.pid"))"
        ALREADY_RUNNING=true
    fi
    if [ "$ALREADY_RUNNING" = true ]; then
        echo -e "\n${RED}服务已在运行，请先执行 ./dev.sh stop${NC}"
        exit 1
    fi

    # 检查并激活 Python 虚拟环境
    if [ -d "$PROJECT_DIR/venv" ]; then
        echo -e "${GREEN}✓${NC} 检测到虚拟环境，正在激活..."
        source "$PROJECT_DIR/venv/bin/activate"
    else
        echo -e "${YELLOW}⚠${NC} 未检测到虚拟环境 (venv)，使用系统 Python"
    fi

    # 同步 Python 依赖（pip 幂等，已装的包秒过）
    echo -e "${BLUE}→${NC} 同步 Python 依赖..."
    pip install -r requirements.txt -q 2>&1 | tail -1 || true

    # 检查前端依赖
    echo -e "${BLUE}→${NC} 检查前端依赖..."
    if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
        echo -e "${YELLOW}⚠${NC} 前端依赖未安装，正在安装..."
        cd "$PROJECT_DIR/frontend"
        npm install
        cd "$PROJECT_DIR"
    else
        echo -e "${GREEN}✓${NC} 前端依赖已就绪"
    fi

    # 创建日志目录
    mkdir -p "$LOGS_DIR"

    # 启动后端（--reload：改动 .py 文件后自动重启，仅开发用；生产请用 python web_ui.py）
    echo -e "\n${GREEN}启动后端服务...${NC}"
    BACKEND_PORT=$BACKEND_PORT python -m uvicorn src.web.app:create_app --factory --reload --host 127.0.0.1 --port $BACKEND_PORT > "$LOGS_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo -e "${GREEN}✓${NC} 后端已启动 (PID: $BACKEND_PID)"
    echo -e "  后端地址: ${BLUE}http://127.0.0.1:${BACKEND_PORT}${NC}"
    echo -e "  API 文档: ${BLUE}http://127.0.0.1:${BACKEND_PORT}/docs${NC}"
    echo -e "  日志文件: $LOGS_DIR/backend.log"

    # 等待后端启动
    echo -e "\n${BLUE}→${NC} 等待后端启动..."
    sleep 3

    # 检查后端是否启动成功
    if ! ps -p $BACKEND_PID > /dev/null; then
        echo -e "${RED}✗${NC} 后端启动失败，请查看日志: $LOGS_DIR/backend.log"
        exit 1
    fi

    # 启动前端
    echo -e "\n${GREEN}启动前端服务...${NC}"
    cd "$PROJECT_DIR/frontend"
    PORT=$FRONTEND_PORT npm run dev > "$LOGS_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✓${NC} 前端已启动 (PID: $FRONTEND_PID)"
    echo -e "  前端地址: ${BLUE}http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "  日志文件: $LOGS_DIR/frontend.log"

    # 保存 PID 到文件
    echo "$BACKEND_PID" > "$LOGS_DIR/backend.pid"
    echo "$FRONTEND_PID" > "$LOGS_DIR/frontend.pid"

    # 打印启动完成信息
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${GREEN}✓ 启动完成！${NC}"
    echo -e "${BLUE}================================${NC}"
    echo -e "\n访问地址："
    echo -e "  前端: ${BLUE}http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "  后端: ${BLUE}http://127.0.0.1:${BACKEND_PORT}${NC}"
    echo -e "\n查看日志："
    echo -e "  后端: tail -f $LOGS_DIR/backend.log"
    echo -e "  前端: tail -f $LOGS_DIR/frontend.log"
    echo -e "\n停止服务："
    echo -e "  运行: ${YELLOW}./dev.sh stop${NC}"
    echo ""
}

# 验证 PID 是否属于当前项目（检查命令行或工作目录）
_pid_is_mine() {
    local pid=$1
    local keyword=$2
    # 检查进程命令行是否包含项目关键字
    if ps -p "$pid" -o command= 2>/dev/null | grep -q "$keyword"; then
        return 0
    fi
    # 检查进程工作目录是否在项目内
    local cwd
    cwd=$(lsof -p "$pid" 2>/dev/null | awk '/cwd/ {print $NF}')
    if [ "$cwd" = "$PROJECT_DIR" ]; then
        return 0
    fi
    return 1
}

# 停止服务
stop_services() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Bo-Distiller 停止服务${NC}"
    echo -e "${BLUE}================================${NC}\n"

    if [ -f "$LOGS_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$LOGS_DIR/backend.pid")
        if ps -p $BACKEND_PID > /dev/null 2>&1 && _pid_is_mine "$BACKEND_PID" "web_ui.py"; then
            echo -e "${BLUE}→${NC} 停止后端服务 (PID: $BACKEND_PID)..."
            kill $BACKEND_PID
            echo -e "${GREEN}✓${NC} 后端服务已停止"
        elif ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠${NC} PID $BACKEND_PID 存在但不属于本项目，跳过"
        else
            echo -e "${YELLOW}⚠${NC} 后端服务未运行 (PID: $BACKEND_PID)"
        fi
        rm "$LOGS_DIR/backend.pid"
    else
        echo -e "${YELLOW}⚠${NC} 未找到后端 PID 文件"
    fi

    if [ -f "$LOGS_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$LOGS_DIR/frontend.pid")
        if ps -p $FRONTEND_PID > /dev/null 2>&1 && _pid_is_mine "$FRONTEND_PID" "vite"; then
            echo -e "${BLUE}→${NC} 停止前端服务 (PID: $FRONTEND_PID)..."
            kill $FRONTEND_PID
            echo -e "${GREEN}✓${NC} 前端服务已停止"
        elif ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠${NC} PID $FRONTEND_PID 存在但不属于本项目，跳过"
        else
            echo -e "${YELLOW}⚠${NC} 前端服务未运行 (PID: $FRONTEND_PID)"
        fi
        rm "$LOGS_DIR/frontend.pid"
    else
        echo -e "${YELLOW}⚠${NC} 未找到前端 PID 文件"
    fi

    echo -e "\n${GREEN}✓ PID 文件记录的服务已停止${NC}\n"
}

# 查看服务状态
show_status() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Bo-Distiller 服务状态${NC}"
    echo -e "${BLUE}================================${NC}\n"

    BACKEND_RUNNING=false
    FRONTEND_RUNNING=false

    # 检查后端状态
    if [ -f "$LOGS_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$LOGS_DIR/backend.pid")
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} 后端服务: ${GREEN}运行中${NC} (PID: $BACKEND_PID)"
            echo -e "  地址: http://127.0.0.1:${BACKEND_PORT}"
            BACKEND_RUNNING=true
        else
            echo -e "${RED}✗${NC} 后端服务: ${RED}已停止${NC}"
        fi
    else
        echo -e "${RED}✗${NC} 后端服务: ${RED}未启动${NC}"
    fi

    # 检查前端状态
    if [ -f "$LOGS_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$LOGS_DIR/frontend.pid")
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} 前端服务: ${GREEN}运行中${NC} (PID: $FRONTEND_PID)"
            echo -e "  地址: http://localhost:${FRONTEND_PORT}"
            FRONTEND_RUNNING=true
        else
            echo -e "${RED}✗${NC} 前端服务: ${RED}已停止${NC}"
        fi
    else
        echo -e "${RED}✗${NC} 前端服务: ${RED}未启动${NC}"
    fi

    echo ""

    # 显示日志文件
    if [ -f "$LOGS_DIR/backend.log" ] || [ -f "$LOGS_DIR/frontend.log" ]; then
        echo -e "查看日志："
        [ -f "$LOGS_DIR/backend.log" ] && echo -e "  后端: tail -f $LOGS_DIR/backend.log"
        [ -f "$LOGS_DIR/frontend.log" ] && echo -e "  前端: tail -f $LOGS_DIR/frontend.log"
        echo ""
    fi
}

# 重启服务
restart_services() {
    echo -e "${YELLOW}重启服务...${NC}\n"
    stop_services
    sleep 2
    start_services
}

# 主逻辑
case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    "")
        start_services
        ;;
    *)
        echo -e "${RED}错误: 未知命令 '$1'${NC}\n"
        show_usage
        exit 1
        ;;
esac
