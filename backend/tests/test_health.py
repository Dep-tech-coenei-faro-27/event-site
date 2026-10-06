from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_health_check_answers_head_requests(client):
    response = client.head("/api/health")
    assert response.status_code == 200


def test_readiness_ok_when_database_answers(auth_client):
    response = auth_client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_readiness_returns_503_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert client.get("/api/health").status_code == 200
