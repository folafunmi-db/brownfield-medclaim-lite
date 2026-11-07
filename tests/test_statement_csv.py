"""T-102: CSV export of a patient's current statement.

Seed fixture facts used here (same as the T-101 tests):
- P-1077 (BCBS-001) has a single unpaid claim C-1077-01: 2023-12-28, 40000 cents.
"""
import csv

from fastapi.testclient import TestClient

from medclaim.api import app
from medclaim.billing.csv_export import export_statement_csv, statement_to_csv
from medclaim.billing.statement import build_statement

HEADER = ["claim_id", "service_date", "charge", "voided"]


def _parse(csv_text):
    return list(csv.reader(csv_text.splitlines()))


def test_csv_has_header_line_rows_and_totals_row(client, seed):
    # add a second claim with an adjustment so totals exercise all three sums.
    new = seed.claim("P-1077", 12345, adjustment_cents=2345,
                     service_date="2024-06-15")

    rows = _parse(export_statement_csv("P-1077"))

    assert rows[0] == HEADER
    body, totals = rows[1:-1], rows[-1]

    by_claim = {r[0]: r for r in body}
    assert by_claim["C-1077-01"] == ["C-1077-01", "2023-12-28", "400.00", "false"]
    assert by_claim[new.id] == [new.id, "2024-06-15", "123.45", "false"]
    assert len(body) == 2

    # TOTALS, total charges, total adjustments, balance — all in dollars.
    # charges 40000+12345, adjustments 2345, no payments -> balance 50000.
    assert totals == ["TOTALS", "523.45", "23.45", "500.00"]


def test_totals_row_matches_statement_balance(client):
    stmt = build_statement("P-1077")
    totals = _parse(statement_to_csv(stmt))[-1]
    assert totals == [
        "TOTALS",
        "400.00",
        "0.00",
        "400.00",
    ]
    assert stmt.balance_cents == 40000


def test_unknown_patient_renders_header_and_zero_totals(client):
    rows = _parse(export_statement_csv("P-NOPE"))
    assert rows == [HEADER, ["TOTALS", "0.00", "0.00", "0.00"]]


def test_csv_endpoint_serves_text_csv(client):
    http = TestClient(app)
    resp = http.get("/patients/P-1077/statement.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    rows = _parse(resp.text)
    assert rows[0] == HEADER
    assert rows[-1][0] == "TOTALS"


def test_csv_endpoint_404s_when_no_statement(client):
    http = TestClient(app)
    resp = http.get("/patients/P-NOPE/statement.csv")
    assert resp.status_code == 404
