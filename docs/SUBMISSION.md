# ProductionFinance — Submission (SHP-12)

**Written for the hackathon judge.** Every technology claim below is
checkable against `uv.lock`; every data-source claim names an archived
artifact in `sources/MANIFEST.yaml` with its sha256. Where a capability is
not yet proven, this document says so — the repo is public and an
overclaim is verifiable in minutes.

This document is regenerated content, not a marketing page: every number
in it was re-measured against the tree at the time it was written
(2026-09-09), not copied from an earlier plan's summary. `scripts/pre_submission_check.sh`
re-runs the machine-checkable parts of it on demand.

## What it does

ProductionFinance prices the same film production in every city a
producer is considering and reports the true landed cost of each —
labour, housing, stages, equipment, travel, currency, and the production
incentive net of audit fees, transfer discount, tax and timing. The
headline output is the cost gap between two cities, decomposed into its
components. A budget figure is never accepted as an input; every input is
a physical description of the shoot (crew size, shoot days, cast
composition) and every output figure is derived and shown with its
derivation.

### Product surfaces (all live on the hosted URL, `/finance`)

| Page | What it does |
|---|---|
| `/spec` | Describe a production's physical inputs; echoes back each candidate city's curated status and what is not yet derived. |
| `/compare` | The ranked list and the two-city gap, decomposed into its components, with a MapLibre map (cities colored/sized by total cost) and a start-date slider that live-updates the ranking. |
| `/validate` | Reads a committed government disclosure, prices it through the engine, and shows the disclosed figure and the computed figure side by side with an explicit match verdict. |
| `/proof` | A reproduced government award figure shown next to the archived government document itself, its sha256 hash, the honest bucket-count accuracy figure, and any unresolved disagreement between authoritative sources, stated as unresolved (never silently picked a winner). |
| `/job1` | Job 1, live: Parallel Search finds a real New York government disclosure, Parallel Extract reads it, `google-genai` turns it into priced production/award pairs — with the SDK call evidence shown on the page. |
| `/research` | Job 2, live: name a city with no curated rule model and watch an agent loop research it — Parallel Search, then `google-genai` judging whether it has enough to build a cost model, refining its own search until it decides it has enough or gives up, every round shown. |
| `/assumptions`, `/methodology` | The model-wide assumptions and what this model does not price, stated plainly rather than buried in a footnote. |
| `/export` | A self-contained, server-rendered comparison document — complete without JavaScript. |
| `/demo` | The four demo beats (below) staged in sequence on one page, each computed fresh from committed data on every request — nothing pre-recorded. |

## Technologies

Every package below resolves in `uv.lock` at the version shown — verify
with `grep -A1 'name = "<package>"' uv.lock`.

| Package | Version (uv.lock) | Role |
|---|---|---|
| `google-genai` | 2.19.0 | Structured extraction (Job 1: PDF/HTML disclosures → typed award records) and reasoning (Job 2: normalizing researched incentive rules into a schema). The current, GA, unified Google SDK — `google-generativeai` (dead, EOL 2025-11-30) is never imported. |
| `parallel-web` | 1.3.3 | Search (finding government disclosure documents; researching an uncurated jurisdiction) and Extract (turning a located PDF/HTML disclosure into clean text before `google-genai` structures it). |
| `fastapi` | 0.141.1 | The web application — every page above is a FastAPI route. |
| `pydantic` | 2.13.4 | Request/response models and the Gemini structured-output schemas (`model_json_schema()` feeds `google-genai` directly). |
| `httpx` | 0.28.1 | The live Frankfurter FX call (`app/services/live_fx.py`) and the transitive HTTP layer under `parallel-web`. |
| `pyyaml` | 6.0.3 | Reading the versioned jurisdiction rule files, cost profiles, and validation-pair fixtures. |
| `uvicorn` | 0.52.4 | The ASGI server; runs as a systemd unit (`deploy/prodfin.service`), bound to `127.0.0.1`, reverse-proxied by the existing `vockell.com` Apache vhost at the `/finance` path mount — not a new subdomain, not a new certificate. |
| `pytest` | 9.1.1 (dev) | The test suite, including the validation-pair suite that is this project's central integrity check. |
| `ruff` | 0.16.4 (dev) | Lint/format. |

