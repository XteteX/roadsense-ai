import importlib

import pytest

pytest.importorskip("httpx")


@pytest.fixture
def client(temp_db):
    from fastapi.testclient import TestClient

    import src.main as main

    importlib.reload(main)
    temp_db.add_defect(dict(type="pothole", lat=43.24, lon=76.89, size_cm=30.0, traffic_level=2,
                            is_near_social=True, score=78.0, category="High", explanation="x"))
    temp_db.add_defect(dict(type="crack", lat=43.25, lon=76.90, size_cm=5.0, traffic_level=1,
                            is_near_social=False, score=3.5, category="Low (planned)", explanation="y"))
    return TestClient(main.app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_defects_sorted_and_filtered(client):
    scores = [d["score"] for d in client.get("/defects").json()]
    assert scores == sorted(scores, reverse=True)
    assert [d["category"] for d in client.get("/defects", params={"category": "High"}).json()] == ["High"]


def test_defect_not_found(client):
    assert client.get("/defects/999").status_code == 404


def test_priority_endpoint(client):
    r = client.post("/priority", json={"type": "pothole", "size_cm": 30, "traffic_level": 2, "is_near_social": True})
    assert r.status_code == 200 and r.json()["score"] == 78.0


def test_priority_validation(client):
    assert client.post("/priority", json={"type": "pothole", "size_cm": 30, "traffic_level": 7}).status_code == 422
