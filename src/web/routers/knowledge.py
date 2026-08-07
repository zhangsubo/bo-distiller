"""
知识库 API

从 web_ui.py 平移而来，保持原有端点行为不变
"""

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# 条目标题，如 "### 1. **Pythia 全球感知引擎**"
_ENTRY_HEADING_RE = re.compile(r"^###\s+\d*[.、]?\s*\*{0,2}(?P<title>.*?)\*{0,2}\s*$")
# 字段行，如 "   - **一句话描述**: ..."
_FIELD_RE = re.compile(r"^\s*-\s*\*\*(?P<key>.+?)\*\*[:：]\s*(?P<value>.*)$")
# 双括号链接 [[标题](url)]
_LINK_RE = re.compile(r"\[\[(?P<title>[^\]]+)\]\((?P<url>[^)\s]+)\)\]")
# 普通 markdown 链接 [标题](url)
_MD_LINK_RE = re.compile(r"\[(?P<title>[^\]]+)\]\((?P<url>[^)\s]+)\)")

# 已知字段名 → 结构化 key（其余进 extra）
_FIELD_KEY_MAP = {
    "一句话描述": "summary",
    "功能描述": "description",
    "官方地址": "official",
}
_ARTICLE_FIELD_KEYS = {"涉及文章", "涉及文章列表", "文章来源"}


def _strip_links(text: str) -> str:
    """把 [[t](u)] / [t](u) 还原为纯文本 t"""
    text = _LINK_RE.sub(lambda m: m.group("title"), text)
    return _MD_LINK_RE.sub(lambda m: m.group("title"), text)


def parse_topic_md(content: str) -> dict:
    """把主题 markdown 解析为 wiki 用的结构化数据。

    结构：# 标题 → > 总结 → ## 分类 → ### 条目（- **字段**: 值）
    解析是宽松的：字段识别不了的进 extra，没有 ### 的主题返回空 sections，
    由前端回退到原始 markdown 渲染。
    """
    title = ""
    summary = ""
    sections: list[dict] = []
    current_section: dict | None = None
    current_entry: dict | None = None

    for line in content.split("\n"):
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("> ") and not summary:
            summary = line[2:].strip()
            continue
        if line.startswith("## "):
            current_section = {"title": line[3:].strip(), "entries": []}
            sections.append(current_section)
            current_entry = None
            continue
        m = _ENTRY_HEADING_RE.match(line)
        if m and current_section is not None:
            current_entry = {
                "id": f"s{len(sections) - 1}-e{len(current_section['entries'])}",
                "title": m.group("title").strip(),
                "summary": "",
                "description": "",
                "official": "",
                "articles": [],
                "extra": [],
            }
            current_section["entries"].append(current_entry)
            continue
        f = _FIELD_RE.match(line)
        if f and current_entry is not None:
            key, value = f.group("key").strip(), f.group("value").strip()
            if key in _ARTICLE_FIELD_KEYS:
                current_entry["articles"] = [
                    {"title": lm.group("title"), "url": lm.group("url")}
                    for lm in _LINK_RE.finditer(value)
                ]
            elif key in _FIELD_KEY_MAP:
                current_entry[_FIELD_KEY_MAP[key]] = _strip_links(value)
            else:
                current_entry["extra"].append({"key": key, "value": _strip_links(value)})

    return {"title": title, "summary": summary, "sections": sections}


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
            "entry_count": 0,
        })

    # 统计每个主题的条目数（### 标题行）
    for doc in documents:
        try:
            with open(output_dir / f"{doc['name']}.md", encoding="utf-8") as f:
                doc["entry_count"] = sum(1 for line in f if line.startswith("### "))
        except Exception as e:
            # 保持默认值 0，记录错误便于排查
            print(f"[WARN] 统计 {doc['name']} 条目数失败: {e}")

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


@router.get("/api/knowledge/{doc_name}/entries")
async def get_knowledge_entries(doc_name: str):
    """获取主题的结构化条目（wiki 二级导航用）。

    sections 为空表示该主题不是「分类→条目」结构，前端回退渲染 raw markdown。
    """
    doc_path = Path(f"output/{doc_name}.md")
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        with open(doc_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    parsed = parse_topic_md(content)
    return {"name": doc_name, "raw": content, **parsed}
