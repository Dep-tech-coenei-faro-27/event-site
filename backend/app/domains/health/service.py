from app.domains.health.schemas import HealthCheckResponse


def get_health_status() -> HealthCheckResponse:
    return HealthCheckResponse(status="OK")
