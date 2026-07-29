# Bo-Distiller Web UI 使用指南

## 功能概述

Web UI 提供了友好的界面来管理 Bo-Distiller，包括：

1. **配置管理** - 查看和编辑系统配置
2. **内容源管理** - 管理 Cubox 和本地 Markdown 源
3. **知识库浏览** - 查看生成的知识文档（Markdown 渲染）
4. **状态监控** - 查看系统运行状态

## 安装依赖

```bash
pip install fastapi uvicorn
```

## 启动 Web UI

### 方式 1：直接运行

```bash
python web_ui.py
```

### 方式 2：通过 CLI

```bash
python distill.py serve
```

启动后访问：http://127.0.0.1:8000

## API 文档

访问 http://127.0.0.1:8000/docs 查看完整的 API 文档（FastAPI 自动生成）

## 技术栈

- **后端**：FastAPI + Uvicorn
- **前端**：Vue 3 + Marked.js（Markdown 渲染）
- **样式**：原生 CSS

## 开发说明

### 添加新的 API 端点

编辑 `web_ui.py`，按照 FastAPI 规范添加路由：

```python
@app.get("/api/your-endpoint")
async def your_endpoint():
    return {"data": "your data"}
```

### 修改前端

编辑 `web/templates/index.html`，在 Vue 实例中添加方法和数据。

## 功能状态

- ✅ 配置查看/编辑
- ✅ 内容源列表
- ✅ 知识库浏览（Markdown 渲染）
- ✅ 状态监控
- 🚧 LLM 连接测试（待实现）
- 🚧 内容同步触发（待实现）

## 安全提示

Web UI 默认只监听 127.0.0.1（本地），不对外开放。
如需远程访问，请配置适当的认证和 HTTPS。
