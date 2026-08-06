# 启动问题排查与修复记录

## 遇到的问题

### 问题 1: 后端启动失败
**错误信息**: 
```
✗ 后端启动失败，请查看日志
```

**根本原因**:
1. 端口 8000 被旧进程占用
2. 数据库 settings 表中的配置数据损坏
3. JSON 解析错误导致配置加载失败

**解决方案**:
```bash
# 1. 清理占用端口的进程
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# 2. 清理损坏的配置数据
sqlite3 data/distiller.db "DELETE FROM settings WHERE key='system_config';"

# 3. 重启服务，配置会从 config.yaml 重新迁移
./dev.sh restart
```

---

### 问题 2: 前端白屏 - 配置读取错误
**错误信息**:
```
Uncaught TypeError: Cannot read properties of undefined (reading 'default_provider')
```

**根本原因**:
API `/api/config` 返回的配置是 JSON 字符串而不是对象，前端期望对象格式。

**排查过程**:
```bash
# 检查 API 返回
curl http://127.0.0.1:8000/api/config | jq '.config | type'
# 返回: "string"  ← 错误！应该是 "object"
```

**解决方案**:
修改 `src/web/routers/config.py`，确保返回对象：

```python
@router.get("/api/config")
async def get_config():
    storage = get_storage()
    config = storage.get_setting("system_config")
    if config is None:
        config_manager = get_config_manager()
        config_manager.load_config()
        config = storage.get_setting("system_config") or {}

    # 确保返回的是对象而不是字符串
    if isinstance(config, str):
        import json
        config = json.loads(config)

    return {"config": config, "status": "ok"}
```

---

### 问题 3: LLM 元数据 API 500 错误
**错误信息**:
```
GET /api/llm/providers/xiaomi-token-plan-cn/metadata 500 (Internal Server Error)
{"detail":"'str' object has no attribute 'get'"}
```

**根本原因**:
`storage.get_setting()` 有时返回 JSON 字符串而不是解析后的字典对象，导致代码尝试调用 `.get()` 方法时失败。

**排查过程**:
```bash
# 测试 API
curl "http://127.0.0.1:8000/api/llm/providers/xiaomi-token-plan-cn/metadata?force_refresh=false"
# 返回: {"detail":"'str' object has no attribute 'get'"}
```

**解决方案**:
修改 `src/llm_metadata.py`，在两个缓存读取方法中添加类型检查和转换：

```python
def get_cached_provider_metadata(self, provider_id: str) -> Optional[Dict]:
    cache_key = self._get_cache_key(provider_id, "metadata")
    cached_data = self.storage.get_setting(cache_key)

    # 确保 cached_data 是字典而不是字符串
    if isinstance(cached_data, str):
        import json
        try:
            cached_data = json.loads(cached_data)
        except:
            return None

    if self._is_cache_valid(cached_data):
        return cached_data.get("data")

    return None

def get_cached_provider_models(self, provider_id: str) -> Optional[List[Dict]]:
    cache_key = self._get_cache_key(provider_id, "models")
    cached_data = self.storage.get_setting(cache_key)

    # 确保 cached_data 是字典而不是字符串
    if isinstance(cached_data, str):
        import json
        try:
            cached_data = json.loads(cached_data)
        except:
            return None

    if self._is_cache_valid(cached_data):
        return cached_data.get("data")

    return None
```

---

## 根本原因分析

### 为什么会出现字符串/对象混淆？

**问题根源**: SQLite 的 `TEXT` 类型存储和 Python 的 JSON 处理之间的不一致。

1. **数据库存储**: `settings` 表的 `value` 字段是 `TEXT` 类型，存储 JSON 字符串
2. **读取逻辑**: `storage.get_setting()` 使用 `json.loads()` 解析返回值
3. **不一致**: 但在某些情况下（可能是旧数据或错误写入），`value` 被二次 JSON 编码

**示例**:
```python
# 正常情况
value = '{"key": "value"}'  # 数据库中
json.loads(value)  # → {"key": "value"}  ✓

# 异常情况（二次编码）
value = '"{\"key\": \"value\"}"'  # 数据库中被二次编码
json.loads(value)  # → '{"key": "value"}'  ✗ 返回字符串而不是对象
```

---

## 预防措施

### 1. 统一数据访问层
所有从 `storage.get_setting()` 读取的地方都应该验证返回类型：

```python
def safe_get_setting(key: str) -> Optional[Dict]:
    """安全地读取设置，确保返回字典"""
    data = storage.get_setting(key)
    
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return None
    
    return data if isinstance(data, dict) else None
```

### 2. 数据库写入规范
确保写入时只进行一次 JSON 编码：

```python
# ✓ 正确
storage.set_setting("key", {"data": "value"})

# ✗ 错误
storage.set_setting("key", json.dumps({"data": "value"}))
```

### 3. 测试覆盖
添加单元测试确保数据读写一致性：

```python
def test_setting_roundtrip():
    test_data = {"nested": {"key": "value"}}
    storage.set_setting("test_key", test_data)
    result = storage.get_setting("test_key")
    assert isinstance(result, dict)
    assert result == test_data
```

---

## 验证清单

运行以下命令验证所有问题已解决：

```bash
# 1. 检查配置 API
curl http://127.0.0.1:8000/api/config | jq '.config | type'
# 应返回: "object"

# 2. 检查 LLM 元数据 API
curl "http://127.0.0.1:8000/api/llm/providers/deepseek/metadata?force_refresh=false" | jq '.status'
# 应返回: "ok"

# 3. 检查缓存统计 API
curl http://127.0.0.1:8000/api/llm/cache/stats | jq '.status'
# 应返回: "ok"

# 4. 检查后端日志无错误
tail -50 logs/backend.log | grep -E "ERROR|500"
# 应该没有输出

# 5. 访问前端
open http://localhost:5173/settings
# 应该正常显示，没有白屏
```

---

## 当前状态

✅ **所有问题已解决**

- ✅ 后端正常启动
- ✅ 前端正常显示
- ✅ 配置 API 返回正确格式
- ✅ LLM 元数据 API 正常工作
- ✅ 无 500 错误

**服务地址**:
- 前端: http://localhost:5173
- 后端: http://127.0.0.1:8000
- API 文档: http://127.0.0.1:8000/docs

---

## 经验总结

1. **类型一致性很重要**: JSON 序列化/反序列化必须保持一致
2. **防御性编程**: 对外部数据源返回值进行类型检查
3. **日志很关键**: 详细的错误日志帮助快速定位问题
4. **测试环境清理**: 开发过程中定期清理旧进程和损坏数据
5. **数据库迁移要小心**: 修改存储逻辑时注意向后兼容性
