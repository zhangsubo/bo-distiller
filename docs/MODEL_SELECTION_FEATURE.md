# 模型选择功能 - 功能说明

## 📋 功能概述

**日期**: 2026-08-05  
**功能**: 在元数据管理中选择启用的模型，只有选中的模型才会在提供商配置页面显示

---

## 🎯 功能说明

### 1. 元数据管理 - 模型选择

在"元数据管理"标签页中，每个提供商卡片有"查看模型列表"按钮。

**操作流程**:
1. 点击"查看模型列表"
2. 弹出模型列表对话框，每个模型右侧有复选框
3. 勾选需要启用的模型
4. 点击"保存选择"按钮

**界面元素**:
- ✅ **全选复选框**: 快速全选/取消全选所有模型
- ✅ **选择计数**: 显示已选择数量，如 "全选 (3/4)"
- ✅ **提示说明**: 说明勾选的模型将在配置页面显示
- ✅ **保存按钮**: 保存当前选择（有更改时才启用）
- ✅ **关闭按钮**: 取消操作

### 2. 提供商配置 - 模型下拉菜单

在"提供商配置"标签页中，模型字段现在只显示已启用的模型。

**行为**:
- 默认显示所有模型（如果未配置 enabled_models）
- 保存模型选择后，只显示已启用的模型
- 自动过滤掉未启用的模型

---

## 🔧 技术实现

### 1. 数据结构

#### LLMProvider 类型扩展

```typescript
export interface LLMProvider {
  api_key: string;
  api_base: string;
  model: string;
  max_context: number;
  max_output: number;
  enabled_models?: string[]; // 新增：用户启用的模型 ID 列表
}
```

### 2. 组件修改

#### ProviderMetadataCard 组件

**新增状态**:
```typescript
const [selectedModels, setSelectedModels] = useState<string[]>([]);
const [hasChanges, setHasChanges] = useState(false);
```

**核心功能**:

1. **加载已保存的选择**
```typescript
useEffect(() => {
  if (showModels && configData?.config) {
    const providerConfig = configData.config.llm.providers[providerId];
    const enabledModels = providerConfig?.enabled_models || [];

    // 如果没有保存过，默认全选
    if (enabledModels.length === 0 && metadata?.models) {
      setSelectedModels(Object.keys(metadata.models));
    } else {
      setSelectedModels(enabledModels);
    }
  }
}, [showModels, configData, providerId, metadata]);
```

2. **保存模型选择**
```typescript
const handleSaveEnabledModels = async () => {
  const updatedConfig = {
    ...configData.config,
    llm: {
      ...configData.config.llm,
      providers: {
        ...configData.config.llm.providers,
        [providerId]: {
          ...configData.config.llm.providers[providerId],
          enabled_models: selectedModels,
        },
      },
    },
  };

  await saveMutation.mutateAsync(updatedConfig);
};
```

#### ProviderConfigCard 组件

**过滤启用的模型**:
```typescript
const getModelOptions = () => {
  if (!metadata?.models) return [];

  const models = metadata.models as Record<string, any>;
  const providerConfig = configData?.config?.llm?.providers?.[providerId];
  const enabledModels = providerConfig?.enabled_models;

  // 如果没有配置 enabled_models，默认显示所有模型
  const modelIds = enabledModels && enabledModels.length > 0
    ? enabledModels
    : Object.keys(models);

  return modelIds
    .filter((modelId) => models[modelId])
    .map((modelId) => ({
      label: models[modelId]?.name || modelId,
      value: modelId,
    }));
};
```

---

## 📸 界面预览

### 元数据管理 - 模型列表对话框

