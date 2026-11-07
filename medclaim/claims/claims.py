# claims/claims.py  --  claim submit + void
#
# Mixed vintage. submit_claim and void_claim_legacy are ORIGINAL BUILD (2018).
# void_claim (the modern path) was added with the soft-delete work in 2022
# (ADR-002). Both void paths still exist; new code should use void_claim.

import logging
import uuid
from datetime import datetime

from medclaim import db

log = logging.getLogger("medclaim.claims")


def submit_claim(patient_id, payer_id, service_date, amount_cents, adjustment_cents=0):
    claim_id = "C-" + uuid.uuid4().hex[:10]
    conn = db.connect()
    try:
        conn.execute(
            "insert into claims (id, patient_id, payer_id, service_date, "
            "amount_cents, adjustment_cents, status, is_deleted) "
            "values (?, ?, ?, ?, ?, ?, 'submitted', 0)",
            (claim_id, patient_id, payer_id, service_date,
             amount_cents, adjustment_cents),
        )
        conn.commit()
    finally:
        conn.close()
    return claim_id


def void_claim(claim_id, reason=None):
    # MODERN void path (2022, ADR-002). Flip is_deleted to 1 AND record the void.
    # This is the one new code should call.
    conn = db.connect()
    try:
        conn.execute("update claims set is_deleted = 1 where id = ?", (claim_id,))
        conn.execute(
            "insert into void_log (claim_id, reason, method, voided_at) "
            "values (?, ?, 'modern', ?)",
            (claim_id, reason, datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def void_claim_legacy(claim_id, reason=None):
    # ORIGINAL void path (2018). Predates the is_deleted column, so it records the
    # void in void_log and nowhere else. Still called from the old ERA-import and
    # correction flows.
    conn = db.connect()
    try:
        # pull the patient for the audit line
        row = conn.execute(
            "select p.name, p.mrn, c.patient_id "
            "from claims c join patients p on p.patient_id = c.patient_id "
            "where c.id = ?",
            (claim_id,),
        ).fetchone()
        if row is not None:
            pat_id = row["patient_id"]   # era-1 called it pat_id here
            # old audit logging. writes the patient name and MRN into the log.
            log.info("legacy void: claim=%s pat=%s patient=%s mrn=%s reason=%s",
                     claim_id, pat_id, row["name"], row["mrn"], reason)
        # T-103: the legacy path predates is_deleted, so it only wrote the
        # void_log row and the claim stayed visible on statements. Set the
        # soft-delete flag too, matching the modern path (ADR-002).
        conn.execute("update claims set is_deleted = 1 where id = ?", (claim_id,))
        conn.execute(
            "insert into void_log (claim_id, reason, method, voided_at) "
            "values (?, ?, 'legacy', ?)",
            (claim_id, reason, datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()
