# LLM 改进快速开始指南

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要新增依赖：
- `aiohttp>=3.9.0` - 异步 HTTP 支持
- `tiktoken>=0.5.0` - Token 计数（已存在）

### 2. 验证安装

```bash
# 语法检查
python3 -c "import ast; ast.parse(open('src/llm_client.py').read()); print('✓ OK')"

# 如果虚拟环境已配置
source venv/bin/activate
python scripts/test_llm_improvements.py
```

### 3. 使用新功能

#### 方式 1: 异步批量调用（推荐）

```python
import asyncio
from src.llm_client import get_llm_client

async def main():
    client = get_llm_client()
    
    # 准备请求
    requests = [
        {
            "messages": [{"role": "user", "content": f"问题 {i}"}],
            "temperature": 0.3,
            "max_tokens": 100,
        }
        for i in range(10)
    ]
    
    # 异步并发处理（3个并发）
    results = await client.batch_chat_async(
        requests,
        max_concurrent=3,
        retry_count=3,
    )
    
    print(f"✓ 完成 {len(results)} 个请求")

# 运行
asyncio.run(main())
```

#### 方式 2: 同步调用（向后兼容）

```python
from src.llm_client import get_llm_client

client = get_llm_client()

# 单次调用
result = client.chat(
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.3,
    max_tokens=100,
)

# 批量调用（串行）
requests = [...]
results = client.batch_chat(requests)
```

#### 方式 3: 启用请求缓存

```python
from src.llm_client import get_llm_client

# 启用缓存（默认开启）
client = get_llm_client(enable_cache=True)

# 第一次调用
result1 = client.chat(messages)  # 调用 API

# 第二次相同调用
result2 = client.chat(messages)  # 从缓存返回（极快）

# 查看缓存状态
print(client.get_cache_stats())  # {'size': 1, 'enabled': True}

# 清除缓存
client.clear_cache()
```

### 4. 使用新的任务管理

#### 启动 Web 服务

```bash
# 使用新的启动脚本
./dev.sh start

# 查看服务状态
./dev.sh status

# 停止服务
./dev.sh stop
```

#### API 使用

```bash
# 启动蒸馏任务
curl -X POST http://localhost:8000/api/distill/start \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek", "incremental": true}'

# 查看任务状态
curl http://localhost:8000/api/distill/status

# 获取任务日志（分页）
curl "http://localhost:8000/api/distill/logs?offset=0&limit=50"

# 停止任务
curl -X POST http://localhost:8000/api/distill/stop
```

#### 实时日志流（SSE）

```javascript
// 前端代码
const eventSource = new EventSource('/api/distill/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.log) {
    console.log('日志:', data.log);
  }
  
  if (data.done) {
    console.log('任务完成:', data.status);
    eventSource.close();
  }
};
```

---

## 📊 性能对比示例

### 串行 vs 并发

```python
import time
import asyncio
from src.llm_client import get_llm_client

client = get_llm_client()
requests = [{"messages": [...]} for _ in range(10)]

# 串行（旧方法）
start = time.time()
results1 = client.batch_chat(requests)
print(f"串行: {time.time() - start:.2f}秒")  # ~100秒

# 并发（新方法）
start = time.time()
results2 = await client.batch_chat_async(requests, max_concurrent=3)
print(f"并发: {time.time() - start:.2f}秒")  # ~25秒

print(f"加速: {100/25:.1f}x")  # 4x
```

---

## 🔧 常见问题

### Q1: 导入错误 "ModuleNotFoundError: No module named 'rich'"

**解决方案**：
```bash
pip install -r requirements.txt
```

### Q2: 如何调整并发数？

**答案**：根据提供商的速率限制调整：
- DeepSeek: 3-5
- OpenAI: 10-20
- MiniMax: 5-10

```python
results = await client.batch_chat_async(
    requests,
    max_concurrent=3,  # 调整这里
)
```

### Q3: 任务管理器如何获取详细日志？

**答案**：
```python
from src.web.tasks import get_task_manager

manager = get_task_manager()
task = manager.get_current_task()

if task:
    # 获取所有日志
    logs = task.logs
    
    # 获取进度信息
    progress = task.get_progress()
    print(progress)
```

### Q4: 如何禁用请求缓存？

**答案**：
```python
client = get_llm_client(enable_cache=False)
```

---

## 📚 更多文档

- [完整改进文档](./docs/LLM_IMPROVEMENTS.md)
- [改进总结](./IMPROVEMENTS_SUMMARY.md)
- [测试脚本](./scripts/test_llm_improvements.py)

---

## ✅ 检查清单

改进完成后，确认以下内容：

- [ ] 依赖已安装 (`pip install -r requirements.txt`)
- [ ] 语法检查通过
- [ ] Web 服务可以启动 (`./dev.sh start`)
- [ ] API 端点可以访问
- [ ] 理解了异步调用的使用方法
- [ ] 查看了完整文档

---

**提示**：所有改进都是向后兼容的，现有代码无需修改即可继续使用！
