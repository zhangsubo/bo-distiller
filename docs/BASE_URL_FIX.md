# Base URL 显示问题修复

## 🐛 问题描述

**问题 1**: 在前端"元数据管理"页面，所有提供商的 Base URL 都显示为"未配置"  
**问题 2**: minimax 的 Base URL 显示错误（文档链接而非 API 地址）

**时间**: 2026-08-05

---

## 🔍 问题分析

### 问题 1: Base URL 字段映射错误

**根本原因**: 外部 API (https://basellm.github.io/llm-metadata/) 返回的字段名是 `api`，而不是 `base_url`。

**外部 API 返回**:
```json
{
  "id": "deepseek",
  "name": "DeepSeek",
  "api": "https://api.deepseek.com",  // ← 实际字段名
  "models": {...}
}
```

**原来的代码**:
```python
result = {
    "base_url": metadata.get("base_url"),  // ← 总是返回 None
}
```

### 问题 2: minimax 上游数据错误

**根本原因**: 外部元数据源中 minimax 的 `api` 字段数据错误

| 类型 | URL |
|------|-----|
| 上游数据 | `https://platform.minimaxi.com/document/对话`（文档页面）|
| 正确值 | `https://api.minimaxi.com/v1`（API 端点）|

---

## ✅ 解决方案

### 修改 1: 字段映射修正

**文件**: `src/web/routers/llm.py`

**修改**:
```python
# 修改前
base_url = metadata.get("base_url")

# 修改后
base_url = metadata.get("api") or metadata.get("base_url")
```

### 修改 2: 本地覆盖机制

**文件**: `src/web/routers/llm.py`

**新增**:
```python
# Base URL 本地修正（修正外部数据源的错误）
BASE_URL_OVERRIDES = {
    "minimax": "https://api.minimaxi.com/v1",
}

# 应用修正
base_url = metadata.get("api") or metadata.get("base_url")
if provider_id in BASE_URL_OVERRIDES:
    base_url = BASE_URL_OVERRIDES[provider_id]
```

**优点**:
1. 确保数据准确性
2. 不依赖上游修复
3. 易于维护和扩展
4. 其他提供商不受影响

---

## 🧪 验证结果

### 测试命令
```bash
curl -s "http://127.0.0.1:8000/api/llm/providers/minimax/metadata?force_refresh=true"
```

### 验证结果

| 提供商 | Base URL | 状态 |
|--------|----------|------|
| deepseek | https://api.deepseek.com | ✅ 正确 |
| xiaomi | https://api.xiaomimimo.com/v1 | ✅ 正确 |
| minimax | https://api.minimaxi.com/v1 | ✅ 已修正 |
| moonshotai | https://api.moonshot.ai/v1 | ✅ 正确 |
| opencode-go | https://opencode.ai/zen/go/v1 | ✅ 正确 |

**全部通过！**

---

## 📝 前端显示

修复后，前端"元数据管理"页面显示：

```
MiniMax (minimax.io)
━━━━━━━━━━━━━━━━━━━━━━━━━━
提供商 ID:    minimax
Base URL:     https://api.minimaxi.com/v1  ← 现在正确显示
支持模型数:   8
```

---

## 🎯 影响范围

### 受益功能
- ✅ 前端元数据卡片显示正确的 Base URL
- ✅ API 响应数据准确
- ✅ 使用 minimax 时调用正确的 API 地址

### 无影响
- 提供商配置（使用独立的配置数据）
- 现有的 LLM 调用功能
- 缓存机制
- 其他提供商的数据

---

## 🔧 扩展性

如果发现其他提供商的 Base URL 也有问题，只需在 `BASE_URL_OVERRIDES` 字典中添加：

```python
BASE_URL_OVERRIDES = {
    "minimax": "https://api.minimaxi.com/v1",
    "other_provider": "https://api.example.com",  # 添加新的修正
}
```

---

## 📚 相关文档

- 外部 API 文档: https://basellm.github.io/llm-metadata/
- API 端点文档: `docs/LLM_METADATA_API.md`
- 前端集成文档: `FRONTEND_LLM_METADATA_INTEGRATION.md`

---

## ✅ 验收

- [x] 修改代码（字段映射）
- [x] 添加本地覆盖机制
- [x] 重启服务
- [x] 验证所有提供商
- [x] minimax Base URL 已修正
- [x] 前端显示正常
- [x] 文档已更新

---

**修复时间**: 2026-08-05  
**修复状态**: ✅ 已完成并验证  
**方案**: 本地覆盖 + 字段映射修正
