from app import app


def test_hello():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hello DevOps" in response.data
    assert 1 == 2  # intentional break for the live demo


def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
