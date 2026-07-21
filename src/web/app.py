"""
Bo-Distiller Web 应用工厂

create_app() 创建 FastAPI 实例：CORS 中间件、注册各 API 路由、
静态挂载（frontend/dist 存在则 SPA 挂载，否则兜底 web/templates/index.html）。
lifespan 中启动定时同步调度器与微信下载 worker，关闭时停止调度器。
"""

import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.web.routers import (
    articles,
    config,
    distill,
    knowledge,
    prompts,
    sync,
    system,
    topics,
    wechat,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动调度器与下载 worker，关闭时清理"""
    from src.config import get_config_manager
    from src.services.scheduler_service import shutdown_scheduler, start_scheduler

    # 定时同步调度器（enabled=false 时也启动，便于动态开启）
    try:
        start_scheduler()
    except Exception:
        traceback.print_exc()

    # 微信下载 worker（含崩溃恢复，不做自动扫描入队）
    try:
        if get_config_manager().load_config().wechat.enabled:
            from src.services.wechat_queue import start_worker

            start_worker()
    except Exception:
        traceback.print_exc()

    yield

    shutdown_scheduler()


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="Bo-Distiller",
        description="智能内容蒸馏工具 - Web UI",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由（顺序与原 web_ui.py 声明顺序一致，
    # articles 中 /api/articles/stats 先于 /api/articles/{article_id}，避免路径冲突）
    app.include_router(articles.router)
    app.include_router(config.router)
    app.include_router(topics.router)
    app.include_router(knowledge.router)
    app.include_router(distill.router)
    app.include_router(system.router)
    app.include_router(sync.router)
    app.include_router(wechat.router)
    app.include_router(prompts.router)

    # ==================== 前端静态文件托管 ====================

    # 优先托管 React 构建产物
    _dist_dir = Path("frontend/dist")
    if _dist_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """SPA 路由：非 API 路径全部返回 index.html"""
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API not found")
            file_path = _dist_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(_dist_dir / "index.html")
    else:
        # 回退到旧版前端
        @app.get("/", response_class=HTMLResponse)
        async def root():
            html_file = Path("web/templates/index.html")
            if html_file.exists():
                return FileResponse(html_file)
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html><head><title>Bo-Distiller</title><meta charset="utf-8"></head>
            <body style="font-family:sans-serif;max-width:600px;margin:100px auto;text-align:center">
            <h1>Bo-Distiller</h1>
            <p>前端未构建。请运行: <code>cd frontend && npm install && npm run build</code></p>
            <p>或启动开发服务器: <code>cd frontend && npm run dev</code></p>
            <p>API 文档: <a href="/docs">/docs</a></p>
            </body></html>
            """)

    return app
