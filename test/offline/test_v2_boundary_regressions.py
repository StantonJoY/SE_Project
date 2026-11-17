"""Independent VERIFY input regressions implemented by BUILD after proxy rejection.

REQ-ADS-ARCH-007/012, REQ-ADS-GOV-001, REQ-ADS-NFR-PERF-001,
INV-ADS-003/012. Negative tests cover lone surrogates and a slow-drip provider.
These reviewer-designed boundary cases supplement, and never alter, existing tests.
"""

from __future__ import annotations

import json
import socket
import sqlite3
import tempfile
import threading
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from app.pipeline_v2 import recommend_v2
from bidding import Ledger, validate_bids
from compliance.rules import SceneRules
from render.schema_v2 import validate_v2_result
from selector.relevance import HTTPRelevanceClient, RelevanceError, parse_relevance_output

ROOT = Path(__file__).resolve().parents[2]
SCENE = {"time_slot": "morning", "device": "mobile", "user_tags": ["student"]}
LONE_SURROGATE = "\ud800"


def _advice(reason: str = "Relevant to the morning scene.") -> str:
    return json.dumps({"scores": [{"ad_id": "ad_001", "relevance": 90, "reason": reason}]})


class _RawClient:
    def __init__(self, raw: str):
        self.raw = raw
        self.calls = 0

    def score(self, scene, candidates):
        self.calls += 1
        return self.raw


@pytest.fixture
def dependencies():
    """REQ-ADS-ARCH-007: use real read-only materials and strict validated bid terms."""
    return {
        "repo": AdRepository.load(ROOT / "data/ads.json"),
        "bids": validate_bids([{"ad_id": "ad_001", "bid_cents": 100, "budget_cents": 200}]),
        "banned_words": BannedWords.load(ROOT / "data/banned_words.json"),
        "rules": SceneRules.load(ROOT / "data/scene_rules.json"),
    }


@pytest.mark.parametrize("raw", [
    LONE_SURROGATE,
    _advice().replace("Relevant to the morning scene.", LONE_SURROGATE),
    _advice(LONE_SURROGATE),
    _advice().replace('"reason":', '"\\ud800":'),
    _advice().replace('"scores":', '"\\ud800":'),
])
def test_parser_rejects_raw_and_json_escaped_lone_surrogates(raw):
    """INV-ADS-003: negative test checks raw text AND decoded reason/object keys."""
    with pytest.raises(RelevanceError):
        parse_relevance_output(raw, ["ad_001"])


def test_invalid_unicode_scene_is_durably_rejected_before_provider(dependencies):
    """REQ-ADS-GOV-001/ARCH-007: malformed input must not become storage uncertainty."""
    scene = {**SCENE, "user_tags": [LONE_SURROGATE]}
    client = _RawClient(_advice())
    # Workspace isolation avoids the documented sandbox OS-temp ACL issue.
    with tempfile.TemporaryDirectory(prefix="v2-unicode-input-", dir=ROOT) as directory:
        path = Path(directory) / "rejection.sqlite3"
        with Ledger(path) as ledger:
            ledger.seed(dependencies["bids"])
            result = recommend_v2(scene, request_id="unicode-input", client=client, ledger=ledger, **dependencies)
            assert result["kind"] == "no_ad"
            assert result["reason_code"] == "scene_invalid"
            assert validate_v2_result(result) == []
            assert client.calls == 0
            assert ledger.budgets()["ad_001"]["spent_cents"] == 0
            assert len(ledger.audit_records()) == 1
            assert ledger.audit_records()[0]["evidence"]["scene"]["user_tags"] == [LONE_SURROGATE]
        with closing(sqlite3.connect(path)) as connection:
            encoded = connection.execute("SELECT record_json FROM audit").fetchone()[0]
            assert "\\ud800" in encoded
            encoded.encode("utf-8")  # Persisted evidence is safe UTF-8 JSON, not lossy replacement.
        with Ledger(path) as reopened:
            replay = recommend_v2(scene, request_id="unicode-input", client=client, ledger=reopened, **dependencies)
            assert replay == result
            assert client.calls == 0
            assert reopened.budgets()["ad_001"]["spent_cents"] == 0
            assert len(reopened.audit_records()) == 1


def test_invalid_unicode_request_identity_is_rejected_without_storage_uncertainty(dependencies):
    """REQ-ADS-GOV-001: an invalid identity uses the explicit request_invalid audit exception."""
    client = _RawClient(_advice())
    with Ledger() as ledger:
        ledger.seed(dependencies["bids"])
        result = recommend_v2(SCENE, request_id=LONE_SURROGATE, client=client, ledger=ledger, **dependencies)
        assert result["kind"] == "no_ad"
        assert result["reason_code"] == "request_invalid"
        assert result["request_id"] == result["audit_id"] == ""
        assert validate_v2_result(result) == []
        json.dumps(result, ensure_ascii=False).encode("utf-8")
        assert client.calls == 0
        assert ledger.budgets()["ad_001"]["spent_cents"] == 0
        assert ledger.audit_records() == []


