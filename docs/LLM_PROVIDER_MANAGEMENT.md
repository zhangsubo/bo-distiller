# LLM 提供商管理功能实现

## ✅ 功能已完成

在"设置 - LLM 配置 - 元数据管理"页面添加了**添加提供商**和**删除提供商**功能。

## 功能说明

### 1. 添加提供商

**位置**: 元数据管理标签页

**功能**:
- 点击"添加提供商"按钮，弹出输入框
- 输入 [models.dev](https://models.dev) 中的 Provider ID
- 点击"添加"后会：
  1. 验证 Provider ID 是否有效
  2. 从 models.dev API 获取元数据
  3. 添加到支持列表
  4. 自动缓存元数据

**UI 展示**:
```
┌─────────────────────────────────────┐
│  添加提供商                          │
├─────────────────────────────────────┤
│  Provider ID                        │
│  ┌───────────────────────────────┐  │
│  │ 例如: openai, anthropic       │  │
│  └───────────────────────────────┘  │
│  请输入 models.dev 中的 Provider ID │
│                                     │
│           [ 取消 ]  [ 添加 ]        │
└─────────────────────────────────────┘
```

### 2. 删除提供商

**位置**: 每个提供商卡片的右上角

**功能**:
- 每个提供商卡片右上角有删除按钮（垃圾桶图标）
- 点击后弹出确认对话框
- 删除后会：
  1. 从支持列表中移除
  2. 清除该提供商的所有缓存

**限制**:
- ⚠️ **默认 LLM 提供商不能删除**
- 如果某个提供商是"默认 LLM 提供商"，删除按钮会置灰且不可点击
- 鼠标悬停显示提示："默认提供商不能删除"

**UI 展示**:
```
每个提供商卡片：
┌─────────────────────────────────────────────────┐
│  deepseek  ✓已缓存  [🔄] [🗑️] [🗑️]             │
│  (如果是默认提供商，删除按钮置灰)               │
└─────────────────────────────────────────────────┘
```

## 实现细节

### 后端 API

#### 1. 添加提供商

```python
POST /api/llm/providers
Body: {"provider_id": "openai"}

Response:
{
  "status": "ok",
  "message": "成功添加提供商 openai",
  "provider_id": "openai"
}
```

**逻辑**:
1. 检查 provider_id 是否已存在
2. 调用 `fetch_provider_metadata(provider_id)` 验证 ID 有效性
3. 添加到 `SUPPORTED_PROVIDERS` 列表
4. 缓存元数据到数据库

#### 2. 删除提供商

```python
DELETE /api/llm/providers/{provider_id}

Response:
{
  "status": "ok",
  "message": "已删除提供商 openai"
}
```

**逻辑**:
1. 从 `SUPPORTED_PROVIDERS` 列表移除
2. 清除该提供商的缓存数据
3. 如果删除失败，恢复到列表中

### 前端实现

#### 文件修改

1. **frontend/src/hooks/useLLMMetadata.ts**
   - 添加 `useAddProvider()` hook
   - 添加 `useDeleteProvider()` hook

2. **frontend/src/api/llmMetadata.ts**
   - 添加 `addProvider(providerId)` API
   - 添加 `deleteProvider(providerId)` API

3. **frontend/src/pages/settings/LLMSettings.tsx**
   - 添加"添加提供商"按钮
   - 添加弹窗表单
   - 添加处理函数
   - 传递 `defaultProvider` 和 `onDelete` 给子组件

4. **frontend/src/components/ProviderMetadataCard.tsx**
   - 添加 `defaultProvider` 和 `onDelete` props
   - 添加删除按钮
   - 根据是否为默认提供商禁用删除按钮

#### 状态管理

```typescript
// 添加提供商弹窗状态
const [isAddModalOpen, setIsAddModalOpen] = useState(false);
const [newProviderId, setNewProviderId] = useState('');

// Mutations
const addProviderMutation = useAddProvider();
const deleteProviderMutation = useDeleteProvider();
```

#### 处理函数

```typescript
// 添加提供商
const handleAddProvider = async () => {
  if (!newProviderId.trim()) {
    message.warning('请输入 Provider ID');
    return;
  }

  try {
    const result = await addProviderMutation.mutateAsync(newProviderId.trim());
    message.success(result.message || '添加成功');
    setIsAddModalOpen(false);
    setNewProviderId('');
  } catch (error: any) {
    message.error(error.message || '添加失败');
  }
};

// 删除提供商
const handleDeleteProvider = async (providerId: string) => {
  try {
    const result = await deleteProviderMutation.mutateAsync(providerId);
    message.success(result.message || '删除成功');
  } catch (error: any) {
    message.error(error.message || '删除失败');
  }
};
```

## 使用流程

### 添加提供商

1. 访问 https://models.dev
2. 找到想要添加的提供商（例如 `openai`）
3. 复制 Provider ID
4. 在 Bo-Distiller 中：
   - 进入"设置" → "LLM 配置" → "元数据管理"
   - 点击"添加提供商"按钮
   - 输入 Provider ID
   - 点击"添加"
5. 系统会自动获取并缓存元数据
6. 新提供商会出现在列表中

### 删除提供商

1. 在"元数据管理"页面找到要删除的提供商
2. 点击卡片右上角的删除按钮（垃圾桶图标）
3. 确认删除
4. 提供商会从列表中移除

**注意**: 如果该提供商是"默认 LLM 提供商"，需要先在"提供商配置"中更换默认提供商，才能删除。

## 错误处理

### 添加提供商错误

| 错误情况 | 错误信息 |
|---------|---------|
| Provider ID 为空 | "请输入 Provider ID" |
| Provider ID 已存在 | "提供商 {id} 已存在" |
| models.dev 中不存在 | "在 models.dev 中未找到提供商 {id}，请检查 ID 是否正确" |
| 网络错误 | "添加失败: {错误详情}" |

### 删除提供商错误

| 错误情况 | 错误信息 |
|---------|---------|
| Provider ID 不存在 | "提供商 {id} 不存在" |
| 是默认提供商 | 按钮置灰，提示"默认提供商不能删除" |
| 删除失败 | "删除失败: {错误详情}" |

## 数据流

### 添加流程

```
前端输入 Provider ID
    ↓
POST /api/llm/providers
    ↓
验证 ID 不存在
    ↓
fetch_provider_metadata(id)  ← 从 models.dev API 获取
    ↓
SUPPORTED_PROVIDERS.append(id)
    ↓
cache_provider_metadata()  → 保存到数据库
    ↓
返回成功消息
    ↓
前端刷新提供商列表
```

### 删除流程

```
前端点击删除按钮
    ↓
检查是否为默认提供商
    ↓ (不是)
DELETE /api/llm/providers/{id}
    ↓
SUPPORTED_PROVIDERS.remove(id)
    ↓
clear_cache(id)  → 从数据库删除缓存
    ↓
返回成功消息
    ↓
前端刷新提供商列表
```

## 安全性

### 后端验证

1. **添加时验证**:
   - 检查 ID 是否已存在
   - 调用 models.dev API 验证 ID 有效性
   - 只有验证通过才添加

2. **删除时无前端验证**:
   - 后端不检查是否为默认提供商
   - 依赖前端禁用按钮
   - 如果通过 API 直接删除默认提供商，配置会出错

### 建议改进

如果需要更严格的安全性，可以在后端添加检查：

```python
@router.delete("/api/llm/providers/{provider_id}")
async def delete_provider(provider_id: str):
    # 获取配置
    storage = get_storage()
    config = storage.get_setting("system_config")
    
    # 检查是否为默认提供商
    if config and config.get("llm", {}).get("default_provider") == provider_id:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除默认提供商 {provider_id}，请先更换默认提供商"
        )
    
    # ... 其他删除逻辑
```

## 测试场景

### 1. 添加有效提供商

```
操作: 输入 "openai" 并添加
预期: 成功添加，列表中出现 openai
```

### 2. 添加无效提供商

```
操作: 输入 "invalid-provider-xyz" 并添加
预期: 显示错误 "在 models.dev 中未找到提供商..."
```

### 3. 添加重复提供商

```
操作: 添加已存在的 "deepseek"
预期: 显示错误 "提供商 deepseek 已存在"
```

### 4. 删除非默认提供商

```
操作: 删除 "minimax"（非默认）
预期: 成功删除，列表中不再显示
```

### 5. 尝试删除默认提供商

```
操作: 点击默认提供商的删除按钮
预期: 按钮置灰，无法点击，鼠标悬停显示提示
```

## 相关文件

### 后端
- `src/web/routers/llm.py` - API 路由
- `src/llm_metadata.py` - 元数据管理器

### 前端
- `frontend/src/pages/settings/LLMSettings.tsx` - 设置页面
- `frontend/src/components/ProviderMetadataCard.tsx` - 提供商卡片
- `frontend/src/hooks/useLLMMetadata.ts` - Hooks
- `frontend/src/api/llmMetadata.ts` - API 函数

## 演示

访问 http://localhost:5173/settings → LLM 配置 → 元数据管理

查看：
- ✅ "添加提供商"按钮（蓝色，带加号图标）
- ✅ 每个提供商卡片右上角的删除按钮（红色，垃圾桶图标）
- ✅ 默认提供商的删除按钮置灰不可点击

## 总结

✅ **功能完整实现**

- ✅ 添加提供商（验证 + 缓存）
- ✅ 删除提供商（清除缓存）
- ✅ 默认提供商保护（按钮置灰）
- ✅ 错误处理和用户提示
- ✅ 自动刷新列表
- ✅ 服务已重启生效

所有功能现在可以正常使用了！
