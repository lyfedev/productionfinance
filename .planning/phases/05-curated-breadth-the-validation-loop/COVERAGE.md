# API Coverage — Phase 5 external data surfaces

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

**Context.** Phase 5 flips three of Phase 4's opt-outs to INTEGRATE, because
Job 1 (agent/job1.py) now genuinely calls both permitted AI services at
runtime — Parallel Search, Parallel Extract, and `google-genai` structured
extraction, in that fixed order with no substitutions (D-82). This is what
satisfies both hard eligibility requirements, SHP-05 and SHP-06, and SHP-06
is pulled forward from Phase 7 into this phase for the reason recorded in
D-80: Job 1 parses a government PDF, and Parallel Extract is the only
permitted way to turn one into text before `google-genai` reads it.

| capability | decision | reason |
|---|---|---|
| parallel.search | INTEGRATE | SHP-06, D-80. `agent/parallel_client.py::search_for_disclosure` calls the Parallel Search API at runtime to locate the NY ESD quarterly Film Tax Credit report, filtered to a primary-government-domain result only (D-88) |
| parallel.extract | INTEGRATE | AGT-09, D-82. `agent/parallel_client.py::extract_document` is the only permitted way to turn the located government PDF into clean text before `google-genai` reads it |
| google-genai.structured-extraction | INTEGRATE | SHP-05, D-83. `agent/gemini_client.py::extract_awards` calls `client.models.generate_content` with `response_json_schema=ExtractedAwardSet.model_json_schema()` — one schema definition serves both the extraction and (were it ever exposed over HTTP) the API contract |
| parallel.task | OPT-OUT | The multi-hop research Task API is Job 2 / Phase 7's tool; Job 1's document is already located by a single Search call, so Task would add latency and cost for nothing this phase needs |
| google-genai.function-calling | OPT-OUT | The pipeline is fixed-sequence (D-82) — no tool-selecting loop. This is also T-05-02's mitigation: the model returns structured data and nothing else, so prompt-injection in the fetched document cannot reach an action |
| aws.textract / every AWS AI endpoint | OPT-OUT | Forbidden by name — see `.claude/CLAUDE.md`'s "Forbidden dependencies" section. Every AWS AI service is a Stage One disqualification; all document reading in this phase goes Parallel Extract -> `google-genai` instead |

**Enforcement.** `.github/scripts/lockfile-scan.sh` (SHP-07 — asserts the
resolved `uv.lock` carries neither a forbidden package nor an extras-bearing
`google-adk`) and `.github/scripts/vendor-scan.sh` (the AWS-AI-service grep,
D-28) both run on every push and both still exit 0 with `google-genai` and
`parallel-web` resolved. `tests/test_agent_eligibility.py` is the standing
CI gate that both SDK imports sit inside a function body on the real call
path, that the D-84 `PRODFIN_SDK_CALL` log line is unconditional at both
call sites, and that the app keeps serving every pre-existing route with no
keys present.

## AGT-08 guardrails

D-97 reverses D-88: nothing in AGT-08 is deferred. All four extraction
guardrails are enforced on the real Job 1 path, and each one has a test
that fails if the guardrail is removed (`tests/test_agent_guardrails.py`,
the single standing gate — its own `test_every_guardrail_has_a_firing_test`
proves this by introspection). This table distinguishes work newly built
in plan 05-07 from a guardrail whose implementation predated this plan.

| AGT-08 clause | Implementing module/function | New here or pre-existing | Firing test | Test new here or pre-existing |
|---|---|---|---|---|
| groundedness checks on extracted quotes | `agent.groundedness.check_grounded`, wired into `agent.job1._price_and_classify_award` | **New** (plan 05-07, Task 1) | `test_groundedness_*`, `test_run_job1_rejects_ungrounded_award_as_extraction_failure`, `tests/test_agent_job1_offline.py::test_offline_loop_rejects_an_ungrounded_award_alongside_the_grounded_rows` | **New** |
| preference for primary government domains | `agent.parallel_client.is_primary_government_url` and the ranked-result loop in `agent.parallel_client.search_for_disclosure` | **Pre-existing** (plan 05-02) — `agent/parallel_client.py` is not modified by plan 05-07 (file ownership) | `test_primary_domain_*` | **New** (plan 05-07, Task 3) — a suite-wide search before this plan found zero references to `is_primary_government_url` or `search_for_disclosure` anywhere in `tests/` |
| locale-aware number parsing | `agent.numbers.parse_money` | **Pre-existing** (plan 05-02) | `tests/test_agent_numbers.py` (full case set); `test_locale_aware_parsing_*` in `tests/test_agent_guardrails.py` is the AGT-08 entry point only — two assertions, never a re-derivation of the full case set | **Pre-existing** (`tests/test_agent_numbers.py`); the two entry-point assertions are new here |
| proposed bill vs. enacted law classification | `agent.enactment.classify_enactment`, persisted on `Job1Run.source_enactment`, rendered on `/job1` | **New** (plan 05-07, Task 2) | `test_enactment_*` (all four branches: enacted, proposed, unknown, both-with-precedence); `tests/test_app_job1_route.py::test_get_job1_with_persisted_proposed_verdict_renders_proposed_not_enacted` | **New** |
