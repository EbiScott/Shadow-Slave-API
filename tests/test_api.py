from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "quotes.db"
client = TestClient(app)


def test_health_reports_a_built_database():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["quote_count"] > 1000
    assert payload["character_count"] > 100
    assert payload["volume_count"] == 12


def test_every_volume_has_quotes():
    connection = sqlite3.connect(DB)
    try:
        volumes = {
            row[0]
            for row in connection.execute("SELECT DISTINCT volume FROM quotes")
        }
    finally:
        connection.close()

    assert volumes == set(range(1, 13))


def test_character_list_uses_real_quote_counts():
    response = client.get("/v1/characters?limit=1")

    assert response.status_code == 200
    payload = response.json()
    health = client.get("/health").json()
    assert payload["items"][0]["character"] == "Sunless"
    assert 1000 < payload["items"][0]["quote_count"] <= health["quote_count"]


def test_alias_resolves_to_canonical_character():
    response = client.get("/v1/characters/Sunny")

    assert response.status_code == 200
    assert response.json()["character"] == "Sunless"
    assert response.json()["quote_count"] > 1000


def test_random_sunless_quote_is_attributed():
    response = client.get(
        "/v1/quotes/random",
        params={"character": "Sunless", "min_words": 6, "max_chars": 220},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["character"] == "Sunless"
    assert payload["attribution"] == "Shadow Slave by Guiltythree"
    assert payload["quote"]


def test_quote_search_filters_by_character():
    response = client.get(
        "/v1/quotes",
        params={"character": "Sunless", "confidence": "tag", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] > 0
    assert len(payload["items"]) == 5
    assert all(item["character"] == "Sunless" for item in payload["items"])


def test_unknown_character_and_quote_return_404():
    assert client.get("/v1/characters/NotARealCharacter").status_code == 404
    assert client.get("/v1/quotes/999999999").status_code == 404