```
┌─────────────────────────────────────────────────────┐
│ DeepSeek - 支持的模型                        [×]     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ℹ️ 模型启用说明                                      │
│ 勾选的模型将在「提供商配置」页面中显示为可选项。         │
│ 至少需要选择一个模型。                               │
│                                                     │
│ ☑️ 全选 (4/4)                                       │
│                                                     │
│ ┌─────────────────────────────────────────┬──────┐ │
│ │ DeepSeek V4 Flash                       │ ☑️   │ │
│ │ 上下文: 1,000,000  最大输出: 384,000     │      │ │
│ ├─────────────────────────────────────────┼──────┤ │
│ │ DeepSeek V4 Pro                         │ ☑️   │ │
│ │ 上下文: 1,000,000  最大输出: 384,000     │      │ │
│ ├─────────────────────────────────────────┼──────┤ │
│ │ DeepSeek Chat                           │ ☑️   │ │
│ │ 上下文: 64,000  最大输出: 8,000          │      │ │
│ ├─────────────────────────────────────────┼──────┤ │
│ │ DeepSeek Reasoner                       │ ☐   │ │
│ │ 上下文: 64,000  最大输出: 8,000          │      │ │
│ └─────────────────────────────────────────┴──────┘ │
│                                                     │
│                       [关闭]  [💾 保存选择]          │
└─────────────────────────────────────────────────────┘
```

### 提供商配置 - 模型下拉菜单

```
┌─────────────────────────────────────┐
│ DeepSeek                            │
├─────────────────────────────────────┤
│ API Key: ************************** │
│ Base URL: https://api.deepseek.com │
│                                     │
│ 模型: [DeepSeek V4 Flash      ▼]   │
│       ├─ DeepSeek V4 Flash         │
│       ├─ DeepSeek V4 Pro           │ (只显示已启用的 3 个)
│       └─ DeepSeek Chat             │
│                                     │
│ 上下文窗口: 1000000                 │
│ 最大输出: 384000                    │
└─────────────────────────────────────┘
```

---

## 🎬 使用场景

### 场景 1: 首次使用（未配置）

1. 打开元数据管理 → 查看模型列表
2. **默认全选**所有模型
3. 保存后，配置页面显示所有模型

### 场景 2: 筛选常用模型

1. 打开元数据管理 → 查看模型列表
2. **取消勾选**不常用的模型
3. 只保留常用的 2-3 个模型
4. 保存后，配置页面只显示选中的模型
5. **优势**: 下拉菜单更简洁，减少误选

### 场景 3: 临时启用某个模型

1. 打开元数据管理 → 查看模型列表
2. 勾选之前禁用的模型
3. 保存
4. 返回配置页面，现在可以选择该模型

---

## ✅ 功能特性

### 用户友好

- ✅ **默认全选**: 首次使用时不需要额外操作
- ✅ **全选/取消全选**: 快速操作
- ✅ **选择计数**: 清楚显示已选数量
- ✅ **提示说明**: 明确功能作用
- ✅ **有改动才启用保存**: 避免无效操作

### 数据安全

- ✅ **至少选择一个**: 保存时验证，避免全部禁用
- ✅ **自动过滤**: 配置页面自动过滤不存在的模型 ID
- ✅ **默认降级**: 如果 enabled_models 为空，显示所有模型

### 实时响应

- ✅ **保存后立即生效**: 无需刷新页面
- ✅ **跨页面同步**: 配置页面自动更新可选模型
- ✅ **状态提示**: 保存成功/失败的明确反馈

---

## 🔄 工作流程

```
用户操作流程:
  1. 元数据管理 → 查看模型列表
        ↓
  2. 勾选/取消勾选模型
        ↓
  3. 点击"保存选择"
        ↓
  4. 保存到配置文件 (enabled_models 字段)
        ↓
  5. 返回提供商配置页面
        ↓
  6. 模型下拉菜单只显示已启用的模型

数据流:
  ProviderMetadataCard (元数据管理)
        ↓ (保存 enabled_models)
  AppConfig (配置文件)
        ↓ (读取 enabled_models)
  ProviderConfigCard (提供商配置)
        ↓ (过滤模型列表)
  Select 下拉菜单 (只显示启用的)
```

