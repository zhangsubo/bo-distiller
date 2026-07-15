# Bo-Distiller

智能内容蒸馏工具 - 将收藏的文章提炼成体系化知识文档

## 项目状态

✅ **Week 1 完成** - 核心框架已实现  
✅ **分类系统升级完成** - 智能分析与分类功能已上线

## 🆕 最新功能（2026-07-13）

### 🎯 Cubox 内容智能分析

已完成对 **2,697 篇** Cubox 文章的深度分析：
- ✅ 识别 20+ 个主题聚类
- ✅ 检测 103 组重复文章
- ✅ 高频关键词提取
- ✅ 同一软件/主题文章聚合

### 🚀 快速体验

```bash
# 分析你的 Cubox 内容
python analyze_cubox_content.py

# 智能分类（自动去重）
python classify_upgrade.py --method keyword

# 查看详细报告
cat CLASSIFICATION_REPORT.md
```

**详细文档**: 
- [完整分析报告](./CLASSIFICATION_REPORT.md)
- [快速开始指南](./QUICKSTART_CLASSIFICATION.md)
- [项目总结](./SUMMARY.md)

## 快速导航

### 📚 设计文档

完整的设计文档位于 `Reference_myself/` 目录：

- [00. README](./Reference_myself/00.%20README.md) - 项目概述与快速开始
- [01. 架构设计](./Reference_myself/01.%20架构设计.md) - 系统架构、模块设计
- [02. 核心机制设计](./Reference_myself/02-core-mechanisms.md) - 四大核心机制详解
- [03. 多源内容聚合](./Reference_myself/03-multi-source-aggregation.md) - 输入源适配器
- [04. 智能主题发现](./Reference_myself/04-topic-discovery.md) - 动态分类与聚类
- [05. 知识图谱设计](./Reference_myself/05-knowledge-graph.md) - 关联关系与可视化
- [06. 技术选型](./Reference_myself/06-tech-stack.md) - 技术栈与依赖
- [07. 实现路线图](./Reference_myself/07-roadmap.md) - 迭代计划与里程碑

## 核心特性

- ✅ **体系化提炼**：两阶段合成（批次提取 + 知识整合）
- ✅ **断点续传**：多层缓存，任意断点恢复
- ✅ **智能分批**：Token 预算动态分配
- ✅ **高度可配置**：YAML 驱动，提示词可定制
- ✅ **多 LLM 支持**：DeepSeek / Mimo / MiniMax / Kimi
- 🔜 **多源聚合**：RSS/书签/链接/本地文件（Week 2）
- 🔜 **智能主题发现**：混合策略（关键词 + 向量）（Week 2）
- 🔜 **知识图谱**：关联可视化（Phase 2）

## 与 content-distiller 的对比

| 维度 | content-distiller | bo-distiller |
|------|-------------------|--------------|
| 定位 | 学习某个博主的完整体系 | 多源内容的个人知识管理 |
| 输入源 | 单一/少数 RSS 源 | RSS/书签/链接/本地文件 |
| 分类 | 预定义（投资/育儿/成长） | 动态主题发现 + 自定义 |
| 输出 | 按分类平铺 | 多层知识体系 |

## 技术栈

- **语言**：Python 3.9+
- **AI**：Qwen / DeepSeek / Claude
- **数据处理**：feedparser, trafilatura, beautifulsoup4
- **ML**：scikit-learn, sentence-transformers
- **CLI**：click, rich

## 快速开始

```bash
# 1. 克隆项目
cd /Users/zhangsubo/Code/bo-distiller

# 2. 创建虚拟环境并安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 4. 配置内容源
# 编辑 sources.yaml 添加你的内容源

# 5. 运行蒸馏
python distill.py run --limit 10  # 测试模式
python distill.py run             # 完整运行
```

## 开发计划

- ✅ **Week 1**: 核心框架（模型、配置、LLM 客户端、缓存、合成器）
- 🔜 **Week 2**: 内容源适配器（RSS、本地 Markdown、Cubox）
- 🔜 **Week 3**: 主题发现、输出模块、CLI 完善

## 已实现模块

### Week 1: 核心框架

| 模块 | 文件 | 功能 |
|------|------|------|
| 数据模型 | `src/models.py` | Article、SourceInfo、SystemConfig 等 Pydantic 模型 |
| 配置管理 | `src/config.py` | 加载 YAML 配置，环境变量替换 |
| LLM 客户端 | `src/llm_client.py` | 统一 LLM 调用接口，支持多提供商 |
| 缓存管理 | `src/cache.py` | 多层缓存，断点续传 |
| 内容清洗 | `src/processors/cleaner.py` | HTML 清洗、噪音去除 |
| 知识合成 | `src/synthesizer.py` | 两阶段合成（批次提取 + 知识整合） |

### CLI 命令

```bash
python distill.py run              # 运行蒸馏流程
python distill.py run --limit 10   # 测试模式（只处理10篇）
python distill.py run --model mimo # 使用指定 LLM
python distill.py status           # 查看项目状态
python distill.py --clear-cache    # 清除缓存
```

## 开始阅读

👉 从 [Reference_myself/00. README.md](./Reference_myself/00.%20README.md) 开始了解项目全貌。

## 协议

MIT License
