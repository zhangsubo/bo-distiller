# Bo-Distiller 快速上手指南

## 项目状态

✅ **设计阶段完成** - 所有设计文档已就绪，可以开始 MVP 开发

## 目录结构

```
bo-distiller/
├── Reference_myself/          # 完整设计文档（10份，~124KB）
│   ├── 00. README.md         # 项目概述
│   ├── 01. 架构设计.md       # 系统架构
│   ├── 02-core-mechanisms.md # 核心机制
│   ├── 03-multi-source-aggregation.md  # Cubox + 本地 MD
│   ├── 04-topic-discovery.md # 主题发现
│   ├── 05-knowledge-graph.md # 知识图谱（Phase 2-3）
│   ├── 06-tech-stack.md      # 技术选型
│   ├── 07-roadmap.md         # 实现路线图⭐
│   ├── 08-llm-client-via-agent.md  # LLM 客户端
│   └── 09-output-modules.md  # 输出模块
├── src/                      # 源代码目录（待实现）
│   ├── __init__.py
│   ├── adapters/             # 适配器（Cubox, 本地 MD）
│   ├── processors/           # 处理器（清洗、分类、蒸馏）
│   ├── outputs/              # 输出模块（飞书、本地）
│   └── utils/                # 工具函数
├── tests/                    # 测试目录
├── .cache/                   # 缓存目录（自动创建）
├── output/                   # 输出目录（自动创建）
├── distill.py                # CLI 入口⭐
├── config.example.yaml       # 配置模板
├── sources.example.yaml      # 内容源配置模板
├── prompts.example.yaml      # 提示词配置模板
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
├── README.md                 # 项目简介
└── UPDATES.md                # 设计更新记录

```

## 第一步：阅读设计文档

### 必读文档（按顺序）

1. **Reference_myself/00. README.md** - 了解项目全貌
2. **Reference_myself/01. 架构设计.md** - 理解系统架构
3. **Reference_myself/02-core-mechanisms.md** - 掌握核心机制
4. **Reference_myself/07-roadmap.md** ⭐ - MVP 实现计划（逐日任务）

### 选读文档

- **03-multi-source-aggregation.md** - 深入了解 Cubox/本地 MD 适配器
- **08-llm-client-via-agent.md** - 了解 LLM 调用方式
- **09-output-modules.md** - 了解飞书/本地输出

## 第二步：环境准备

### 1. Python 环境

```bash
# 检查 Python 版本（需要 3.9+）
python --version

# 创建虚拟环境
cd /Users/zhangsubo/Code/bo-distiller
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 外部工具（可选）

**Cubox CLI**（如果使用 Cubox 源）：
```bash
# 假设通过 npm 安装
npm install -g cubox-cli

# 配置
cubox config --token YOUR_CUBOX_TOKEN

# 测试
cubox list --limit 5
```

**飞书 CLI**（如果使用飞书输出）：
```bash
# 假设通过 npm 安装
npm install -g feishu-cli

# 登录
feishu login

# 配置知识库空间
feishu config --space-id YOUR_SPACE_ID
```

### 3. 配置文件

```bash
# 复制配置模板
cp config.example.yaml config.yaml
cp sources.example.yaml sources.yaml
cp prompts.example.yaml prompts.yaml
cp .env.example .env

# 编辑环境变量
vim .env  # 填入 API Keys
```

**.env 配置**：
```ini
# 至少配置一个 LLM API Key
DEEPSEEK_API_KEY=sk-xxx  # 推荐

# 可选
MIMO_API_KEY=your_key
MOONSHOT_API_KEY=sk-xxx
MINIMAX_API_KEY=your_key

# 飞书（可选）
FEISHU_SPACE_ID=your_space_id
```

**sources.yaml 配置**：
```yaml
sources:
  - type: cubox
    name: "Cubox 收藏"
    identifier: "cubox export"
    enabled: true
  
  - type: local_markdown
    name: "我的笔记"
    identifier: "/Users/zhangsubo/Documents/notes"  # 修改为实际路径
    enabled: true
```

## 第三步：开始实现（MVP）

### Week 1: 基础框架（5-7天）

参考 **Reference_myself/07-roadmap.md** 的详细任务分解。

#### Day 1-2: 项目结构
```bash
# 已完成：项目结构已创建
# 下一步：实现数据模型
```

创建 `src/models.py`：
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class SourceInfo(BaseModel):
    type: str
    name: str
    identifier: str

class Article(BaseModel):
    id: str
    title: str
    content: str
    url: Optional[str]
    source: SourceInfo
    author: Optional[str]
    published_date: Optional[datetime]
    fetched_date: datetime
    metadata: Dict[str, Any]
```

