# Cubox CLI 和飞书 CLI 使用指南

根据实际调研，本文档说明 Bo-Distiller 如何集成这两个 CLI 工具。

## 1. Cubox CLI

### 官方信息

- **官方仓库**：https://github.com/OLCUBO/cubox-cli
- **帮助文档**：https://help.cubox.pro/ai/agents/
- **安装方式**：从 GitHub 安装

### 核心能力

1. **检索功能**
   - 按收藏夹、标签、时间、关键词查找
   - 支持 RAG 语义检索

2. **阅读功能**
   - 获取 Markdown 格式正文
   - 获取 AI 解读内容

3. **整理功能**
   - 修改星标、已读状态
   - 移动分类
   - 打标签

### 认证方式

需要从 Cubox 设置的 API 扩展获取 API Key，然后在本地终端配置。

### Bo-Distiller 集成策略

**方案 1：使用 Cubox CLI（推荐）**

```python
class CuboxAdapter:
    def fetch_all(self):
        # 调用 cubox-cli 检索所有内容
        # 获取 Markdown 格式正文
        pass
    
    def fetch_incremental(self, since: datetime):
        # 按时间过滤检索
        pass
```

**方案 2：直接使用 Cubox API**

如果 CLI 不支持导出功能，可以直接调用 Cubox API（需要参考官方文档）。

### 待确认事项

- [ ] Cubox CLI 是否支持批量导出？
- [ ] 导出的数据格式是什么？
- [ ] 是否支持按时间过滤？
- [ ] API Key 如何配置？

## 2. 飞书 CLI (lark-cli)

### 官方信息

- **命令名称**：`lark-cli`（不是 `feishu`）
- **官方仓库**：https://github.com/larksuite/cli
- **已安装路径**：`/opt/homebrew/bin/lark-cli` ✅

### 核心 Agent Skills

#### 文档相关

1. **lark-doc**
   - 创建、读取、更新、搜索文档
   - 基于 Markdown

2. **lark-markdown**
   - 创建、读取、patch、覆盖更新 Drive 中的 `.md` 文件
   - 更精细的 Markdown 操作

3. **lark-wiki**
   - 管理知识空间、节点、文档
   - 知识库结构化操作

### 认证流程

```bash
# 1. 配置应用凭证
lark-cli config init

# 2. 登录授权
lark-cli auth login --recommend

# 3. 检查状态
lark-cli auth status
```

### 关键命令

#### 创建文档

```bash
# 使用快捷命令（+ 前缀）
lark-cli docs +create \
  --doc-format markdown \
  --content $'<title>标题</title>\n# 内容\n正文...'
```

#### 更新文档

```bash
# 更新已有文档
lark-cli docs +update \
  --doc-id <document_id> \
  --content $'更新后的内容'
```

#### 知识库操作

```bash
# 通过 lark-wiki skill 操作
lark-cli wiki +create-node \
  --space-id <space_id> \
  --title "节点标题"
```

### 输出格式

```bash
# JSON 格式（默认）
lark-cli docs +list --format json

# 表格格式
lark-cli docs +list --format table

# 预览模式（不实际执行）
lark-cli docs +create --dry-run --content "..."
```

### Bo-Distiller 集成策略

```python
class FeishuOutput:
    def __init__(self, space_id: str):
        self.space_id = space_id
        self.cli_name = "lark-cli"  # 注意：不是 feishu
    
    def create_or_update_doc(self, title: str, content: str, doc_id: str = None):
        """创建或更新飞书文档"""
        
        if doc_id:
            # 更新已有文档
            cmd = [
                self.cli_name, "docs", "+update",
                "--doc-id", doc_id,
                "--content", content
            ]
        else:
            # 创建新文档
            cmd = [
                self.cli_name, "docs", "+create",
                "--doc-format", "markdown",
                "--title", title,
                "--content", content,
                "--format", "json"
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            return response.get("doc_id")
        else:
            raise Exception(f"飞书文档操作失败: {result.stderr}")
```

### 文档映射管理

```json
{
  "技术": "doc_abc123",
  "技术-原文合集": "doc_def456",
  "产品": "doc_ghi789",
  "INDEX": "doc_jkl012"
}
```

保存在 `.cache/feishu_doc_mapping.json`

## 3. 实施建议

### Phase 1 (MVP)

1. **Cubox 集成**
   - 先确认 Cubox CLI 的实际能力
   - 如果 CLI 功能不足，考虑直接调用 Cubox API
   - 实现基础的全量抓取

2. **飞书输出**
   - 使用 `lark-cli docs +create` 创建文档
   - 使用 `lark-cli docs +update` 更新文档
   - 维护文档映射文件

3. **本地 Markdown**
   - 作为备选输出方式
   - 无依赖，始终可用

### Phase 2

1. **Cubox 增量同步**
   - 实现按时间过滤的增量抓取
   - 状态文件管理

2. **飞书知识库结构化**
   - 使用 `lark-wiki` 创建知识空间层次
   - 文档分类管理

## 4. 配置示例

### config.yaml

```yaml
# 飞书配置
output:
  feishu:
    enabled: true
    cli_command: "lark-cli"  # 注意：不是 feishu
    space_id: "${FEISHU_SPACE_ID}"
    doc_format: "markdown"
```

### sources.yaml

```yaml
sources:
  # Cubox 源（待确认实际配置）
  - type: cubox
    name: "Cubox 收藏"
    identifier: "cubox"  # 或者 API 配置
    enabled: true
    metadata:
      api_key_env: "CUBOX_API_KEY"  # 如果需要
  
  # 本地 Markdown
  - type: local_markdown
    name: "我的笔记"
    identifier: "/Users/zhangsubo/Documents/notes"
    enabled: true
```

## 5. 下一步行动

### 立即执行

1. **验证 Cubox CLI**
   ```bash
   # 检查 cubox-cli 是否已安装
   which cubox-cli
   
   # 查看帮助
   cubox-cli --help
   
   # 测试基础功能
   cubox-cli list --limit 5
   ```

2. **测试 lark-cli**
   ```bash
   # 检查认证状态
   lark-cli auth status
   
   # 测试创建文档（预览模式）
   lark-cli docs +create \
     --dry-run \
     --content "# 测试\n这是测试内容"
   ```

3. **更新设计文档**
   - 根据实际 CLI 能力调整 `03-multi-source-aggregation.md`
   - 根据实际 CLI 能力调整 `09-output-modules.md`

### 如果 Cubox CLI 功能不足

考虑以下备选方案：
1. 直接使用 Cubox API（需要查阅官方 API 文档）
2. 使用 Cubox 的 Obsidian 同步插件导出
3. 暂时只实现本地 Markdown 源，Phase 2 再加 Cubox

---

**更新时间**：2026-07-09  
**状态**：等待验证 Cubox CLI 实际能力