---

## 🧪 测试指南

### 测试步骤

**步骤 1: 验证默认行为（首次使用）**

1. 访问: http://localhost:5173 → 设置 → LLM 设置
2. 切换到"元数据管理"标签
3. 点击 deepseek 的"查看模型列表"
4. ✅ 应该看到所有模型都被勾选（默认全选）
5. ✅ 显示计数，如 "全选 (4/4)"

**步骤 2: 测试模型选择**

1. 取消勾选一个模型（如 DeepSeek Reasoner）
2. ✅ 计数变为 "全选 (3/4)"
3. ✅ "保存选择"按钮变为可用
4. 点击"保存选择"
5. ✅ 显示成功提示

**步骤 3: 验证配置页面**

1. 切换到"提供商配置"标签
2. 找到 deepseek 配置卡片
3. 点击"模型"下拉菜单
4. ✅ 只显示 3 个模型（DeepSeek Reasoner 不显示）
5. ✅ 可以正常选择模型

**步骤 4: 测试全选/取消全选**

1. 返回"元数据管理" → 查看模型列表
2. 点击"全选"复选框（取消全选）
3. ✅ 所有模型都被取消勾选
4. 尝试保存
5. ✅ 显示警告: "至少需要选择一个模型"
6. 重新勾选几个模型，保存成功

**步骤 5: 测试跨提供商**

1. 对 xiaomi、minimax 等其他提供商重复上述操作
2. ✅ 每个提供商独立保存选择
3. ✅ 不同提供商的选择互不影响

---

## 📊 数据示例

### 配置文件结构

```json
{
  "llm": {
    "providers": {
      "deepseek": {
        "api_key": "sk-xxx",
        "api_base": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "max_context": 1000000,
        "max_output": 384000,
        "enabled_models": [
          "deepseek-v4-flash",
          "deepseek-v4-pro",
          "deepseek-chat"
        ]
      },
      "xiaomi": {
        "api_key": "sk-yyy",
        "api_base": "https://api.xiaomimimo.com/v1",
        "model": "gemma-3-9b",
        "max_context": 8000,
        "max_output": 2000,
        "enabled_models": [
          "gemma-3-9b",
          "llama-3.3-70b"
        ]
      }
    }
  }
}
```

---

## 🎯 优势总结

### 用户体验

- ✅ **简化选择**: 配置页面只显示需要的模型
- ✅ **避免误选**: 不常用模型不会出现在列表中
- ✅ **灵活管理**: 随时调整启用的模型

### 维护性

- ✅ **集中管理**: 在元数据管理统一管理模型
- ✅ **数据持久化**: 选择保存到配置文件
- ✅ **向后兼容**: 未配置时默认显示所有模型

### 扩展性

- ✅ **支持所有提供商**: 通用的实现方式
- ✅ **独立配置**: 每个提供商独立管理
- ✅ **易于扩展**: 可添加更多筛选条件

---

## 🔧 故障排除

### 问题 1: 保存后模型列表不更新

**原因**: 前端缓存未刷新

**解决**:
1. 刷新浏览器页面
2. 或清除前端缓存（React Query 会自动重新获取）

### 问题 2: 无法保存选择

**检查**:
1. 是否至少选择了一个模型
2. 检查浏览器控制台是否有错误
3. 检查后端日志

### 问题 3: 配置页面仍显示所有模型

**原因**: enabled_models 未正确保存

**解决**:
1. 重新保存模型选择
2. 检查配置文件是否有 enabled_models 字段
3. 刷新配置页面

---

## 📝 相关文档

- `LLM_CONFIG_IMPROVEMENTS.md` - LLM 配置改进总览
- `LLM_CONFIG_TEST_GUIDE.md` - 完整测试指南
- `FINAL_WORK_SUMMARY.md` - 最终工作总结

---

**创建时间**: 2026-08-05  
**状态**: ✅ 开发完成，等待测试
