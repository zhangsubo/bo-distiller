# LLM 元数据管理 - 快速参考

## 🚀 快速开始

### 1. 启动服务
```bash
./dev.sh start
```

### 2. 测试功能
```bash
python scripts/test_llm_metadata.py
```

### 3. API 访问
访问 http://localhost:8000/docs 查看交互式 API 文档

---

## 📡 常用 API

### 获取提供商列表
```bash
curl http://localhost:8000/api/llm/providers
```

### 获取提供商元数据
```bash
# 从缓存获取
curl http://localhost:8000/api/llm/providers/deepseek/metadata

# 强制刷新
curl "http://localhost:8000/api/llm/providers/deepseek/metadata?force_refresh=true"
```

### 获取模型列表
```bash
# 从缓存/元数据获取
curl http://localhost:8000/api/llm/providers/deepseek/models

# 从提供商 API 实时获取
curl "http://localhost:8000/api/llm/providers/deepseek/models?api_base=https://api.deepseek.com&api_key=sk-xxxxx"
```

### 刷新元数据
```bash
# 刷新单个提供商
curl -X POST http://localhost:8000/api/llm/providers/deepseek/refresh

# 刷新所有提供商
curl -X POST http://localhost:8000/api/llm/providers/refresh-all
```

### 缓存管理
```bash
# 查看缓存状态
curl http://localhost:8000/api/llm/cache/stats

# 清除指定提供商缓存
curl -X DELETE http://localhost:8000/api/llm/providers/deepseek/cache

# 清除所有缓存
curl -X DELETE http://localhost:8000/api/llm/cache
```

---

## 🎯 支持的提供商

| ID | 名称 | 说明 |
|----|------|------|
| `deepseek` | DeepSeek | DeepSeek AI |
| `xiaomi` | Xiaomi | 小米大模型 |
| `xiaomi-token-plan-cn` | Xiaomi Token Plan | 小米按量计费 |
| `minimax` | MiniMax | MiniMax AI |
| `moonshotai` | Moonshot | 月之暗面 Kimi |
| `opencode-go` | OpenCode Go | OpenCode |

---

## 💡 使用场景

### 场景 1: 初始化 LLM 配置页面
```javascript
// 1. 获取提供商列表
const { providers } = await fetch('/api/llm/providers').then(r => r.json());

// 2. 获取每个提供商的配置
for (const id of providers) {
  const { data } = await fetch(`/api/llm/providers/${id}/metadata`).then(r => r.json());
  console.log(`${data.name}: ${data.base_url}`);
}
```

### 场景 2: 用户输入 API Key 后获取模型
```javascript
const apiBase = 'https://api.deepseek.com';
const apiKey = 'sk-xxxxx';

const { data } = await fetch(
  `/api/llm/providers/deepseek/models?api_base=${apiBase}&api_key=${apiKey}`
).then(r => r.json());

// 显示模型列表
data.models.forEach(m => console.log(m.id));
```

### 场景 3: 定期刷新元数据
```javascript
// 每天刷新一次
setInterval(async () => {
  await fetch('/api/llm/providers/refresh-all', { method: 'POST' });
}, 24 * 60 * 60 * 1000);
```

---

## 📦 返回数据结构

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
      "max_output": 8000
    }
  ]
}
```

### 模型列表
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

---

## 🔧 常见问题

### Q: 缓存多久过期？
**A**: 默认 24 小时。过期后会自动重新获取。

### Q: 如何强制刷新？
**A**: 在 API 请求中添加 `?force_refresh=true` 参数。

### Q: API 请求失败怎么办？
**A**: 会自动使用过期缓存（如果存在），确保基本可用。

### Q: 支持添加新的提供商吗？
**A**: 在 `src/llm_metadata.py` 的 `SUPPORTED_PROVIDERS` 列表中添加即可。

---

## 📚 完整文档

- **API 文档**: `docs/LLM_METADATA_API.md`
- **实现总结**: `LLM_METADATA_SUMMARY.md`
- **测试脚本**: `scripts/test_llm_metadata.py`

---

## ✅ 检查清单

使用前确认：
- [ ] 服务已启动 (`./dev.sh start`)
- [ ] 网络连接正常（需访问外部 API）
- [ ] 数据库可写（用于缓存）
- [ ] 查看了 API 文档 (`/docs`)

---

**提示**: 所有 API 都支持在 http://localhost:8000/docs 中交互式测试！
