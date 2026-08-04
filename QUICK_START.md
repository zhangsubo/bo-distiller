# 快速开始

Bo-Distiller 智能内容蒸馏工具 - 快速上手指南

## 环境准备

### 系统要求

- Python 3.9+
- 虚拟环境（推荐）

### 安装步骤

```bash
# 1. 克隆项目
cd /Users/zhangsubo/Code/bo-distiller

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入必要的 API Key
```

## 核心功能

### 1. Cubox 内容分析与智能分类

分析你的 Cubox 收藏内容,自动发现主题聚类、检测重复文章、提取高频关键词。

**5 分钟上手**:

```bash
# 分析 Cubox 内容
python analyze_cubox_content.py

# 智能分类（自动去重）
python classify_upgrade.py --method keyword

# 查看分析报告
cat docs/reports/classification-report.md
```

**详细指南**: [Cubox 分类系统完整文档](docs/guide/cubox-classification.md)

### 2. 微信公众号本地化下载

完全本地化的微信公众号文章下载工具,无需第三方 API。

**5 分钟上手**:

```bash
# 1. 扫码登录（7天有效）
python distill.py wechat login

# 2. 同步公众号文章列表
python distill.py wechat sync "公众号名称" --limit 50

# 3. 下载文章（支持 Markdown 和 HTML）
python distill.py wechat download --limit 10

# 4. 查看微信工具状态
python distill.py wechat status
```

**详细指南**: [微信下载工具完整文档](docs/guide/wechat-download.md)

### 3. 内容蒸馏（核心功能）

将多源收藏内容提炼成体系化知识文档。

```bash
# 配置内容源
# 编辑 sources.yaml 添加你的内容源

# 运行蒸馏流程
python distill.py run              # 完整运行
python distill.py run --limit 10   # 测试模式

# 查看项目状态
python distill.py status
```

## 常见使用场景

### 场景 1: 清理 Cubox 收藏夹

```bash
# 1. 分析内容,找出重复和主题
python analyze_cubox_content.py

# 2. 查看分析报告
cat cubox_analysis_report.json

# 3. 基于关键词智能分类
python classify_upgrade.py --method keyword
```

### 场景 2: 批量下载公众号历史文章

```bash
# 1. 登录微信公众平台
python distill.py wechat login

# 2. 同步目标公众号
python distill.py wechat sync "科技博客" --max 100

# 3. 批量下载
python distill.py wechat download --limit 50

# 4. 查看下载状态
python distill.py wechat status
```

### 场景 3: 构建个人知识库

```bash
# 1. 配置多个内容源（sources.yaml）
# 2. 运行蒸馏
python distill.py run

# 3. 查看生成的知识文档
ls output/
```

## CLI 命令速查

### 主命令 (distill.py)

```bash
python distill.py run              # 运行蒸馏流程
python distill.py run --limit 10   # 测试模式
python distill.py run --model mimo # 指定 LLM
python distill.py status           # 查看项目状态
python distill.py serve            # 启动 Web UI
```

### 微信工具

```bash
python distill.py wechat login              # 扫码登录
python distill.py wechat sync "公众号"       # 同步文章列表
python distill.py wechat sync "公众号" --limit 50  # 限制同步数量
python distill.py wechat download           # 下载所有待处理文章
python distill.py wechat download --limit 10  # 限制下载数量
python distill.py wechat status             # 查看下载状态
```

### 内容源管理

```bash
python distill.py sources add --cubox    # 添加 Cubox 源
python distill.py sources list           # 列出所有内容源
```

## Web UI 使用

启动 Web 界面:

```bash
python distill.py serve
# 访问 http://localhost:8000
```

Web UI 功能:
- 可视化管理内容源
- 实时查看蒸馏进度
- 浏览生成的知识文档
- 微信文章下载管理

## 配置文件说明

### config.yaml - 系统配置

```yaml
llm:
  default_provider: deepseek
  providers:
    deepseek:
      api_key: ${DEEPSEEK_API_KEY}
      base_url: https://api.deepseek.com
```

### sources.yaml - 内容源配置

```yaml
sources:
  - name: cubox
    type: cubox
    enabled: true
```

### prompts.yaml - 提示词配置

自定义 LLM 提示词模板,控制知识提取和合成风格。

## 故障排查

### 问题 1: ModuleNotFoundError

```bash
# 确保虚拟环境已激活
source venv/bin/activate
pip install -r requirements.txt
```

### 问题 2: 微信登录失败

```bash
# 清除缓存重新登录
rm -rf data/wechat_native.db
python distill.py wechat login --qr-display text
```

### 问题 3: LLM API 调用失败

检查 `.env` 文件中的 API Key 是否正确配置。

## 下一步

- 📖 阅读 [设计文档](Reference_myself/00.%20README.md) 了解架构
- 🔧 查看 [详细使用指南](docs/guide/) 深入使用
- 📊 参考 [分析报告](docs/reports/) 了解项目能力
- 🕐 浏览 [历史归档](docs/archives/) 了解项目演进

## 获取帮助

- 查看命令帮助: `python distill.py --help`
- 查看子命令帮助: `python distill.py wechat --help`
- 查看项目文档: `docs/` 目录

---

**项目协议**: MIT License
