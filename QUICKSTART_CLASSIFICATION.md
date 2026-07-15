# 🚀 Cubox 内容分析与分类 - 快速开始

## 一分钟了解

你的 Cubox 已收藏 **2,697 篇文章**，主要关于：
- AI 编程工具（Claude, Codex, OpenClaw）
- 开源项目（GitHub 推荐）
- 技术教程和工具软件

现在，项目已升级支持：
✅ 智能主题识别
✅ 自动去重
✅ 同一软件/主题的文章聚合
✅ 详细分析报告

---

## 🎯 三步上手

### 步骤 1：分析你的内容

```bash
python analyze_cubox_content.py
```

**输出**：
- 高频关键词 TOP 30
- 潜在主题聚类
- 来源网站统计
- 重复文章检测
- 保存报告到 `cubox_analysis_report.json`

### 步骤 2：智能分类

```bash
# 快速分类（推荐）
python classify_upgrade.py --method keyword --limit 500

# 完整分类所有文章
python classify_upgrade.py --method keyword

# 保存到数据库
python classify_upgrade.py --method keyword --save-db
```

**输出**：
- 自动识别 15-20 个主题
- 去除重复文章
- 保存结果到 `classification_result.json`

### 步骤 3：查看结果

```bash
# 查看分类报告
cat classification_result.json

# 查看完整分析
cat cubox_analysis_report.json

# 查看总结报告
cat CLASSIFICATION_REPORT.md
```

---

## 📊 你的数据洞察

根据分析，你收藏的文章有这些特点：

### 🔥 热门主题 TOP 5

1. **OpenClaw** - 98 篇文章
   - 多 Agent 协同开发工具
   - 最近 6 个月持续关注

2. **Skill 管理** - 86 篇文章
   - Agent 技能系统
   - Claude/Codex 的扩展能力

3. **开源项目** - 78 篇文章
   - GitHub 项目推荐
   - 新工具发现

4. **Claude 相关** - 78 篇文章
   - Claude Code 使用技巧
   - CLAUDE.md 配置

5. **数据资产** - 40 篇文章
   - 企业数据资产入表
   - 专业财经内容

### 📈 收藏趋势

- **2026年5月**: 487 篇（高峰期）
- **2026年6月**: 385 篇
- **2026年7月**: 285 篇（至今）

### ⚠️ 发现的问题

- **103 组重复文章** - 相同标题被收藏多次
- **建议**: 定期运行去重工具

---

## 🛠️ 进阶使用

### 使用 LLM 智能分类

如果你有 DeepSeek API Key，可以使用更智能的分类：

```bash
# 1. 配置 API Key
export DEEPSEEK_API_KEY=sk-your-key

# 2. 使用 LLM 分类
python classify_upgrade.py --method llm --limit 100

# 3. 混合策略（关键词 + LLM）
python classify_upgrade.py --method hybrid
```

### 自定义分类规则

编辑 `topics.yaml` 添加你自己的主题：

```yaml
predefined_topics:
  你的主题名:
    keywords: ["关键词1", "关键词2"]
    prompt_key: "tech"
    description: "主题描述"
```

### 集成到蒸馏流程

```bash
# 使用新的分类配置运行蒸馏
python distill.py run --config topics.yaml
```

---

## 📂 生成的文件说明

| 文件 | 说明 |
|------|------|
| `cubox_analysis_report.json` | 完整统计数据（关键词、域名、时间分布等） |
| `classification_result.json` | 分类结果详情（每个主题包含哪些文章） |
| `CLASSIFICATION_REPORT.md` | 详细分析报告和使用说明 |
| `topics.yaml` | 优化后的主题配置（基于你的实际数据） |

---

## 💡 建议的工作流

### 日常使用

```bash
# 每周运行一次（处理新收藏的文章）
python analyze_cubox_content.py --limit 100
python classify_upgrade.py --method keyword --limit 100
```

### 完整整理

```bash
# 每月运行一次（完整分析+去重）
python analyze_cubox_content.py
python classify_upgrade.py --method keyword --save-db
```

### 主题发现

```bash
# 当你发现新的兴趣领域，想重新分类时
python classify_upgrade.py --method hybrid
# 根据结果更新 topics.yaml
```

---

## 🎓 核心优势

### 升级前 vs 升级后

| 维度 | 升级前 | 升级后 |
|------|--------|--------|
| 分类数 | 3个固定分类 | 15-20个动态主题 |
| 去重 | ❌ 不支持 | ✅ 自动去重 |
| 同主题识别 | ❌ 不支持 | ✅ 智能聚合 |
| 分析报告 | ❌ 无 | ✅ 详细统计 |
| 分类方法 | 简单关键词 | 关键词 + LLM |

---

## 🔍 常见问题

### Q: 分类结果不满意怎么办？

**A**: 有三种方式优化：

1. **调整关键词** - 编辑 `topics.yaml` 添加更多关键词
2. **使用 LLM 分类** - 配置 API Key 后用 `--method llm`
3. **调整阈值** - 修改代码中的 `min_cluster_size` 参数

### Q: 如何处理重复文章？

**A**: 分类工具会自动识别和报告重复文章，你可以：

```bash
# 查看重复组
python analyze_cubox_content.py | grep "相似组"

# 自动去重后分类
python classify_upgrade.py --method keyword
```

### Q: 可以只分析特定时间段的文章吗？

**A**: 修改 SQL 查询添加时间过滤：

```python
# 在 analyze_cubox_content.py 中修改
query = """
SELECT * FROM articles 
WHERE fetched_date >= '2026-06-01'
ORDER BY fetched_date DESC
"""
```

---

## 📞 技术支持

- **完整文档**: `CLASSIFICATION_REPORT.md`
- **配置说明**: `topics.yaml`
- **代码文档**: `src/processors/smart_classifier.py`

---

**快速开始**: `python analyze_cubox_content.py`

**更新时间**: 2026-07-13
