# LLM 配置改进 - 元数据集成

## 📋 修改概述

**日期**: 2026-08-05  
**状态**: ✅ 已完成

---

## 🎯 改进目标

1. **元数据来源更新**: 使用 models.dev（MIT License）
2. **缓存时长优化**: 从 24 小时延长至 30 天
3. **Base URL 自动填充**: 从元数据缓存自动获取
4. **上下文窗口/最大输出自动填充**: 从元数据获取，可手动修改
5. **模型下拉选择**: 从元数据动态获取模型列表

---

## 🔧 具体修改

### 1. 后端修改

#### 文件: `src/llm_metadata.py`

**修改 1: 更新元数据来源**
```python
# 旧版
LLM_METADATA_BASE_URL = "https://basellm.github.io/llm-metadata/api/providers"

# 新版
LLM_METADATA_API_URL = "https://models.dev/api.json"
```

**修改 2: 延长缓存时间**
```python
# 旧版
self.cache_duration = timedelta(hours=24)  # 24 小时

# 新版
self.cache_duration = timedelta(days=30)  # 30 天（1 个月）
```

**修改 3: 调整数据获取逻辑**
```python
# 新版: 一次获取所有提供商数据
async def fetch_provider_metadata(self, provider_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(LLM_METADATA_API_URL, timeout=10) as response:
            data = await response.json()
            return data.get(provider_id)  # 从字典中提取
```

---

### 2. 前端修改

#### 新增文件: `frontend/src/components/ProviderConfigCard.tsx`

**功能**: 智能提供商配置卡片

**特性**:
1. 自动从元数据获取 Base URL
2. 自动填充上下文窗口和最大输出
3. 模型下拉选择（从元数据获取）
4. 选择模型后自动更新上下文窗口和最大输出
5. 所有自动填充的值都可手动修改

**核心逻辑**:
```typescript
// 加载元数据
const { data: metadata, isLoading } = useProviderMetadata(providerId);

// 自动填充默认值（仅在字段为空时）
useEffect(() => {
  if (metadata?.base_url && !currentValues.api_base) {
    form.setFieldValue(['providers', providerId, 'api_base'], metadata.base_url);
  }
  // 类似地处理其他字段...
}, [metadata]);

// 模型切换时更新参数
const handleModelChange = (modelId: string) => {
  const model = metadata.models[modelId];
  if (model?.limit) {
    form.setFieldValue(['providers', providerId, 'max_context'], model.limit.context);
    form.setFieldValue(['providers', providerId, 'max_output'], model.limit.output);
  }
};
```

#### 修改文件: `frontend/src/pages/settings/LLMSettings.tsx`

**修改内容**:
1. 导入新组件 `ProviderConfigCard`
2. 替换原有的配置表单
3. 更新元数据来源说明

```typescript
// 旧版: 手动输入所有字段
{LLM_MODELS.map((model) => (
  <Card key={model}>
    <Input /> {/* API Key */}
    <Input /> {/* Base URL */}
    <Input /> {/* 模型名 */}
    <InputNumber /> {/* 上下文窗口 */}
    <InputNumber /> {/* 最大输出 */}
  </Card>
))}

// 新版: 使用智能配置卡片
{LLM_MODELS.map((model) => (
  <ProviderConfigCard
    key={model}
    providerId={model}
    providerName={model}
  />
))}
```

---

## 🎨 用户体验改进

### 配置流程对比

**旧版流程**:
1. 手动输入 API Key ❌
2. 手动输入 Base URL ❌
3. 手动输入模型名 ❌
4. 手动输入上下文窗口 ❌
5. 手动输入最大输出 ❌

**新版流程**:
1. 输入 API Key ✅（必填）
2. Base URL 自动填充 ✅（可修改）
3. 从下拉菜单选择模型 ✅（清晰明了）
4. 上下文窗口自动填充 ✅（可修改）
5. 最大输出自动填充 ✅（可修改）

### 新增功能

1. **模型下拉菜单**:
   - 显示模型的完整名称（如 "DeepSeek V4 Flash"）
   - 支持搜索过滤
   - 自动获取最新模型列表

