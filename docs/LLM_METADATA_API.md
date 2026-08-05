# LLM 元数据管理 API 文档

## 概述

LLM 元数据管理功能允许从外部 API 获取提供商配置（如 base_url、上下文窗口等）和模型列表，并缓存到数据库中。支持手动刷新和缓存管理。

## 支持的提供商

- `deepseek`
- `xiaomi`
- `xiaomi-token-plan-cn`
- `minimax`
- `moonshotai`
- `opencode-go`

---

## API 端点

### 1. 获取支持的提供商列表

```http
GET /api/llm/providers
```

**响应示例**:
```json
{
  "providers": [
    "deepseek",
    "xiaomi",
    "xiaomi-token-plan-cn",
    "minimax",
    "moonshotai",
    "opencode-go"
  ],
  "status": "ok"
}
```

---

### 2. 获取提供商元数据

```http
GET /api/llm/providers/{provider_id}/metadata?force_refresh=false
```

**路径参数**:
- `provider_id`: 提供商 ID

**查询参数**:
- `force_refresh`: 是否强制刷新缓存（默认 false）

**响应示例**:
```json
{
  "data": {
    "provider_id": "deepseek",
    "name": "DeepSeek",
    "base_url": "https://api.deepseek.com",
    "models": [
      {
        "id": "deepseek-chat",
        "context_window": 128000,
        "max_output": 8000
      }
    ],
    "description": "DeepSeek AI 提供商",
    "full_metadata": { ... }
  },
  "status": "ok"
}
```

---

### 3. 获取提供商模型列表

```http
GET /api/llm/providers/{provider_id}/models?api_base=xxx&api_key=xxx&force_refresh=false
```

**路径参数**:
- `provider_id`: 提供商 ID

**查询参数**:
- `api_base`: API 基础 URL（可选，用于实时查询）
- `api_key`: API Key（可选，用于实时查询）
- `force_refresh`: 是否强制刷新缓存（默认 false）

**响应示例**:
```json
{
  "data": {
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
  },
  "status": "ok"
}
```

**说明**:
- 如果提供了 `api_base` 和 `api_key`，则从提供商的 `/v1/models` 接口获取
- 否则从缓存或元数据中获取

---

### 4. 刷新指定提供商元数据

```http
POST /api/llm/providers/{provider_id}/refresh
```

**路径参数**:
- `provider_id`: 提供商 ID

**响应示例**:
```json
{
  "status": "ok",
  "message": "成功刷新 deepseek 元数据",
  "provider_id": "deepseek"
}
```

---

### 5. 刷新所有提供商元数据

```http
POST /api/llm/providers/refresh-all
```

**响应示例**:
```json
{
  "status": "ok",
  "message": "已刷新 6/6 个提供商",
  "results": {
    "deepseek": true,
    "xiaomi": true,
    "xiaomi-token-plan-cn": true,
    "minimax": true,
    "moonshotai": true,
    "opencode-go": false
  }
}
```

---

### 6. 清除指定提供商缓存

```http
DELETE /api/llm/providers/{provider_id}/cache
```

**路径参数**:
- `provider_id`: 提供商 ID

**响应示例**:
```json
{
  "status": "ok",
  "message": "已清除 deepseek 缓存"
}
```

---

### 7. 清除所有提供商缓存

```http
DELETE /api/llm/cache
```

**响应示例**:
```json
{
  "status": "ok",
  "message": "已清除所有提供商缓存"
}
```

---

### 8. 获取缓存统计信息

```http
GET /api/llm/cache/stats
```

**响应示例**:
```json
{
  "data": {
    "deepseek": {
      "metadata_cached": true,
      "models_cached": false
    },
    "xiaomi": {
      "metadata_cached": true,
      "models_cached": true
    },
    "minimax": {
      "metadata_cached": false,
      "models_cached": false
    }
  },
  "status": "ok"
}
```

---

## 使用场景

### 场景 1: 首次加载 LLM 配置页面

```javascript
// 1. 获取支持的提供商列表
const providersRes = await fetch('/api/llm/providers');
const { providers } = await providersRes.json();

// 2. 获取每个提供商的元数据（优先从缓存）
for (const providerId of providers) {
  const metadataRes = await fetch(`/api/llm/providers/${providerId}/metadata`);
  const { data } = await metadataRes.json();
  
  // 显示 base_url、context_window 等配置
  console.log(`${data.name}: ${data.base_url}`);
}
```

---

### 场景 2: 用户点击"刷新元数据"

```javascript
// 刷新指定提供商
const refreshRes = await fetch(`/api/llm/providers/deepseek/refresh`, {
  method: 'POST'
});
const result = await refreshRes.json();

if (result.status === 'ok') {
  // 重新获取元数据显示
  const metadataRes = await fetch(`/api/llm/providers/deepseek/metadata?force_refresh=true`);
  const { data } = await metadataRes.json();
  // 更新 UI
}
```

