# ProductionFinance

Total landed cost of one identical production, priced per city, with every figure sourced, dated, and provably matching what a government actually paid.

## Status

This is a hackathon build in progress. No figure the application computes is authoritative until its jurisdiction model is validated against a government-disclosed award figure.

## Installation

```bash
uv sync
```

## Running

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
bash scripts/smoke.sh
```

## Repository layout

- `app/` — the Python backend: FastAPI skeleton, pricing engine, jurisdiction rule loading
- `tests/` — pytest suite, including validation-pair fixtures
- `sources/` — archived government source documents (byte-for-byte, cited by every figure)
- `deploy/` — systemd unit, Apache vhost config, and the deploy script for the host
- `scripts/` — reusable operational scripts, including the end-to-end HTTP smoke check
- `.planning/` — the GSD planning artifacts for this project: roadmap, requirements, phase plans and research

## Provenance

Strategy notes: [`productionfinance-brief.md`](./productionfinance-brief.md), [`idea-2-incentives.md`](./idea-2-incentives.md), [`feasibility-incentives.md`](./feasibility-incentives.md), [`hackathon-brief.md`](./hackathon-brief.md), and the full planning history in [`.planning/`](./.planning/).

Every figure this project encodes carries a source URL and the date it was checked.

## Licence

MIT — see [`LICENSE`](./LICENSE).
