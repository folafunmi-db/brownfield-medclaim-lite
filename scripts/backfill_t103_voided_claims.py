"""One-time backfill for T-103: flag claims voided through the legacy path.

Before the T-103 fix, ``void_claim_legacy`` recorded the void in ``void_log``
but never set ``claims.is_deleted``, so legacy-voided claims kept appearing in
statement history. The code fix only covers voids performed after it shipped;
this script repairs the rows voided before it.

Per ADR-002, ``void_log`` is authoritative — every void is recorded there
regardless of path — so a claim with a ``void_log`` row and ``is_deleted``
not already 1 was voided and must be hidden. Era-1 rows whose ``is_deleted``
is NULL but have no void record are legitimate active claims and are left
untouched (the earlier incident described in ADR-002).

The script is idempotent: rerunning it after the backfill updates 0 rows.

Usage:
    python scripts/backfill_t103_voided_claims.py [--db PATH]

Without ``--db`` it uses the active database (``MEDCLAIM_DB`` or the repo
default).
"""
from __future__ import annotations

import argparse

from medclaim import db


def backfill_voided_claims() -> int:
    """Set ``is_deleted = 1`` on every claim with a void record.

    Returns the number of claim rows updated.
    """
    conn = db.connect()
    try:
        cursor = conn.execute(
            "update claims set is_deleted = 1 "
            "where id in (select claim_id from void_log) "
            "and is_deleted is not 1"
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        help="path to the SQLite database (default: the active database)",
    )
    args = parser.parse_args()
    if args.db:
        db.set_active_db(args.db)
    updated = backfill_voided_claims()
    print(f"T-103 backfill: {updated} claim(s) marked voided "
          f"in {db.active_db_path()}")


if __name__ == "__main__":
    main()
