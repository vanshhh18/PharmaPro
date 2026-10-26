def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "aivoa-backend"
    assert body["database"]["connected"] is True


def test_health_isolated_test_db_used(client):
    response = client.get("/api/investigations/dashboard")
    assert response.status_code == 200
