---
phase: 05-curated-breadth-the-validation-loop
verified: 2026-09-09T09:46:57Z
status: gaps_found
score: 9/12 truths verified (2 deferred as root-cause-identical to the gaps, 1 gap group covering AGT-03/SHP-05)
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "AGT-03 — Job 1 reproduces at least three published government award figures exactly (ROADMAP Phase 5 SC3, Phase 5's own declared requirement)"
    status: failed
    reason: >
      This is a live-outcome claim and it is literally false today. No live
      Parallel Search, Parallel Extract, or google-genai call has ever been
      made in this repository's history — PARALLEL_API_KEY and
      GEMINI_API_KEY/GOOGLE_API_KEY are unset both locally (confirmed this
      session: empty env vars) and on the production box
      (/opt/prodfin/.env, confirmed by 05-03-SUMMARY.md's grep -c
      immediately before its deploy, and unchanged since). No
      `runs/job1/*.json` live-run artifact exists in the repo. The full
      extract-price-classify loop is proven correct only against a
      committed, self-declared offline test double
      (tests/fixtures/agent/esd_excerpt_double.md) — zero real ESD figures
      have been reproduced. REQUIREMENTS.md correctly leaves AGT-03
      unchecked (`[ ]`); WINDOWS.md entries #26 and #28 name this
      explicitly and are still `open`. This is honest reporting by the
      phase's own artifacts, not a discovery by this verification — but
      the codebase evidence confirms the underlying SC is genuinely unmet,
      and it was assigned to Phase 5 by ROADMAP.md's own Requirements line
      ("JUR-02, JUR-03, JUR-04, AGT-01, AGT-02, AGT-03, AGT-04, AGT-08,
      AGT-09, SHP-05"), so it cannot be waved through as a later phase's
      job.
    artifacts:
      - path: "agent/job1.py"
        issue: "run_job1() is correctly built, tested offline, and matches the introspected real SDK call signatures — but has never executed a real network call end to end"
      - path: "runs/job1/"
        issue: "directory does not exist — no live run has ever been persisted"
    missing:
      - "A human must obtain PARALLEL_API_KEY and a GEMINI_API_KEY/GOOGLE_API_KEY, install them into /opt/prodfin/.env (mode 600) on the Lightsail box, restart the prodfin service, and trigger POST /job1 from a logged-out browser"
      - "The resulting run must show run_mode == \"live\" and accuracy.exact_match >= 3, and must be committed under runs/job1/"
      - "WINDOWS.md entries #26 and #28 should then be marked fixed, and REQUIREMENTS.md's AGT-03/SHP-05 rows flipped to Complete"
  - truth: "SHP-05 — a permitted Google SDK is imported and genuinely called at runtime, verified by a timestamped log line at the call site (ROADMAP Phase 5's own declared requirement)"
    status: failed
    reason: >
      The D-84 log-line mechanism (agent/telemetry.py::sdk_call) is
      correctly built, unconditional (no debug/verbosity gate — verified
      by tests/test_agent_eligibility.py::test_sdk_call_implementation_has_no_verbosity_guard),
      and wired at both the google-genai and parallel-web call sites
      (verified by direct grep of agent/gemini_client.py and
      agent/parallel_client.py). But the literal requirement text is a
      live-outcome claim — "genuinely called at runtime" — and this
      verifier confirmed directly against the deployed production page
      (https://vockell.com/finance/job1, HTTP 200) that it currently
      renders the not-configured state naming both PARALLEL_API_KEY and
      GEMINI_API_KEY, not a completed run. `journalctl -u prodfin`
      (per 05-03-SUMMARY.md and WINDOWS.md #28) contains zero
      PRODFIN_SDK_CALL lines. Same root cause and same remediation as the
      AGT-03 gap above — this is one blocker, not two.
    artifacts:
      - path: "agent/telemetry.py"
        issue: "sdk_call() context manager is correct and tested, but has never fired against a real SDK call in this environment or in production"
    missing:
      - "Same human action as AGT-03 above — the two close together via the same live run"
deferred:
  - truth: "SC2 — Job 1 ingests a published government disclosure document and extracts every production/award pair from it (ROADMAP Phase 5 SC2, literal live clause)"
    addressed_in: "Phase 8"
    evidence: "Phase 8's 'Re-verification sweep' note: 'grep production logs for at least one real Gemini call (SHP-05) and one real Parallel call (SHP-06) fired by a live logged-out session within 24 hours of submission' — the same underlying live-run gap this Phase 5 verification records, explicitly re-armed and re-checked by Phase 8, not newly built there."
  - truth: "SC5 (production-log clause only) — 'proven by a timestamped log line at the call site in production logs' (ROADMAP Phase 5 SC5)"
    addressed_in: "Phase 8"
    evidence: "Same Phase 8 'Re-verification sweep' note, naming SHP-05 and SHP-06 explicitly as gates 'armed earlier' (i.e. in Phase 5) that Phase 8 re-proves against production logs before submission."
  - truth: "SHP-06 — Parallel Search genuinely called at runtime (formally a Phase 7 requirement per REQUIREMENTS.md's own table, pulled forward into Phase 5's build only per D-80)"
    addressed_in: "Phase 7 / Phase 8"
    evidence: "REQUIREMENTS.md assigns SHP-06 to 'Phase 7 — Live Research, Caching & Durable Jobs', and Phase 8's re-verification sweep names SHP-06 explicitly alongside SHP-05."
---

# Phase 5: Curated Breadth & the Validation Loop Verification Report

**Phase Goal:** Four jurisdictions are modelled and an agent proves the models against published government disclosures, reporting a real, honest accuracy figure.
**Verified:** 2026-09-09T09:46:57Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Summary judgment

Everything this phase could build and prove without a network credential is
built, wired, live-deployed, and independently verified against the actual
codebase and (where reachable) the live production URL in this session —
not just against the SUMMARYs' claims. Four jurisdictions are genuinely
modelled from primary government sources (three of their figures
spot-checked byte-for-byte against the archived source text below), all
four of AGT-08's guardrails are wired onto the real extraction path and
each has a firing test, the mismatch taxonomy is a genuinely closed
three-value enum with no blended figure anywhere, and the honest-refusal
path was independently exercised live against all five transferable
pairs the phase names, returning a real refusal reason and HTTP 200 —
never a fabricated number, never a 500.

The gap is real, not a summary-rounding error: **AGT-03 and SHP-05 are
both explicitly listed as Phase 5's own requirements in ROADMAP.md, and
both are live-outcome claims that remain false** — no live Parallel or
Gemini call has ever fired, in this session or in production, because no
API key exists anywhere this phase can reach. This is exactly what the
phase's own artifacts (WINDOWS.md #26/#28, REQUIREMENTS.md's `[ ]` rows)
already say, and this verification independently confirmed it rather than
taking the SUMMARYs' word for it (empty env vars checked directly;
production page fetched directly; `runs/job1/` confirmed absent). The
phase did not overclaim — but the phase's own ROADMAP success criteria are
not yet fully true, and an honest verification records that as
`gaps_found`, not `passed`, however well-documented and however external
the blocker.

## Goal Achievement

### Observable Truths (dispatcher's "what must be true", verified against the tree)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Four jurisdictions modelled, loaded, wired into `/validate` | ✓ VERIFIED | `jurisdictions/{us-ny,us-ca,us-nj,us-ct}.yaml` all exist; `app/services/_paths.py::RULESET_PATH_BY_JURISDICTION` maps all four; full suite (720 tests) passes including per-jurisdiction reproduction tests |
| 2 | Every figure sourced — spot-checked | ✓ VERIFIED | See "Figure spot-checks" below — CA 35% rate, CA $120M/$750M caps, NJ 30% pre-2021 rate, NJ 75% transfer floor, CT Colony Video / Mako Games CSV rows all traced byte-for-byte to archived source text with matching sha256 |
| 3 | AGT-08's four guardrails present, wired, each with a firing test | ✓ VERIFIED | `agent/groundedness.py`, `agent/enactment.py` (new, 05-07), `agent/parallel_client.py::is_primary_government_url`, `agent/numbers.py::parse_money` (pre-existing) — all four wired into `agent/job1.py`'s real path (grep-confirmed at lines 43/45/246/372); `tests/test_agent_guardrails.py` 16/16 pass including the introspecting registry test |
| 4 | Mismatch taxonomy closed 3-value enum, bucket counts only | ✓ VERIFIED | `agent/taxonomy.py::MatchClass` has exactly 3 members; `AccuracySummary` asserted (by a dedicated test walking `dataclasses.fields()`/`dir()`) to expose no pct/percent/mean/average/blended/aggregate/error field |
| 5 | Honest-refusal path for the five transferable pairs | ✓ VERIFIED | Independently queried live via TestClient this session: `nj_joker`, `nj_trial_of_the_chicago_7`, `ct_christmas_always`, `ct_colony_video_2015_productions`, `ct_mako_games` all return HTTP 200, `verdict: "cannot be computed"`, a real named reason — never $0, never fabricated, never 500 |
| 6 | `disclosure_stage` reaches the page; "Credit issued" only when genuinely issued | ✓ VERIFIED | Independently queried live: `ny_anora→issued`, `ca_clueless_s1→allocated`, `nj_joker→estimated`, `ct_christmas_always→issued`; template greps confirm the literal string "Credit issued" never appears — only the dynamic `Credit disclosed ({{ stage }})` |
| 7 | No forbidden vendor anywhere | ✓ VERIFIED | `vendor-scan.sh` and `lockfile-scan.sh` both exit 0; manual grep for `textract/bedrock/comprehend/rekognition/transcribe/polly/kendra/sagemaker` and `openai/anthropic/langchain/llama_index/crewai` across `.py` files returns only the CI's own intentional violation fixture (`.github/fixtures/violation/bad_client.py`) and a docstring's use of the English word "transcribed" |
| 8 | AGT-03 — at least 3 published government award figures reproduced exactly, live | ✗ FAILED | No live SDK call has ever fired anywhere (no keys, no `runs/job1/` artifact); confirmed directly this session (empty env vars, production page shows not-configured state) |
| 9 | SHP-05 — Google SDK genuinely called at runtime, proven by a production log line | ✗ FAILED | Same root cause as #8; production page fetched live this session shows the not-configured state, not a completed run |

**Score:** 7/9 truths verified in this table (the phase's own claimed AGT-03/SHP-05 gaps confirmed as genuinely open, not overclaimed)

### Deferred Items

Root-cause-identical to gaps #8/#9 above, and explicitly re-owned by Phase 8's own roadmap text rather than newly built there.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | SC2 — Job 1 ingests a live government document | Phase 8 | "Re-verification sweep... grep production logs for at least one real Gemini call (SHP-05) and one real Parallel call (SHP-06)" |
| 2 | SC5 (production-log clause) | Phase 8 | Same re-verification sweep note, explicit |
| 3 | SHP-06 (formally Phase 7's requirement per REQUIREMENTS.md's table) | Phase 7 / 8 | REQUIREMENTS.md assigns SHP-06 to Phase 7; Phase 8's sweep names it explicitly |

### Figure spot-checks (independent, against archived source bytes)

| Jurisdiction | Figure in `jurisdictions/*.yaml` | Source document | Result |
|---|---|---|---|
| California | `base_rate: "0.35"`, `mechanism: nonrefundable_credit` | `sources/ca/2026-09-09-leginfo-rtc-17053-98-1.html` (sha256 matches manifest exactly) | Confirmed: statute subdivision (a)(4)(A) states "Thirty-five percent of the qualified expenditures... including... a feature or a television series" |
| California | `per_project_cap: $120,000,000`, `annual_programme_cap: $750,000,000` | same document | Confirmed: "up to one hundred twenty million dollars ($120,000,000)" per project, appears verbatim |
| New Jersey | `base_rate: "0.30"` (pre-2021-01-07 tier) | `sources/nj/2026-09-09-njeda-nj-a-c-19-31t-...pdf` (sha256 matches manifest exactly) | Confirmed via `pdftotext`: "For completed applications received prior to January 7, 2021, 30 percent of the qualified film..." |
| New Jersey | `mechanism: transferable`, `transfer_discount.typical_rate_low: 0.75`, `typical_rate_high: null` | same document | Confirmed: "shall not be exchanged for consideration received by the approved applicant of less than 75 percent of the transferred credit amount" — no ceiling stated anywhere in the document, matching the deliberate `null` |
| Connecticut | `ct_colony_video_2015_productions.yaml` ($187,220 → $18,722, 10%) | `sources/ct/2026-08-24-ct-film-tax-credits-issued.csv` | Confirmed exact CSV row match: `"Colony Video 2015 Productions","$187,220.00","2016-11-10T00:00:00.000","$18,722",...` |
| Connecticut | `ct_mako_games.yaml` ($593,380 → $89,007, 15%) | same CSV | Confirmed exact CSV row match: `"Mako Games LLC","$593,380.00","2011-08-15T00:00:00.000","$89,007",...` |

No figure I attempted to trace could not be traced. `tests/test_source_truth.py` (10/10 pass) programmatically re-verifies every manifest sha256 against the archived bytes, so this is not merely a five-sample spot-check — it is machine-enforced for the whole manifest.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `jurisdictions/us-ca.yaml` | CA rule model, sourced | ✓ VERIFIED | Loads via `engine.models.load_ruleset`; wired into `RULESET_PATH_BY_JURISDICTION` |
| `jurisdictions/us-nj.yaml` | NJ rule model, sourced | ✓ VERIFIED | Same |
| `jurisdictions/us-ct.yaml` | CT rule model, full band coverage | ✓ VERIFIED | All 3 tiers (10%/15%/30%) now covered by real disclosed CSV rows |
| `agent/groundedness.py` | Quote/figure grounding check | ✓ VERIFIED | 124 lines, pure function, wired into `agent/job1.py` line 246 |
| `agent/enactment.py` | Enacted vs. proposed classification | ✓ VERIFIED | 157 lines, pure function, wired into `agent/job1.py` line 372 |
| `agent/taxonomy.py` | 3-value mismatch enum + bucket counts | ✓ VERIFIED | No percentage/mean/blended field, test-enforced |
| `app/routers/job1.py`, `app/templates/job1_result.html` | `/job1` hosted page | ✓ VERIFIED | Deployed and live at `https://vockell.com/finance/job1` (curl confirmed 200 this session, correctly shows not-configured state) |
| `runs/job1/` | Committed live-run artifact | ✗ MISSING | Directory does not exist — expected, since no live run has occurred |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `agent/job1.py::_price_and_classify_award` | `agent/groundedness.py::check_grounded` | direct call, required kwarg | ✓ WIRED | Confirmed by grep + `test_run_job1_rejects_ungrounded_award_as_extraction_failure` |
| `agent/job1.py::run_job1` | `agent/enactment.py::classify_enactment` | direct call after Extract | ✓ WIRED | Confirmed by grep + route-level test rendering the verdict |
| `agent/parallel_client.py::search_for_disclosure` | `is_primary_government_url` | ranked-result filter loop | ✓ WIRED | Confirmed by `test_primary_domain_run_job1_prefers_a_government_result_over_a_higher_ranked_one` |
| `app/services/validate.py` | `app/services/_paths.py::RULESET_PATH_BY_JURISDICTION` | shared import | ✓ WIRED | Same dict object imported by both `spec.py` and `validate.py`, identity-tested |
| `agent/gemini_client.py` / `agent/parallel_client.py` | real SDK (`google.genai`, `parallel`) | lazy `import` inside function body | ✓ WIRED (code), ✗ NEVER FIRED (runtime) | Import statements confirmed real, but zero executions recorded anywhere — this is the AGT-03/SHP-05 gap |

### Behavioral Spot-Checks (run live this session, not from SUMMARYs)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green | `uv run --frozen pytest -q` | 720 passed, 0 failed | ✓ PASS |
| Golden totals unregressed | `pytest tests/test_golden_cost.py tests/test_route_a_basis_walk.py -q` | 9 passed; NY $758,427 / LA $693,521 / London £548,595 ($747,735) / gap $64,906 confirmed by literal grep | ✓ PASS |
| `engine/` untouched by this phase | `git diff --stat -- engine/` | empty | ✓ PASS |
| Vendor scan | `bash .github/scripts/vendor-scan.sh` | exit 0 | ✓ PASS |
| Lockfile scan | `bash .github/scripts/lockfile-scan.sh` | exit 0 | ✓ PASS |
| Honest refusal fires live for 5 pairs | `TestClient(app).get("/api/v1/validate/{pid}")` × 5 | all 200, `verdict="cannot be computed"`, real reason | ✓ PASS |
| `disclosure_stage` renders correctly | same TestClient calls | `issued`/`allocated`/`estimated` all correct | ✓ PASS |
| Production `/job1` reachable, honest | `curl https://vockell.com/finance/job1` | 200, shows not-configured naming both env vars | ✓ PASS (confirms the gap, not a defect) |
| Production `/` still 200 | `curl https://vockell.com/finance/` | 200 | ✓ PASS |
| AGT-08 guardrail registry test | `pytest tests/test_agent_guardrails.py -q` | 16 passed | ✓ PASS |
| Sourced figures trace to archived bytes | `pytest tests/test_source_truth.py -q` | 10 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| JUR-02 | 05-04, 05-08 | California modelled, allocation-stage labelled | ✓ SATISFIED | REQUIREMENTS.md `[x]`; verified live above |
| JUR-03 | 05-05, 05-08 | New Jersey modelled, estimated-stage labelled | ✓ SATISFIED | REQUIREMENTS.md `[x]`; verified live above |
| JUR-04 | 05-06, 05-08 | Connecticut modelled, full band coverage | ✓ SATISFIED | REQUIREMENTS.md `[x]`; all 3 tiers covered |
| AGT-01 | 05-01, 05-02 | Job 1 extracts every award | ✓ SATISFIED (mechanism) | Offline-proven; `limit=None` default confirmed in code |
| AGT-02 | 05-01..05-03 | Job 1 re-runs the model, reports accuracy | ✓ SATISFIED (mechanism, deployed) | `/job1` live, route tests pass |
| AGT-03 | 05-02 | ≥3 government figures reproduced exactly, live | ✗ BLOCKED | No live run — see gap above |
| AGT-04 | 05-02 | 3-value taxonomy, built-in not retrofitted | ✓ SATISFIED | Verified structurally |
| AGT-08 | 05-07 | Four guardrails enforced | ✓ SATISFIED | All four wired + tested, confirmed above |
| AGT-09 | 05-01 | Extraction only via permitted Google SDK | ✓ SATISFIED | vendor-scan clean, lazy-import confirmed |
| SHP-05 | 05-01, 05-03 | Google SDK genuinely called, log-line proof | ✗ BLOCKED | No live call anywhere — see gap above |
| SHP-06 | 05-01 (pulled forward), formally Phase 7 | Parallel genuinely called at runtime | ✗ BLOCKED (deferred to Phase 7/8 per REQUIREMENTS.md's own assignment) | Same root cause |

No orphaned requirements found — REQUIREMENTS.md's Phase 5 rows match what the 8 plans collectively declare.

### Anti-Patterns Found

None. Scanned all agent/*.py, app/routers/job1.py, app/routers/validate.py, app/services/validate.py, app/services/_paths.py, all three phase-5 templates, and all three new jurisdiction YAML files for `TBD|FIXME|XXX|TODO|HACK|placeholder|coming soon|not yet implemented|not available` — zero matches. The only vendor-scan-adjacent matches found anywhere in the tree are the CI's own intentional test fixture (`.github/fixtures/violation/bad_client.py`) and the English word "transcribed" inside a docstring — both correctly not flagged.

## Gaps Summary

Two closely related, root-cause-identical gaps, both **Phase 5's own declared
requirements** per ROADMAP.md, both live-outcome claims that remain false
because no `PARALLEL_API_KEY`/`GEMINI_API_KEY` exists anywhere this phase
can reach (confirmed directly by this verification, not merely quoted from
a SUMMARY):

1. **AGT-03** — Job 1 has never reproduced a real government figure; only
   an offline test double.
2. **SHP-05** — the Google SDK has never actually fired at runtime,
   confirmed live against the production `/job1` page in this session.

Both gaps are honestly and completely pre-documented by the phase's own
artifacts (WINDOWS.md #26 and #28, REQUIREMENTS.md's `[ ]` rows) — this
verification did not discover anything the executors were hiding. The
fix is a single external human action (obtain both API keys, install them,
trigger one live run) that no agent in this environment can perform. Once
that happens, both gaps close automatically per the test gates already
built (`test_agt_03_gate_is_satisfied_by_exactly_one_state` and the
production `journalctl` grep documented in `deploy/README.md`).

Everything else this phase claimed — four jurisdictions genuinely sourced
and wired, all four AGT-08 guardrails genuinely enforced with firing
tests, a genuinely closed 3-value taxonomy, a genuinely fired
honest-refusal path for all five named transferable pairs, and
`disclosure_stage` genuinely reaching the page with correct stage-aware
wording — was independently verified against the live codebase and (where
reachable) the live production URL in this session, not accepted on the
SUMMARYs' word.

---

_Verified: 2026-09-09T09:46:57Z_
_Verifier: Claude (gsd-verifier)_
