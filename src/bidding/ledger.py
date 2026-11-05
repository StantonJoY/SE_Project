"""Atomic integer-cent settlement and canonical audit under ADR-005 §2.

Enforces REQ-ADS-ARCH-005/006/007/008/010/012, REQ-ADS-FR-007/008,
REQ-ADS-GOV-001 and INV-ADS-012. Budget, idempotent response and audit are
separate SQLite tables written in one short transaction. Only current budget
state and request identity may be read for decisions; audit_records is an
offline evidence interface and is never used by settlement or selection.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .models import Bid, BidError


class LedgerError(RuntimeError):
    """Settlement cannot safely commit (ADR-005 §2, REQ-ADS-GOV-001)."""


class RequestConflict(LedgerError):
    """A request ID was reused with different input (ADR-005 §2)."""


class InsufficientBudget(LedgerError):
    """The current offer is inactive or unaffordable (REQ-ADS-ARCH-006)."""


def _text(value: object, name: str) -> str:
    """Require explicit identities for REQ-ADS-GOV-001 evidence."""
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{name} must be a nonempty string")
    return value


def _json(value: object) -> str:
    """Encode finite JSON without coercing NaN/Inf (REQ-ADS-NFR-SAFETY-007)."""
    try:
        return json.dumps(value, ensure_ascii=True, allow_nan=False,
                          sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise LedgerError("settlement data must be finite, serializable JSON") from exc


_SCHEMA = """
CREATE TABLE IF NOT EXISTS budget (
    ad_id TEXT PRIMARY KEY,
    seed_json TEXT NOT NULL,
    bid_cents INTEGER NOT NULL CHECK(typeof(bid_cents) = 'integer' AND bid_cents > 0),
    total_cents INTEGER NOT NULL CHECK(typeof(total_cents) = 'integer' AND total_cents >= 0),
    spent_cents INTEGER NOT NULL CHECK(typeof(spent_cents) = 'integer' AND spent_cents >= 0),
    remaining_cents INTEGER NOT NULL CHECK(typeof(remaining_cents) = 'integer' AND remaining_cents >= 0),
    status TEXT NOT NULL CHECK(status IN ('active', 'paused', 'exhausted')),
    CHECK(spent_cents <= total_cents AND remaining_cents = total_cents - spent_cents)
);
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    response_json TEXT NOT NULL,
    audit_id TEXT NOT NULL UNIQUE,
    ad_id TEXT REFERENCES budget(ad_id),
    charge_cents INTEGER NOT NULL CHECK(typeof(charge_cents) = 'integer' AND charge_cents >= 0)
);
CREATE TABLE IF NOT EXISTS audit (
    audit_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE REFERENCES requests(request_id),
    record_json TEXT NOT NULL
);
"""


class Ledger:
    """Persist budgets without resetting them on reopen (ADR-005 §2).

    REQ-ADS-ARCH-005/007: BEGIN IMMEDIATE serializes competing settlements;
    an instance lock also allows one Ledger to be used by multiple threads.
    Each instance owns its connection. No model work belongs in a transaction.
    """

    def __init__(
        self, path: str | Path = ":memory:", *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize storage; report all initialization failures as LedgerError."""
        self._lock = threading.RLock()
        self._closed = False
        self._fault_hook = fault_hook
        self._conn: sqlite3.Connection | None = None
        try:
            if not isinstance(path, (str, Path)) or not str(path):
                raise LedgerError("path must be a nonempty string or Path")
            if fault_hook is not None and not callable(fault_hook):
                raise LedgerError("fault_hook must be callable")
            self._conn = sqlite3.connect(str(path), timeout=5.0,
                                         isolation_level=None, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.execute("PRAGMA synchronous = FULL")
            self._conn.executescript(_SCHEMA)
        except Exception as exc:
            if self._conn is not None:
                self._conn.close()
            self._closed = True
            if isinstance(exc, LedgerError):
                raise
            raise LedgerError("ledger initialization failed") from exc

    def _connection(self) -> sqlite3.Connection:
        """Fail closed after close (REQ-ADS-GOV-001)."""
        if self._closed or self._conn is None:
            raise LedgerError("ledger is closed")
        return self._conn

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit debit/response/audit together or roll back (REQ-ADS-ARCH-007)."""
        with self._lock:
            connection = self._connection()
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except BaseException as exc:
                try:
                    connection.rollback()
                except sqlite3.Error as rollback_error:
                    raise LedgerError("ledger rollback failed") from rollback_error
                if isinstance(exc, LedgerError) or not isinstance(exc, Exception):
                    raise
                raise LedgerError("ledger transaction failed") from exc

    def seed(self, bids: Mapping[str, Bid]) -> None:
        """Install an immutable initial offer contract (REQ-ADS-ARCH-005/008).

        Repeating the same seed preserves all spending and runtime statuses.
        A changed initial contract, including the ad set, is rejected atomically.
        """
        if not isinstance(bids, Mapping):
            raise LedgerError("bids must be a mapping")
        initial: dict[str, tuple[Bid, str]] = {}
        for ad_id, bid in bids.items():
            if not isinstance(bid, Bid) or ad_id != bid.ad_id:
                raise LedgerError("seed entries must be Bid values matching their keys")
            try:
                bid.__post_init__()
            except BidError as exc:
                raise LedgerError("invalid seed offer") from exc
            initial[ad_id] = (bid, _json(asdict(bid)))
        with self._transaction() as connection:
            existing = {row["ad_id"]: row["seed_json"] for row in
                        connection.execute("SELECT ad_id, seed_json FROM budget")}
            if existing:
                if existing != {ad_id: entry[1] for ad_id, entry in initial.items()}:
                    raise LedgerError("persistent seed contract cannot be changed")
                return
            for bid, seed_json in initial.values():
                status = ("exhausted" if bid.status == "active" and bid.budget_cents == 0
                          else bid.status)
                connection.execute(
                    "INSERT INTO budget VALUES (?, ?, ?, ?, 0, ?, ?)",
                    (bid.ad_id, seed_json, bid.bid_cents, bid.budget_cents,
                     bid.budget_cents, status),
                )

    def budgets(self) -> dict[str, dict]:
        """Read current budget state, never audit history (REQ-ADS-ARCH-005)."""
        with self._lock:
            try:
                rows = self._connection().execute(
                    "SELECT ad_id, total_cents, spent_cents, remaining_cents, "
                    "status FROM budget ORDER BY ad_id"
                ).fetchall()
                return {row["ad_id"]: {
                    "total_cents": row["total_cents"],
                    "spent_cents": row["spent_cents"],
                    "remaining_cents": row["remaining_cents"],
                    "status": row["status"],
                } for row in rows}
            except sqlite3.Error as exc:
                raise LedgerError("cannot read current budgets") from exc

    @staticmethod
    def _lookup(
        connection: sqlite3.Connection, request_id: str, fingerprint: str,
    ) -> dict | None:
        """Read the idempotency table only (ADR-005 §2, REQ-ADS-ARCH-007)."""
        row = connection.execute(
            "SELECT fingerprint, response_json FROM requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            return None
        if row["fingerprint"] != fingerprint:
            raise RequestConflict("request_id was already used for different input")
        try:
            result = json.loads(row["response_json"])
        except (TypeError, ValueError) as exc:
            raise LedgerError("saved response is invalid JSON") from exc
        if not isinstance(result, dict):
            raise LedgerError("saved response must be an object")
        return result

    def lookup(self, request_id: str, fingerprint: str) -> dict | None:
        """Return the exact saved response or reject ID conflict (ADR-005 §2)."""
        _text(request_id, "request_id")
        _text(fingerprint, "fingerprint")
        with self._lock:
            try:
                return self._lookup(self._connection(), request_id, fingerprint)
            except sqlite3.Error as exc:
                raise LedgerError("request lookup failed") from exc

    def finalize(
        self, request_id: str, fingerprint: str, result: dict, evidence: dict, *,
        ad_id: str | None = None, charge_cents: int = 0,
    ) -> dict:
        """Atomically settle once and persist evidence (ADR-005 §2).

        Enforces REQ-ADS-ARCH-005/006/007/008/010, REQ-ADS-FR-007/008 and
        INV-ADS-012. A raced retry returns the original committed response;
        all injected debit/audit/commit failures roll the transaction back.
        """
        _text(request_id, "request_id")
        _text(fingerprint, "fingerprint")
        if type(charge_cents) is not int or charge_cents < 0:
            raise LedgerError("charge_cents must be a nonnegative integer")
        if ad_id is not None:
            _text(ad_id, "ad_id")
        if not isinstance(result, dict) or not isinstance(evidence, dict):
            raise LedgerError("result and evidence must be objects")
        # Snapshot mutable caller data before opening the transaction.
        saved = json.loads(_json(result))
        captured = json.loads(_json(evidence))
        with self._transaction() as connection:
            repeated = self._lookup(connection, request_id, fingerprint)
            if repeated is not None:
                return repeated
            if saved.get("request_id") != request_id:
                raise LedgerError("result request_id must match settlement request_id")
            audit_id = _text(saved.get("audit_id"), "audit_id")
            if saved.get("kind") not in {"ad", "no_ad"}:
                raise LedgerError("result kind must be ad or no_ad")
            before = after = None
            if ad_id is None:
                if charge_cents != 0 or saved["kind"] != "no_ad":
                    raise LedgerError("a no-ad decision must have no charge or winner")
            else:
                if saved["kind"] != "ad":
                    raise LedgerError("charged settlement requires an ad result")
                ad = saved.get("ad")
                if not isinstance(ad, dict) or ad.get("ad_id") != ad_id:
                    raise LedgerError("result ad_id must match settlement winner")
                row = connection.execute("SELECT * FROM budget WHERE ad_id = ?",
                                         (ad_id,)).fetchone()
                if row is None:
                    raise LedgerError("settlement winner is not seeded")
                if charge_cents != row["bid_cents"]:
                    raise LedgerError("charge must equal the persisted bid_cents")
                if row["status"] != "active" or row["remaining_cents"] < charge_cents:
                    raise InsufficientBudget("winner is inactive or no longer affordable")
                before = row["remaining_cents"]
                after = before - charge_cents
                status = "exhausted" if after == 0 else "active"
                connection.execute(
                    "UPDATE budget SET spent_cents = spent_cents + ?, "
                    "remaining_cents = ?, status = ? WHERE ad_id = ?",
                    (charge_cents, after, status, ad_id),
                )
                auction = saved.setdefault("auction", {})
                if not isinstance(auction, dict):
                    raise LedgerError("result auction must be an object")
                auction.update(bid_cents=row["bid_cents"], price_cents=charge_cents,
                               budget_before_cents=before, budget_after_cents=after)
            self._fault("after_debit")
            response_json = _json(saved)
            connection.execute(
                "INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?)",
                (request_id, fingerprint, response_json, audit_id, ad_id, charge_cents),
            )
            record = {
                "request_id": request_id, "audit_id": audit_id, "final": saved,
                "evidence": captured,
                "settlement": {"ad_id": ad_id, "charge_cents": charge_cents,
                               "budget_before_cents": before,
                               "budget_after_cents": after},
            }
            self._fault("before_audit")
            connection.execute("INSERT INTO audit VALUES (?, ?, ?)",
                               (audit_id, request_id, _json(record)))
            self._fault("before_commit")
            return saved

    def _fault(self, stage: str) -> None:
        """Expose rollback verification points for REQ-ADS-ARCH-007/GOV-001."""
        if self._fault_hook is not None:
            self._fault_hook(stage)

    def audit_records(self) -> list[dict]:
        """Read canonical evidence offline only (REQ-ADS-FR-008, INV-ADS-012)."""
        with self._lock:
            try:
                rows = self._connection().execute(
                    "SELECT record_json FROM audit ORDER BY rowid"
                ).fetchall()
                return [json.loads(row["record_json"]) for row in rows]
            except (sqlite3.Error, ValueError, TypeError) as exc:
                raise LedgerError("cannot read canonical audit evidence") from exc

    def close(self) -> None:
        """Close this instance's connection (ADR-005 §2 persistent state)."""
        with self._lock:
            if not self._closed:
                try:
                    self._connection().close()
                except sqlite3.Error as exc:
                    raise LedgerError("cannot close ledger") from exc
                self._closed = True

    def __enter__(self) -> Ledger:
        """Use the ledger as a context manager (ADR-005 §2)."""
        self._connection()
        return self

    def __exit__(self, *_: object) -> None:
        """Release resources after settlement work (ADR-005 §2)."""
        self.close()
