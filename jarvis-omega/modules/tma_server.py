import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger("jarvis.tma_server")

STATIC_DIR = Path(__file__).parent.parent / "static"


class CommandRequest(BaseModel):
    command: str
    args: dict = {}


def create_app(brain) -> FastAPI:
    app = FastAPI(title="Jarvis-Omega TMA API", version="1.0.0")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def root():
        dashboard = STATIC_DIR / "dashboard.html"
        if dashboard.exists():
            return FileResponse(str(dashboard))
        return JSONResponse({"status": "Jarvis-Omega TMA running"})

    @app.get("/api/metrics")
    async def get_metrics():
        try:
            metrics = await brain.get_metrics()
            return JSONResponse(metrics)
        except Exception as e:
            logger.error(f"[TMA] Error fetching metrics: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch metrics")

    @app.post("/api/command")
    async def run_command(req: CommandRequest):
        cmd = req.command.lower().strip()
        logger.info(f"[TMA] Received command: {cmd}")

        if cmd == "pause":
            await brain.pause_workers()
            return {"status": "ok", "message": "Workers paused"}
        elif cmd == "resume":
            await brain.resume_workers()
            return {"status": "ok", "message": "Workers resumed"}
        elif cmd == "status":
            metrics = await brain.get_metrics()
            return {"status": "ok", "metrics": metrics}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown command: {cmd}")

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


async def start_server(brain):
    app = create_app(brain)
    host = os.getenv("TMA_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("TMA_SERVER_PORT", "8000"))

    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"[TMA] Starting FastAPI server on {host}:{port}")
    await server.serve()
