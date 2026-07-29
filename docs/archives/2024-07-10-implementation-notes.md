# Bo-Distiller 实施注意事项

## 关键发现

### 1. 飞书 CLI 已就绪 ✅

- **命令**：`lark-cli`（已安装在 `/opt/homebrew/bin/lark-cli`）
- **功能**：完全支持文档创建、更新、知识库管理
- **集成难度**：低，有完整的文档和示例

**结论**：飞书输出模块可以按原计划实施。

### 2. Cubox CLI 待确认 ⚠️

- **命令**：`cubox-cli`（当前系统未找到）
- **仓库**：https://github.com/OLCUBO/cubox-cli
- **状态**：需要先安装和测试

**待办事项**：
1. 从 GitHub 安装 Cubox CLI
2. 配置 API Key（从 Cubox 设置获取）
3. 测试导出功能
4. 确认数据格式和增量支持

### 3. 实施优先级调整

**推荐实施顺序**：

#### Week 1: 基础框架（不变）
- Day 1-2: 数据模型（Pydantic）
- Day 3-4: 配置管理（YAML）
- Day 5-7: LLM 客户端（OpenAI SDK）

#### Week 2: 内容处理（调整）
- Day 1-2: **本地 Markdown 适配器**（优先，无外部依赖）
- Day 3-4: 清洗 + 分类
- Day 5-7: Cubox 适配器（需要先安装 cubox-cli）

#### Week 3: 知识蒸馏与输出（不变）
- Day 1-3: 智能分批 + 缓存
- Day 4-6: 两阶段合成
- Day 7: 输出模块（飞书 + 本地）

## 立即行动清单

### 优先级 P0（立即执行）

1. **验证 lark-cli 认证状态**
   ```bash
   lark-cli auth status
   ```
   如果未认证，执行：
   ```bash
   lark-cli config init
   lark-cli auth login --recommend
   ```

2. **安装 Cubox CLI**
   ```bash
   # 从 GitHub 安装（需要确认实际安装方式）
   # 可能需要：
   git clone https://github.com/OLCUBO/cubox-cli.git
   cd cubox-cli
   # 按照 README 指示安装
   ```

3. **测试 Cubox CLI**
   ```bash
   cubox-cli --help
   cubox-cli list --limit 5
   ```

### 优先级 P1（本周完成）

1. **实现本地 Markdown 适配器**（无外部依赖，优先实施）
   - 创建 `src/adapters/local_markdown_adapter.py`
   - 实现全量扫描
   - 实现增量扫描（基于 mtime）
   - 单元测试

2. **实现飞书输出模块**（lark-cli 已就绪）
   - 创建 `src/outputs/feishu_output.py`
   - 测试文档创建
   - 测试文档更新
   - 文档映射管理

### 优先级 P2（下周）

1. **实现 Cubox 适配器**（依赖 cubox-cli 安装）
   - 等待 cubox-cli 安装和测试完成
   - 根据实际 CLI 能力设计接口
   - 如果 CLI 不足，考虑直接调用 Cubox API

## 备选方案

### 如果 Cubox CLI 不可用

**方案 A：Cubox API**
- 查阅 Cubox 官方 API 文档
- 直接使用 HTTP 请求访问 Cubox API
- 需要处理认证、分页、错误重试

**方案 B：先实现本地 Markdown**
- MVP 只支持本地 Markdown 源
- Phase 2 再实现 Cubox 集成
- 用户可以先手动从 Cubox 导出到本地

**方案 C：Obsidian 同步桥接**
- 使用 Cubox 的 Obsidian 同步插件
- 同步到本地 Obsidian vault
- Bo-Distiller 读取 Obsidian vault（本地 MD）

### 如果 lark-cli 有问题

**方案 A：飞书开放平台 API**
- 直接使用 HTTP 请求调用飞书 API
- 需要处理应用认证（app_id + app_secret）
- 参考：https://open.feishu.cn/document

**方案 B：只输出本地 Markdown**
- MVP 暂时只支持本地输出
- Phase 2 再实现飞书输出

## 设计文档更新计划

### 需要更新的文档

1. **03-multi-source-aggregation.md**
   - 更新 Cubox CLI 的实际命令
   - 添加备选方案（API/Obsidian）
   - 调整实施优先级

2. **09-output-modules.md**
   - 确认使用 `lark-cli` 而非 `feishu`
   - 添加实际命令示例
   - 更新代码示例

3. **07-roadmap.md**
   - 调整 Week 2 任务顺序
   - 本地 MD 优先于 Cubox
   - 添加风险说明

## 成功标准

### MVP 最小可行产品

**必须实现**：
- ✅ 本地 Markdown 源（全量 + 增量）
- ✅ 知识蒸馏（两阶段合成）
- ✅ 本地 Markdown 输出
- ✅ 飞书输出（使用 lark-cli）

**可选实现**：
- 🔜 Cubox 源（依赖 CLI 可用性）

### Phase 2 扩展

- Cubox 集成（如果 MVP 未完成）
- 智能主题发现
- 知识图谱基础版

## 当前项目状态

- ✅ 设计文档完成
- ✅ 项目结构就绪
- ✅ lark-cli 已安装
- ⚠️ cubox-cli 待安装
- 📝 准备开始 Week 1 实现

---

**更新时间**：2026-07-09  
**下一步**：验证 lark-cli 认证状态，安装 cubox-cli
