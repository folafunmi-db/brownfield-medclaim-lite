"""Tests for the T-103 backfill (scripts/backfill_t103_voided_claims.py).

The fixed void paths now set is_deleted themselves, so these tests recreate
the historical broken state directly: a void_log row with the claim's
is_deleted left as it was before the fix.
"""
from datetime import datetime

from medclaim import db
from medclaim.billing.history import get_statement_history
from scripts.backfill_t103_voided_claims import backfill_voided_claims


def _legacy_void_without_flag(claim_id):
    """Recreate a pre-fix legacy void: void_log row only, flag untouched."""
    conn = db.connect()
    try:
        conn.execute(
            "insert into void_log (claim_id, reason, method, voided_at) "
            "values (?, 'historical', 'legacy', ?)",
            (claim_id, datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def _set_is_deleted(claim_id, value):
    conn = db.connect()
    try:
        conn.execute(
            "update claims set is_deleted = ? where id = ?", (value, claim_id)
        )
        conn.commit()
    finally:
        conn.close()


def _is_deleted(claim_id):
    conn = db.connect()
    try:
        row = conn.execute(
            "select is_deleted from claims where id = ?", (claim_id,)
        ).fetchone()
    finally:
        conn.close()
    return row["is_deleted"]


def test_backfill_hides_historically_legacy_voided_claims(client, seed):
    claim = seed.claim(patient_id="P-1042", amount_cents=15_000)
    _set_is_deleted(claim.id, None)  # era-1 style row
    _legacy_void_without_flag(claim.id)

    assert claim.id in [ln.claim_id for ln in get_statement_history("P-1042")]

    updated = backfill_voided_claims()

    assert updated == 1
    assert _is_deleted(claim.id) == 1
    assert claim.id not in [ln.claim_id for ln in get_statement_history("P-1042")]


def test_backfill_leaves_unvoided_era1_null_rows_visible(client, seed):
    # ADR-002: NULL without a void record is a legitimate active era-1 claim.
    claim = seed.claim(patient_id="P-1042", amount_cents=9_000)
    _set_is_deleted(claim.id, None)

    backfill_voided_claims()

    assert _is_deleted(claim.id) is None
    assert claim.id in [ln.claim_id for ln in get_statement_history("P-1042")]


def test_backfill_leaves_active_claims_untouched_and_is_idempotent(client, seed):
    active = seed.claim(patient_id="P-1042", amount_cents=5_000)
    voided = seed.claim(patient_id="P-1042", amount_cents=7_000)
    _legacy_void_without_flag(voided.id)  # is_deleted still 0

    assert backfill_voided_claims() == 1
    assert _is_deleted(active.id) == 0
    assert _is_deleted(voided.id) == 1
    # rerun updates nothing
    assert backfill_voided_claims() == 0
