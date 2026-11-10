from app.services.analysis.rag import RagAnalyzer
from tests.test_rag import ScriptedProvider


async def test_upload_analysis_review_and_failure_preserves_items(client, monkeypatch, tmp_path):
    from app.core.config import settings
    from app.services import analysis_service

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    email = "maya@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "safe-demo-pass"})
    login = await client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": "safe-demo-pass",
        },
    )
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Northstar website",
            "currency": "EUR",
            "client_name": "Maya Chen",
            "client_email": "maya@northstar.example",
        },
    )
    assert response.status_code == 201, response.text
    project_id = response.json()["id"]
    base = f"/api/v1/projects/{project_id}"
    email_content = (
        b"From: Maya <maya@northstar.example>\r\nTo: alex@studio.example\r\n"
        b"Subject: Authentication\r\nContent-Type: text/plain\r\n\r\n"
        b"I approve authentication for EUR 200 and accept the delivery."
    )
    uploaded = await client.post(
        base + "/documents",
        files={
            "files": ("approval.eml", email_content, "message/rfc822"),
        },
    )
    assert uploaded.status_code < 300, uploaded.text
    monkeypatch.setattr(analysis_service, "get_analyzer", lambda: RagAnalyzer(ScriptedProvider()))
    response = await client.post(base + "/analysis")
    assert response.status_code == 200, response.text
    review = response.json()
    assert review["analysis"]["engine"] == "rag"
    assert len(review["items"]) == 1
    assert all(e["verified"] for e in review["items"][0]["evidence"])
    item_id = review["items"][0]["id"]

    class FailingAnalyzer:
        name = "rag"

        async def analyze(self, *args):
            raise RuntimeError("Provider unavailable")

    monkeypatch.setattr(analysis_service, "get_analyzer", FailingAnalyzer)
    failed = await client.post(base + "/analysis")
    assert failed.status_code == 502
    review = (await client.get(base + "/review")).json()
    assert review["analysis"]["status"] == "failed"
    assert review["items"][0]["id"] == item_id
