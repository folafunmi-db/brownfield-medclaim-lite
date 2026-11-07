"""CSV export of a patient statement (T-102).

Era-3 module: a pure consumer of ``build_statement()``. One row per statement
line (claim id, service date, charge, voided flag) followed by a single
``TOTALS`` row carrying total charges, total adjustments, and balance.

Money is stored in integer cents everywhere else in the system; conversion to
dollars-and-cents strings happens only here, at the rendering edge, and never
goes through floats.
"""
from __future__ import annotations

import csv
import io

from medclaim.billing.statement import build_statement
from medclaim.models import Statement

CSV_HEADER = ["claim_id", "service_date", "charge", "voided"]
TOTALS_LABEL = "TOTALS"


def _cents_to_dollars(cents: int) -> str:
    """Render integer cents as a dollars-and-cents string, e.g. 40000 -> '400.00'."""
    sign = "-" if cents < 0 else ""
    dollars, remainder = divmod(abs(cents), 100)
    return f"{sign}{dollars}.{remainder:02d}"


def statement_to_csv(stmt: Statement) -> str:
    """Render a Statement as CSV text.

    Header, one row per line, then a final ``TOTALS`` row with total charges,
    total adjustments, and balance (in that order, all in dollars).
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_HEADER)
    for line in stmt.lines:
        writer.writerow([
            line.claim_id,
            line.service_date,
            _cents_to_dollars(line.charge_cents),
            "true" if line.is_voided else "false",
        ])
    writer.writerow([
        TOTALS_LABEL,
        _cents_to_dollars(stmt.total_charges_cents),
        _cents_to_dollars(stmt.total_adjustments_cents),
        _cents_to_dollars(stmt.balance_cents),
    ])
    return buf.getvalue()


def export_statement_csv(patient_id: str) -> str:
    """Build the patient's current statement and render it as CSV."""
    return statement_to_csv(build_statement(patient_id))