#### Day 3-4: 配置管理
创建 `src/config.py`，加载 YAML 配置。

#### Day 5-7: LLM 客户端
创建 `src/llm_client.py`，实现直接 API 调用。

### Week 2: 内容处理流程（5-7天）

#### Day 1-2: Cubox 适配器
创建 `src/adapters/cubox_adapter.py`。

#### Day 3-4: 本地 Markdown 适配器
创建 `src/adapters/local_markdown_adapter.py`。

#### Day 5-7: 清洗和分类
创建 `src/processors/cleaner.py` 和 `src/processors/classifier.py`。

### Week 3: 知识蒸馏与输出（5-7天）

#### Day 1-3: 智能分批
创建 `src/processors/batcher.py`。

#### Day 4-6: 两阶段合成
创建 `src/processors/distiller.py`。

#### Day 7: 输出模块
创建 `src/outputs/feishu_output.py` 和 `src/outputs/local_output.py`。

## 第四步：测试

```bash
# 测试模式（处理 10 篇文章）
python distill.py run --limit 10

# 查看结果
ls -lh output/

# 如果配置了飞书，检查飞书知识库
```

## 开发工具

### CLI 命令

```bash
# 查看状态
python distill.py status

# 添加内容源
python distill.py add-source --cubox
python distill.py add-source --folder ~/Documents/notes

# 列出所有源
python distill.py list-sources

# 运行蒸馏
python distill.py run                # 增量模式
python distill.py run --full         # 全量模式
python distill.py run --limit 10     # 测试模式
python distill.py run --model mimo   # 指定模型

# 单独输出
python distill.py output --feishu
python distill.py output --local
```

### 代码质量工具（开发依赖）

```bash
# 安装开发依赖
pip install black ruff mypy pytest

# 格式化代码
black src/

# 代码检查
ruff check src/

# 类型检查
mypy src/

# 运行测试
pytest tests/
```

## 关键设计决策

### 1. 内容源
- ✅ Cubox CLI（全量 + 增量）
- ✅ 本地 Markdown（全量 + 增量）
- ❌ 不支持 RSS/书签/URL 列表

### 2. LLM 提供商
- ✅ DeepSeek（主推荐，¥0.001/1K）
- ✅ Xiaomi Mimo（coding-plan）
- ✅ Kimi-code（coding-plan）
- ✅ MiniMax
- ❌ 移除千问支持

### 3. 输出方式
- ✅ 飞书知识库（通过飞书 CLI）
- ✅ 本地 Markdown

### 4. 核心机制（继承 content-distiller）
- ✅ 体系化提炼（两阶段合成）
- ✅ 断点续传（5 层缓存）
- ✅ 智能分批（Token 预算管理）
- ✅ 高度可配置（YAML 驱动）

## 常见问题

### Q: 依赖安装失败？
A: 确保 Python 3.9+，使用虚拟环境，逐个安装依赖排查问题。

### Q: Cubox CLI 在哪里下载？
A: 需要确认 Cubox 是否提供官方 CLI 工具。如果没有，可能需要自己实现 API 调用。

### Q: 飞书 CLI 在哪里下载？
A: 需要确认飞书是否提供官方 CLI 工具。如果没有，可以使用飞书开放平台 API。

### Q: 如何贡献代码？
A: 当前处于设计阶段，欢迎提 Issue 讨论设计方案。

## 下一步行动

1. ✅ **设计完成** - 所有文档已就绪
2. 📝 **阅读文档** - 从 Reference_myself/00. README.md 开始
3. 🚀 **开始实现** - 按照 Reference_myself/07-roadmap.md Week 1 计划
4. 🧪 **测试验证** - 使用 `--limit 10` 测试
5. 🔄 **迭代优化** - 根据实际效果调整

## 联系方式

- **项目路径**：`/Users/zhangsubo/Code/bo-distiller`
- **设计文档**：`Reference_myself/` 目录
- **实现路线图**：`Reference_myself/07-roadmap.md` ⭐

---

**设计完成日期**：2026-07-09  
**预计 MVP 完成**：3 周后  
**祝开发顺利！** 🚀
