# Healthcare Claims & Patient Billing System – Lite Version

Legacy healthcare claims & patient billing service. Handles the claim lifecycle
(submit / adjudicate / void), payer contracts, patient statements, and
notifications.

This is an **inherited** system – roughly eight years old, built across three
teams, and it shows. New work follows the current (era-3) style; a lot of the
older code does not. Read `docs/domain-primer.md` before your first change, and
`docs/adr/` for the decisions behind the parts that look strange.

## Stack

Python 3.12, FastAPI (API layer only), SQLite. No Docker, no cloud, no network.

## Quick start

```bash
python -m pip install -e ".[dev]"   # fastapi, pydantic, pytest, pytest-mock, ruff
make seed                            # build medclaim.db from seed/data/*.json
make test                            # run the pytest suite
make run                             # serve the API at http://localhost:8000
```

`make seed` is deterministic: the same JSON produces the same database every
time. `make test` seeds a database and runs pytest; the full suite is green and
runs in a few seconds.

## Layout

```
medclaim/
  api.py            FastAPI app (era 3)
  db.py             SQLite connection + schema
  models.py         shared dataclasses (era 2)
  claims/           claim submit / void  (era 1 + era 2)
  billing/          statements, contracts, history  (era 1)
  repo/             data-access layer, half-adopted  (era 2)
  notify/           patient notifications  (era 2)
seed/               deterministic seed data + builder
tests/              pytest suite
docs/               domain primer, ADRs, tickets
```

## Notes for newcomers

- Money is integer **cents** everywhere. Some old comments say dollars; the
  comments are wrong, the integers are right.
- `make test` runs against a throwaway database, never your dev one.
- There is no agent-instructions file in this repo. Writing one is the first
  exercise.
