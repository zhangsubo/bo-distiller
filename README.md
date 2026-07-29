# Bo-Distiller

智能内容蒸馏工具 - 将收藏的文章提炼成体系化知识文档

## 核心功能

- **Cubox 内容分析与智能分类** - 自动主题聚类、重复检测、关键词提取
- **微信公众号本地化下载** - 无需第三方 API，支持批量下载和断点续传
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
python distill.py wechat login          # 微信下载工具
python analyze_cubox_content.py        # Cubox 内容分析
python distill.py run --limit 10        # 知识蒸馏（测试模式）
```

📖 **详细指南**：[QUICK_START.md](QUICK_START.md)

## 项目状态

✅ **v0.2.0** - 微信公众号下载工具已发布  
✅ **v0.1.0** - Cubox 智能分析与分类系统已上线  
✅ **v0.0.1** - 核心蒸馏框架已实现

查看完整变更：[CHANGELOG.md](CHANGELOG.md)

## 文档导航

### 使用指南
- [Cubox 内容分析与分类](docs/guide/cubox-classification.md)
- [微信公众号下载工具](docs/guide/wechat-download.md)

### 设计文档
完整的架构和设计文档位于 `Reference_myself/` 目录：
- [00. 项目概述](Reference_myself/00.%20README.md)
- [01. 架构设计](Reference_myself/01.%20架构设计.md)
- [02. 核心机制设计](Reference_myself/02-core-mechanisms.md)
- [03. 多源内容聚合](Reference_myself/03-multi-source-aggregation.md)

### 分析报告
- [Cubox 分类报告](docs/reports/classification-report.md)
- [Web UI 状态](docs/reports/web-ui-status.md)

### 历史归档
项目演进过程的历史文档：[docs/archives/](docs/archives/)

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

# 微信工具
python distill.py wechat login     # 扫码登录
python distill.py wechat sync      # 同步公众号
python distill.py wechat download  # 下载文章

# 内容源管理
python distill.py sources add --cubox
python distill.py sources list

# Cubox 分析
python analyze_cubox_content.py
python classify_upgrade.py --method keyword
```

## 开发计划

- ✅ **Week 1**: 核心框架（模型、配置、LLM 客户端、缓存、合成器）
- ✅ **Week 2**: Cubox 分析与分类系统
- ✅ **Week 3**: 微信公众号下载工具
- 🔜 **Week 4**: CLI 统一与测试完善
- 🔜 **Week 5**: 多源聚合（RSS、本地文件）
- 🔜 **Phase 2**: 知识图谱与可视化

## 与 content-distiller 的对比

| 维度 | content-distiller | bo-distiller |
|------|-------------------|--------------|
| 定位 | 学习某个博主的完整体系 | 多源内容的个人知识管理 |
| 输入源 | 单一/少数 RSS 源 | RSS/Cubox/微信/书签/本地文件 |
| 分类 | 预定义（投资/育儿/成长） | 动态主题发现 + 自定义 |
| 输出 | 按分类平铺 | 多层知识体系 |

## 贡献

欢迎提交 Issue 和 Pull Request！

## 协议

MIT License

---

**开始使用**：阅读 [QUICK_START.md](QUICK_START.md)  
**了解架构**：阅读 [Reference_myself/00. README.md](Reference_myself/00.%20README.md)  
**获取帮助**：运行 `python distill.py --help`
