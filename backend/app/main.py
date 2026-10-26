from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .db import check_database
from .routers import analysis, investigations, reports

app = FastAPI(
    title="AIVOA API",
    description="Decision support for deviation investigation. Not validated GMP software.",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(investigations.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(analysis.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health")
def health_check() -> dict:
    db_connected, db_detail = check_database()
    return {
        "status": "ok" if db_connected else "degraded",
        "service": "aivoa-backend",
        "version": __version__,
        "environment": settings.environment,
        "database": {"connected": db_connected, "detail": db_detail},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
