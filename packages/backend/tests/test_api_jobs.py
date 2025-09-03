from __future__ import annotations

import json
from fastapi.testclient import TestClient
from types import SimpleNamespace

from boards.api.app import app


def test_submit_generation_smoke(monkeypatch):
    client = TestClient(app)

    # Monkeypatch the actor send to avoid needing Redis during test
    sent = {}

    from boards.workers import actors
    from boards.jobs import repository as jobs_repo

    def fake_send(gen_id: str):
        sent["id"] = gen_id

    monkeypatch.setattr(actors.process_generation, "send", fake_send)

    # Bypass DB FKs by faking create_generation
    async def fake_create_generation(db, **kwargs):
        return SimpleNamespace(id="00000000-0000-0000-0000-0000000000aa")

    monkeypatch.setattr(jobs_repo, "create_generation", fake_create_generation)

    payload = {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "board_id": "00000000-0000-0000-0000-000000000002",
        "user_id": "00000000-0000-0000-0000-000000000003",
        "generator_name": "flux-pro",
        "provider_name": "replicate",
        "artifact_type": "image",
        "input_params": {
            "prompt": "hello",
            "aspect_ratio": "1:1",
            "safety_tolerance": 2,
        },
    }

    # Include authorization header for the test
    headers = {"Authorization": "Bearer test-token-please-replace"}
    resp = client.post("/api/jobs/generations", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "generation_id" in data
    assert sent.get("id") == data["generation_id"]
