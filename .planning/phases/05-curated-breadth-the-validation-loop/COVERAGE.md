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
