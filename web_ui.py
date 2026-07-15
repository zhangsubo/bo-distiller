#!/usr/bin/env python3
"""
Bo-Distiller Web UI

提供 Web 界面查看配置和生成的内容
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Bo-Distiller",
    description="智能内容蒸馏工具 - Web UI",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_storage():
    """延迟导入 SQLiteStorage"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from src.storage import get_storage
    return get_storage()


def _article_to_dict(article) -> dict:
    """Article 对象转 dict"""
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "url": article.url,
        "source_type": article.source.type.value if hasattr(article.source.type, 'value') else str(article.source.type),
        "source_name": article.source.name,
        "source_identifier": article.source.identifier,
        "author": article.author,
        "published_date": article.published_date.isoformat() if article.published_date else None,
        "fetched_date": article.fetched_date.isoformat() if article.fetched_date else None,
        "metadata": article.metadata,
    }


# ==================== 文章 API ====================

@app.get("/api/articles")
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    source_type: Optional[str] = None,
):
    """分页文章列表"""
    try:
        storage = _get_storage()
        offset = (page - 1) * page_size

        if search:
            all_articles = storage.search_articles(search)
            total = len(all_articles)
            articles = all_articles[offset:offset + page_size]
        elif source_type:
            all_articles = storage.get_articles_by_source(source_type)
            total = len(all_articles)
            articles = all_articles[offset:offset + page_size]
        else:
            total = storage.get_article_count()
            articles = storage.get_all_articles(limit=page_size, offset=offset)

        return {
            "data": [_article_to_dict(a) for a in articles],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/articles/stats")
async def get_article_stats():
    """文章统计"""
    try:
        storage = _get_storage()
        stats = storage.get_stats()
        return {"data": stats}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/articles/{article_id}")
async def get_article(article_id: str):
    """获取单篇文章"""
    storage = _get_storage()
    article = storage.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"data": _article_to_dict(article)}


@app.delete("/api/articles/{article_id}")
async def delete_article(article_id: str):
    """删除文章"""
    storage = _get_storage()
    success = storage.delete_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"status": "ok"}


# ==================== Cubox 同步 API ====================

