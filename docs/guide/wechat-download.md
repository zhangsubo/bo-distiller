# 微信公众号本地化下载工具

完全本地化的微信公众号文章下载方案，**无需第三方 API**。

## 核心特性

- ✅ **本地化运行**：直接调用微信公众平台 API，无外部依赖
- ✅ **扫码登录**：一次认证，7 天有效
- ✅ **公众号搜索**：关键词快速定位目标公众号
- ✅ **批量下载**：支持 Markdown 和 HTML 双格式
- ✅ **断点续传**：基于 SQLite 的任务状态管理
- ✅ **智能限速**：遵守微信 API 频率限制

## 快速开始

### 步骤 1：扫码登录

```bash
python distill.py wechat login
```

执行后会显示二维码，使用微信扫码即可完成登录。登录状态保持 7 天。

**参数说明**：
- `--qr-display [text|image]`：二维码显示方式（默认 text）

### 步骤 2：搜索并同步公众号

```bash
# 搜索公众号
python distill.py wechat sync "公众号名称"

# 限制同步数量
python distill.py wechat sync "公众号名称" --max 100
```

**功能说明**：
- 自动搜索匹配的公众号
- 显示公众号信息供确认
- 同步文章列表到本地数据库

### 步骤 3：下载文章

```bash
# 下载所有待处理文章
python distill.py wechat download

# 限制下载数量（测试用）
python distill.py wechat download --limit 10
```

**输出格式**：
- Markdown：`data/wechat_articles/{fakeid}/{title}.md`
- HTML：`data/wechat_articles/{fakeid}/{title}.html`

### 步骤 4：查看状态

```bash
python distill.py wechat status
```

显示信息：
- 登录状态
- 已同步公众号数量
- 待下载/已下载文章统计

## 高级用法

### 批量同步多个公众号

```bash
# 方式 1：逐个同步
python distill.py wechat sync "公众号A"
python distill.py wechat sync "公众号B"
python distill.py wechat sync "公众号C"

# 方式 2：一次性下载所有
python distill.py wechat download
```

### 增量更新

```bash
# 同步最新文章
python distill.py wechat sync "公众号名称" --max 20

# 下载新增文章
python distill.py wechat download
```

### 重新下载失败的文章

```bash
# 查看失败记录
sqlite3 data/wechat_native.db "SELECT * FROM articles WHERE status='failed'"

# 清除失败状态，重新下载
sqlite3 data/wechat_native.db "UPDATE articles SET status='pending' WHERE status='failed'"
python distill.py wechat download
```

## 技术原理

### 认证机制

使用微信公众平台 Web 版登录：

1. 获取登录二维码
2. 扫码确认
3. 提取 `token` 和 Cookie
4. 存储到 SQLite 数据库（7 天有效期）

### API 调用

调用微信公众平台内部 API：

- **搜索公众号**：`/cgi-bin/searchbiz`
- **获取文章列表**：`/cgi-bin/appmsgpublish`
- **获取文章内容**：直接访问文章 URL

### 限速策略

- 搜索 API：每次调用间隔 2 秒
- 文章列表 API：每次调用间隔 1 秒
- 文章下载：每篇间隔 0.5 秒

### 数据存储

SQLite 数据库 `data/wechat_native.db`：

**表结构**：

```sql
-- 认证信息
CREATE TABLE auth (
    token TEXT PRIMARY KEY,
    cookies TEXT,
    expires_at TIMESTAMP
);

-- 公众号
CREATE TABLE accounts (
    fakeid TEXT PRIMARY KEY,
    nickname TEXT,
    alias TEXT,
    round_head_img TEXT,
    service_type INTEGER
);

-- 文章
CREATE TABLE articles (
    aid TEXT PRIMARY KEY,
    fakeid TEXT,
    title TEXT,
    url TEXT,
    publish_time TIMESTAMP,
    status TEXT,  -- pending/downloaded/failed
    local_path TEXT,
    created_at TIMESTAMP
);
```

## Web UI 集成

### 启动 Web 界面

