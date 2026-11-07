# billing/contracts.py  --  payer contract lookups
#
# ORIGINAL BUILD (2018). Two ways to get a contract: the date-aware one and the
# quick one. Statements go through resolve_contract() so there is a single place
# that decides. See docs/adr/ADR-003 for how this is supposed to work.

from medclaim import db
from medclaim.models import Contract


def _row_to_contract(row):
    return Contract(
        rate_pct=row["rate_pct"],
        payer_id=row["payer_id"],
        effective_date=row["effective_date"],
        end_date=row["end_date"],
    )


def current_contract(payer_id):
    # latest contract on file for this payer, ignoring service date.
    # only safe when a payer has never renewed.
    conn = db.connect()
    try:
        row = conn.execute(
            "select * from contracts where payer_id = ? "
            "order by effective_date desc limit 1",
            (payer_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return _row_to_contract(row)


def contract_for_date(payer_id, service_date):
    # the contract that was in force on the service date. this is the correct
    # lookup for billing.
    conn = db.connect()
    try:
        row = conn.execute(
            "select * from contracts where payer_id = ? "
            "and effective_date <= ? "
            "and (end_date is null or end_date >= ?) "
            "order by effective_date desc limit 1",
            (payer_id, service_date, service_date),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return _row_to_contract(row)


def resolve_contract(payer_id, service_date):
    # single entry point for statement code. ADR-003: resolve by the contract in
    # force on the service date, not whatever contract is current now (T-101).
    return contract_for_date(payer_id, service_date)
