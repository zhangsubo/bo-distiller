# MySQL 支持文档

Bo-Distiller 现已支持 MySQL 数据库，可以替代默认的 SQLite 存储方案。

## 快速开始

### 1. 安装依赖

```bash
pip install pymysql DBUtils
```

或者重新安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 初始化 MySQL 数据库

#### 方法一：使用 SQL 脚本

```bash
# 创建数据库并初始化表结构
mysql -u root -p < scripts/create_mysql_schema.sql
```

#### 方法二：手动创建

```sql
-- 登录 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE distill CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 导入表结构
USE distill;
SOURCE /path/to/scripts/create_mysql_schema.sql;
```

### 3. 配置数据库连接

编辑 `config.yaml`：

```yaml
database:
  type: mysql  # 改为 mysql
  mysql:
    host: 127.0.0.1
    port: 3306
    user: root
    password: root
    database: distill
```

或者使用环境变量（推荐）：

在 `.env` 文件中配置：

```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=distill
```

然后在 `config.yaml` 中使用环境变量：

```yaml
database:
  type: mysql
  mysql:
    host: ${MYSQL_HOST:-127.0.0.1}
    port: ${MYSQL_PORT:-3306}
    user: ${MYSQL_USER:-root}
    password: ${MYSQL_PASSWORD}
    database: ${MYSQL_DATABASE:-distill}
```

### 4. 启动应用

```bash
# 启动 Web UI
npm start

# 或直接启动后端
python -m src.web_ui
```

应用会自动根据配置连接到 MySQL 数据库。

## 数据迁移

### 从 SQLite 迁移到 MySQL

如果你之前使用 SQLite，现在想迁移到 MySQL：

#### 1. 准备工作

- 确保 MySQL 数据库已创建并初始化表结构
- 备份 SQLite 数据库：`cp data/distiller.db data/distiller.db.backup`

#### 2. 配置环境变量

在 `.env` 文件中配置：

```bash
# MySQL 配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=distill

# SQLite 数据库路径
SQLITE_DB_PATH=./data/distiller.db
```

#### 3. 执行迁移

```bash
python scripts/migrate_sqlite_to_mysql.py
```

迁移脚本会：
- 读取 SQLite 中的所有数据
- 批量导入到 MySQL
- 验证数据完整性
- 显示迁移统计信息

#### 4. 切换到 MySQL

修改 `config.yaml`：

```yaml
database:
  type: mysql  # 从 sqlite 改为 mysql
```

然后重启应用。

## 数据库表结构

### articles - 文章表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(255) | 文章唯一标识（主键） |
| title | TEXT | 文章标题 |
| content | LONGTEXT | 文章正文内容 |
| url | TEXT | 原文链接 |
| source_type | VARCHAR(50) | 来源类型 |
| source_name | VARCHAR(255) | 来源名称 |
| source_identifier | VARCHAR(255) | 来源标识 |
| author | VARCHAR(255) | 作者 |
| published_date | DATETIME | 发布时间 |
| fetched_date | DATETIME | 抓取时间 |
| metadata | JSON | 元数据 |
| url_duplicate | TINYINT | URL 重复标记 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### sync_state - 同步状态表

| 字段 | 类型 | 说明 |
|------|------|------|
| source_type | VARCHAR(50) | 来源类型（主键） |
| source_name | VARCHAR(255) | 来源名称（主键） |
| last_sync | DATETIME | 最后同步时间 |
| total_articles | INT | 总文章数 |
| metadata | JSON | 元数据 |
| updated_at | DATETIME | 更新时间 |

### topics - 主题表

| 字段 | 类型 | 说明 |
|------|------|------|
| name | VARCHAR(255) | 主题名称（主键） |
| keywords | JSON | 关键词列表 |
| article_count | INT | 文章数量 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### knowledge_docs - 知识文档表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 文档 ID（主键，自增） |
| topic | VARCHAR(255) | 主题名称 |
| content | LONGTEXT | 文档内容 |
| article_count | INT | 来源文章数 |
| batch_count | INT | 批次数 |
| created_at | DATETIME | 创建时间 |
| metadata | JSON | 元数据 |

### settings - 设置表

| 字段 | 类型 | 说明 |
|------|------|------|
| key | VARCHAR(255) | 设置键（主键） |
| value | JSON | 设置值 |
| updated_at | DATETIME | 更新时间 |

## 性能优化建议

### 1. 索引优化

表结构已包含关键索引，如需添加更多索引：

```sql
-- 为文章标题添加全文索引（仅适用于 InnoDB）
ALTER TABLE articles ADD FULLTEXT INDEX idx_title_fulltext (title);

-- 为作者添加索引
CREATE INDEX idx_author ON articles(author);
```

### 2. 连接池配置

MySQL 存储使用了连接池，默认配置：

- 最大连接数：10
- 最小缓存连接：2
- 最大缓存连接：5

如需调整，修改 `src/mysql_storage.py` 中的 `PooledDB` 参数。

### 3. 字符集说明

数据库使用 `utf8mb4` 字符集，支持存储 Emoji 和特殊字符。

## 常见问题

### Q: MySQL 连接失败？

**A:** 检查以下项：
1. MySQL 服务是否启动：`mysql.server status` 或 `systemctl status mysql`
2. 用户名密码是否正确
3. 数据库是否已创建
4. 防火墙是否允许连接

### Q: 迁移后数据丢失？

**A:** 
1. 检查迁移日志，确认是否有错误
2. 使用 `SELECT COUNT(*) FROM articles` 验证数据
3. 如有问题，从备份恢复 SQLite 数据库

### Q: 如何切回 SQLite？

**A:** 修改 `config.yaml`：

```yaml
database:
  type: sqlite
  sqlite:
    path: ./data/distiller.db
```

然后重启应用。

### Q: 支持远程 MySQL 吗？

**A:** 支持。在配置中指定远程主机地址即可：

```yaml
database:
  type: mysql
  mysql:
    host: remote.mysql.server.com
    port: 3306
    user: your_user
    password: your_password
    database: distill
```

### Q: 如何备份 MySQL 数据？

**A:** 使用 mysqldump：

```bash
mysqldump -u root -p distill > backup_$(date +%Y%m%d).sql
```

恢复：

```bash
mysql -u root -p distill < backup_20260806.sql
```

## 技术架构

项目采用了存储抽象层设计：

```
StorageBase (抽象基类)
    ├── SQLiteStorage (SQLite 实现)
    └── MySQLStorage (MySQL 实现)
```

所有数据操作通过 `get_storage()` 获取存储实例，根据配置自动选择数据库类型，无需修改业务代码。

## 开发者信息

如需扩展其他数据库（如 PostgreSQL），只需：

1. 创建新的存储类继承 `StorageBase`
2. 实现所有抽象方法
3. 在 `get_storage()` 中添加判断逻辑

示例：

```python
from src.storage_base import StorageBase

class PostgreSQLStorage(StorageBase):
    def __init__(self, **kwargs):
        # 初始化 PostgreSQL 连接
        pass
    
    def save_article(self, article):
        # 实现保存逻辑
        pass
    
    # ... 实现其他方法
```
