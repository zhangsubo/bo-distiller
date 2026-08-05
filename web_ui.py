#!/usr/bin/env python3
"""
Bo-Distiller Web UI

提供 Web 界面查看配置和生成的内容。
应用实现已拆分到 src/web/ 包，本文件仅作为启动入口。
"""

import uvicorn

from src.web.app import create_app

app = create_app()

# 调试：列出所有路由
print("\n[DEBUG] 应用中的所有 API 路由:")
from fastapi.openapi.utils import get_openapi
schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
paths = [p for p in schema.get('paths', {}).keys() if p.startswith('/api')]
for path in sorted(paths):
    print(f"  {path}")
print(f"[DEBUG] 总计 {len(paths)} 个 API 路由\n")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Bo-Distiller Web UI")
    print("=" * 50)
    print(f"\n  访问: http://127.0.0.1:8000")
    print(f"  API 文档: http://127.0.0.1:8000/docs")
    print(f"\n  按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
