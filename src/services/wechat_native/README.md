# 微信公众号本地化下载工具

基于微信公众平台后台 API 的本地化文章下载工具，无需依赖第三方服务。

## 特性

- ✅ **完全本地化**：直接调用微信公众平台 API，无第三方依赖
- ✅ **扫码登录**：一次登录，7 天有效
- ✅ **公众号搜索**：关键词搜索公众号
- ✅ **文章列表同步**：批量获取公众号所有文章
- ✅ **多格式下载**：支持 Markdown 和 HTML
- ✅ **断点续传**：基于 SQLite 状态管理
- ✅ **自动限速**：避免触发风控
- ✅ **数据库集成**：与 bo-distiller 无缝集成

## 与旧版对比

| 特性 | 旧版 wechat-exporter | 新版 wechat_native |
|------|---------------------|-------------------|
| 依赖外部服务 | ✅ 是 (down.mptext.top) | ❌ 否 |
| 限速 | 游客 1/分钟，会员 60/分钟 | 自适应（更高） |
| 认证 | 无需（API token 可选） | 扫码登录（一次性） |
| 稳定性 | 依赖第三方可用性 | 完全自主可控 |
| 功能 | 仅下载 | 搜索+列表+下载 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 登录认证

```bash
./venv/bin/python cli/wechat_native.py login
```

扫码后等待登录成功，Cookie 会保存到 `~/.bo-distiller/wechat_cookie.json`。

### 3. 同步公众号文章列表

```bash
# 搜索并同步指定公众号的所有文章
./venv/bin/python cli/wechat_native.py sync "阮一峰的网络日志"

# 限制同步数量
./venv/bin/python cli/wechat_native.py sync "公众号名称" --max 100
```

文章列表会写入 `data/distiller.db` 的 `articles` 表。

### 4. 下载文章全文

```bash
# 下载所有待处理的文章
./venv/bin/python cli/wechat_native.py download

# 限制下载数量
./venv/bin/python cli/wechat_native.py download --limit 10
```

下载的文章会保存到 `data/wechat_articles/YYYY-MM/标题_aid/`。

### 5. 查看状态

```bash
./venv/bin/python cli/wechat_native.py status
```

## 配置说明

配置文件位于 `src/services/wechat_native/config.yaml`：

```yaml
auth:
  cookie_file: ~/.bo-distiller/wechat_cookie.json
  token_expire_days: 7
  qr_display: terminal  # 或 image

download:
  rpm: 60  # 每分钟请求数
  formats:
    - markdown
    - html
  localize_images: true
  output_dir: ./data/wechat_articles
  min_content_len: 200

database:
  path: ./data/distiller.db
```

## 数据库结构

### articles 表

现有表，存储文章基本信息：

```sql
CREATE TABLE articles (
    id TEXT PRIMARY KEY,           -- 文章 ID（aid）
    title TEXT,                    -- 标题
    url TEXT,                      -- 原文 URL
    author TEXT,                   -- 作者
    published_date TEXT,           -- 发布时间
    content TEXT,                  -- 全文（Markdown）
    source TEXT,                   -- 来源（wechat）
    metadata TEXT,                 -- JSON 元数据
    created_at TEXT
);
```

### wechat_downloads 表

新增表，管理下载状态：

```sql
CREATE TABLE wechat_downloads (
    id TEXT PRIMARY KEY,
    article_id TEXT,
    status TEXT,                   -- pending / downloading / done / failed
    attempts INTEGER,              -- 重试次数
    last_error TEXT,
    files TEXT,                    -- JSON，保存的文件路径
    created_at TEXT,
    updated_at TEXT
);
```

### wechat_accounts 表

新增表，记录同步的公众号：

```sql
CREATE TABLE wechat_accounts (
    fakeid TEXT PRIMARY KEY,
    nickname TEXT,
    alias TEXT,
    signature TEXT,
    synced_at TEXT
);
```

## 使用场景

### 场景 1：首次使用

```bash
# 1. 登录
./venv/bin/python cli/wechat_native.py login

# 2. 同步公众号
./venv/bin/python cli/wechat_native.py sync "阮一峰的网络日志"

# 3. 下载全文
./venv/bin/python cli/wechat_native.py download
```

### 场景 2：定期更新

```bash
# 1. 检查认证状态
./venv/bin/python cli/wechat_native.py status

# 2. 增量同步（仅新文章）
./venv/bin/python cli/wechat_native.py sync "公众号名称"

# 3. 下载新文章
./venv/bin/python cli/wechat_native.py download
```

### 场景 3：批量下载多个公众号

```bash
# 逐个同步
./venv/bin/python cli/wechat_native.py sync "公众号A"
./venv/bin/python cli/wechat_native.py sync "公众号B"
./venv/bin/python cli/wechat_native.py sync "公众号C"

# 统一下载
./venv/bin/python cli/wechat_native.py download
```

## 常见问题

### Q: 认证失效怎么办？

A: 重新执行 `login` 命令即可：

```bash
./venv/bin/python cli/wechat_native.py login
```

### Q: 下载失败的文章如何重试？

A: 将失败的任务重置为 pending：

```sql
sqlite3 data/distiller.db "UPDATE wechat_downloads SET status='pending' WHERE status='failed';"
```

然后重新执行 `download` 命令。

### Q: 如何跳过已下载的文章？

A: 下载器会自动跳过 `done` 状态的文章，支持断点续传。

### Q: 二维码无法显示？

A: 修改配置文件中的 `qr_display` 为 `image`，二维码会保存为图片文件。

### Q: 与旧版 wechat-exporter 可以共存吗？

A: 可以。新版使用独立的配置和数据表，不影响旧版。

## 技术实现

### 核心模块

- **auth.py**：认证模块，扫码登录、Cookie 管理
- **api.py**：API 封装，公众号搜索、文章列表、下载
- **downloader.py**：下载器，任务调度、限速、数据库集成
- **cli/wechat_native.py**：命令行接口

### 参考来源

核心逻辑提取自 [wechat-article/wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter)，用 Python 重写以保持技术栈统一。

## 许可

MIT License

## 注意事项

- 请合理使用，避免频繁请求触发风控
- 文章内容版权归原作者所有
- 仅供个人学习和研究使用
