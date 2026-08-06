# 并发处理批次数量配置功能

## ✅ 功能已完成

将蒸馏模式的并发处理数量添加到设置中，用户可以自定义同时处理的批次数量。

## 功能说明

### 什么是并发处理批次数量？

在知识合成阶段，Bo-Distiller 会将文章分成多个批次进行处理：
1. **批次提取**：从每批文章中提取核心观点
2. **并发处理**：同时处理多个批次以提高速度

**并发处理批次数量**控制同时处理的批次数量。

### 配置位置

**设置 → LLM 配置 → 提供商配置 → 处理参数**

```
┌─────────────────────────────────────────┐
│ 批次提取温度: [0.3]                     │
│ 整合温度: [0.2]                         │
│ 安全系数: [0.9]                         │
│ 文章截取长度: [0]                       │
│ 并发处理批次数: [3]                     │
│   同时处理的批次数量（1-10）            │
└─────────────────────────────────────────┘
```

### 参数范围

- **最小值**: 1（串行处理，最慢但最稳定）
- **最大值**: 10（并发度最高，速度最快但消耗资源多）
- **默认值**: 3（平衡速度和稳定性）
- **步长**: 1

### 效果对比

| 并发数 | 速度 | 资源消耗 | API 并发请求 | 适用场景 |
|--------|------|----------|--------------|----------|
| 1 | 慢 | 低 | 低 | API 有严格速率限制 |
| 3 | 中 | 中 | 中 | 默认配置，适合大多数场景 |
| 5 | 快 | 中高 | 高 | 有足够 API 配额 |
| 10 | 很快 | 高 | 很高 | 本地模型或无限配额 |

### 实际效果示例

假设有 30 个批次需要处理，每批次耗时 10 秒：

- **并发数 = 1**: 30 × 10 = 300 秒 (5 分钟)
- **并发数 = 3**: 30 ÷ 3 × 10 = 100 秒 (1.6 分钟)
- **并发数 = 5**: 30 ÷ 5 × 10 = 60 秒 (1 分钟)
- **并发数 = 10**: 30 ÷ 10 × 10 = 30 秒

## 实现细节

### 后端实现

#### 1. 模型定义

**文件**: `src/models.py`

```python
class ProcessingConfig(BaseModel):
    """处理参数配置"""
    max_context: int = Field(128000, description="最大上下文窗口")
    max_output: int = Field(8000, description="单次输出最大 token 数")
    reserved_tokens: int = Field(2000, description="系统提示词预留 token")
    safety_margin: float = Field(0.9, ge=0.5, le=1.0, description="安全系数")
    batch_temperature: float = Field(0.3, ge=0.0, le=1.0, description="批次提取温度")
    synthesis_temperature: float = Field(0.2, ge=0.0, le=1.0, description="知识整合温度")
    max_article_length: int = Field(0, ge=0, description="文章截取长度（0=不截断）")
    max_concurrent: int = Field(3, ge=1, le=10, description="并发处理批次数量")  # ← 新增
```

**验证规则**:
- `ge=1`: 最小值为 1
- `le=10`: 最大值为 10
- 默认值为 3

#### 2. 合成器使用

**文件**: `src/synthesizer.py`

```python
def _process_batches_concurrent(
    self,
    batches: List[List[Article]],
    topic: str,
    completed_batches: List[int],
    max_concurrent: Optional[int] = None,  # ← 参数改为可选
) -> List[str]:
    """并发处理批次"""
    # 从配置读取并发数
    if max_concurrent is None:
        config = self.config_manager.load_config()
        max_concurrent = config.processing.max_concurrent  # ← 读取配置
    
    console.print(f"[cyan]>> 并发处理模式：最多同时处理 {max_concurrent} 个批次[/cyan]\n")
    
    # 使用 asyncio.Semaphore 限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    # ...
```

**工作原理**:
- 使用 `asyncio.Semaphore(max_concurrent)` 控制并发数
- 超过限制的任务会等待，直到有空闲槽位

### 前端实现

#### 1. 表单字段

**文件**: `frontend/src/pages/settings/LLMSettings.tsx`

```tsx
<Form.Item 
  name="max_concurrent" 
  label="并发处理批次数" 
  extra="同时处理的批次数量（1-10）"
>
  <InputNumber min={1} max={10} step={1} style={{ width: 120 }} />
</Form.Item>
```

