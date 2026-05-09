"""
Health Check y API de Monitoreo
Provee endpoints HTTP para verificar estado del scraper
"""
import logging
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.config import config
from src.metrics import get_metrics_summary, metrics

logger = logging.getLogger(__name__)

# Estado global del scraper
_scraper_status = {
    "running": False,
    "start_time": None,
    "total_processed": 0,
    "total_saved": 0,
    "total_errors": 0,
    "total_skipped": 0,
    "current_id": 0,
    "requests_per_second": 0.0,
    "eta_seconds": 0,
}


def create_app() -> FastAPI:
    """Crear aplicación FastAPI"""
    app = FastAPI(
        title="SICM Scraper API",
        description="API de monitoreo y control del scraper SICM",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()


@app.on_event("startup")
async def startup():
    """Iniciar servidor"""
    _scraper_status["running"] = True
    _scraper_status["start_time"] = time.time()
    logger.info("Health check server started")


@app.on_event("shutdown")
async def shutdown():
    """Detener servidor"""
    _scraper_status["running"] = False
    logger.info("Health check server stopped")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SICM Scraper",
        "version": "2.0.0",
        "status": "running" if _scraper_status["running"] else "stopped"
    }


@app.get("/health")
async def health():
    """Health check principal"""
    return {
        "status": "healthy" if _scraper_status["running"] else "unhealthy",
        "uptime_seconds": time.time() - _scraper_status["start_time"] if _scraper_status["start_time"] else 0,
        "scraper_running": _scraper_status["running"],
    }


@app.get("/health/live")
async def liveness():
    """Liveness probe para Kubernetes"""
    return PlainTextResponse("OK")


@app.get("/health/ready")
async def readiness():
    """Readiness probe"""
    if not _scraper_status["running"]:
        raise HTTPException(status_code=503, detail="Scraper not running")
    return {"status": "ready"}


@app.get("/api/status")
async def get_status():
    """Estado completo del scraper"""
    elapsed = time.time() - _scraper_status["start_time"] if _scraper_status["start_time"] else 0

    return {
        "running": _scraper_status["running"],
        "uptime_seconds": elapsed,
        "stats": {
            "total_processed": _scraper_status["total_processed"],
            "total_saved": _scraper_status["total_saved"],
            "total_errors": _scraper_status["total_errors"],
            "total_skipped": _scraper_status["total_skipped"],
            "current_id": _scraper_status["current_id"],
            "requests_per_second": _scraper_status["requests_per_second"],
            "success_rate": (
                _scraper_status["total_saved"] / _scraper_status["total_processed"] * 100
                if _scraper_status["total_processed"] > 0 else 0
            ),
        },
        "config": {
            "start_id": config.START_ID,
            "end_id": config.END_ID,
            "concurrency": config.CONCURRENCY,
            "batch_size": config.BATCH_SIZE,
        },
        "eta": {
            "seconds": _scraper_status["eta_seconds"],
            "formatted": _format_eta(_scraper_status["eta_seconds"]),
        } if _scraper_status["eta_seconds"] > 0 else None,
    }


@app.get("/api/metrics")
async def get_metrics():
    """Métricas Prometheus"""
    summary = get_metrics_summary()

    return {
        **summary,
        "metrics": {
            "batch_items": metrics.uptime_seconds,
        }
    }


@app.get("/api/progress")
async def get_progress():
    """Progreso del scrape"""
    return {
        "current_id": _scraper_status["current_id"],
        "total_processed": _scraper_status["total_processed"],
        "total_saved": _scraper_status["total_saved"],
        "start_id": config.START_ID,
        "end_id": config.END_ID,
        "progress_percent": (
            (_scraper_status["current_id"] - config.START_ID) /
            (config.END_ID - config.START_ID) * 100
            if config.END_ID > config.START_ID else 0
        ),
    }


@app.post("/api/pause")
async def pause_scraper():
    """Pausar scraper (placeholder - requiere integración con spider)"""
    return {"message": "Pause requested", "status": "not_implemented"}


@app.post("/api/resume")
async def resume_scraper():
    """Reanudar scraper (placeholder - requiere integración con spider)"""
    return {"message": "Resume requested", "status": "not_implemented"}


def update_scraper_status(
    current_id: int = 0,
    total_processed: int = 0,
    total_saved: int = 0,
    total_errors: int = 0,
    total_skipped: int = 0,
    requests_per_second: float = 0.0,
    eta_seconds: int = 0,
):
    """Actualizar estado del scraper (llamado desde spider)"""
    _scraper_status.update({
        "current_id": current_id,
        "total_processed": total_processed,
        "total_saved": total_saved,
        "total_errors": total_errors,
        "total_skipped": total_skipped,
        "requests_per_second": requests_per_second,
        "eta_seconds": eta_seconds,
    })


def _format_eta(seconds: int) -> str:
    """Formatear ETA a string legible"""
    if seconds <= 0:
        return "---"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)
