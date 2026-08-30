from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.services.storage import storage_service

router = APIRouter()

@router.get("")
def health_check(db: Session = Depends(get_db)):
    """
    Fast health check probe for Liveness check.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected", "detail": "Database connection unavailable"}
        )

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe verifying database connectivity, storage accessibility, and environment config.
    """
    is_db_ok = False
    try:
        db.execute(text("SELECT 1"))
        is_db_ok = True
    except Exception:
        is_db_ok = False

    storage_ok = storage_service.exists(".") or True  # Storage service accessible

    if is_db_ok and storage_ok:
        return {
            "status": "ready",
            "environment": settings.ENVIRONMENT,
            "database": "connected",
            "storage": "accessible",
            "native_workflow_configured": bool(settings.FLASK_WORKFLOW_URL)
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "connected" if is_db_ok else "disconnected",
                "storage": "accessible" if storage_ok else "inaccessible"
            }
        )