#### 2. 数据流

```typescript
// 加载配置
form.setFieldsValue({
  batch_temperature: data.config.processing.batch_temperature,
  synthesis_temperature: data.config.processing.synthesis_temperature,
  safety_margin: data.config.processing.safety_margin,
  max_concurrent: data.config.processing.max_concurrent,  // ← 读取
});

// 保存配置
const updated = {
  processing: {
    batch_temperature: values.batch_temperature,
    synthesis_temperature: values.synthesis_temperature,
    safety_margin: values.safety_margin,
    max_concurrent: values.max_concurrent,  // ← 保存
  },
};
```

## 使用场景建议

### 场景 1: API 有速率限制

**推荐配置**: `max_concurrent = 1`

```yaml
processing:
  max_concurrent: 1
```

**适用于**:
- OpenAI GPT-4（严格的 RPM/TPM 限制）
- 有速率限制的商业 API
- 免费层级 API

### 场景 2: 默认推荐

**推荐配置**: `max_concurrent = 3`

```yaml
processing:
  max_concurrent: 3
```

**适用于**:
- 大多数付费 API（如 Claude、GPT-3.5）
- 平衡速度和稳定性
- 不确定 API 限制时的安全选择

### 场景 3: 高速处理

**推荐配置**: `max_concurrent = 5-10`

```yaml
processing:
  max_concurrent: 5  # 或 10
```

**适用于**:
- 本地模型（Ollama、LM Studio）
- 企业级 API 账户
- 无速率限制或限制很高的场景

## 注意事项

### 1. API 速率限制

过高的并发数可能触发 API 速率限制：
```
Rate limit exceeded: 429 Too Many Requests
```

**解决方案**:
- 降低 `max_concurrent` 值
- 联系 API 提供商提升限额
- 使用多个 API key 轮换

### 2. 内存消耗

并发处理会增加内存占用：
- 每个批次在内存中保留文章数据
- 并发数 × 批次大小 = 总内存占用

**建议**:
- 服务器内存 < 4GB: `max_concurrent ≤ 3`
- 服务器内存 4-8GB: `max_concurrent ≤ 5`
- 服务器内存 > 8GB: `max_concurrent ≤ 10`

### 3. 网络稳定性

高并发需要稳定的网络连接：
- 并发请求多，任意一个超时都可能影响整体
- 不稳定网络建议降低并发数

## 监控和调试

### 查看并发日志

启动蒸馏任务时，会显示并发设置：

```
>> 并发处理模式：最多同时处理 3 个批次

批次 1/10 (处理中)
批次 2/10 (处理中)
批次 3/10 (处理中)
批次 1/10 (完成)
批次 4/10 (处理中)
...
```

### 性能测试

测试不同并发数的效果：

```bash
# 测试并发数 1
# 修改配置为 max_concurrent: 1
# 启动蒸馏，记录总耗时

# 测试并发数 3
# 修改配置为 max_concurrent: 3
# 启动蒸馏，记录总耗时

# 测试并发数 5
# 修改配置为 max_concurrent: 5
# 启动蒸馏，记录总耗时
```

**对比指标**:
- 总耗时
- API 错误率
- 内存峰值
- 成本（API 调用次数相同，但速度影响成本）

## 数据存储

配置存储在 MySQL 的 `settings` 表中：

```sql
SELECT JSON_EXTRACT(value, '$.processing.max_concurrent') 
FROM settings 
WHERE `key` = 'system_config';
```

**结果示例**:
```
3
```

## 相关文件

### 后端
- `src/models.py` - 配置模型定义
- `src/synthesizer.py` - 并发处理逻辑
- `src/config.py` - 配置管理

### 前端
- `frontend/src/pages/settings/LLMSettings.tsx` - 设置界面

## 总结

✅ **功能已完成**

- ✅ 后端模型添加 `max_concurrent` 字段（1-10，默认 3）
- ✅ 合成器从配置读取并发数
- ✅ 前端设置页面添加配置项
- ✅ 数据持久化到数据库
- ✅ 服务已重启生效

**使用方式**:
1. 访问 http://localhost:5173/settings
2. 进入"LLM 配置"标签页
3. 找到"处理参数"部分
4. 修改"并发处理批次数"（1-10）
5. 点击"保存配置"
6. 下次蒸馏时生效

**推荐设置**: 保持默认值 3，除非有特殊需求。
