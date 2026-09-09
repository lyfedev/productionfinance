---
phase: 06-the-interface
status: gaps_found
verified_by: orchestrator (main thread, independent of the executing agents)
verified_at: 2026-09-09
plans: 4
summaries: 4
---

# Phase 6 Verification — The Interface

Verified against the codebase, not the plan summaries.

## Requirements

| ID | Verdict | Evidence |
|---|---|---|
| UI-01 | **PASS** | `GET /compare` returns 200 for an anonymous request with no cookie or query string; prices NY, LA, London through the real pipeline. |
| UI-02 | **PASS** | MapLibre GL 6.5.0 via a plain script tag, SRI-pinned against hashes computed from the real fetched CDN bytes; marker fill driven by a data-driven `interpolate` expression over a numeric GeoJSON property. |
| UI-03 | **PASS** | Slider re-ranks live; the client sends only `start_index` and renders a server-rendered fragment. An equivalence test proves each settled position's figures match an independent `build_comparison` at the same date. No-JS path is a native `<input type="range">` inside a GET form, proven under `TestClient` (executes no script). |
| UI-04 | **PASS** | `RankedCity.arrival` carries when the cash arrives, alongside net cost and incentive value. |
| UI-05 | **PASS** | Decomposed gap with components summing exactly to the headline, asserted as an identity. A cross-band selection renders an explicit refusal and no number. |
| UI-06 | **PASS** | `app/templates/_figure.html` renders provenance for every figure; a three-state classification (`sourced` / `computed` / `unavailable`) avoids mislabelling an aggregate — whose provenance is its input tree — as unsourced. |
| UI-08 | **PASS** | `app/services/permalink.py` is the sole persistence mechanism. Grep confirms **no `set_cookie` and no `SessionMiddleware`** anywhere in `app/`. Round-trip asserted across a generated matrix of 108 input combinations. A truncated token raises `PermalinkDecodeError` naming the missing field rather than letting defaults silently substitute. |
| UI-11 | **PASS** | `original_value`/`original_unit` are always populated; `converted_value` is strictly additive. The government figure is never replaced. |
| UI-12 | **PASS** | `cannot_determine` is a distinct third state in the `Literal["unchanged", "changed", "cannot_determine"]` union, resolved for zero-match or ambiguous multi-match, proven as a property across match counts 0/1/2/3. An unchanged link renders an explicit "No changes" banner rather than silence. |
| PRV-04 | **PASS** | `GET /assumptions` derives its rate list by walking the real `Figure.inputs` DAG; a non-vacuity test independently re-walks the tree and confirms every leaf appears. Print stylesheet, not a screenshot. |
| PRV-05 | **PASS** | `GET /methodology` returns 200 at a stable linkable URL. |

## Honesty constraints

| Decision | Verdict | Evidence |
|---|---|---|
| D-55 two bands never interleaved | **PASS** | Separate tuples → separate `<section>`s → separate GeoJSON shapes. A test parses the rendered HTML and asserts the two `city_id` sets are disjoint. |
| D-56 unmodelled incentive never `$0` | **PASS** | Renders `unknown — not modelled` (`_ranked_list.html:86,148`). A money-shaped regex scoped to that column asserts no match. |
| D-58/D-59 basis and confidence distinct | **PASS** | Two separate spans, never concatenated; a test proves the confidence label cannot carry the four-tier source vocabulary. |
| D-78 golden totals | **PASS** | NY $758,427 / LA $693,521 / London £548,595 = $747,735 / gap $64,906. `tests/test_golden_cost.py` and `test_route_a_basis_walk.py` show an empty diff since Phase 5 planning — not edited to pass. |

## Corrected during verification

Plan 06-02 removed Q3 2026 from the slider to avoid an uncaught `ValueError`, recording it as a pre-existing engine bug. The engine was correct: it refuses to price a perturbed date past the committed union-rate window rather than carrying a rate forward from an expired row. The real defect was the refusal reaching the UI uncaught, and the workaround silently narrowed the product's offered range. Fixed in `55a5fa5` — the refusal is now stated through `sensitivity_reason`, and Q3 2026 is restored. Mutation-tested.

Plan 06-04 found that `collect_rate_figures` dedupes by content (correct for a printable rate list, wrong for summation) and would have reconstructed London at £491,419 instead of £548,595. Fixed before commit.

## Gaps

**The MapLibre map has not been verified visually.** Headless browsers lack WebGL2, which MapLibre 6.x requires, so the map container renders empty under automated testing. Server-rendered content displays correctly and every figure is present in the HTML body before any script runs (progressive enhancement holds), but **the map itself needs a human spot-check in a real desktop browser.**

**Phase 6 is not deployed.** The Lightsail box is running an older commit; none of this is live yet.
