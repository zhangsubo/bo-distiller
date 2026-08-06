# Bo-Distiller MySQL 集成完成

## ✅ 已完成的工作

### 1. 代码实现
- ✅ 创建存储抽象层 (`src/storage_base.py`)
- ✅ 实现 MySQL 存储类 (`src/mysql_storage.py`)
- ✅ 修改 SQLite 存储继承抽象基类
- ✅ 更新 `get_storage()` 支持多数据库
- ✅ 添加数据库配置模型到 `models.py`
- ✅ 更新配置管理器支持数据库配置

### 2. 数据库脚本
- ✅ MySQL 建表脚本 (`scripts/create_mysql_schema.sql`)
- ✅ 数据迁移脚本 (`scripts/migrate_sqlite_to_mysql.py`)
- ✅ 测试脚本 (`scripts/test_mysql.py`)

### 3. 文档
- ✅ MySQL 使用文档 (`docs/MYSQL_SUPPORT.md`)
- ✅ 本说明文档

### 4. 配置文件
- ✅ 更新 `config.yaml` 支持数据库配置
- ✅ 更新 `requirements.txt` 添加 MySQL 依赖

### 5. 测试验证
- ✅ MySQL 连接测试通过
- ✅ 表结构创建成功
- ✅ 数据插入和查询正常

## 📋 MySQL 建表脚本

完整的建表脚本已生成在：
```
scripts/create_mysql_schema.sql
```

### 使用方法

#### 方法一：直接执行脚本
```bash
mysql -u root -proot < scripts/create_mysql_schema.sql
```

#### 方法二：手动执行
```bash
# 1. 登录 MySQL
mysql -u root -proot

# 2. 创建数据库
CREATE DATABASE distill CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 3. 使用数据库
USE distill;

# 4. 执行建表语句
SOURCE /Users/zhangsubo/orca/workspaces/bo-distiller/pleco/scripts/create_mysql_schema.sql;
```

## 🔧 配置说明

### 当前配置（config.yaml）

```yaml
database:
  type: mysql  # 改为 mysql 启用
  # SQLite 配置
  sqlite:
    path: ./data/distiller.db
  # MySQL 配置
  mysql:
    host: ${MYSQL_HOST:-127.0.0.1}
    port: ${MYSQL_PORT:-3306}
    user: ${MYSQL_USER:-root}
    password: ${MYSQL_PASSWORD:-root}
    database: ${MYSQL_DATABASE:-distill}
```

### 环境变量（.env）

创建或编辑 `.env` 文件：

```bash
# MySQL 配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=distill
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install pymysql DBUtils
```

### 2. 初始化数据库
```bash
# 已经完成，数据库和表已创建
mysql -u root -proot -e "SHOW TABLES FROM distill;"
```

### 3. 切换到 MySQL

编辑 `config.yaml`，将 `database.type` 改为 `mysql`：

```yaml
database:
  type: mysql  # 从 sqlite 改为 mysql
```

### 4. 启动应用
```bash
npm start
# 或
python -m src.web_ui
```

应用会自动连接到 MySQL 数据库。

## 📊 数据库表结构

### 核心表

1. **articles** - 文章表
   - 主键：id (VARCHAR(255))
   - 索引：source_type, source_name, fetched_date, url
   - 支持 JSON 元数据

2. **sync_state** - 同步状态表
   - 主键：(source_type, source_name)
   - 记录各来源的同步状态

3. **topics** - 主题表
   - 主键：name
   - 存储主题和关键词

4. **knowledge_docs** - 知识文档表
   - 主键：id (自增)
   - 索引：topic
   - 存储蒸馏后的知识文档

5. **settings** - 设置表
   - 主键：key
   - 存储系统配置（JSON 格式）

## 🔄 数据迁移

如果你之前使用 SQLite，可以迁移数据到 MySQL：

```bash
# 配置环境变量
export MYSQL_HOST=127.0.0.1
export MYSQL_USER=root
export MYSQL_PASSWORD=root
export MYSQL_DATABASE=distill
export SQLITE_DB_PATH=./data/distiller.db

# 执行迁移
python scripts/migrate_sqlite_to_mysql.py
```

迁移脚本会：
- 读取 SQLite 中的所有数据
- 批量导入到 MySQL
- 显示迁移进度和统计
- 验证数据完整性

## ✨ 主要特性

### 1. 抽象存储层
```python
StorageBase (抽象基类)
    ├── SQLiteStorage (SQLite 实现)
    └── MySQLStorage (MySQL 实现)
```

### 2. 自动配置加载
```python
# 自动从 config.yaml 读取数据库类型
storage = get_storage()
```

### 3. 连接池管理
- MySQL 使用 DBUtils 连接池
- 最大连接数：10
- 最小缓存连接：2
- 最大缓存连接：5

### 4. 字符集支持
- 使用 utf8mb4 字符集
- 支持 Emoji 和特殊字符

### 5. JSON 字段
- metadata、keywords、value 等字段使用 JSON 类型
- 原生 JSON 查询和索引支持

## 🧪 测试

运行测试脚本验证 MySQL 功能：

```bash
python scripts/test_mysql.py
```

预期输出：
```
✓ MySQL 连接成功
✓ 找到 5 个表
✓ 数据插入成功
✓ 当前文章数: 1
✓ 所有测试通过！
```

## 📁 文件清单

### 新增文件
```
src/storage_base.py              # 存储抽象基类
src/mysql_storage.py             # MySQL 存储实现
scripts/create_mysql_schema.sql  # MySQL 建表脚本
scripts/migrate_sqlite_to_mysql.py  # 数据迁移脚本
scripts/test_mysql.py            # 测试脚本
docs/MYSQL_SUPPORT.md           # 详细文档
docs/MYSQL_SETUP.md             # 本文档
```

### 修改文件
```
src/storage.py                   # 更新 get_storage() 支持多数据库
src/models.py                    # 添加 DatabaseConfig 模型
src/config.py                    # 支持数据库配置解析
config.yaml                      # 添加 database 配置节
requirements.txt                 # 添加 pymysql 和 DBUtils
```

## 🔍 验证清单

- [x] MySQL 数据库已创建（distill）
- [x] 5 个表已创建（articles, sync_state, topics, knowledge_docs, settings）
- [x] 表结构正确（字段、类型、索引）
- [x] 连接测试通过
- [x] 插入和查询正常
- [x] 配置文件已更新
- [x] 依赖已安装（pymysql, DBUtils）

## 📚 下一步

1. **切换到 MySQL**
   ```bash
   # 编辑 config.yaml
   vi config.yaml
   # 将 database.type 改为 mysql
   ```

2. **（可选）迁移历史数据**
   ```bash
   python scripts/migrate_sqlite_to_mysql.py
   ```

3. **启动应用**
   ```bash
   npm start
   ```

4. **验证功能**
   - 访问 http://127.0.0.1:8000
   - 测试文章列表
   - 测试文章同步
   - 测试蒸馏功能

## 💡 提示

- 环境变量配置优先级高于 config.yaml
- 首次使用建议先在测试环境验证
- 生产环境建议配置 MySQL 主从复制
- 定期备份数据库：`mysqldump -u root -p distill > backup.sql`

## 📖 详细文档

完整的使用文档请查看：
```
docs/MYSQL_SUPPORT.md
```

## 🎉 完成！

MySQL 支持已完全集成，你现在可以：
- 使用 MySQL 替代 SQLite
- 在 SQLite 和 MySQL 之间切换
- 迁移历史数据到 MySQL
- 享受 MySQL 的性能和扩展性

有任何问题请查看文档或联系开发者。
