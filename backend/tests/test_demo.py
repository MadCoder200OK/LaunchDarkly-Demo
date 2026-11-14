"""Isolated API behavior checks; never read a reviewer's key or contact their LD account."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def test_targeting_and_rollback():
    """Verify preview audiences and that rollback bypasses a new-panel incident."""
    with TestClient(create_app(settings=Settings())) as client:
        for key, variant in [("qa-001", "new"), ("premium-001", "new"), ("standard-001", "existing"), ("experiment-001", "existing")]:
            assert client.get("/api/experience", params={"profile_key": key}).json()["decision"]["variant"] == variant
        client.put("/api/demo/state", json={"release": "existing", "incident": True})
        view = client.get("/api/experience", params={"profile_key": "qa-001"}).json()
        assert view["decision"]["variant"] == "existing"
        assert view["incident"] is False


def test_incident_recovery_and_validation():
    """Check the failure/recovery path and reject unknown identities and invalid inputs."""
    with TestClient(create_app(settings=Settings())) as client:
        payload = {"profile_key": "qa-001", "offer_id": "travel"}
        client.put("/api/demo/state", json={"release": "new", "incident": True})
        failure = client.post("/api/engagement", json=payload)
        assert failure.status_code == 503
        assert failure.headers['X-Demo-Incident'] == 'offers'
        client.put("/api/demo/state", json={"release": "existing", "incident": True})
        recovery = client.post("/api/engagement", json=payload)
        assert recovery.status_code == 200
        assert 'X-Demo-Incident' not in recovery.headers
        assert client.post("/api/engagement", json={**payload, "offer_id": "unknown"}).status_code == 404
        assert client.get("/api/experience", params={"profile_key": "unknown"}).status_code == 404
        assert client.post("/api/chat", json={"profile_key": "qa-001", "message": " "}).status_code == 422
        assert "Scripted preview" in client.post("/api/chat", json={"profile_key": "qa-001", "message": "travel"}).json()["source"]
