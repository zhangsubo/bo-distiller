#!/usr/bin/env python3
"""
Bo-Distiller Web UI

提供 Web 界面查看配置和生成的内容。
应用实现已拆分到 src/web/ 包，本文件仅作为启动入口。
"""

import uvicorn

from src.web.app import create_app

app = create_app()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Bo-Distiller Web UI")
    print("=" * 50)
    print(f"\n  访问: http://127.0.0.1:8000")
    print(f"  API 文档: http://127.0.0.1:8000/docs")
    print(f"\n  按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
