"""T-101 regression tests: statement amounts must use the contract in force on
each claim's service date, not the payer's current contract.

Seed fixture facts used here:
- P-1077 (BCBS-001) has a single unpaid claim C-1077-01: 2023-12-28, 40000 cents.
- BCBS-001: 80% allowed through 2023-12-31, 70% from 2024-01-01.
"""
from medclaim.billing.statement import build_statement


def _patient_due_by_claim(rendered_text):
    """Parse the rendered statement into {claim_id: patient_due_cents}."""
    due = {}
    current_claim = None
    for line in rendered_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("C-"):
            current_claim = stripped.split()[0]
        elif stripped.startswith("you may owe (est)") and current_claim:
            due[current_claim] = int(stripped.split()[-1])
    return due


def test_december_claim_uses_december_rate(client):
    # T-101 repro: 40000 at the 2023 rate (80%) -> patient due 8000.
    # the buggy current-contract path (70%) showed 12000.
    stmt = build_statement("P-1077")
    due = _patient_due_by_claim(stmt.rendered_text)
    assert due["C-1077-01"] == 8000


def test_mixed_period_statement_rates_each_claim_by_its_own_date(client, seed):
    # a statement spanning the BCBS renewal must rate each line by its own
    # service date: Dec-2023 at 80%, Jun-2024 at 70%.
    new = seed.claim("P-1077", 10000, service_date="2024-06-15")
    stmt = build_statement("P-1077")
    due = _patient_due_by_claim(stmt.rendered_text)
    assert due["C-1077-01"] == 8000          # 40000 - 80% allowed
    assert due[new.id] == 3000               # 10000 - 70% allowed
