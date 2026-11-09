from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.health.schemas import HealthCheckResponse
from app.domains.health.service import get_health_status

router = APIRouter(tags=["health"])


@router.head("/health", include_in_schema=False)
@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
)
def health_check() -> HealthCheckResponse:
    return get_health_status()


@router.head("/health/ready", include_in_schema=False)
@router.get(
    "/health/ready",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
)
def readiness_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from None
    return get_health_status()