```bash
python distill.py serve
# 访问 http://localhost:8000
```

### Web UI 功能

1. **认证管理**
   - 扫码登录
   - 查看登录状态
   - 显示剩余有效期

2. **公众号管理**
   - 搜索并添加公众号
   - 查看已同步公众号列表
   - 同步文章列表

3. **下载管理**
   - 批量下载任务
   - 实时进度显示
   - 下载历史记录

4. **内容预览**
   - Markdown 渲染
   - HTML 原文查看
   - 文章元信息展示

## 常见问题

### Q1: 登录二维码不显示

**原因**：终端不支持图片显示

**解决**：
```bash
python distill.py wechat login --qr-display text
```

### Q2: 登录状态过期

**现象**：提示 "token expired" 或 "请重新登录"

**解决**：
```bash
python distill.py wechat login
```

### Q3: 搜索不到公众号

**可能原因**：
1. 公众号名称拼写错误
2. 公众号未认证（无法通过 API 搜索）
3. 公众号已停用

**解决**：
- 使用精确的公众号名称
- 尝试使用公众号别名（英文 ID）

### Q4: 下载速度慢

**原因**：限速保护机制

**说明**：
- 这是正常现象，避免触发微信反爬虫
- 不建议修改限速参数，可能导致账号封禁

### Q5: 部分文章下载失败

**可能原因**：
1. 文章已删除
2. 文章设置了访问权限
3. 网络超时

**解决**：
```bash
# 查看失败原因
sqlite3 data/wechat_native.db "SELECT title, status FROM articles WHERE status='failed'"

# 重试
sqlite3 data/wechat_native.db "UPDATE articles SET status='pending' WHERE status='failed'"
python distill.py wechat download
```

## 最佳实践

### 1. 定期增量同步

```bash
# 每周运行一次
python distill.py wechat sync "公众号名称" --max 50
python distill.py wechat download
```

### 2. 批量管理公众号

创建脚本 `sync_all.sh`：

```bash
#!/bin/bash
accounts=("公众号A" "公众号B" "公众号C")

for account in "${accounts[@]}"; do
    python distill.py wechat sync "$account" --max 20
    sleep 5
done

python distill.py wechat download
```

### 3. 数据备份

```bash
# 备份数据库
cp data/wechat_native.db data/wechat_native.db.backup

# 备份文章
tar -czf wechat_articles_backup.tar.gz data/wechat_articles/
```

### 4. 清理旧数据

```bash
# 删除 6 个月前的文章
sqlite3 data/wechat_native.db "DELETE FROM articles WHERE publish_time < datetime('now', '-6 months')"

# 清理对应的文件
# (需要根据实际情况编写清理脚本)
```

## 配置文件

### config.yaml 配置示例

```yaml
wechat:
  download:
    formats: [markdown, html]  # 下载格式
    output_dir: data/wechat_articles  # 输出目录
  
  rate_limit:
    search_delay: 2.0     # 搜索延迟（秒）
    list_delay: 1.0       # 列表延迟（秒）
    download_delay: 0.5   # 下载延迟（秒）
  
  storage:
    db_path: data/wechat_native.db
```

## 技术限制

1. **认证有效期**：7 天，需定期重新登录
2. **搜索限制**：只能搜索已认证的公众号
3. **下载速度**：受限速保护影响，约 2 篇/秒
4. **并发限制**：不支持多账号并发下载
5. **历史文章**：部分公众号可能限制历史文章访问

## 后续计划

- [ ] 支持导出为 PDF
- [ ] 自动提取文章图片
- [ ] 支持文章全文搜索
- [ ] 集成到主蒸馏流程
- [ ] 支持公众号订阅管理

## 参考资料

- [微信公众平台 API 文档](https://developers.weixin.qq.com/doc/)
- [项目技术方案](./.claude/plans/wechat-integration.md)
- [实现总结](../archives/2024-07-25-wechat-summary.md)

---

**维护者**: Bo-Distiller Team  
**最后更新**: 2024-07-25
