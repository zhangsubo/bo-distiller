"""
知识库 API

从 web_ui.py 平移而来，保持原有端点行为不变
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


# ==================== 知识库 API ====================

@router.get("/api/knowledge")
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


@router.get("/api/knowledge/search")
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


@router.get("/api/knowledge/{doc_name}")
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
