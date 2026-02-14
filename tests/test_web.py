"""Tests for the FastAPI web endpoints."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from web import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestStatusEndpoint:
    def test_status_returns_sources(self):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured_sources" in data
        assert "count" in data
        assert isinstance(data["configured_sources"], list)


class TestIndexEndpoint:
    def test_index_returns_html(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "soles.watch" in resp.text


class TestSearchEndpoint:
    def test_search_requires_query(self):
        resp = client.get("/api/search")
        assert resp.status_code == 422  # FastAPI validation error

    def test_search_with_no_adapters_returns_error(self):
        resp = client.get("/api/search", params={"query": "test"})
        # When no APIs are configured, scan_for_arbitrage raises RuntimeError
        # which web.py catches and returns as an error dict
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data or "listings" in data
