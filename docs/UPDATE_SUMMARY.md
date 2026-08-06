# 配置简化和 MySQL 支持更新说明

## ✅ 完成的更新

### 1. 环境变量配置简化

**更新文件**: `.env.example`

**变更内容**:
- ❌ 移除：所有 LLM API Key 配置项
- ❌ 移除：飞书配置
- ❌ 移除：业务相关配置
- ✅ 保留：数据库连接配置（启动必需）
- ✅ 保留：服务端口配置（可选）

**新的 .env.example**:
```bash
# 数据库配置（必需）
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=./data/distiller.db

# MySQL 配置（DATABASE_TYPE=mysql 时使用）
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=distill

# 服务端口（可选）
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### 2. 配置优先级实现

**更新文件**: `src/config.py`

**变更逻辑**:
```
环境变量 > 数据库配置 > config.yaml
```

**数据库配置读取**:
1. 从 `DATABASE_TYPE` 环境变量读取数据库类型
2. SQLite: 从 `SQLITE_DB_PATH` 读取路径
3. MySQL: 从 `MYSQL_*` 环境变量读取连接信息
4. 未设置时使用 config.yaml 默认值

### 3. 配置文件更新

**更新文件**: `config.yaml`

**变更内容**:
- 修正 `database.type` 为 `sqlite`（之前错误为 `host`）
- 添加配置优先级说明注释
- 明确标注哪些配置可通过环境变量覆盖

### 4. MySQL 支持

**新增功能**:
- ✅ 完整的 MySQL 存储实现
- ✅ 连接池管理
- ✅ UTF8MB4 字符集支持
- ✅ 数据迁移工具
- ✅ 建表脚本

**相关文件**:
- `src/storage_base.py` - 存储抽象接口
- `src/mysql_storage.py` - MySQL 实现
- `scripts/create_mysql_schema.sql` - 建表脚本
- `scripts/schema_only.sql` - 精简版建表脚本
- `scripts/migrate_sqlite_to_mysql.py` - 数据迁移工具

### 5. 文档

**新增文档**:
- `docs/CONFIG_MIGRATION.md` - 配置迁移指南
- `docs/MYSQL_SUPPORT.md` - MySQL 详细使用文档
- `docs/MYSQL_SETUP.md` - MySQL 快速开始指南

## 🎯 配置管理原则

### 核心理念

**环境变量（.env）**:
- 仅用于影响项目启动的配置
- 数据库连接信息
- 服务端口

**数据库存储**:
- 所有业务配置
- LLM API Key 和模型参数
- Cubox Token
- 飞书配置
- 数据源配置
- 提示词模板

**Web UI**:
- 配置管理界面
- 动态更新，无需重启
- 可视化编辑

## 📋 迁移步骤

### 从旧版迁移

1. **备份现有配置**
   ```bash
   cp .env .env.backup
   ```

2. **创建新的 .env**
   ```bash
   cp .env.example .env
   # 编辑 .env，只填写数据库配置
   ```

3. **启动应用**
   ```bash
   npm start
   ```

4. **在 Web UI 中配置业务参数**
   - 访问 http://127.0.0.1:8000
   - 在设置页面添加 LLM API Key
   - 配置数据源（Cubox 等）

### 切换到 MySQL

1. **安装依赖**
   ```bash
   pip install pymysql DBUtils
   ```

2. **初始化数据库**
   ```bash
   mysql -u root -proot < scripts/create_mysql_schema.sql
   ```

3. **配置环境变量**
   ```bash
   # 编辑 .env
   DATABASE_TYPE=mysql
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=root
   MYSQL_DATABASE=distill
   ```

4. **（可选）迁移数据**
   ```bash
   python scripts/migrate_sqlite_to_mysql.py
   ```

5. **启动应用**
   ```bash
   npm start
   ```

## 🔍 验证

### 检查配置加载

启动应用后查看日志：

```bash
# 应该看到类似输出
>> 迁移 config.yaml 到数据库
定时同步已启动：每 60 分钟
INFO:     Application startup complete.
```

### 检查数据库

**SQLite**:
```bash
sqlite3 data/distiller.db "SELECT key FROM settings;"
```

**MySQL**:
```bash
mysql -u root -proot -e "SELECT \`key\` FROM distill.settings;"
```

预期输出：
```
system_config
sources
prompts
topics
```

### 测试 MySQL 连接

```bash
python scripts/test_mysql.py
```

预期输出：
```
✓ MySQL 连接成功
✓ 找到 5 个表
✓ 数据插入成功
✓ 所有测试通过！
```

## 📚 相关文档

- [配置迁移指南](docs/CONFIG_MIGRATION.md) - 详细的配置管理说明
- [MySQL 支持文档](docs/MYSQL_SUPPORT.md) - MySQL 完整功能说明
- [MySQL 快速开始](docs/MYSQL_SETUP.md) - MySQL 设置步骤

## ⚙️ 技术细节

### 配置读取流程

```python
# 1. 从环境变量读取数据库类型
db_type = os.getenv("DATABASE_TYPE") or config.yaml.database.type

# 2. 根据类型读取对应配置
if db_type == "mysql":
    host = os.getenv("MYSQL_HOST") or config.yaml.database.mysql.host
    # ...

# 3. 初始化存储
storage = get_storage()  # 自动根据配置选择 SQLite 或 MySQL
```

### 数据库配置存储

配置存储在 `settings` 表：

| key | value | 说明 |
|-----|-------|------|
| system_config | JSON | 系统配置（LLM、处理参数等） |
| sources | JSON | 数据源配置 |
| prompts | JSON | 提示词模板 |
| topics | JSON | 主题配置 |

### 优先级示例

假设配置：
- `.env`: `DATABASE_TYPE=mysql`
- `config.yaml`: `database.type=sqlite`

最终使用：**MySQL**（环境变量优先）

## 🚨 注意事项

1. **环境变量优先级最高**
   - 确保 .env 文件配置正确
   - 生产环境建议使用环境变量而非 config.yaml

2. **首次启动会迁移配置**
   - config.yaml 内容会写入数据库
   - 后续修改请通过 Web UI

3. **敏感信息保护**
   - .env 文件不要提交到 Git
   - 已添加到 .gitignore
   - 生产环境使用强密码

4. **数据库类型切换**
   - 切换前建议备份数据
   - 使用迁移工具保持数据一致

## 📝 总结

### 改进点

✅ **简化 .env 文件** - 只保留启动必需配置
✅ **环境变量优先** - 支持灵活的部署方式
✅ **MySQL 支持** - 生产环境性能更好
✅ **配置数据库化** - 通过 Web UI 动态管理
✅ **迁移工具** - 平滑升级和数据迁移

### 文件变更

**新增**:
- src/storage_base.py
- src/mysql_storage.py
- scripts/create_mysql_schema.sql
- scripts/schema_only.sql
- scripts/migrate_sqlite_to_mysql.py
- scripts/test_mysql.py
- docs/CONFIG_MIGRATION.md
- docs/MYSQL_SUPPORT.md
- docs/MYSQL_SETUP.md

**修改**:
- .env.example（简化）
- config.yaml（添加注释）
- src/config.py（环境变量优先）
- src/storage.py（支持多数据库）
- src/models.py（数据库配置模型）
- requirements.txt（MySQL 依赖）

**无需修改**:
- 业务逻辑代码
- Web UI 代码
- API 接口

所有更新向后兼容，现有功能不受影响！
