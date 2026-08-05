# Bo-Distiller

智能内容蒸馏工具 - 将收藏的文章提炼成体系化知识文档

## 核心功能

- **Cubox 内容分析与智能分类** - 自动主题聚类、重复检测、关键词提取
- **知识蒸馏合成** - 两阶段 LLM 提炼，将多源内容整合成结构化知识文档
- **多 LLM 提供商支持** - 支持 DeepSeek、Xiaomi、MiniMax、Moonshot、Kimi 等 7+ 提供商
- **Web UI 管理界面** - 可视化配置、内容管理、蒸馏任务监控

## 快速开始

### 方式 1: 使用开发脚本（推荐）

```bash
# 1. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..

# 2. 配置环境
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 启动服务
./dev.sh start

# 访问 Web UI: http://localhost:5173
# API 文档: http://127.0.0.1:8000/docs
```

### 方式 2: 命令行模式

```bash
# 1. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 快速体验
python distill.py run --limit 10           # 知识蒸馏（测试模式）
python scripts/analyze_cubox_content.py    # Cubox 内容分析
```

📖 **详细指南**：查看 `docs/QUICK_START.md`

## 项目状态

✅ **v0.3.1** - LLM 元数据管理与增强配置  
✅ **v0.3.0** - 代码重构与模块化  
✅ **v0.2.0** - Web UI 集成与 Docker 支持  
✅ **v0.1.0** - Cubox 智能分析与分类系统  

## 主要特性

### 🎯 智能 LLM 配置
- **自动元数据获取** - 集成 models.dev API，自动填充提供商配置
- **连通性测试** - 保存前测试 API 配置，确保可用性
- **动态模型选择** - 支持启用/禁用特定模型
- **自定义提供商** - 支持添加任意兼容 OpenAI API 的提供商

### 📊 内容分析
- **主题聚类** - 基于 sentence-transformers 的语义聚类
- **重复检测** - 智能识别重复或相似内容
- **关键词提取** - 自动提取主题关键词
- **分类管理** - 支持关键词和 ML 两种分类方式

### 🔄 知识蒸馏
- **两阶段处理** - 批次提取 → 知识合成
- **上下文管理** - 自动计算 token 并处理上下文窗口限制
- **缓存优化** - LLM 响应缓存，避免重复调用
- **增量更新** - 支持增量蒸馏，只处理新内容

### 🌐 Web UI
- **可视化配置** - 友好的 LLM 提供商配置界面
- **内容管理** - 浏览、搜索、分类管理文章
- **任务监控** - 实时查看蒸馏任务状态
- **元数据管理** - 查看和刷新提供商元数据缓存

## 支持的 LLM 提供商

| 提供商 | Base URL | 特性 |
|--------|----------|------|
| DeepSeek | `https://api.deepseek.com` | 高性价比，长上下文 |
| Xiaomi | `https://api.xiaomy.net` | 国内访问稳定 |
| MiniMax | `https://api.minimaxi.com/v1` | 多模态支持 |
| Moonshot | `https://api.moonshot.cn/v1` | 200K 上下文 |
| Kimi | `https://api.kimi.moonshot.cn/v1` | Moonshot 别名 |
| OpenCode | `https://api.opencode.dev/v1` | 开发优化 |
| Kimi For Coding | `https://api.kimi.com/coding/v1` | 代码辅助专用 |
| 自定义 | 自定义 | 任意兼容 OpenAI API 的提供商 |

