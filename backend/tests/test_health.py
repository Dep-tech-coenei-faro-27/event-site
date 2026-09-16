def test_root_returns_api_running(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "API is running"}


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
