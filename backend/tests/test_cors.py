ALLOWED_ORIGIN = "http://localhost:3000"
DISALLOWED_ORIGIN = "http://localhost:4000"


def test_allowed_origin_has_cors_headers(client):
    response = client.get(
        "/api/health",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_disallowed_origin_has_no_cors_allow_origin_header(client):
    response = client.get(
        "/api/health",
        headers={"Origin": DISALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allows_allowed_origin(client):
    response = client.options(
        "/api/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_rejects_disallowed_origin(client):
    response = client.options(
        "/api/health",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
