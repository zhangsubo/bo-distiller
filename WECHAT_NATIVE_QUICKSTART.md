# 微信公众号本地化下载工具 - 快速开始

## 5 分钟上手

### 1. 登录认证（一次性）

```bash
./venv/bin/python cli/wechat_native.py login
```

使用微信扫描终端显示的二维码，确认登录后，认证信息会保存 7 天。

### 2. 同步文章列表

```bash
# 搜索并同步公众号的所有文章到数据库
./venv/bin/python cli/wechat_native.py sync "阮一峰的网络日志"
```

输出示例：
```
正在搜索公众号: 阮一峰的网络日志
✓ 找到公众号: 阮一峰的网络日志 (fakeid: xxx)
获取文章列表: begin=0, count=10
  本页新增 10 篇文章
获取文章列表: begin=10, count=10
  本页新增 8 篇文章
✓ 同步完成，共 18 篇新文章
```

### 3. 下载全文

```bash
# 下载前 10 篇测试
./venv/bin/python cli/wechat_native.py download --limit 10

# 下载全部
./venv/bin/python cli/wechat_native.py download
```

输出示例：
```
开始下载 10 篇文章（限速 60 次/分钟）
[1/10] 科技爱好者周刊（第 289 期）：宽容从何而来...
  ✓ 成功
[2/10] 科技爱好者周刊（第 288 期）：技术写作的...
  ✓ 成功
...
✓ 下载完成
```

### 4. 查看下载结果

```bash
# 查看状态
./venv/bin/python cli/wechat_native.py status

# 查看下载的文件
ls data/wechat_articles/2026-07/
```

## 文件结构

```
data/wechat_articles/
└── 2026-07/
    ├── 科技爱好者周刊（第289期）_a1b2c3d4/
    │   ├── article.md      # Markdown 格式
    │   └── article.html    # HTML 格式
    └── 科技爱好者周刊（第288期）_e5f6g7h8/
        ├── article.md
        └── article.html
```

## 常用操作

### 定期更新

```bash
# 1. 增量同步新文章
./venv/bin/python cli/wechat_native.py sync "公众号名称"

# 2. 下载新文章
./venv/bin/python cli/wechat_native.py download
```

### 批量下载多个公众号

```bash
# 逐个同步
./venv/bin/python cli/wechat_native.py sync "公众号A"
./venv/bin/python cli/wechat_native.py sync "公众号B"
./venv/bin/python cli/wechat_native.py sync "公众号C"

# 统一下载
./venv/bin/python cli/wechat_native.py download
```

### 重试失败的下载

```bash
# 1. 重置失败状态
sqlite3 data/distiller.db "UPDATE wechat_downloads SET status='pending' WHERE status='failed';"

# 2. 重新下载
./venv/bin/python cli/wechat_native.py download
```

## 配置调整

编辑 `src/services/wechat_native/config.yaml`：

```yaml
download:
  rpm: 60  # 限速：每分钟请求数（可根据实际情况调整）
  formats:
    - markdown  # 删除 html 可只下载 Markdown
    - html
  output_dir: ./data/wechat_articles  # 修改保存路径
```

## 故障排除

### 问题 1：认证失效

**现象**：`✗ 认证已失效`

**解决**：重新登录
```bash
./venv/bin/python cli/wechat_native.py login
```

### 问题 2：二维码无法显示

**现象**：终端二维码乱码

**解决**：保存为图片
```bash
# 修改 config.yaml 中的 qr_display: image
# 或直接在命令中指定
./venv/bin/python cli/wechat_native.py login --qr-display image
```

### 问题 3：下载速度慢

**现象**：60 次/分钟仍然很慢

**解决**：
1. 检查网络连接
2. 调高 rpm（谨慎，避免触发风控）：
   ```yaml
   download:
     rpm: 120  # 提高到 120 次/分钟
   ```

### 问题 4：公众号搜索不到

**现象**：`未找到公众号: xxx`

**解决**：
1. 检查公众号名称是否正确（完整名称）
2. 尝试使用公众号简称或别名
3. 确认该公众号是否已注销

## 下一步

- 查看完整文档：`src/services/wechat_native/README.md`
- 了解技术细节：`.claude/plans/wechat-integration.md`
- 集成到蒸馏流程：使用 `data/distiller.db` 中的文章数据

## 与旧版对比

**旧版** (`wechat-exporter/`)：
- ✅ 无需登录
- ❌ 依赖第三方 API
- ❌ 限速低（1-60/分钟）
- ❌ 需要服务器 24/7 运行

**新版** (`wechat_native`)：
- ✅ 完全本地化
- ✅ 更高限速（60+/分钟）
- ✅ 功能完整（搜索+列表+下载）
- ⚠️ 需扫码登录（一次性）

推荐使用新版进行日常下载，旧版作为备选。
