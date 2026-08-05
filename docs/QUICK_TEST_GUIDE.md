# 🚀 LLM 元数据管理 - 快速测试指南

## 📍 访问地址

**重要提示**: 后端 API 必须使用 `127.0.0.1`，不能使用 `localhost`（会被 OrbStack 拦截）

```
前端:     http://localhost:5173
后端 API: http://127.0.0.1:8000
API 文档: http://127.0.0.1:8000/docs
```

---

## 🧪 测试步骤

### 1. 启动服务

```bash
./dev.sh start
```

等待启动完成后继续。

---

### 2. 测试后端 API

打开终端，运行以下命令：

```bash
# 测试 1: 获取提供商列表
curl http://127.0.0.1:8000/api/llm/providers | python3 -m json.tool

# 期望结果: 返回 6 个提供商
# {
#   "providers": ["deepseek", "xiaomi", "xiaomi-token-plan-cn", "minimax", "moonshotai", "opencode-go"],
#   "status": "ok"
# }
```

```bash
# 测试 2: 获取 DeepSeek 元数据
curl http://127.0.0.1:8000/api/llm/providers/deepseek/metadata | python3 -m json.tool | head -20

# 期望结果: 返回元数据，包含 base_url、models 等
```

```bash
# 测试 3: 缓存统计
curl http://127.0.0.1:8000/api/llm/cache/stats | python3 -m json.tool

# 期望结果: deepseek 的 metadata_cached 为 true（首次访问后自动缓存）
```

```bash
# 测试 4: 刷新元数据
curl -X POST http://127.0.0.1:8000/api/llm/providers/deepseek/refresh

# 期望结果: {"status": "ok"}
```

```bash
# 测试 5: 刷新所有提供商
curl -X POST http://127.0.0.1:8000/api/llm/providers/refresh-all | python3 -m json.tool

# 期望结果: 显示每个提供商的刷新结果
```

---

### 3. 测试前端 UI

#### 步骤 1: 访问设置页面

1. 打开浏览器，访问 http://localhost:5173
2. 点击左侧导航的"设置"
3. 点击"LLM 设置"

#### 步骤 2: 查看提供商配置（原有功能）

默认在"提供商配置"标签页：
- ✅ 查看默认 LLM 提供商选项
- ✅ 查看各个提供商的配置表单（API Key、Base URL 等）
- ✅ 注意顶部的蓝色提示框

#### 步骤 3: 切换到元数据管理

点击"元数据管理"标签页：

**统计面板**（最上方）：
- ✅ 查看"支持的提供商"数量（应该是 6）
- ✅ 查看"已缓存"数量（应该是 1/6，因为测试时访问了 deepseek）
- ✅ 查看"刷新所有"和"清除所有缓存"按钮

**提示信息**（蓝色提示框）：
- ✅ 说明元数据来源和缓存策略

**提供商卡片列表**（6 个卡片）：

每个卡片显示：
- 提供商名称（如 "DeepSeek"）
- 缓存状态（绿色"已缓存"标签，如果有）
- Base URL
- 支持模型数
- 右上角操作按钮：
  - 刷新按钮（圆形箭头图标）
  - 清除缓存按钮（垃圾桶图标）
- "查看模型列表"链接

#### 步骤 4: 测试刷新功能

**单个刷新**：
1. 找到 "deepseek" 卡片
2. 点击右上角的刷新按钮（圆形箭头）
3. ✅ 观察按钮显示 loading 状态
4. ✅ 看到成功提示："已刷新 deepseek 元数据"

**批量刷新**：
1. 点击统计面板的"刷新所有"按钮
2. ✅ 观察按钮 loading 状态
3. ✅ 看到成功提示："已刷新 X/6 个提供商"
4. ✅ 缓存统计更新，"已缓存"数量增加

#### 步骤 5: 查看模型列表

1. 点击任意卡片的"查看模型列表"链接
2. ✅ 弹出对话框
3. ✅ 显示模型列表，包含：
   - 模型 ID（如 "deepseek-chat"）
   - 描述（英文）
   - 标签：
     - 上下文窗口（如 "上下文: 1,000,000"）
     - 最大输出（如 "最大输出: 8,000"）
     - 模型系列（蓝色标签）
     - 知识截止日期（绿色标签）

#### 步骤 6: 测试清除缓存

**单个清除**：
1. 找到有"已缓存"标签的卡片
2. 点击右上角的垃圾桶图标
3. ✅ 显示确认对话框："确定清除缓存？"
4. 点击"确定"
5. ✅ 看到成功提示："已清除 xxx 缓存"
6. ✅ 绿色"已缓存"标签消失