2. **智能默认值**:
   - 选择不同模型时，自动更新对应的上下文窗口和最大输出
   - 减少配置错误

3. **元数据状态提示**:
   - 加载中显示 Spin
   - 加载失败显示警告
   - 提示数据来源

---

## 📊 数据流

```
用户打开配置页面
    ↓
前端请求元数据 (useProviderMetadata)
    ↓
检查前端缓存（React Query, 1 小时）
    ↓ (未命中)
请求后端 API (/api/llm/providers/{id}/metadata)
    ↓
检查后端缓存（30 天）
    ↓ (未命中)
请求 models.dev API
    ↓
返回元数据 → 缓存 30 天
    ↓
前端自动填充表单字段
    ↓
用户可以修改任何字段
    ↓
保存配置
```

---

## ✅ 验证清单

### 后端验证
- [x] 缓存时长已更新为 30 天
- [x] API 来源已切换到 models.dev
- [x] 所有提供商元数据可正常获取
- [x] Base URL 正确（包括 minimax 的本地修正）

### 前端验证
- [x] ProviderConfigCard 组件创建成功
- [x] TypeScript 编译通过
- [x] 构建成功
- [x] 服务启动正常

### 功能验证（需手动测试）
- [ ] 打开 LLM 设置页面
- [ ] 查看提供商配置
- [ ] Base URL 自动填充
- [ ] 模型下拉菜单显示正确
- [ ] 选择模型后参数自动更新
- [ ] 可以手动修改所有字段
- [ ] 保存配置成功

---

## 🎯 优势总结

### 1. 协议安全
- ✅ MIT License（无传染性）
- ✅ 可商用
- ✅ 无 AGPL 风险

### 2. 数据质量
- ✅ 180+ 提供商
- ✅ 数据更详细（reasoning、tool_call 等）
- ✅ 持续维护更新

### 3. 用户体验
- ✅ 减少 80% 的手动输入
- ✅ 避免配置错误
- ✅ 模型选择更直观

### 4. 维护性
- ✅ 30 天缓存减少 API 请求
- ✅ 统一数据来源
- ✅ 自动同步最新数据

---

## 📝 使用指南

### 配置新提供商

1. **访问设置页面**
   - 导航：设置 → LLM 设置 → 提供商配置

2. **配置步骤**
   - 输入 API Key
   - Base URL 自动填充（如需要可修改）
   - 从下拉菜单选择模型
   - 上下文窗口和最大输出自动填充（如需要可修改）
   - 点击"保存配置"

3. **更新元数据**
   - 切换到"元数据管理"标签
   - 点击"刷新所有"更新元数据缓存
   - 返回"提供商配置"查看最新数据

---

## 🔧 技术细节

### React Query 缓存策略

```typescript
useProviderMetadata(providerId, {
  staleTime: 1000 * 60 * 60,  // 前端缓存 1 小时
  cacheTime: 1000 * 60 * 60 * 24,  // 保留 24 小时
})
```

### 表单默认值设置策略

```typescript
// 只在字段为空时设置默认值
if (!currentValues.api_base) {
  form.setFieldValue(['providers', providerId, 'api_base'], metadata.base_url);
}
```

这样确保：
- 首次加载时自动填充
- 用户修改后不会被覆盖
- 刷新元数据后可以看到新值（如果用户没改）

---

## 📋 待优化项（可选）

### 功能增强
- [ ] 添加"恢复默认值"按钮
- [ ] 显示模型的详细信息（reasoning、tool_call 等）
- [ ] 批量配置多个提供商
- [ ] 导入/导出配置

### 性能优化
- [ ] 批量加载所有提供商元数据（减少请求数）
- [ ] 预加载常用提供商的元数据

### 用户体验
- [ ] 添加配置向导
- [ ] 提供配置模板
- [ ] 配置验证（测试连接）

---

## 📚 相关文档

- `MIGRATE_TO_MODELS_DEV.md` - 数据源迁移文档
- `BASE_URL_FIX.md` - Base URL 修复文档
- `QUICK_TEST_GUIDE.md` - 快速测试指南

---

**创建时间**: 2026-08-05  
**最终状态**: ✅ 已完成，待测试