@app.post("/api/articles/sync")
async def sync_cubox():
    """同步 Cubox 收藏"""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from src.adapters.cubox_adapter import CuboxAdapter
        from src.models import SourceConfig

        adapter = CuboxAdapter(use_sqlite=True)
        source_config = SourceConfig(
            type="cubox",
            name="Cubox 收藏",
            identifier="cubox-cli",
            enabled=True,
        )

        if not adapter.validate(source_config):
            raise HTTPException(status_code=400, detail="Cubox CLI 不可用")

        articles = adapter.fetch(source_config)
        return {
            "status": "ok",
            "message": f"同步完成，获取 {len(articles)} 篇文章",
            "count": len(articles),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 配置 API ====================

@app.get("/api/config")
async def get_config():
    """获取配置"""
    config_file = Path("config.yaml")
    if not config_file.exists():
        config_file = Path("config.example.yaml")
    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return {"config": config, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
async def update_config(config: dict):
    """更新配置"""
    try:
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
        return {"status": "ok", "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 内容源 API ====================

@app.get("/api/sources")
async def get_sources():
    """获取内容源列表"""
    sources_file = Path("sources.yaml")
    if not sources_file.exists():
        return {"sources": []}
    try:
        with open(sources_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {"sources": data.get("sources", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sources")
async def save_sources(body: dict):
    """保存内容源列表（全量替换）"""
    sources_file = Path("sources.yaml")
    try:
        data = {"sources": body.get("sources", [])}
        with open(sources_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 主题配置 API ====================

@app.get("/api/topics/config")
async def get_topics_config():
    """获取 topics.yaml 配置"""
    topics_file = Path("topics.yaml")
    if not topics_file.exists():
        return {"config": {}}
    try:
        with open(topics_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {"config": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/topics/config")
async def save_topics_config(config: dict):
    """保存 topics.yaml 配置"""
    try:
        with open("topics.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 知识库 API ====================

@app.get("/api/knowledge")
async def get_knowledge_list():
    """获取知识库文档列表"""
    output_dir = Path("output")
    if not output_dir.exists():
        return {"documents": []}

    documents = []
    for md_file in sorted(output_dir.glob("*.md")):
        if md_file.name == "INDEX.md":
            continue
        stat = md_file.stat()
        # 从第一行提取标题
        title = md_file.stem
        try:
            with open(md_file, encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line.startswith("# "):
                    title = first_line[2:]
        except Exception:
            pass

        documents.append({
            "name": md_file.stem,
            "title": title,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return {"documents": documents}


@app.get("/api/knowledge/search")
async def search_knowledge(q: str = Query(..., min_length=1)):
    """搜索知识库"""
    output_dir = Path("output")
    if not output_dir.exists():
        return {"results": []}

    results = []
    for md_file in output_dir.glob("*.md"):
        try:
            with open(md_file, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if q.lower() in content.lower():
            title = md_file.stem
            lines = content.split("\n")
            snippet = ""
            for line in lines:
                if q.lower() in line.lower():
                    snippet = line.strip()[:200]
                    break
            results.append({
                "name": md_file.stem,
                "title": title,
                "snippet": snippet,
            })

    return {"results": results}


@app.get("/api/knowledge/{doc_name}")
async def get_knowledge_doc(doc_name: str):
    """获取单个知识文档"""
    doc_path = Path(f"output/{doc_name}.md")
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        with open(doc_path, encoding="utf-8") as f:
            content = f.read()
        return {"name": doc_name, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 蒸馏控制 API ====================

_distill_process: Optional[subprocess.Popen] = None
_distill_status = {
    "running": False,
    "step": "idle",
    "started_at": None,
    "error": None,
}


@app.post("/api/distill/start")
async def start_distill(body: dict):
    """启动蒸馏任务"""
    global _distill_process, _distill_status
    try:
        if _distill_status["running"]:
            raise HTTPException(status_code=409, detail="蒸馏任务已在运行")

        model = body.get("model", "minimax")
        incremental = body.get("incremental", True)

        cmd = ["python3", "distill.py", "run", "--model", model]
        if not incremental:
            cmd.append("--full")

        _distill_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(Path(__file__).parent),
        )
        _distill_status = {
            "running": True,
            "step": "started",
            "started_at": datetime.now().isoformat(),
            "error": None,
        }
        return {"status": "ok", "message": "蒸馏任务已启动"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/distill/stop")
async def stop_distill():
    """停止蒸馏任务"""
    global _distill_process, _distill_status
    if _distill_process:
        _distill_process.terminate()
        try:
            _distill_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _distill_process.kill()
        _distill_process = None
    _distill_status["running"] = False
    _distill_status["step"] = "stopped"
    return {"status": "ok"}


@app.get("/api/distill/status")
async def get_distill_status():
    """获取蒸馏状态"""
    global _distill_process, _distill_status
    try:
        cache_dir = Path(".cache")

        # 从实际文件状态推断进度
        topics_done = []
        if (cache_dir / "final").exists():
            topics_done = [f.stem for f in (cache_dir / "final").glob("*.txt")]

        # 推断当前步骤
        step = "idle"
        if _distill_status["running"]:
            if (cache_dir / "final").exists() and list((cache_dir / "final").glob("*.txt")):
                step = "synthesize"
            elif (cache_dir / "topics.pkl").exists():
                step = "classify"
            elif (cache_dir / "cleaned.pkl").exists():
                step = "clean"
            elif (cache_dir / "articles.pkl").exists():
                step = "fetch"
            else:
                step = "started"

        # 检查子进程是否已结束
        if _distill_process and _distill_process.poll() is not None:
            _distill_status["running"] = False
            if _distill_process.returncode != 0:
                _distill_status["error"] = f"进程退出码: {_distill_process.returncode}"
            _distill_status["step"] = "done"
            _distill_process = None

        return {
            "data": {
                "running": _distill_status["running"],
                "step": step,
                "started_at": _distill_status["started_at"],
                "error": _distill_status["error"],
                "cache": {
                    "articles_cached": (cache_dir / "articles.pkl").exists(),
                    "cleaned_cached": (cache_dir / "cleaned.pkl").exists(),
                    "topics_cached": (cache_dir / "topics.pkl").exists(),
                    "batch_count": len(list((cache_dir / "batches").glob("*.txt")))
                    if (cache_dir / "batches").exists()
                    else 0,
                    "final_count": len(topics_done),
                },
                "topics_done": topics_done,
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/distill/stream")
async def distill_log_stream():
    """SSE 实时日志流"""

    async def event_generator():
        while _distill_process and _distill_process.poll() is None:
            line = _distill_process.stdout.readline()
            if line:
                yield f"data: {json.dumps({'log': line.strip()})}\n\n"
            else:
                await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ==================== 系统状态 API ====================

@app.get("/api/status")
async def get_status():
    """系统状态"""
    cache_dir = Path(".cache")
    output_dir = Path("output")

    cache_info = {}
    if cache_dir.exists():
        cache_info = {
            "articles": (cache_dir / "articles.pkl").exists(),
            "cleaned": (cache_dir / "cleaned.pkl").exists(),
            "topics": (cache_dir / "topics.pkl").exists(),
        }

    output_count = len(list(output_dir.glob("*.md"))) if output_dir.exists() else 0

    return {
        "cache": cache_info,
        "output_documents": output_count,
        "status": "idle" if not _distill_status["running"] else "running",
    }


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


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Bo-Distiller Web UI")
    print("=" * 50)
    print(f"\n  访问: http://127.0.0.1:8000")
    print(f"  API 文档: http://127.0.0.1:8000/docs")
    print(f"\n  按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
