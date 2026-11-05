from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Lexeme
from app.services.reviews import ensure_cards_for_lexeme


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_word_crud(client: TestClient) -> None:
    payload = {
        "headword": "zz-test-word",
        "kind": "word",
        "senses": [{"pos": "n.", "definition_zh": "测试词"}],
    }
    created = client.post("/api/words", json=payload)
    assert created.status_code == 201, created.text
    lexeme_id = created.json()["id"]

    fetched = client.get(f"/api/words/{lexeme_id}")
    assert fetched.status_code == 200
    assert fetched.json()["headword"] == "zz-test-word"

    updated = client.patch(
        f"/api/words/{lexeme_id}",
        json={"senses": [{"pos": "n.", "definition_zh": "更新后的释义"}]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["senses"][0]["definition_zh"] == "更新后的释义"

    found = client.get("/api/words", params={"q": "zz-test-word"})
    assert found.json()["total"] >= 1

    deleted = client.delete(f"/api/words/{lexeme_id}")
    assert deleted.status_code == 200
    archived = client.get(f"/api/words/{lexeme_id}")
    assert archived.json()["status"] == "archived"


def test_graph_has_no_dangling_edges(client: TestClient) -> None:
    view = client.get("/api/graph", params={"limit": 120}).json()
    node_ids = {node["id"] for node in view["nodes"]}
    assert node_ids
    for edge in view["edges"]:
        assert edge["source_node_id"] in node_ids
        assert edge["target_node_id"] in node_ids


def test_review_submit_is_idempotent(client: TestClient, db) -> None:
    lexeme = db.scalar(select(Lexeme).where(Lexeme.status == "active").order_by(Lexeme.id))
    assert lexeme is not None
    ensure_cards_for_lexeme(db, lexeme)
    db.commit()

    due = client.get("/api/reviews/due").json()
    assert due, "expected at least one due card"
    card = next(item for item in due if item["lexeme_id"] == lexeme.id)

    token = "test-token-001"
    first = client.post(
        "/api/reviews/submit",
        json={"card_id": card["card_id"], "result": "good", "client_token": token},
    )
    assert first.status_code == 200, first.text
    assert first.json()["state"]["reps"] == 1

    second = client.post(
        "/api/reviews/submit",
        json={"card_id": card["card_id"], "result": "good", "client_token": token},
    )
    assert second.status_code == 200
    assert second.json().get("duplicate") is True

    history = client.get("/api/reviews/history").json()
    assert any(item["card_id"] == card["card_id"] for item in history)


def test_statistics_overview(client: TestClient) -> None:
    stats = client.get("/api/statistics/overview").json()
    assert stats["total_lexemes"] >= 1
    assert "due_today" in stats
    assert isinstance(stats["weak_words"], list)


def test_backup_and_restore(client: TestClient) -> None:
    backup = client.post("/api/backup")
    assert backup.status_code == 200, backup.text
    name = backup.json()["file"]
    restore = client.post("/api/restore", json={"file": name})
    assert restore.status_code == 200, restore.text
    assert client.get("/api/words").json()["total"] >= 1
