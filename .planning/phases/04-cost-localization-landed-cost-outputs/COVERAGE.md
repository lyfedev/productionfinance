# API Coverage — Phase 4 external data surfaces

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

**Context.** Phase 4 adds **no runtime external-API integration**. D-57 is explicit: the phase makes no runtime network call and adds no dependency; every cost input lands as a committed, dated snapshot read with the `pyyaml` already in `pyproject.toml`. The external services below are touched exactly once, during data acquisition, and their output is committed to the repo. `DataFreshnessGate` and the live cache boundary are Phase 7's artifact, and these snapshots become its cold-start seed.

The matrix below therefore records, per capability, whether Phase 4 uses it as a one-time acquisition (`INTEGRATE`) or deliberately does not (`OPT-OUT`), so no capability is an undecided hole.

| capability | decision | reason |
|---|---|---|
| gsa.per-diem-bulk-file | INTEGRATE | One-time download of the no-key CSV/Excel bulk file; committed to `data/per_diem/gsa/` (plan 04-03) |
| gsa.per-diem-json-api | OPT-OUT | Requires a registered API key and would be a runtime dependency — forbidden by D-57; the no-key bulk file supplies the same data |
| gsa.per-diem-live-refresh | OPT-OUT | Phase 7 owns the live refresh through `DataFreshnessGate`; half-building the cache boundary here would leave Phase 7 inheriting a partial one |
| state-dept.foreign-per-diem-table | INTEGRATE | One-time read of the DSSR Section 925 / bulk Excel London row; committed to `data/per_diem/state-dept/` (plan 04-05) |
| state-dept.live-refresh | OPT-OUT | Phase 7, same reason as the GSA live refresh |
| frankfurter.dated-rate | INTEGRATE | One-time fetch of the dated GBP→USD rate; archived under `sources/fx/` and committed to `data/fx/gbp-usd.yaml` (plan 04-05) |
| frankfurter.latest-rate | OPT-OUT | A live "latest" call is a runtime network dependency; D-57 forbids one in this phase and D-74 requires a dated committed snapshot instead |
| frankfurter.time-series | OPT-OUT | Not needed — a single dated rate per pair satisfies COST-08; a series would only serve a historical index, which is Milestone 2 |
| frankfurter.currency-list | OPT-OUT | Supported currency codes are a small closed committed tuple in `engine/fx.py`, which is also the path-safety control for snapshot file selection |
| union-sites.rate-card-documents | INTEGRATE | One-time fetch and byte-archive of IATSE, SAG-AFTRA, DGA, WGA and BECTU published rate cards under `sources/unions/` (plans 04-02, 04-05) |
| union-sites.live-refresh | OPT-OUT | No union publishes a machine-readable rate API; and a live refresh would be a runtime dependency forbidden by D-57 |
| parallel.search | OPT-OUT | Parallel is imported and called at runtime in Phase 7 (live research for uncurated cities); Phase 4 is offline-deterministic by design so that its golden cost totals are meaningful in CI |
| parallel.extract | OPT-OUT | Phase 5 (Job 1 — parsing government award PDFs); Phase 4 parses no disclosure document |
| google-genai.structured-extraction | OPT-OUT | Phase 5 (Job 1) and Phase 7 (Job 2); Phase 4 imports no AI SDK at all — a plan proposing one is a scope error |
| aws.textract | OPT-OUT | Forbidden by name — every AWS AI endpoint is a Stage One disqualification, and Textract is the specific trap on this project because per-diem files and union rate cards are PDFs. All document reading is a plain fetch and parse. |

**Enforcement.** The zero-new-dependency rule is enforced by the existing `lockfile-scan` CI job plus a per-plan acceptance criterion asserting `git diff --stat pyproject.toml uv.lock` is empty. The no-AWS-AI rule is enforced by the existing `vendor-scan` CI job plus explicit grep acceptance criteria in plans 04-02 and 04-03.