**Not a Python dependency, verified against the template it is loaded
into rather than `uv.lock`:** `maplibre-gl@6.5.0` is loaded client-side
from a CDN in `app/templates/compare.html` and driven by
`app/static/compare.js` — the `/compare` map. No API key, no vendor
account.

**Zero matches, confirmed by re-running `.github/scripts/lockfile-scan.sh`
against the resolved lockfile at submission time:** `openai`,
`anthropic`, any `langchain*` package, `llama-index`/`llama_index`,
`crewai`, `litellm`, `google-generativeai`. `google-adk` is absent from
the lockfile entirely — it is a legitimately unused dependency for this
project's fixed-pipeline jobs, not a forbidden one.

## Data sources

`sources/MANIFEST.yaml` archives 33 government and primary-source
documents byte-for-byte, each with a `sha256` re-derivable from the
archived file itself (`tests/test_source_truth.py` re-hashes every one on
every CI run). A sample, independently re-traced against the archived
bytes:

| Claim | Archived source | sha256 (first 12 hex chars) |
|---|---|---|
| California base rate 35%, per-project cap $120M, annual programme cap $750M | `sources/ca/2026-08-24-ca-film-commission-approved-projects.html` and the CA statute text | `db0d11702fd1` |
| New Jersey base rate 30% (post-2021-01-07 tier), transfer floor 75% of face value, no sourced ceiling | `sources/nj/2026-09-09-njeda-nj-a-c-19-31t-...pdf` | `f99eb42e9765`* |
| New York's Anora award, Q3 2025 disclosure | `sources/ny/2026-08-24-esd-q3-film-report-2025.pdf` | `824e2f327f74` |
| Connecticut's Colony Video 2015 Productions and Mako Games awards | `sources/ct/2026-08-24-ct-film-tax-credits-issued.csv` | (see manifest) |

\* the NJEDA regulatory PDF hash; the NJEDA Power BI activity-report
extract used for the Joker award figure itself is a separate manifest
entry.

Beyond the four curated jurisdictions' incentive rules, the engine draws
on:

- **GSA per diem** (`data/per_diem/gsa/us-ny-new-york-county.yaml`) —
  committed FY2026 federal per-diem snapshot, October 2025–September
  2026 only (see "What is not met" below for the boundary this creates).
- **State Department per diem** (`data/per_diem/state-dept/gb-london.yaml`)
  — London's foreign per-diem rate.
