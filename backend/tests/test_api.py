import json
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from alchemy.api import create_app
from alchemy.puzzles import BANK, load_answer_key


def test_daily_release_and_completion(tmp_path):
    bank = json.loads((BANK / "puzzles.json").read_text())
    solution = load_answer_key()[1]
    app = create_app(database_url=f"sqlite:///{tmp_path / 'results.sqlite3'}",
                     today_fn=lambda: date.fromisoformat(bank["launch_date"]))
    client = TestClient(app)
    public = client.get("/puzzle/today")
    assert public.status_code == 200
    assert public.json()["number"] == 1
    assert "path" not in public.json()
    assert client.get("/puzzle/2").status_code == 404
    assert client.get("/puzzle/1/stats").json()["completions"] == 0

    partial = client.post("/puzzle/1/validate", json={"intermediates": [solution[1], None, None]})
    assert [item["status"] for item in partial.json()["steps"]] == ["valid", "pending", "pending", "pending"]
    invalid = client.post("/puzzle/1/validate", json={"intermediates": ["ZZZZZ", solution[2], solution[3]]})
    assert invalid.json()["steps"][0]["reason"] == "not_a_word"
    payload = {"intermediates": solution[1:4], "device_id": str(uuid4()), "seconds": 85, "hints_used": 1}
    assert client.post("/puzzle/1/validate", json={"intermediates": solution[1:4]}).json()["solved"]
    assert client.post("/puzzle/1/complete", json=payload).json()["recorded"]
    assert client.post("/puzzle/1/complete", json=payload).json()["already_completed"]
    assert client.get("/puzzle/1/stats").json() == {"completions": 1, "median_seconds": 85}


def test_no_future_or_bad_completion(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path / 'results.sqlite3'}", today_fn=lambda: date(2026, 9, 30))
    client = TestClient(app)
    assert client.get("/puzzle/today").status_code == 404
    assert client.post("/puzzle/1/complete", json={"intermediates": ["AAAAA"] * 3,
                       "device_id": str(uuid4()), "seconds": 10, "hints_used": 0}).status_code == 404


def test_hard_mode_hides_rules_and_step_feedback(tmp_path):
    bank = json.loads((BANK / "puzzles.json").read_text())
    solution = load_answer_key()[1]
    app = create_app(database_url=f"sqlite:///{tmp_path / 'results.sqlite3'}",
                     today_fn=lambda: date.fromisoformat(bank["launch_date"]))
    client = TestClient(app)

    standard = client.get("/puzzle/today").json()
    hard = client.get("/puzzle/today?mode=hard").json()
    assert standard["mode"] == "standard" and len(standard["rules"]) == 4
    assert hard == {key: value for key, value in standard.items() if key != "rules"} | {"mode": "hard"}
    assert client.get("/puzzle/1?mode=hard").json() == hard
    assert client.get("/puzzle/today?mode=unknown").status_code == 422

    partial = {"intermediates": [solution[1], None, None]}
    full = {"intermediates": solution[1:4]}
    assert client.post("/puzzle/1/validate?mode=hard", json=partial).json() == {"solved": False}
    assert client.post("/puzzle/1/validate?mode=hard", json=full).json() == {"solved": True}
    assert "steps" in client.post("/puzzle/1/validate", json=full).json()
    assert client.post("/puzzle/1/validate?mode=unknown", json=full).status_code == 422


def test_render_requires_persistent_database(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        create_app()
