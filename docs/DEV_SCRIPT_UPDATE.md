# dev.sh 端口配置优化

## 更新内容

### 修改的文件
1. **dev.sh** - 启动脚本
2. **web_ui.py** - 后端入口文件

### 功能改进

#### 1. 从 .env 读取配置
`dev.sh` 现在会自动加载 `.env` 文件中的配置：

```bash
# 加载 .env 配置
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | grep -v '^$' | xargs)
    echo -e "${GREEN}✓${NC} 已加载 .env 配置"
fi
```

#### 2. 端口可配置
支持通过环境变量配置前后端端口：

```bash
# .env 文件
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

#### 3. 默认值兼容
如果未配置，使用默认端口：
- 后端：8000
- 前端：5173

### 使用方法

#### 1. 配置端口（可选）

编辑 `.env` 文件：
```bash
# 自定义端口
BACKEND_PORT=9000
FRONTEND_PORT=3000
```

#### 2. 启动服务

```bash
./dev.sh start
```

输出示例：
```
✓ 已加载 .env 配置
================================
  Bo-Distiller 启动服务
================================

✓ 后端已启动 (PID: 12345)
  后端地址: http://127.0.0.1:9000
  API 文档: http://127.0.0.1:9000/docs

✓ 前端已启动 (PID: 12346)
  前端地址: http://localhost:3000

================================
✓ 启动完成！
================================

访问地址：
  前端: http://localhost:3000
  后端: http://127.0.0.1:9000
```

#### 3. 查看状态

```bash
./dev.sh status
```

输出示例：
```
================================
  Bo-Distiller 服务状态
================================

✓ 后端服务: 运行中 (PID: 12345)
  地址: http://127.0.0.1:9000
✓ 前端服务: 运行中 (PID: 12346)
  地址: http://localhost:3000
```

### 技术细节

#### web_ui.py 端口读取

```python
# 从环境变量读取端口配置
port = int(os.getenv("BACKEND_PORT", 8000))

# 启动服务
uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
```

#### dev.sh 环境变量

```bash
# 端口配置（从环境变量读取，带默认值）
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

# 启动后端时传递端口
BACKEND_PORT=$BACKEND_PORT python "$PROJECT_DIR/web_ui.py"

# 启动前端时传递端口
PORT=$FRONTEND_PORT npm run dev
```

### 优势

1. **灵活配置** - 通过 .env 文件统一管理端口
2. **开发友好** - 避免端口冲突，支持多实例
3. **向后兼容** - 未配置时使用默认端口
4. **一致性** - 所有输出信息都使用实际端口

### 配置示例

#### 开发环境
```bash
# .env
DATABASE_TYPE=sqlite
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

#### 多实例环境
```bash
# 实例 1 (.env)
BACKEND_PORT=8000
FRONTEND_PORT=5173

# 实例 2 (.env.instance2)
BACKEND_PORT=8001
FRONTEND_PORT=5174
```

启动实例 2：
```bash
# 加载不同的 .env 文件
cp .env.instance2 .env
./dev.sh start
```

### 与其他配置的关系

**.env 文件结构**：
```bash
# 数据库配置
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=./data/distiller.db

# MySQL 配置（如果使用）
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=distill

# 服务端口
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

所有配置都在一个文件中，便于管理。

### 兼容性

- ✅ 支持 macOS、Linux
- ✅ 兼容现有配置（未设置时使用默认值）
- ✅ 支持所有 dev.sh 命令（start/stop/restart/status）

### 验证

测试端口配置是否生效：

```bash
# 1. 设置自定义端口
echo "BACKEND_PORT=9000" >> .env
echo "FRONTEND_PORT=3000" >> .env

# 2. 启动服务
./dev.sh start

# 3. 检查端口
lsof -i :9000  # 应该看到 Python 进程
lsof -i :3000  # 应该看到 Node 进程

# 4. 访问服务
curl http://127.0.0.1:9000/api/status
open http://localhost:3000
```

### 总结

通过这次更新：
- ✅ 端口配置统一管理在 .env 文件
- ✅ dev.sh 自动读取并应用配置
- ✅ 所有显示信息使用实际端口
- ✅ 保持向后兼容性
