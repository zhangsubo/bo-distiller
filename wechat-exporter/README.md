# wechat-exporter

微信文章批量下载器（独立自包含版本）。从 bo-distiller 的 `distiller.db` 导出微信文章清单，
在 24 小时运行的服务器上断点续跑下载全文（Markdown + HTML + 图片本地化）。

与 bo-distiller 的关系：本目录是 `src/services/wechat_downloader.py` 已验证逻辑的**独立副本**，
不 import 项目任何代码；下载产物目录结构一致，可拷回 bo-distiller 的 `data/wechat_articles/` 复用。

## 使用流程

### 1. 本地：导出 URL 清单

```bash
cd wechat-exporter
python3 export_urls.py            # 默认读 ../data/distiller.db，写 urls.jsonl
```

可选参数：`--db` 指定数据库路径，`-o` 指定输出文件，
`--skip-done <下载目录>` 跳过已下载的文章（增量导出用）。

### 2. 部署到服务器

```bash
scp -r wechat-exporter/ user@server:~/
ssh user@server
cd wechat-exporter
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. 启动下载

所有配置都在 `config.yaml` 里改（见下节），改完直接启动：

nohup 方式：

```bash
nohup python3 download.py > download.log 2>&1 &
```

systemd unit 示例（`/etc/systemd/system/wechat-exporter.service`）：

```ini
[Unit]
Description=WeChat Article Exporter
After=network.target

[Service]
WorkingDirectory=/home/user/wechat-exporter
ExecStart=/home/user/wechat-exporter/venv/bin/python download.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 配置文件

所有配置项都在 `config.yaml` 中维护（带中文注释），包括 API 地址、会员令牌、
限速（rpm）、下载格式、图片本地化开关、落盘目录、URL 清单和状态库路径。

- 优先级：**命令行参数 > config.yaml > 内置默认值**，CLI 参数仅用于临时覆盖
  （如 `--rpm 5` 临时提速）；
- 启动日志会逐项打印生效配置及来源（cli/config/default），api_token 脱敏显示；
- 也可用 `--config <路径>` 指定其他配置文件；
- 没有 config.yaml 时行为与旧版完全一致（纯 CLI/默认值）。

## 限速与耗时预估

- 游客（无 token）：限 1 次/分钟/IP。每篇文章 markdown + html 各一次请求，约 2 分钟/篇，
  2388 篇约 **80 小时**；若把 config.yaml 的 formats 改为 `[markdown]` 则约 40 小时。
- 会员：在 config.yaml 填入 `api_token` 并把 `rpm` 改为 60，约 1.3 小时跑完。

## 常用操作

查进度（不启动下载，同样读取 config.yaml 中的 state 路径）：

```bash
python3 download.py --status
```

失败重试（重置 failed 为 pending 后重新启动即可）：

```bash
sqlite3 jobs.db "UPDATE jobs SET status='pending' WHERE status='failed';"
python3 download.py
```

断点续传：重复启动不会重复下载，`done` 自动跳过；进程被中断（含 kill/重启）
后重跑会自动把 `downloading` 恢复为 `pending` 续跑。Ctrl+C / SIGTERM 会优雅退出。

## 产物结构

```
wechat_articles/
└── 2026-07/
    └── 文章标题_a1b2c3d4/
        ├── article.md
        ├── article.html
        └── images/          # 本地化的微信图片
```

## 回灌到 bo-distiller

服务器跑完后，把 `wechat_articles/` 目录拷回本地（如放回 bo-distiller 的 `data/wechat_articles/`），
执行回灌脚本把全文写入 `distiller.db`，主项目的蒸馏流程即可用上全文：

```bash
cd bo-distiller/wechat-exporter
# 先干跑确认统计
../venv/bin/python import_back.py --articles-dir ../data/wechat_articles --dry-run
# 正式回灌
../venv/bin/python import_back.py --articles-dir ../data/wechat_articles
```

行为说明：

- 按文章目录名尾部的 `_id前8位` 匹配 `articles` 表（带微信 URL 撞车保护）；
- 更新 `content` 为全文，`metadata` 合并 `wechat_files` / `wechat_downloaded_at`，
  并在 `wechat_downloads` 表置 `done`（与主项目内置下载器写库语义一致，不会重复下载）；
- 已是全文或无变化的文章自动跳过，重复执行幂等；
- `--min-content-len`（默认 200）以下的正文视为无效跳过；
- 每篇独立事务，单篇出错不影响其他文章。
