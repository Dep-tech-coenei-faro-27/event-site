from fastapi import APIRouter, status

from app.domains.health.schemas import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
)
def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="OK")
