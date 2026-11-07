"""HTTP API (era 3, current team).

Thin FastAPI layer over the billing/claims logic. Pydantic models at the
boundary; the interesting work lives in the modules this delegates to. Most of
the exercises drive those modules directly rather than going over HTTP.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from medclaim.billing.csv_export import statement_to_csv
from medclaim.billing.history import get_statement_history
from medclaim.billing.render_legacy import render_statement_legacy
from medclaim.billing.statement import build_statement

app = FastAPI(title="med-claim-lite", version="0.1.0")


class StatementLineOut(BaseModel):
    claim_id: str
    service_date: str
    charge_cents: int
    is_voided: bool


class StatementOut(BaseModel):
    patient_id: str
    total_charges_cents: int
    total_adjustments_cents: int
    balance_cents: int
    lines: list[StatementLineOut]


@app.get("/patients/{patient_id}/statement", response_model=StatementOut)
def patient_statement(patient_id: str) -> StatementOut:
    stmt = build_statement(patient_id)
    return StatementOut(
        patient_id=stmt.patient_id,
        total_charges_cents=stmt.total_charges_cents,
        total_adjustments_cents=stmt.total_adjustments_cents,
        balance_cents=stmt.balance_cents,
        lines=[
            StatementLineOut(
                claim_id=ln.claim_id,
                service_date=ln.service_date,
                charge_cents=ln.charge_cents,
                is_voided=ln.is_voided,
            )
            for ln in stmt.lines
        ],
    )


@app.get("/patients/{patient_id}/history", response_model=list[StatementLineOut])
def patient_history(patient_id: str) -> list[StatementLineOut]:
    return [
        StatementLineOut(
            claim_id=ln.claim_id,
            service_date=ln.service_date,
            charge_cents=ln.charge_cents,
            is_voided=ln.is_voided,
        )
        for ln in get_statement_history(patient_id)
    ]


@app.get("/patients/{patient_id}/statement.csv")
def patient_statement_csv(patient_id: str) -> Response:
    # T-102: CSV export of the current statement. 404-on-empty mirrors the
    # statement.txt endpoint below.
    stmt = build_statement(patient_id)
    if not stmt.lines:
        raise HTTPException(status_code=404, detail="no statement for patient")
    return Response(content=statement_to_csv(stmt), media_type="text/csv")


@app.get("/patients/{patient_id}/statement.txt")
def patient_statement_legacy_text(patient_id: str) -> Response:
    # the ONE remaining caller of the deprecated renderer (ADR-004). A downstream
    # print job still parses this exact fixed-width text. Do not "modernise" it.
    stmt = build_statement(patient_id)
    if not stmt.lines:
        raise HTTPException(status_code=404, detail="no statement for patient")
    return Response(content=render_statement_legacy(stmt), media_type="text/plain")
