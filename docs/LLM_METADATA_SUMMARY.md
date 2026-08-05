# LLM 元数据管理功能 - 实现总结

## 🎯 功能概述

实现了 LLM 提供商元数据的自动获取、缓存和管理功能，支持从外部 API 获取提供商配置（base_url、上下文窗口等）和模型列表，并在 Web UI 中提供查看和更新操作。

---

## ✅ 实现内容

### 1. 核心模块

#### `src/llm_metadata.py` - 元数据管理器

**主要类**:
- `LLMMetadataManager`: 元数据管理核心类

**主要功能**:
- ✅ 从外部 API 获取提供商元数据
- ✅ 从提供商 API 获取模型列表（OpenAI 兼容 `/v1/models`）
- ✅ 24 小时缓存机制
- ✅ 缓存有效性检查
- ✅ 降级策略（API 失败时使用过期缓存）
- ✅ 批量刷新所有提供商
- ✅ 缓存清除

**支持的提供商**:
```python
SUPPORTED_PROVIDERS = [
    "deepseek",
    "xiaomi",
    "xiaomi-token-plan-cn",
    "minimax",
    "moonshotai",
    "opencode-go",
]
```

---

### 2. API 路由

#### `src/web/routers/llm.py` - LLM 元数据 API

**端点列表**:

| 方法 | 路径 | 功能 |
|-----|------|------|
| GET | `/api/llm/providers` | 获取支持的提供商列表 |
| GET | `/api/llm/providers/{id}/metadata` | 获取提供商元数据 |
| GET | `/api/llm/providers/{id}/models` | 获取提供商模型列表 |
| POST | `/api/llm/providers/{id}/refresh` | 刷新指定提供商元数据 |
| POST | `/api/llm/providers/refresh-all` | 刷新所有提供商元数据 |
| DELETE | `/api/llm/providers/{id}/cache` | 清除指定提供商缓存 |
| DELETE | `/api/llm/cache` | 清除所有缓存 |
| GET | `/api/llm/cache/stats` | 获取缓存统计信息 |

---

### 3. 数据流程

```
前端 UI
   ↓
API 路由 (/api/llm/...)
   ↓
LLMMetadataManager
   ↓
检查缓存 (数据库)
   ↓
如果未缓存或需刷新
   ↓
外部 API 请求
   ├─ 元数据: https://basellm.github.io/llm-metadata/api/providers/{id}.json
   └─ 模型列表: {api_base}/v1/models
   ↓
缓存到数据库 (24小时有效期)
   ↓
返回数据给前端
```

---

## 📦 文件清单

### 新增文件（3个）

1. **`src/llm_metadata.py`** (~300 行)
   - LLMMetadataManager 类
   - 元数据获取和缓存逻辑

2. **`src/web/routers/llm.py`** (~200 行)
   - 8 个 API 端点
   - 请求参数验证
   - 错误处理

3. **`scripts/test_llm_metadata.py`** (~200 行)
   - 功能测试脚本
   - 5 个测试用例

4. **`docs/LLM_METADATA_API.md`** (文档)
   - 完整 API 文档
   - 使用场景示例
   - 前端集成指南

### 修改文件（3个）

1. **`src/web/app.py`**
   - 导入 llm 路由
   - 注册到应用

2. **`src/web/routers/__init__.py`**
   - 导出 llm 模块

3. **`requirements.txt`** (已在之前改进中添加)
   - aiohttp>=3.9.0

---

## 🔑 核心特性

### 1. 智能缓存机制

**缓存策略**:
- 缓存时长: 24 小时
- 缓存键格式: `llm_metadata_{provider_id}_{data_type}`
- 存储位置: SQLite 数据库

**缓存行为**:
```python
# 自动使用有效缓存
metadata = await manager.get_or_fetch_provider_metadata(provider_id)

# 强制刷新
metadata = await manager.get_or_fetch_provider_metadata(provider_id, force_refresh=True)

# 降级策略（API 失败时使用过期缓存）
if api_failed and expired_cache_exists:
    return expired_cache
```

---

### 2. 双重数据源

**元数据来源**:
1. **外部 API**: `https://basellm.github.io/llm-metadata/api/providers/{id}.json`
   - 提供 base_url、context_window、max_output 等配置
   - 静态元数据，更新频率低

2. **提供商 API**: `{api_base}/v1/models`
   - 实时获取当前可用模型列表
   - 需要 API Key 认证
   - 动态数据，可能随时变化

---

### 3. 错误处理和降级

**错误处理**:
- ✅ 网络超时（10 秒）
- ✅ API 返回错误
- ✅ 不支持的提供商 (404)
- ✅ 无法获取数据 (500)

**降级策略**:
- ✅ API 失败时使用过期缓存
- ✅ 友好的错误提示
- ✅ 不中断用户操作

---

### 4. 批量操作

**批量刷新**:
```python
# 刷新所有提供商
results = await manager.refresh_all_providers()
# 返回: {"deepseek": True, "xiaomi": True, ...}
```

**批量清除缓存**:
```python
# 清除所有缓存
manager.clear_cache()

# 清除指定提供商
manager.clear_cache("deepseek")
```

---

## 🚀 使用示例

### Python 代码

```python
from src.llm_metadata import get_metadata_manager

manager = get_metadata_manager()

# 获取元数据
metadata = await manager.get_or_fetch_provider_metadata("deepseek")
print(f"Base URL: {metadata.get('base_url')}")
print(f"Models: {metadata.get('models')}")

# 获取模型列表
models = await manager.get_or_fetch_provider_models(
    "deepseek",
    api_base="https://api.deepseek.com",
    api_key="sk-xxxxx"
)
print(f"Available models: {[m['id'] for m in models]}")

# 刷新所有
results = await manager.refresh_all_providers()
print(f"Success: {sum(1 for v in results.values() if v)}/{len(results)}")
```

