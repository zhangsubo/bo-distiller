# 配置迁移指南

## 概述

Bo-Distiller 配置管理已优化为：
- **环境变量（.env）**：仅保留影响项目启动的核心配置（数据库连接等）
- **数据库存储**：业务配置（LLM、飞书、Cubox 等）全部存储在数据库，通过 Web UI 管理

## 配置分类

### 1. 环境变量配置（.env）

**仅包含项目启动必需的配置**

```bash
# 数据库配置
DATABASE_TYPE=sqlite          # 或 mysql
SQLITE_DB_PATH=./data/distiller.db
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=distill

# 服务端口（可选）
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### 2. 数据库存储配置（通过 Web UI 管理）

**所有业务相关配置**

- LLM 提供商配置（API Key、模型参数）
- Cubox Token
- 飞书配置
- 数据源配置
- 主题配置
- 提示词模板
- 处理参数

## 迁移步骤

### 从旧版 .env 迁移

#### 1. 备份现有配置

```bash
cp .env .env.backup
```

#### 2. 创建新的 .env

```bash
cp .env.example .env
```

#### 3. 填写数据库配置

编辑 `.env`，只保留数据库相关配置：

```bash
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=./data/distiller.db
```

或使用 MySQL：

```bash
DATABASE_TYPE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=distill
```

#### 4. 启动应用

```bash
npm start
```

#### 5. 在 Web UI 中配置业务参数

访问 http://127.0.0.1:8000，在设置页面配置：

- **LLM 设置**：添加 API Key、选择默认提供商
- **数据源设置**：配置 Cubox、RSS 等
- **输出设置**：配置飞书空间 ID（如需要）

## 配置优先级

环境变量 > 数据库配置 > config.yaml 默认值

### 数据库配置读取逻辑

```python
# 1. 优先读取环境变量
DATABASE_TYPE = os.getenv("DATABASE_TYPE") or config.yaml.database.type

# 2. 如果是 MySQL，从环境变量覆盖
if DATABASE_TYPE == "mysql":
    MYSQL_HOST = os.getenv("MYSQL_HOST") or config.yaml.database.mysql.host
    MYSQL_PORT = os.getenv("MYSQL_PORT") or config.yaml.database.mysql.port
    # ...
```

## 配置存储位置

### 环境变量（.env）
```
项目根目录/.env
```

### 数据库配置
```
SQLite: ./data/distiller.db -> settings 表
MySQL: distill.settings 表
```

配置以 JSON 格式存储：

```sql
SELECT * FROM settings;
+------------------+------------------------------------------+
| key              | value                                    |
+------------------+------------------------------------------+
| system_config    | {"llm": {...}, "processing": {...}}     |
| sources          | {"sources": [{...}]}                     |
| prompts          | {"general": {...}, "investment": {...}} |
| topics           | {"predefined_topics": {...}}            |
+------------------+------------------------------------------+
```

## 旧配置文件说明

### config.yaml

**保留但简化**：
- 仅作为默认模板
- 首次启动时迁移到数据库
- 后续配置通过 Web UI 修改，存储在数据库

### 不再需要的文件

以下配置不再从文件读取：
- ~~sources.yaml~~ → 数据库 settings 表
- ~~prompts.yaml~~ → 数据库 settings 表
- ~~topics.yaml~~ → 数据库 settings 表

但文件保留作为配置示例。

## 环境变量配置示例

### 开发环境

```bash
# .env
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=./data/distiller.db
BACKEND_PORT=8000
```

### 生产环境

```bash
# .env.production
DATABASE_TYPE=mysql
MYSQL_HOST=192.168.1.100
MYSQL_PORT=3306
MYSQL_USER=distiller
MYSQL_PASSWORD=strong_password_here
MYSQL_DATABASE=distill
BACKEND_PORT=8000
```

### Docker 环境

```bash
# .env.docker
DATABASE_TYPE=mysql
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD}
MYSQL_DATABASE=distill
```

## 配置管理最佳实践

### 1. 敏感信息处理

✅ **推荐**：
- 数据库密码 → 环境变量
- LLM API Key → 数据库（Web UI 配置）
- 飞书 Token → 数据库（Web UI 配置）

❌ **不推荐**：
- 硬编码在 config.yaml
- 提交到 Git 仓库

### 2. 配置备份

```bash
# 备份数据库配置
python scripts/export_config.py > config_backup.json

# 恢复配置
python scripts/import_config.py config_backup.json
```

### 3. 多环境管理

```bash
# 开发环境
cp .env.example .env.dev
# 编辑 .env.dev

# 生产环境
cp .env.example .env.prod
# 编辑 .env.prod

# 启动时指定
ENV_FILE=.env.prod npm start
```

## FAQ

### Q: 为什么不把 LLM API Key 放在 .env？

**A**: 
1. LLM 配置经常需要调整（切换模型、修改参数）
2. 通过 Web UI 管理更直观，无需重启服务
3. 支持多个提供商，环境变量不够灵活
4. 数据库存储支持加密和权限管理

### Q: 数据库配置会暴露密码吗？

**A**: 
- LLM API Key 等敏感信息存储在数据库
- 数据库本身的密码在 .env 中
- 生产环境建议：
  - 使用专用数据库用户（非 root）
  - 设置强密码
  - .env 文件权限设为 600
  - 使用环境变量注入（Docker、K8s）

### Q: 如何在多台机器间同步配置？

**A**: 
1. 备份数据库
2. 在新机器上恢复数据库
3. 只需配置 .env 中的数据库连接

### Q: config.yaml 还有用吗？

**A**: 
- 首次启动时作为默认配置
- 后续配置以数据库为准
- 可以保留作为配置模板

### Q: 如何恢复默认配置？

**A**: 
```sql
-- 清空配置
DELETE FROM settings WHERE key = 'system_config';

-- 重启应用，会从 config.yaml 重新迁移
```

## 升级清单

- [x] 简化 .env.example（只保留启动配置）
- [x] 更新 config.py（环境变量优先）
- [x] 数据库存储 LLM 配置
- [x] 数据库存储源配置
- [x] Web UI 配置管理界面
- [x] 配置备份/恢复脚本
- [x] 迁移文档

## 总结

**核心原则**：
- 环境变量 = 基础设施配置（数据库、端口）
- 数据库 = 业务配置（API Key、模型、参数）
- Web UI = 配置管理界面

**优势**：
- ✅ 配置更直观（通过 UI 管理）
- ✅ 无需重启服务
- ✅ 支持动态更新
- ✅ 便于备份和迁移
- ✅ 减少环境变量文件大小
