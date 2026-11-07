# ADR-003: Contract resolution should use the claim service date

**Status:** Accepted — enforced
**Date:** 2023

## Context

Payer contracts renew. The allowed rate that applies to a claim depends on the
claim's **service date**, not on the current date. `contracts.py` provides two
lookups:

- `current_contract(payer_id)` — the latest contract for a payer, ignoring date.
- `contract_for_date(payer_id, service_date)` — the contract in force on a date.

`contract_for_date` is correct for billing. `current_contract` is a convenience
that is only safe when a payer has never renewed.

## Decision

Billing code should resolve contracts with `contract_for_date`. Statements are
generated through a single wrapper, `resolve_contract(payer_id, service_date)`,
so there is one place to get this right.

## Status note

Enforced (T-101). `resolve_contract` now delegates to `contract_for_date`, so
statements use the contract in force on the service date. `build_statement`
resolves through the wrapper **per claim line**: a statement that spans a payer
renewal rates each claim by its own service date rather than assuming a single
contract period per statement.
