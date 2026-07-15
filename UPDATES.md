# Bo-Distiller 设计更新记录

根据用户需求完成的设计文档更新。

## 更新时间

2026-07-09

## 核心需求

1. **内容源支持**：
   - ✅ Cubox CLI（全量 + 增量）
   - ✅ 本地 Markdown 文件夹（全量 + 增量）

2. **大模型支持**：
   - ✅ DeepSeek（主推荐）
   - ✅ Xiaomi Mimo（coding-plan）
   - ✅ MiniMax
   - ✅ Kimi-code（coding-plan）
   - ❌ 移除千问支持

3. **LLM 调用方式**：
   - ✅ 直接 API 调用（推荐）
   - ✅ 通过 Coding Agent CLI（可选，利用 coding-plan 套餐）

4. **输出方式**：
   - ✅ 飞书知识库（通过飞书 CLI）
   - ✅ 本地 Markdown 文件

## 更新的文档

### 新增文档

1. **08-llm-client-via-agent.md**
   - LLM Proxy 设计（通过 Agent CLI 调用）
   - 直接 API 调用方案
   - 支持的提供商配置
   - 重试机制与成本优化

2. **09-output-modules.md**
   - 飞书知识库输出设计（FeishuOutput）
   - 本地 Markdown 输出设计（LocalMarkdownOutput）
   - 统一输出管理器（OutputManager）
   - 文档映射与增量更新

### 重大更新

1. **03-multi-source-aggregation.md**（完全重写）
   - 移除 RSS/书签/URL 列表适配器
   - 新增 Cubox CLI 适配器（核心）
     - 全量抓取：`cubox export --format json`
     - 增量抓取：`cubox export --since <timestamp>`
     - 状态管理：`.cache/cubox_state.json`
   - 增强本地 Markdown 适配器
     - 支持 Frontmatter 解析
     - 增量扫描（基于文件 mtime）
     - 状态管理：`.cache/local_markdown_*_state.json`
   - 统一聚合器（支持增量模式）

2. **00. README.md**（完全重写）
   - 更新项目定位（Cubox + 本地 Markdown）
   - 更新核心特性（增量同步、飞书输出）
   - 更新快速开始指南
   - 更新 LLM 提供商对比表

3. **06-tech-stack.md**（部分更新）
   - 移除 RSS 相关依赖（feedparser, beautifulsoup4, trafilatura）
   - 更新 LLM 提供商列表
   - 新增外部依赖说明（Cubox CLI, 飞书 CLI）
   - 更新 requirements.txt

### 新增配置文件

1. **config.example.yaml**
   - 完整的配置文件模板
   - LLM 提供商配置（DeepSeek/Mimo/MiniMax/Kimi）
   - 飞书输出配置
   - 本地输出配置

2. **.env.example**
   - API Keys 配置示例
   - 飞书空间 ID 配置

### 项目根目录

- **README.md**：更新为符合新需求的简版
- **config.example.yaml**：配置模板
- **.env.example**：环境变量模板

## 核心设计变更

### 1. 内容源架构

**之前（content-distiller）**：
```
RSS 源 → RSSAdapter → Articles
```

**现在（bo-distiller）**：
```
Cubox CLI → CuboxAdapter → Articles（增量支持）
本地文件夹 → LocalMarkdownAdapter → Articles（增量支持）
```

### 2. 增量同步机制

**Cubox**：
```python
# 状态文件：.cache/cubox_state.json
{
  "last_sync": "2024-01-15T10:30:00",
  "total_articles": 1000
}

# 增量抓取
cubox export --since 2024-01-15T10:30:00
```

**本地 Markdown**：
```python
# 状态文件：.cache/local_markdown_{hash}_state.json
{
  "last_sync": "2024-01-15T10:30:00",
  "processed_files": {
    "note1.md": 1705302600.0,  # mtime
    "note2.md": 1705302700.0
  }
}

# 增量扫描：比对 mtime
```

### 3. LLM 调用架构

**直接 API（推荐）**：
```
distill.py → LLMClient → OpenAI SDK → LLM API
```

**通过 Agent CLI（可选）**：
```
distill.py → LLMProxy → Agent CLI → LLM API
                         (Claude Code / Pi / Hermes)
```

### 4. 输出架构

```
KnowledgeDistiller
       ↓
   蒸馏结果
       ↓
 OutputManager
    ├─→ FeishuOutput → 飞书 CLI → 飞书知识库
    └─→ LocalMarkdownOutput → 本地文件
```

## 文档总览

| 文档 | 大小 | 说明 |
|------|------|------|
| 00. README.md | 9.2KB | 项目概述（已更新） |
| 01. 架构设计.md | 15KB | 系统架构（未改动） |
| 02-core-mechanisms.md | 23KB | 核心机制（未改动） |
| 03-multi-source-aggregation.md | 23KB | 多源聚合（完全重写） |
| 04-topic-discovery.md | 14KB | 主题发现（未改动） |
| 05-knowledge-graph.md | 550B | 知识图谱（未改动） |
| 06-tech-stack.md | 5.5KB | 技术选型（已更新） |
| 07-roadmap.md | 7.8KB | 路线图（未改动） |
| 08-llm-client-via-agent.md | 11KB | LLM 客户端（新增） |
| 09-output-modules.md | 16KB | 输出模块（新增） |

**总计**：~124KB，10 份完整设计文档

## 配置文件

| 文件 | 说明 |
|------|------|
| config.example.yaml | 完整配置模板 |
| .env.example | 环境变量模板 |
| README.md | 项目简介 |

## 下一步行动

1. ✅ **设计文档已完成**
2. 📝 **创建项目结构**：
   ```bash
   cd /Users/zhangsubo/Code/bo-distiller
   mkdir -p src/{adapters,processors,outputs,utils} tests
   ```

3. 📝 **开始 MVP 实现**（参考 07-roadmap.md）：
   - Week 1: 基础框架（模型、配置、LLM 客户端）
   - Week 2: 内容处理流程（Cubox/本地适配器、清洗、分类）
   - Week 3: 知识蒸馏、缓存、输出模块

4. 📝 **测试外部依赖**：
   - 确认 Cubox CLI 实际命令和输出格式
   - 确认飞书 CLI 实际命令和 API

## 与 content-distiller 的对比

| 维度 | content-distiller | bo-distiller |
|------|-------------------|--------------|
| 输入源 | RSS（单一类型） | Cubox + 本地 Markdown |
| 增量同步 | ❌ | ✅ 两种源都支持 |
| LLM 提供商 | Qwen/DeepSeek | DeepSeek/Mimo/MiniMax/Kimi |
| 输出方式 | 本地 Markdown | 飞书知识库 + 本地 |
| 调用方式 | 直接 API | 直接 API + Agent CLI（可选） |
| 分类方式 | 预定义 | 动态主题发现 + 自定义 |

## 关键特性继承

从 content-distiller 继承的核心机制（已验证可行）：

1. ✅ **体系化提炼**：两阶段合成
2. ✅ **断点续传**：多层缓存
3. ✅ **智能分批**：Token 预算管理
4. ✅ **高度可配置**：YAML 驱动

## 新增特性

1. ✨ **Cubox 集成**：全量 + 增量同步
2. ✨ **本地 Markdown**：支持 Frontmatter，增量扫描
3. ✨ **飞书输出**：通过飞书 CLI 同步知识库
4. ✨ **多模型支持**：4 个 LLM 提供商
5. ✨ **Coding-plan 利用**：通过 Agent CLI 调用（可选）

---

**设计完成时间**：2026-07-09  
**预计开始实现**：立即  
**MVP 预计完成**：3 周后