> 所有提供商配置信息自动从 [models.dev](https://models.dev) 获取并缓存 30 天

查看完整变更：[CHANGELOG.md](CHANGELOG.md)

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI (React)                        │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ 配置管理     │ 内容管理     │ 蒸馏任务                 │ │
│  │ - LLM 配置   │ - 文章列表   │ - 任务启动               │ │
│  │ - 元数据管理 │ - 主题分类   │ - 进度监控               │ │
│  │ - 连通性测试 │ - 搜索过滤   │ - 结果查看               │ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓ REST API
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ 路由层       │ 服务层       │ 数据层                   │ │
│  │ - /config    │ - Sync       │ - SQLite (WAL)           │ │
│  │ - /articles  │ - Scheduler  │ - 元数据缓存             │ │
│  │ - /distill   │              │ - LLM 响应缓存           │ │
│  │ - /llm       │              │                          │ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Core Modules                            │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ 适配器       │ 处理器       │ 合成器                   │ │
│  │ - Cubox      │ - Classifier │ - LLM Client             │ │
│  │ - Local MD   │ - Cleaner    │ - Synthesizer            │ │
│  │ - Aggregator │ - Smart ML   │ - Context Manager        │ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

**后端**:
- FastAPI - 高性能异步 Web 框架
- SQLite - 轻量级数据库（WAL 模式）
- Pydantic - 数据验证和配置管理
- OpenAI SDK - LLM 调用
- scikit-learn + sentence-transformers - ML 分类

**前端**:
- React 18 + TypeScript
- Vite - 构建工具
- Ant Design - UI 组件库
- React Query - 服务端状态管理

## 项目结构

```
bo-distiller/
├── distill.py                 # CLI 入口
├── web_ui.py                  # Web UI 启动入口
├── config.yaml                # 系统配置
├── sources.yaml               # 内容源配置
├── topics.yaml                # 主题配置
├── prompts.yaml               # 提示词配置
├── src/
│   ├── orchestrator.py        # 蒸馏业务编排
│   ├── models.py              # 数据模型（Article, SystemConfig 等）
│   ├── config.py              # 配置加载与验证
│   ├── storage.py             # SQLite 持久化存储
│   ├── cache.py               # 缓存管理（JSON 文件）
│   ├── llm_client.py          # LLM 客户端（多提供商）
│   ├── synthesizer.py         # 知识合成（两阶段）
│   ├── utils.py               # 共享工具函数
│   ├── adapters/              # 内容源适配器
│   │   ├── base.py            # 适配器基类
│   │   ├── aggregator.py      # 内容聚合器
│   │   ├── cubox_adapter.py   # Cubox CLI 适配器
│   │   └── local_markdown.py  # 本地 Markdown 适配器
│   ├── processors/            # 内容处理
│   │   ├── cleaner.py         # 内容清洗
│   │   └── classifier.py      # 主题分类
│   ├── services/              # 后台服务
│   │   ├── scheduler_service.py
│   │   └── sync_service.py
│   └── web/                   # Web API
│       ├── app.py             # FastAPI 应用
│       ├── deps.py            # 共享依赖
│       └── routers/           # API 路由
├── frontend/                  # React 前端
├── scripts/                   # 独立分析脚本
│   ├── analyze_cubox_content.py
│   ├── classify_upgrade.py
│   └── analyze_deps.py
└── tests/                     # 测试
```

## 文档导航

### 使用指南
- [Cubox 内容分析与分类](docs/guide/cubox-classification.md)

### 设计文档
完整的架构和设计文档位于 `Reference_myself/` 目录：
- [00. 项目概述](Reference_myself/00.%20README.md)
- [01. 架构设计](Reference_myself/01.%20架构设计.md)
- [02. 核心机制设计](Reference_myself/02-core-mechanisms.md)
- [03. 多源内容聚合](Reference_myself/03-multi-source-aggregation.md)

### 分析报告
- [Cubox 分类报告](docs/reports/classification-report.md)

## 核心特性

- ✅ **体系化提炼**：两阶段合成（批次提取 + 知识整合）
- ✅ **断点续传**：多层缓存，任意断点恢复
- ✅ **智能分批**：Token 预算动态分配
- ✅ **高度可配置**：YAML 驱动，提示词可定制
- ✅ **多 LLM 支持**：DeepSeek / Mimo / MiniMax / Kimi
- 🔜 **多源聚合**：RSS/书签/链接/本地文件
- 🔜 **知识图谱**：关联可视化

## 技术栈

- **语言**：Python 3.9+
- **AI**：DeepSeek / Mimo / Claude / Qwen
- **数据处理**：feedparser, trafilatura, beautifulsoup4
- **ML**：scikit-learn, sentence-transformers
- **Web**：FastAPI, React
- **CLI**：click, rich

## CLI 命令速查

```bash
# 主命令
python distill.py run              # 运行蒸馏流程
python distill.py status           # 查看项目状态
python distill.py serve            # 启动 Web UI

# 内容源管理
python distill.py sources add --cubox
python distill.py sources list

# 分析脚本
python scripts/analyze_cubox_content.py
python scripts/classify_upgrade.py --method keyword
```

## 开发计划

- ✅ **v0.3.1**: LLM 元数据管理与配置增强
- ✅ **v0.3.0**: 代码重构与模块化
- ✅ **v0.2.0**: Web UI 集成与 Docker 支持
- ✅ **v0.1.0**: Cubox 分析与分类系统
- 🔜 **v0.4.0**: CLI 统一与测试完善
- 🔜 **v0.5.0**: 多源聚合（RSS、本地文件）
- 🔜 **v1.0.0**: 知识图谱与可视化

## 文档

- 📖 [快速开始](docs/QUICK_START.md) - 安装和基本使用
- 🏗️ [架构指南](AGENT.md) - 项目架构和开发指南
- 📝 [变更日志](CHANGELOG.md) - 版本历史和变更记录
- 🔧 [配置示例](config.example.yaml) - 配置文件模板

## 贡献

欢迎提交 Issue 和 Pull Request！

## 协议

MIT License

---

**快速开始**: `./dev.sh start`  
**API 文档**: http://127.0.0.1:8000/docs  
**Web UI**: http://localhost:5173  
**获取帮助**: `python distill.py --help`
