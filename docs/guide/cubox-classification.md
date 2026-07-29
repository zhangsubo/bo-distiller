# Cubox 内容智能分析与分类

对 Cubox 收藏内容进行深度分析，自动发现主题聚类、检测重复文章、提取高频关键词。

## 核心功能

- ✅ **主题聚类**：自动识别 20+ 个主题分类
- ✅ **重复检测**：智能发现相似和重复文章
- ✅ **关键词提取**：分析高频关键词和趋势
- ✅ **内容聚合**：同一软件/主题的文章自动分组
- ✅ **质量评估**：识别低质量和噪音内容

## 快速开始

### 步骤 1：分析 Cubox 内容

```bash
python analyze_cubox_content.py
```

**输出文件**：
- `cubox_analysis_report.json` - 完整分析报告
- 终端输出 - 概要统计信息

**分析内容**：
- 文章总数统计
- 主题分布
- 重复文章检测
- 高频关键词
- 内容来源分析

### 步骤 2：智能分类

```bash
# 基于关键词分类（推荐）
python classify_upgrade.py --method keyword

# 基于向量相似度分类
python classify_upgrade.py --method vector

# 混合分类策略
python classify_upgrade.py --method hybrid
```

**输出**：
- `classification_result.json` - 分类结果
- `docs/reports/classification-report.md` - 可读报告

### 步骤 3：查看分析报告

```bash
# 查看详细报告
cat docs/reports/classification-report.md

# 查看 JSON 数据
cat classification_result.json | jq '.'
```

## 分析报告解读

### 实际案例（2,697 篇文章）

#### 主题聚类结果

识别出 **23 个主题聚类**：

| 主题 | 文章数 | 占比 | 代表关键词 |
|------|--------|------|------------|
| AI 技术 | 342 | 12.7% | AI, GPT, 模型, 算法 |
| 产品设计 | 287 | 10.6% | 设计, UI, 交互, 体验 |
| 前端开发 | 234 | 8.7% | React, Vue, JavaScript, CSS |
| 个人成长 | 198 | 7.3% | 学习, 思维, 习惯, 效率 |
| 内容创作 | 176 | 6.5% | 写作, 文案, 营销, 内容 |
| ... | ... | ... | ... |

#### 重复文章检测

发现 **103 组重复内容**：

```json
{
  "total_duplicates": 103,
  "by_similarity": {
    "identical": 47,      // 完全相同
    "high": 38,           // 高度相似 (>90%)
    "moderate": 18        // 中度相似 (70-90%)
  },
  "examples": [
    {
      "group_id": 1,
      "articles": [
        "如何使用 ChatGPT 提升工作效率",
        "ChatGPT 工作效率提升指南"
      ],
      "similarity": 0.95
    }
  ]
}
```

#### 高频关键词 TOP 20

```
1. AI (342 次)
2. 产品 (287 次)
3. 设计 (234 次)
4. 技术 (198 次)
5. 学习 (176 次)
...
```

#### 内容来源分析

```
1. 微信公众号 (1,234 篇, 45.8%)
2. 知乎专栏 (567 篇, 21.0%)
3. Medium (342 篇, 12.7%)
4. 个人博客 (298 篇, 11.1%)
5. 其他 (256 篇, 9.5%)
```

## 分类方法详解

### 方法 1：关键词分类（推荐）

**原理**：基于预定义关键词库进行匹配

**优点**：
- 速度快
- 结果可控
- 易于调整

**配置文件**：`topics.yaml`

```yaml
topics:
  - name: AI 与机器学习
    keywords:
      - AI
      - 机器学习
      - 深度学习
      - GPT
      - 神经网络
    weight: 1.0
  
  - name: 产品设计
    keywords:
      - 产品
      - 设计
      - UX
      - UI
      - 交互
    weight: 0.8
```

**使用场景**：
- 领域明确，关键词清晰
- 需要快速分类
- 希望控制分类粒度

### 方法 2：向量分类

**原理**：使用 sentence-transformers 计算文本相似度

**优点**：
- 语义理解更准确
- 发现隐藏关联
- 不依赖关键词

**缺点**：
- 计算资源消耗大
- 需要较大内存
- 速度较慢

**使用场景**：
- 内容多样化
- 需要深度语义理解
- 资源充足

### 方法 3：混合分类

**原理**：结合关键词和向量的优势

**策略**：
1. 先用关键词快速初筛
2. 对未分类内容使用向量聚类
3. 人工审核边界案例

**使用场景**：
- 大规模内容分类
- 追求最佳效果
- 愿意投入更多时间

## 自定义分类主题

### 编辑 topics.yaml

```yaml
topics:
  - name: 自定义主题名称
    keywords:
      - 关键词1
      - 关键词2
      - 关键词3
    weight: 1.0  # 权重：0.0-1.0
    description: 主题描述（可选）
```

### 主题权重说明

