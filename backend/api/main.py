"""
奥运数据看板后端
================
职责：读取 build_data.py 预生成的 dashboard.json，按 REST 接口提供给前端。
启动：python backend/api/main.py   （默认 http://127.0.0.1:8010）

说明
----
- 只读 JSON，不依赖 pandas / 数据库，启动即可用；
- 数据文件在首次请求时加载并常驻内存，避免每请求重复解析 800 KB JSON。
"""

from __future__ import annotations

import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "dashboard.json"
S4_FILE = BASE_DIR / "data" / "s4.json"
HOST = "127.0.0.1"
PORT = 8010

app = FastAPI(
    title="数说奥运数据看板 API",
    description="读取预生成 JSON，向 Vue 前端提供奥运可视化数据",
    version="1.0.0",
)

# 开发期允许 Vite（5500）跨域直连；生产可收紧为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache: dict | None = None
_s4_cache: dict | None = None


def load_json(path: Path) -> dict:
    """读取 JSON 文件。"""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_data() -> dict:
    """惰性加载主看板 JSON，并缓存到进程内存。"""
    global _cache
    if _cache is None:
        if not DATA_FILE.exists():
            raise HTTPException(
                status_code=503,
                detail=f"数据文件不存在：{DATA_FILE}，请先运行 python backend/api/build_data.py",
            )
        _cache = load_json(DATA_FILE)
    return _cache


def load_s4() -> dict:
    """惰性加载 S4 专题 JSON，并缓存到进程内存。"""
    global _s4_cache
    if _s4_cache is None:
        if not S4_FILE.exists():
            raise HTTPException(
                status_code=503,
                detail=f"数据文件不存在：{S4_FILE}，请先运行 python backend/api/build_s4_data.py",
            )
        _s4_cache = load_json(S4_FILE)
    return _s4_cache


@app.get("/api/health")
def health() -> dict:
    """健康检查：前端启动时可用来判断后端是否就绪。"""
    data = load_data()
    return {"status": "ok", "editions": data["meta"]["officialEditions"], "source": DATA_FILE.name}


@app.get("/api/dashboard")
def dashboard() -> dict:
    """整包数据：前端一次拉取后全部筛选与联动都在客户端完成。"""
    return load_data()


@app.get("/api/dashboard/{section}")
def dashboard_section(section: str) -> dict:
    """按区块取数，便于后续拆页或调试。"""
    data = load_data()
    if section not in data:
        raise HTTPException(status_code=404, detail=f"未知区块：{section}")
    return data[section]


@app.get("/api/s4")
def s4() -> dict:
    """S4 小代表团专题整包数据。"""
    return load_s4()


@app.get("/api/s4/{section}")
def s4_section(section: str) -> dict:
    """按区块取 S4 数据，便于调试。"""
    data = load_s4()
    if section not in data:
        raise HTTPException(status_code=404, detail=f"未知区块：{section}")
    return data[section]


if __name__ == "__main__":
    # 传 app 对象而不是 "main:app"，这样从项目根目录或 api 目录启动都能工作
    uvicorn.run(app, host=HOST, port=PORT, reload=False)