@pytest.mark.parametrize("raw", [
    LONE_SURROGATE,
    _advice().replace("Relevant to the morning scene.", LONE_SURROGATE),
    _advice(LONE_SURROGATE),
    _advice().replace('"reason":', '"\\ud800":'),
])
def test_invalid_unicode_advice_is_durably_rejected_with_raw_evidence(dependencies, raw):
    """INV-ADS-003/012: raw/escaped surrogate output is no_ad with zero charge and audit."""
    client = _RawClient(raw)
    with tempfile.TemporaryDirectory(prefix="v2-unicode-output-", dir=ROOT) as directory:
        path = Path(directory) / "rejection.sqlite3"
        with Ledger(path) as ledger:
            ledger.seed(dependencies["bids"])
            result = recommend_v2(SCENE, request_id="unicode-advice", client=client, ledger=ledger, **dependencies)
            assert result["kind"] == "no_ad"
            assert result["reason_code"] == "llm_output_invalid"
            assert validate_v2_result(result) == []
            assert client.calls == 1
            assert ledger.budgets()["ad_001"]["spent_cents"] == 0
            assert len(ledger.audit_records()) == 1
            assert ledger.audit_records()[0]["evidence"]["raw_relevance_output"] == raw
        with Ledger(path) as reopened:
            replay = recommend_v2(SCENE, request_id="unicode-advice", client=client, ledger=reopened, **dependencies)
            assert replay == result and client.calls == 1
            assert reopened.budgets()["ad_001"]["spent_cents"] == 0
            assert len(reopened.audit_records()) == 1


class _DripResponse:
    """A valid response arrives in eight-byte chunks every 80ms (VERIFY's input)."""

    def __init__(self):
        self.body = json.dumps({"choices": [{"message": {"content": _advice()}}]}).encode()
        self.offset = 0
        self.closed = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed.set()

    def read1(self, size):
        time.sleep(0.08)
        chunk = self.body[self.offset:self.offset + min(size, 8)]
        self.offset += len(chunk)
        return chunk

    def read(self, size):
        # The old single read saw repeated activity and could exceed its timeout.
        chunks = []
        while len(b"".join(chunks)) < size:
            chunk = self.read1(size - len(b"".join(chunks)))
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)


def test_http_total_deadline_covers_slow_drip_body():
    """REQ-ADS-NFR-PERF-001: negative test distinguishes wall time from socket inactivity."""
    response = _DripResponse()
    client = HTTPRelevanceClient("http://unused.invalid/chat/completions", model="fixture",
                                 api_key="test-placeholder", timeout_sec=0.15,
                                 transport=lambda req, timeout: response)
    started = time.monotonic()
    with pytest.raises(RelevanceError, match="total deadline"):
        client.score(SCENE, [{"ad_id": "ad_001", "title": "Coffee", "category": "food", "target_tags": []}])
    elapsed = time.monotonic() - started
    assert 0.10 <= elapsed < 0.40
    assert response.closed.wait(1.0), "resumed worker must close its response"


def test_http_total_deadline_covers_blocked_headers_and_bounds_workers():
    """REQ-ADS-NFR-PERF-001: a blocked transport must not hold the public call or spawn retries."""
    release = threading.Event()
    calls = []
    response = _DripResponse()

    def blocked_transport(req, timeout):
        calls.append(timeout)
        release.wait(2.0)
        return response

    client = HTTPRelevanceClient("http://unused.invalid/chat/completions", model="fixture",
                                 api_key="test-placeholder", timeout_sec=0.15, transport=blocked_transport)
    try:
        started = time.monotonic()
        with pytest.raises(RelevanceError, match="total deadline"):
            client.score(SCENE, [])
        assert 0.10 <= time.monotonic() - started < 0.40
        started = time.monotonic()
        with pytest.raises(RelevanceError, match="unfinished"):
            client.score(SCENE, [])
        assert time.monotonic() - started < 0.10
        assert len(calls) == 1
    finally:
        release.set()
        assert response.closed.wait(1.0)


def test_real_loopback_slow_drip_respects_total_deadline(monkeypatch):
    """REQ-ADS-NFR-PERF-001: actual urllib/socket drip regression, when loopback is permitted."""
    body = json.dumps({"choices": [{"message": {"content": _advice()}}]}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                for offset in range(0, len(body), 8):
                    self.wfile.write(body[offset:offset + 8])
                    self.wfile.flush()
                    time.sleep(0.08)
            except OSError:
                pass  # Expected when the deadline closes the client response.

        def log_message(self, *args):
            pass

    try:
        server = HTTPServer(("127.0.0.1", 0), Handler)
    except OSError as exc:
        pytest.skip(f"environment cannot bind loopback ({type(exc).__name__})")
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    try:
        try:
            with socket.create_connection(server.server_address, timeout=0.5):
                pass
        except OSError as exc:
            pytest.skip(f"environment cannot connect to loopback ({type(exc).__name__})")
        client = HTTPRelevanceClient(f"http://127.0.0.1:{server.server_port}/chat/completions",
                                     model="loopback", api_key="test-placeholder", timeout_sec=0.15)
        started = time.monotonic()
        with pytest.raises(RelevanceError, match="total deadline"):
            client.score(SCENE, [])
        elapsed = time.monotonic() - started
        assert 0.10 <= elapsed < 0.40
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)
