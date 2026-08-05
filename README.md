# Bo-Distiller

智能内容蒸馏工具 - 将收藏的文章提炼成体系化知识文档

## 核心功能

- **Cubox 内容分析与智能分类** - 自动主题聚类、重复检测、关键词提取
- **知识蒸馏合成** - 两阶段 LLM 提炼，将多源内容整合成结构化知识文档

## 快速开始

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

📖 **详细指南**：[QUICK_START.md](QUICK_START.md)

## 项目状态

✅ **v0.3.0** - 代码重构与模块化  
✅ **v0.2.0** - Web UI 集成与 Docker 支持  
✅ **v0.1.0** - Cubox 智能分析与分类系统已上线  
✅ **v0.0.1** - 核心蒸馏框架已实现

查看完整变更：[CHANGELOG.md](CHANGELOG.md)

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

- ✅ **Week 1**: 核心框架（模型、配置、LLM 客户端、缓存、合成器）
- ✅ **Week 2**: Cubox 分析与分类系统
- ✅ **Week 3**: 代码重构与模块化
- 🔜 **Week 4**: CLI 统一与测试完善
- 🔜 **Week 5**: 多源聚合（RSS、本地文件）
- 🔜 **Phase 2**: 知识图谱与可视化

## 贡献

欢迎提交 Issue 和 Pull Request！

## 协议

MIT License

---

**开始使用**：阅读 [QUICK_START.md](QUICK_START.md)  
**了解架构**：阅读 [Reference_myself/00. README.md](Reference_myself/00.%20README.md)  
**获取帮助**：运行 `python distill.py --help`
