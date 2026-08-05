# 更换 LLM 元数据源至 models.dev

## 📋 变更概述

**目标**: 将 LLM 元数据 API 从 `basellm.github.io` 更换为 `models.dev`  
**原因**: 规避 AGPL 协议风险  
**日期**: 2026-08-05  
**状态**: ✅ 已完成

---

## 🔄 变更内容

### 旧数据源
- **URL**: `https://basellm.github.io/llm-metadata/`
- **协议**: AGPL-3.0（传染性开源协议）
- **问题**: 使用该数据源可能导致项目被强制开源

### 新数据源
- **URL**: `https://models.dev/api.json`
- **项目**: https://github.com/anomalyco/models.dev
- **协议**: MIT License（宽松许可证）
- **优点**: 
  - 无传染性，可商用
  - 数据更丰富（180+ 提供商）
  - 维护活跃
  - 数据格式更规范

---

## 📊 数据对比

### API 格式差异

**旧格式** (basellm):
```
每个提供商一个文件：
https://basellm.github.io/llm-metadata/deepseek.json
```

**新格式** (models.dev):
```
单一 API 端点返回所有数据：
https://models.dev/api.json
{
  "deepseek": {...},
  "xiaomi": {...},
  ...
}
```

### 数据结构对比

**共同字段**:
- `id` / `provider_id`
- `name`
- `api` (Base URL)
- `models` (模型列表)

**models.dev 新增字段**:
- `env` - 环境变量名
- `npm` - NPM 包名
- `doc` - 文档链接
- 更详细的模型信息（reasoning、tool_call 等）

---

## 🛠️ 代码修改

### 修改文件

**`src/llm_metadata.py`**:

```python
# 修改前
LLM_METADATA_BASE_URL = "https://basellm.github.io/llm-metadata/api/providers"

async def fetch_provider_metadata(self, provider_id: str):
    url = f"{LLM_METADATA_BASE_URL}/{provider_id}.json"
    # 单独请求每个提供商
```

```python
# 修改后
LLM_METADATA_API_URL = "https://models.dev/api.json"

async def fetch_provider_metadata(self, provider_id: str):
    # 获取所有提供商数据
    async with aiohttp.ClientSession() as session:
        async with session.get(LLM_METADATA_API_URL, timeout=10) as response:
            data = await response.json()
            return data.get(provider_id)  # 提取指定提供商
```

**`src/web/routers/llm.py`**:

保持本地覆盖机制：
```python
BASE_URL_OVERRIDES = {
    "minimax": "https://api.minimaxi.com/v1",
}
```

---

## ✅ 验证结果

### 所有提供商验证通过

| 提供商 | Base URL | 模型数 | 状态 |
|--------|----------|--------|------|
| deepseek | `https://api.deepseek.com` | 4 | ✅ |
| xiaomi | `https://api.xiaomimimo.com/v1` | 6 | ✅ |
| minimax | `https://api.minimaxi.com/v1` | 7 | ✅ (本地修正) |
| moonshotai | `https://api.moonshot.ai/v1` | 10 | ✅ |
| opencode-go | `https://opencode.ai/zen/go/v1` | 24 | ✅ |

### API 测试

```bash
# 测试命令
curl -s "http://127.0.0.1:8000/api/llm/providers/deepseek/metadata"

# 返回数据
{
  "data": {
    "provider_id": "deepseek",
    "name": "DeepSeek",
    "base_url": "https://api.deepseek.com",
    "models": {
      "deepseek-v4-flash": {...},
      "deepseek-v4-pro": {...},
      ...
    }
  },
  "status": "ok"
}
```

---

## 🎯 优势总结

### 协议优势
- ✅ **MIT License**: 无传染性，可商用
- ✅ 无需担心 AGPL 传染风险
- ✅ 可以闭源商业化使用

### 技术优势
- ✅ **数据更丰富**: 180+ 提供商 vs 20+ 提供商
- ✅ **维护活跃**: GitHub Star 400+，持续更新
- ✅ **数据质量**: 来自 opencode.ai 内部使用的生产数据
- ✅ **格式规范**: 统一的 JSON 结构，字段完整

### 性能优势
- ✅ **单次请求**: 一次 API 调用获取所有数据
- ✅ **CDN 加速**: Cloudflare CDN，访问速度快
- ✅ **缓存友好**: 24 小时缓存策略依然有效

---

## 📝 注意事项

### 1. minimax Base URL 修正

**问题**: models.dev 中 minimax 的 `api` 字段也是错误的（文档链接）

**解决**: 保留本地覆盖机制
```python
BASE_URL_OVERRIDES = {
    "minimax": "https://api.minimaxi.com/v1",
}
```

### 2. 数据格式差异

models.dev 的模型数据更详细，包含：
- `reasoning` - 是否支持推理模式
- `reasoning_options` - 推理模式选项
- `tool_call` - 是否支持工具调用
- `structured_output` - 是否支持结构化输出
- `temperature` - 是否支持温度参数
- `open_weights` - 是否开源权重
- `cost` - 详细定价信息

前端可以利用这些新字段提供更丰富的展示。

### 3. API 变更影响

- ✅ **无影响**: 前端无需修改
- ✅ **无影响**: 路由接口保持不变
- ✅ **无影响**: 缓存机制保持不变
- ✅ **数据增强**: 返回的数据更详细

---

## 🔗 相关资源

- **models.dev 官网**: https://models.dev
- **GitHub 仓库**: https://github.com/anomalyco/models.dev
- **API 文档**: https://github.com/anomalyco/models.dev#api
- **协议**: https://github.com/anomalyco/models.dev/blob/dev/LICENSE (MIT)

---

## 📋 迁移检查清单

- [x] 更新 API URL
- [x] 修改数据获取逻辑
- [x] 保留本地覆盖机制
- [x] 重启服务
- [x] 验证所有提供商
- [x] 验证 Base URL 正确性
- [x] 验证模型数据完整性
- [x] 更新文档说明
- [x] 清理旧注释和代码

---

## 🎉 迁移完成

**状态**: ✅ 已成功迁移  
**影响**: 无破坏性变更  
**收益**: 
- 规避 AGPL 协议风险
- 数据质量和数量提升
- 维护更活跃的数据源

---

**创建时间**: 2026-08-05  
**最终状态**: ✅ 生产就绪
