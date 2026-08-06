# Cubox 同步超时问题修复

## 问题描述

点击"同步 Cubox"时，前端报错：`timeout of 30000ms exceeded`

## 根本原因

同步操作需要为每篇文章调用 `fetch_card_detail()`，当文章数量较多时，总耗时会远超前端设置的 30 秒超时限制。

## 解决方案

将同步操作改为**异步后台任务**：

1. **后端改动**：
   - 修改 `sync_service.py`：添加全局状态管理和后台线程执行
   - 修改 `articles.py` 路由：同步请求立即返回，实际工作在后台执行
   - 新增 `/api/articles/sync/status` 接口：查询同步进度

2. **前端改动**：
   - 新增 `getSyncStatus()` API 调用
   - 新增 `useSyncStatus()` hook：自动轮询同步状态（同步中时每 2 秒查询一次）
   - 修改 `SyncSettings.tsx`：实时显示同步进度和状态

## 用户体验改进

- ✅ 点击"立即同步"后立即收到响应，不再等待
- ✅ 实时显示同步进度（已处理/总数）
- ✅ 显示同步状态消息（初始化、正在获取文章列表等）
- ✅ 同步完成后自动刷新文章列表
- ✅ 同步期间按钮显示旋转图标和"同步中..."文字

## 技术细节

### 后端状态管理

```python
_sync_status = {
    "running": bool,         # 是否正在同步
    "progress": str,         # 进度描述
    "total": int,            # 总文章数
    "processed": int,        # 已处理数
    "error": str | None,     # 错误信息
    "last_sync_time": str,   # 最后同步时间
}
```

### 前端轮询策略

- 使用 React Query 的 `refetchInterval`
- 仅在 `running=true` 时轮询（2 秒间隔）
- 同步完成后停止轮询，避免不必要的请求

## 兼容性

- 保留 `background` 参数：定时任务可以使用 `run_sync(background=False)` 同步执行
- API 响应格式兼容旧版本

## 测试

访问 http://localhost:5173/settings，点击"立即同步"，观察：
1. 按钮立即变为"同步中..."状态
2. 页面显示进度条和状态消息
3. 同步完成后自动显示成功消息并刷新列表