---

### JavaScript/前端

```javascript
// 获取提供商列表
const { providers } = await fetch('/api/llm/providers').then(r => r.json());

// 获取元数据
const { data } = await fetch('/api/llm/providers/deepseek/metadata').then(r => r.json());
console.log('Base URL:', data.base_url);

// 获取模型列表（需要 API Key）
const { data: modelsData } = await fetch(
  `/api/llm/providers/deepseek/models?api_base=${apiBase}&api_key=${apiKey}`
).then(r => r.json());
console.log('Models:', modelsData.models);

// 刷新元数据
await fetch('/api/llm/providers/deepseek/refresh', { method: 'POST' });

// 查看缓存状态
const { data: stats } = await fetch('/api/llm/cache/stats').then(r => r.json());
console.log('Cache stats:', stats);
```

---

## 📊 数据结构

### 提供商元数据

```json
{
  "provider_id": "deepseek",
  "name": "DeepSeek",
  "base_url": "https://api.deepseek.com",
  "models": [
    {
      "id": "deepseek-chat",
      "context_window": 128000,
      "max_output": 8000,
      "description": "DeepSeek Chat 模型"
    }
  ],
  "description": "DeepSeek AI 提供商",
  "full_metadata": { /* 完整元数据 */ }
}
```

### 模型列表（OpenAI 格式）

```json
{
  "provider_id": "deepseek",
  "models": [
    {
      "id": "deepseek-chat",
      "object": "model",
      "created": 1234567890,
      "owned_by": "deepseek"
    }
  ],
  "count": 1
}
```

### 缓存数据结构

```json
{
  "data": { /* 元数据或模型列表 */ },
  "cached_at": "2026-08-05T12:00:00"
}
```

---

## 🧪 测试

### 运行测试脚本

```bash
# 添加执行权限
chmod +x scripts/test_llm_metadata.py

# 运行测试
python scripts/test_llm_metadata.py
```

### 测试覆盖

- ✅ 测试 1: 获取提供商列表
- ✅ 测试 2: 获取元数据
- ✅ 测试 3: 缓存功能
- ✅ 测试 4: 缓存统计
- ✅ 测试 5: 刷新所有提供商

---

## 🎨 前端集成建议

### 1. LLM 配置页面布局

```
┌─────────────────────────────────────────┐
│ LLM 提供商配置                            │
├─────────────────────────────────────────┤
│                                         │
│ [刷新所有] [清除缓存] [查看缓存状态]      │
│                                         │
│ ┌─ DeepSeek ──────────────────┐        │
│ │ Base URL: api.deepseek.com   │        │
│ │ 上下文窗口: 128,000 tokens    │        │
│ │ 最大输出: 8,000 tokens        │        │
│ │ [查看模型] [刷新]              │        │
│ └─────────────────────────────┘        │
│                                         │
│ ┌─ Xiaomi ────────────────────┐        │
│ │ Base URL: api.xiaomi.com     │        │
│ │ ...                          │        │
│ └─────────────────────────────┘        │
│                                         │
└─────────────────────────────────────────┘
```

### 2. 操作流程

**首次加载**:
1. 获取提供商列表
2. 并行获取所有元数据（优先使用缓存）
3. 显示配置信息

**用户配置**:
1. 用户输入 API Key
2. 点击"获取模型列表"
3. 调用 `/api/llm/providers/{id}/models`
4. 显示可用模型供用户选择

**手动刷新**:
1. 用户点击"刷新"按钮
2. 调用刷新 API（force_refresh=true）
3. 更新 UI 显示

---

## ⚠️ 注意事项

1. **网络依赖**
   - 依赖 `basellm.github.io` 服务
   - 需要稳定的网络连接
   - 建议在初始化时批量获取

2. **API Key 安全**
   - 前端传递 API Key 时使用 HTTPS
   - 后端不保存 API Key（仅用于临时查询）
   - 日志中不输出敏感信息

3. **缓存时效**
   - 默认 24 小时，适合静态元数据
   - 模型列表可能需要更短的缓存时间
   - 可根据实际情况调整

4. **并发控制**
   - 刷新所有提供商为串行执行
   - 避免同时发起过多请求
   - 前端应显示加载状态

5. **错误处理**
   - 优雅降级（使用过期缓存）
   - 友好的错误提示
   - 不阻塞用户其他操作

---

## 🔮 后续优化方向

1. **缓存优化**
   - 支持不同数据类型的缓存时长
   - 模型列表缓存 1 小时，元数据缓存 24 小时

2. **并发优化**
   - 批量刷新改为并发执行
   - 控制并发数避免速率限制

3. **数据增强**
   - 合并元数据和实时模型列表
   - 提供统一的数据视图

4. **UI 增强**
   - 显示缓存更新时间
   - 支持单个字段刷新
   - 提供刷新进度提示

5. **监控告警**
   - API 请求失败率监控
   - 缓存命中率统计
   - 异常情况告警

---

## ✅ 验收标准

所有功能均已实现并测试：

- [x] 支持 6 个提供商
- [x] 从外部 API 获取元数据
- [x] 从提供商 API 获取模型列表
- [x] 24 小时缓存机制
- [x] 手动刷新功能
- [x] 缓存管理（清除、统计）
- [x] 8 个 API 端点
- [x] 完整的错误处理
- [x] 降级策略
- [x] 测试脚本
- [x] 完整文档

---

**实现时间**: 2026-08-05  
**版本**: v1.0.0  
**状态**: ✅ 完成并验证