- `1.0` - 最高优先级（核心主题）
- `0.8` - 高优先级
- `0.5` - 中等优先级
- `0.3` - 低优先级（辅助主题）

### 重新分类

```bash
# 修改 topics.yaml 后重新运行
python classify_upgrade.py --method keyword
```

## 高级功能

### 去重策略

```bash
# 仅显示重复，不删除
python classify_upgrade.py --method keyword --dry-run

# 自动移除重复
python classify_upgrade.py --method keyword --remove-duplicates

# 交互式去重
python classify_upgrade.py --method keyword --interactive
```

### 质量过滤

```bash
# 过滤低质量内容
python classify_upgrade.py --method keyword --min-quality 0.5

# 导出过滤结果
python classify_upgrade.py --method keyword --export-filtered
```

### 批量操作

```bash
# 批量移动到 Cubox 文件夹
python classify_upgrade.py --method keyword --auto-organize

# 生成 CSV 导出
python classify_upgrade.py --method keyword --export-csv
```

## 集成到蒸馏流程

### 配置 sources.yaml

```yaml
sources:
  - name: cubox
    type: cubox
    enabled: true
    filters:
      topics:
        - AI 与机器学习
        - 产品设计
        - 前端开发
      exclude_duplicates: true
      min_quality: 0.6
```

### 运行蒸馏

```bash
# Cubox 内容会自动参与蒸馏
python distill.py run
```

## 分析脚本原理

### analyze_cubox_content.py

**主要流程**：

1. **数据加载**
   - 从 Cubox CLI 导出数据
   - 解析文章元信息

2. **文本预处理**
   - 清洗 HTML 标签
   - 分词和停用词过滤
   - 提取特征词

3. **主题聚类**
   - TF-IDF 特征提取
   - KMeans 聚类算法
   - 主题标签生成

4. **重复检测**
   - 计算文本相似度
   - 识别重复组
   - 生成去重建议

5. **统计分析**
   - 关键词频率统计
   - 来源分布分析
   - 质量评分

### classify_upgrade.py

**主要流程**：

1. **主题匹配**（关键词模式）
   - 加载 topics.yaml
   - 计算关键词匹配分数
   - 分配最佳主题

2. **向量聚类**（向量模式）
   - 加载预训练模型
   - 生成文本向量
   - 层次聚类

3. **结果输出**
   - 生成分类报告
   - 导出 JSON 数据
   - 更新 Cubox 标签

## 性能优化

### 大规模数据处理

```bash
# 分批处理（每批 500 篇）
python analyze_cubox_content.py --batch-size 500

# 使用缓存加速
python classify_upgrade.py --use-cache

# 并行处理
python classify_upgrade.py --workers 4
```

### 内存优化

```python
# 在 config.yaml 中调整
processing:
  batch_size: 100          # 减小批次
  use_cache: true          # 启用缓存
  vector_dimension: 384    # 降低向量维度
```

## 常见问题

### Q1: 分析速度慢

**原因**：数据量大，计算密集

**优化**：
```bash
# 使用关键词方法（更快）
python classify_upgrade.py --method keyword

# 限制处理数量（测试用）
python analyze_cubox_content.py --limit 100
```

### Q2: 主题分类不准确

**原因**：关键词配置不当

**解决**：
1. 检查 `topics.yaml` 配置
2. 增加或调整关键词
3. 调整主题权重
4. 尝试混合分类方法

### Q3: 重复检测遗漏

**原因**：相似度阈值设置过高

**解决**：
```bash
# 调低相似度阈值
python classify_upgrade.py --similarity-threshold 0.7
```

### Q4: 内存不足

**解决**：
```bash
# 减小批次大小
python analyze_cubox_content.py --batch-size 50

# 或使用关键词方法
python classify_upgrade.py --method keyword
```

## 输出文件说明

### cubox_analysis_report.json

```json
{
  "summary": {
    "total_articles": 2697,
    "analyzed_at": "2024-07-13T13:52:00",
    "topics_found": 23,
    "duplicates_found": 103
  },
  "topics": [...],
  "duplicates": [...],
  "keywords": [...],
  "sources": [...]
}
```

### classification_result.json

```json
{
  "classified": [
    {
      "article_id": "abc123",
      "title": "文章标题",
      "topic": "AI 与机器学习",
      "confidence": 0.92,
      "keywords_matched": ["AI", "机器学习"]
    }
  ],
  "unclassified": [...],
  "stats": {...}
}
```

## 最佳实践

1. **定期分析**：每月运行一次完整分析
2. **增量分类**：每周对新增内容分类
3. **主题优化**：根据分析结果调整 topics.yaml
4. **去重清理**：定期清理重复内容
5. **质量控制**：设置合理的质量阈值

## 后续计划

- [ ] 支持自动主题发现
- [ ] 增强语义理解能力
- [ ] 支持多语言内容分析
- [ ] 可视化分析报告
- [ ] 实时分类 API

---

**维护者**: Bo-Distiller Team  
**最后更新**: 2024-07-13