---

### 场景 3: 用户输入 API Key 后获取模型列表

```javascript
// 用户输入了 API Base 和 API Key
const apiBase = 'https://api.deepseek.com';
const apiKey = 'sk-xxxxx';

// 获取该提供商支持的模型列表
const modelsRes = await fetch(
  `/api/llm/providers/deepseek/models?api_base=${encodeURIComponent(apiBase)}&api_key=${encodeURIComponent(apiKey)}`
);
const { data } = await modelsRes.json();

// 显示模型选择器
data.models.forEach(model => {
  console.log(`模型: ${model.id}`);
});
```

---

### 场景 4: 查看缓存状态

```javascript
// 获取缓存统计
const statsRes = await fetch('/api/llm/cache/stats');
const { data } = await statsRes.json();

// 显示每个提供商的缓存状态
Object.entries(data).forEach(([providerId, stats]) => {
  console.log(`${providerId}:`);
  console.log(`  元数据缓存: ${stats.metadata_cached ? '✓' : '✗'}`);
  console.log(`  模型缓存: ${stats.models_cached ? '✓' : '✗'}`);
});
```

---

## 缓存机制

### 缓存策略
- **缓存时长**: 24 小时
- **缓存键**: `llm_metadata_{provider_id}_{data_type}`
  - 数据类型: `metadata` 或 `models`
- **存储位置**: 数据库（通过 `storage.set_setting()`）

### 缓存行为
1. **自动使用缓存**: 默认情况下，如果缓存在有效期内，直接返回缓存数据
2. **强制刷新**: 设置 `force_refresh=true` 强制从 API 获取最新数据
3. **降级策略**: 如果 API 请求失败，使用过期缓存（如果存在）

### 缓存更新时机
- 首次访问时自动获取并缓存
- 用户手动点击"刷新"按钮
- 缓存过期（24 小时后）
- 手动清除缓存

---

## 错误处理

### 常见错误

**1. 不支持的提供商**
```json
{
  "detail": "不支持的提供商: invalid_provider"
}
```
状态码: `404`

**2. 无法获取元数据**
```json
{
  "detail": "无法获取 deepseek 元数据"
}
```
状态码: `500`

**3. API 请求失败**
- 自动使用过期缓存（如果有）
- 控制台显示警告信息

---

## 前端集成示例

### React 组件示例

```tsx
import { useState, useEffect } from 'react';

interface ProviderMetadata {
  provider_id: string;
  name: string;
  base_url: string;
  models: any[];
}

function LLMConfigPanel() {
  const [providers, setProviders] = useState<string[]>([]);
  const [metadata, setMetadata] = useState<Record<string, ProviderMetadata>>({});
  const [loading, setLoading] = useState(false);

  // 加载提供商列表
  useEffect(() => {
    fetch('/api/llm/providers')
      .then(res => res.json())
      .then(data => setProviders(data.providers));
  }, []);

  // 加载元数据
  useEffect(() => {
    providers.forEach(async (providerId) => {
      const res = await fetch(`/api/llm/providers/${providerId}/metadata`);
      const { data } = await res.json();
      setMetadata(prev => ({ ...prev, [providerId]: data }));
    });
  }, [providers]);

  // 刷新元数据
  const handleRefresh = async (providerId: string) => {
    setLoading(true);
    await fetch(`/api/llm/providers/${providerId}/refresh`, { method: 'POST' });
    const res = await fetch(`/api/llm/providers/${providerId}/metadata?force_refresh=true`);
    const { data } = await res.json();
    setMetadata(prev => ({ ...prev, [providerId]: data }));
    setLoading(false);
  };

  return (
    <div>
      <h2>LLM 提供商配置</h2>
      {providers.map(providerId => (
        <div key={providerId}>
          <h3>{metadata[providerId]?.name || providerId}</h3>
          <p>Base URL: {metadata[providerId]?.base_url}</p>
          <button onClick={() => handleRefresh(providerId)} disabled={loading}>
            刷新
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## 测试

### 运行测试脚本

```bash
python scripts/test_llm_metadata.py
```

### 手动测试

```bash
# 启动服务
./dev.sh start

# 测试 API
curl http://localhost:8000/api/llm/providers
curl http://localhost:8000/api/llm/providers/deepseek/metadata
curl -X POST http://localhost:8000/api/llm/providers/deepseek/refresh
curl http://localhost:8000/api/llm/cache/stats
```

---

## 注意事项

1. **网络依赖**: 元数据 API 依赖外部服务 `basellm.github.io`，需要网络连接
2. **API Key 安全**: 不要在日志中暴露 API Key
3. **缓存时效**: 默认 24 小时，可根据需要调整
4. **并发限制**: 刷新所有提供商时为串行执行，避免并发过高
5. **降级策略**: API 失败时会使用过期缓存，确保基本可用

---

**更新时间**: 2026-08-05  
**版本**: v1.0.0