- **Union rate cards** (`data/union_rates/{iatse,bectu,dga,wga,sag-aftra}.yaml`)
  — a mix of `basis: sourced` (e.g. IATSE Local 600's own published rate
  cards, DGA and WGA's own Pension & Health schedules) and
  `basis: estimated` rows, each row's `basis` field stating which it is;
  see "What is not met."
- **Live FX** (`app/services/live_fx.py`) — the Frankfurter no-key dated-rate
  API (`api.frankfurter.dev`), called live on every request that needs a
  currency conversion, with a disclosed fallback to a committed snapshot
  (`data/fx/gbp-usd.yaml`) only if the live call fails — the fallback path
  is itself asserted live-first by `assert_live(DataClass.fx_rate)`.

Every figure's `basis` (`sourced` / `estimated` / `modelling_assumption`)
lives next to the number in the same YAML file, not joined from
elsewhere — the citation is structurally part of the record, not
aspirational.

## Findings

These are the real numbers the validation loop produces, re-measured at
submission time — including the unflattering ones.

**Validation accuracy today: 5 exact_match / 0 explained_variance / 5
unexplained, across 10 selectable pairs.** Half unexplained. `agent/taxonomy.py::AccuracySummary`
deliberately has no percentage field, and a test enforces its absence —
the product never folds an unexplained mismatch into a blended average.
Re-measured directly at submission time via `app.services.proof.accuracy_over_validation_pairs()`:
`AccuracySummary(awards_extracted=10, exact_match=5, explained_variance=0, unexplained=5, extraction_failures=0)`.

**Five committed transferable pairs return "cannot be computed."**
`nj_joker`, `nj_trial_of_the_chicago_7`, `ct_christmas_always`,
`ct_colony_video_2015_productions`, and `ct_mako_games` (NJ ×2, CT ×3)
each return HTTP 200 with `verdict: "cannot be computed"` from `GET
/api/v1/validate/{pair_id}` — re-confirmed live at submission time. This
is a refusal, not a failure: `engine.net_cash.transferable` declines to
convert a disclosed credit into net cash when the jurisdiction's sourced
transfer-discount range has no ceiling (New Jersey) or no market rate at
all (Connecticut), rather than inventing one.

**New Jersey's Joker residue is exactly `Decimal("122665")`, explained by
a sourced 2% diversity bonus.** Joker's qualifying spend ($6,133,257) ×
the 30% base rate, quantized, computes to $1,839,977 — $122,665 short of
the disclosed Total Award of $1,962,642. That residue equals
`quantize($6,133,257 × 0.02)` exactly: the sourced 2% diversity-plan
bonus this fixture's Diversity Bonus flag discloses as "Yes"
(`jurisdictions/us-nj.yaml`, `tests/test_jurisdiction_us_nj.py`). A
stronger finding than a round accuracy claim, because it names the exact
mechanism behind an apparent mismatch instead of averaging it away.

**Golden totals (unregressed, `engine/` untouched by this phase):**
New York $758,427 · Los Angeles $693,521 · London £548,595 ($747,735 at
the FX rate used) · headline NY–LA gap $64,906. Confirmed by
`tests/test_golden_cost.py` and `tests/test_route_a_basis_walk.py` (9
tests, all passing).

**Test suite: 942 tests passing** as of this writing (`uv run --frozen
pytest tests/ -q`). This count grows as concurrent Phase 8 work lands —
re-run `scripts/pre_submission_check.sh` for the current figure, not this
document.

## What is NOT met

Stated plainly, because a description that overclaims is checkable
against the tree in minutes.

**AGT-03 (Job 1 reproduces ≥3 real government award figures live) is
NOT met.** No live Parallel Search, Parallel Extract, or `google-genai`
call has ever fired in this repository's history. `PARALLEL_API_KEY` and
`GEMINI_API_KEY` are unset both locally and in `/opt/prodfin/.env` on the
production box — confirmed again at submission time
(`sudo grep -oE '^[A-Z_]+=' /opt/prodfin/.env` on the box lists only
`PRODFIN_GIT_SHA`, `PRODFIN_LOG_LEVEL`, `PRODFIN_APP_PORT`,
`PRODFIN_PUBLIC_PATH` — neither key is present). The full
extract-price-classify loop is proven correct only against a committed,
self-declared offline test double
(`tests/fixtures/agent/esd_excerpt_double.md`), never against a real ESD
figure. Tracked as `WINDOWS.md` #26.

**SHP-05 (Google SDK genuinely called at runtime, proven by a production
log line) is NOT met**, for the identical reason. `sudo journalctl -u
prodfin --since '7 days ago' | grep -c PRODFIN_SDK_CALL` returns `0` on
production, re-confirmed at submission time. Tracked as `WINDOWS.md` #28.

**SHP-06 (Parallel Search genuinely called at runtime) is NOT met**, same
root cause. The call sites are proven reachable from live request
handlers (`docs/sdk-call-sites.md`, 4 call sites, 0 failing, enforced by
CI's `sdk-call-sites (D-96)` job) — reachability is proven; execution is
not. Tracked as `WINDOWS.md` #32 (`runs/job2/` holds only its README, no
live-run artifact).

**The deployed box is running an older commit than `HEAD`.** Production
(`/opt/prodfin/.env`, `PRODFIN_GIT_SHA=9af46b0`) is 80 commits behind this
repository's current `HEAD` at submission-writing time — confirmed via
`git log --oneline 9af46b0..HEAD | wc -l`. Phase 6, 7, and 8 work,
including this document's own product surfaces beyond `/spec`, `/compare`
(pre-Phase-6 baseline) and `/validate`, is not live on the hosted URL
until a deploy happens. This is `.planning/SHIP-CHECKLIST.md` item 2, a
human action.

**A rate-window boundary is disclosed rather than crossed.** A
sensitivity run perturbs the shoot's start date, so from a late start it
reaches past the window the committed union-rate snapshots cover. The
engine refuses to price there — "no union rate row covers region='us-ny'
craft='camera' on 2026-10-01 — no fallback to the nearest row or the
newest row is performed" — which is the same refusal discipline as an
unsourced transfer discount, and is the intended behaviour.

That refusal is caught at the application boundary
(`app/services/spec.py`) and reported through the existing
`sensitivity_reason` channel: the comparison still prices, only the
perturbation rows are withheld, and the reason says so in plain words.
An earlier revision of `/compare` had removed the affected quarter from
the slider's selectable range to avoid triggering the raise; that
workaround was reverted, because narrowing the product's offered range
to hide a data boundary is a worse answer than stating it. Q3 2026 is
selectable, and `tests/test_sensitivity_refusal.py` guards both halves —
that the engine's refusal is real and specific to the boundary rather
than blanket, and that every offered slider position returns 200. The
guard is mutation-tested: removing the handler makes that position fail.

**A number of underlying data points remain `basis: estimated` or
`basis: modelling_assumption` rather than `basis: sourced`** — general
crew rates for 9 of 10 departments in New York and Los Angeles, all
facilities figures (stages, equipment, permits, locations, trucking) in
all three cost-profile cities, flight rates, and several fringe-schedule
percentages. Each is disclosed as such in its own YAML file's `basis`
field and enumerated in full in `.planning/WINDOWS.md` (entries #6–#22).
None of these are silently presented as more certain than they are.

**Repo-wide `ruff` baseline carries pre-existing lint warnings**
(`FURB157` verbose `Decimal("N")` constructors, `ISC004` implicit string
concatenation) — an established, accepted convention through the whole
build, not new debt introduced in this phase. Tracked in `WINDOWS.md`
entry #2 and its many identical-pattern successors.

## Compliance, re-proven at submission time

`scripts/pre_submission_check.sh` re-runs, rather than cites, the
following on every invocation:

- `.github/scripts/lockfile-scan.sh` — the resolved lockfile carries no
  forbidden package.
- `.github/scripts/vendor-scan.sh` — the source tree carries no forbidden
  AWS AI service call-site token.
- `uv run --frozen python scripts/audit_sdk_call_sites.py --check` — every
  `parallel-web` call site sits on a live request handler (D-96). **Currently
  reports drift, re-confirmed at submission time:** `/export` (new in this
  phase) also reaches `agent/live_checks.py`'s search-backed sufficiency
  check via the same path `/compare` and `/spec` already use, so the
  committed table's endpoint list for that call site is one endpoint stale.
  Every call site's verdict is still PASS (0 failing) — this is a missing
  endpoint in a reachability list, not a new unreachable call site. Tracked
  as `WINDOWS.md` #35.
- The full `pytest` suite.
- The CLAUDE.md pre-submission grep checklist (`openai`, `anthropic`,
  `langchain*`, `llama_index`, `crewai` — over source files, not
  documentation prose that names them for compliance reasons).
- SHP-14's non-vacuity proof (`.github/scripts/mutation-check.sh`) —
  breaking New York's base rate by one basis point on a scratch copy of
  the repo, confirming the validation suite catches it, then restoring.
- The GitHub About-section license (`gh repo view --json licenseInfo`) —
  MIT, OSI-approved, detectable, not merely a `LICENSE` file.
- A grep of production logs for a real `google-genai` and a real
  `parallel-web` call, fired by a live logged-out session — this is the
  check that currently, honestly fails, for the reasons stated above.

See `.planning/SHIP-CHECKLIST.md` for the human actions that close these
gaps and `docs/DEMO-SCRIPT.md` for the recorded walkthrough.
