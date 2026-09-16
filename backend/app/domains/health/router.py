from fastapi import APIRouter, status

from app.domains.health.schemas import HealthCheckResponse
from app.domains.health.service import get_health_status

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
)
def health_check() -> HealthCheckResponse:
    return get_health_status()