**批量清除**：
1. 点击统计面板的"清除所有缓存"按钮（红色）
2. ✅ 显示确认对话框
3. 点击"确定"
4. ✅ 看到成功提示："已清除所有缓存"
5. ✅ 所有"已缓存"标签消失
6. ✅ 缓存统计更新为 0/6

---

## 🎯 预期结果

### 后端测试 ✅
- [x] 提供商列表返回 6 个
- [x] 元数据获取成功
- [x] 缓存统计正确
- [x] 刷新功能正常
- [x] 清除缓存正常

### 前端测试 ⏳
- [ ] 页面正常渲染
- [ ] 统计数据正确显示
- [ ] 卡片列表显示 6 个提供商
- [ ] 缓存状态标识正确
- [ ] 刷新按钮工作正常
- [ ] 模型列表对话框正常
- [ ] 清除缓存功能正常
- [ ] 批量操作正常

---

## 🐛 常见问题

### 问题 1: API 返回 404

**症状**: `curl http://localhost:8000/api/llm/providers` 返回 `{"detail": "API not found"}`

**原因**: OrbStack 拦截了 localhost:8000

**解决**: 使用 `127.0.0.1:8000` 而不是 `localhost:8000`
```bash
curl http://127.0.0.1:8000/api/llm/providers
```

### 问题 2: 前端无法加载数据

**检查**:
1. 打开浏览器开发者工具（F12）
2. 切换到 Network 标签
3. 筛选 "llm"
4. 查看请求 URL 是否正确（应该是 127.0.0.1:8000）

**解决**: 前端 API 配置在 `frontend/src/api/llmMetadata.ts` 中，使用相对路径 `const API_BASE = '';`，会自动使用当前域名。

### 问题 3: 元数据不显示

**可能原因**:
1. 后端服务未启动 → 运行 `./dev.sh status` 检查
2. 网络问题 → 检查网络连接
3. 外部 API 不可访问 → 检查 https://basellm.github.io/llm-metadata/

**检查**: 查看后端日志
```bash
tail -f logs/backend.log
```

### 问题 4: 刷新后数据未更新

**原因**: React Query 缓存未失效

**解决**: 
1. 强制刷新浏览器（Cmd+Shift+R / Ctrl+Shift+R）
2. 或清除浏览器缓存

---

## 📊 测试数据示例

### DeepSeek 元数据示例

```json
{
  "provider_id": "deepseek",
  "name": "DeepSeek",
  "base_url": null,
  "models": {
    "deepseek-chat": {
      "id": "deepseek-chat",
      "description": "DeepSeek chat model...",
      "family": "deepseek",
      "limit": {
        "context": 1000000,
        "output": 8000
      },
      "knowledge": "2025-09",
      "cost": {
        "input": 0.14,
        "output": 0.28,
        "cache_read": 0.0028
      }
    }
  }
}
```

---

## 🔧 开发者工具

### 浏览器控制台

打开开发者工具（F12）后：

**Network 标签**:
- 筛选 "llm" 查看 API 请求
- 检查请求状态、响应数据

**Console 标签**:
- 查看错误信息
- 检查 React 组件状态

**Application 标签** (Chrome):
- 查看 React Query 缓存（需要安装 React Query DevTools）

---

## ✅ 验收清单

复制以下清单，完成测试后打勾：

### 后端 API
- [ ] GET /api/llm/providers
- [ ] GET /api/llm/providers/deepseek/metadata
- [ ] GET /api/llm/cache/stats
- [ ] POST /api/llm/providers/deepseek/refresh
- [ ] POST /api/llm/providers/refresh-all
- [ ] DELETE /api/llm/providers/deepseek/cache
- [ ] DELETE /api/llm/cache

### 前端功能
- [ ] 访问设置页面
- [ ] 切换到元数据管理标签
- [ ] 查看统计面板
- [ ] 查看提供商卡片列表
- [ ] 点击查看模型列表
- [ ] 单个刷新功能
- [ ] 批量刷新功能
- [ ] 单个清除缓存
- [ ] 批量清除缓存
- [ ] 缓存状态标识

---

## 📞 需要帮助？

如果遇到问题，请检查：

1. **服务状态**
   ```bash
   ./dev.sh status
   ```

2. **后端日志**
   ```bash
   tail -f logs/backend.log
   ```

3. **前端日志**
   ```bash
   tail -f logs/frontend.log
   ```

4. **文档**
   - `FRONTEND_LLM_METADATA_INTEGRATION.md` - 前端集成文档
   - `VERIFICATION_SUCCESS.md` - 验证报告
   - `docs/LLM_METADATA_API.md` - API 文档

---

**祝测试顺利！** 🎉
