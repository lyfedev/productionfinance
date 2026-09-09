# Phase 7: Live Research, Caching & Durable Jobs - Context

**Gathered:** 2026-09-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Job 2 — the live research agent. A user names a jurisdiction with no curated model; an
agent researches it, builds a cost model on the fly, prices it, and labels the result
unvalidated.

This phase is delivered in FULL. Nothing in it is cut, deferred, staged, or reduced.

</domain>

<decisions>
## Implementation Decisions

### Owner-stated requirements — verbatim, binding

These were stated directly by the project owner. They are not derived, not negotiable, and
not subject to scope reduction by any downstream agent.

- **D-89 — Parallel's Search API must execute on a live user request, not during data prep.** The official `parallel-web` SDK is called directly. LangChain and every other framework are forbidden. Curated jurisdictions may use cached rule models; the live research path must not read from cache. — **Reversibility:** one-way — a Search call that fires in a build step or a prep script rather than on a request fails the partner requirement outright, and moving it later means rewriting the entry point.

- **D-90 — The unknown-jurisdiction path is an AGENT with a self-terminating research loop, not a fixed sequence.** When a user names a jurisdiction with no curated model, the agent: searches for the programme via Parallel; reads the results and judges whether it has enough to build a cost model; if not, searches again with a refined query; repeats until it can build the model or decides to stop; and returns the model plus its own assessment of what it could not determine. **The agent decides when it has enough. Retry count is not fixed in advance.** This is the structural difference from Job 1, which is deliberately a fixed sequence — do not implement Job 2 by copying Job 1's shape. — **Reversibility:** one-way — a hardcoded iteration count is precisely the requirement being ruled out here.

- **D-91 — Sufficiency is judged against five named fields.** The agent judges whether it has enough to build a cost model on: **rate**, **qualifying base definition**, **caps**, **payout mechanism**, and **current availability**. These five are the sufficiency contract. A model missing any of them is not sufficient, and the agent says which ones it could not determine. — **Reversibility:** reversible.

- **D-92 — Every iteration is recorded and persisted.** What it searched, what it found, what was still missing, what it searched next, and how many rounds. Persisted — not held in memory for the duration of a request — so that both the UI and the written submission can show the agent's actual reasoning trail. — **Reversibility:** costly — the UI and the write-up both bind to this record's shape.

- **D-93 — Results from the live path are labelled unvalidated, visibly distinct from curated jurisdictions validated against published government awards.** The repo already carries the vocabulary for this: `Figure.confidence` is `validated` | `researched` and is deliberately never conflated with `sources[].confidence` (RD-02, D-58). A live-researched jurisdiction is `researched`. Do not invent a third vocabulary. — **Reversibility:** reversible.

- **D-94 — Fail open, never fabricate.** If research is inconclusive, return what was found and state what is missing. **Never fabricate a rate.** This extends D-87 and D-94's sibling gates from Phase 5 — the AST-level test asserting no award object is constructed outside `schema.py` is the pattern to follow for rule models. "No programme found" is a legitimate, correct result (AGT-06), never an error to be papered over. — **Reversibility:** one-way — a fabricated rate inside a priced jurisdiction is the exact dishonesty the whole product exists to refute, and the repo is public.

- **D-95 — `google-genai` for reasoning, `parallel-web` for search. No other AI dependency.** The reasoning calls — sufficiency judgment, query refinement, and coercing findings into the rule schema — all go through `google-genai`. No additional AI package enters `pyproject.toml`. — **Reversibility:** one-way — any other AI vendor is a Stage One disqualification.

### Verification the owner requires before this phase is reported done

- **D-96 — Every `parallel-web` call site must be proven to sit on a request handler.** Reporting this phase complete requires listing the **file and line of each call site and which endpoint reaches it**. A call site reachable only from a CLI `__main__`, a build step, or a prep script does not satisfy D-89 and must be reported as failing, not explained away. This verification is a deliverable of the phase, not a courtesy. — **Reversibility:** reversible.

### Claude's Discretion

How the loop terminates on the agent's own judgment, how query refinement is prompted, the
persistence mechanism for the iteration record, the shape of the progress surface, retry
and timeout policy on individual SDK calls, and module and file naming. Prefer reusing the
`agent/` package, `engine/`, and the existing FastAPI + Jinja2 surface over introducing
anything new.

</decisions>

<specifics>
## Specific Ideas

The agent's reasoning trail is a product surface, not debug output. D-92 exists so a visitor
can see the agent's actual rounds — what it looked for, what it missed, what it did next.
That visible trail is a large part of what distinguishes this from a black-box lookup.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 7 section
- `.planning/REQUIREMENTS.md` — AGT-05, AGT-06, AGT-07, AGT-10, AGT-11, UI-10, SHP-06

### Non-negotiable vendor constraints
- `.claude/CLAUDE.md` — the AI-vendor line and the forbidden-dependency list
- `.github/scripts/vendor-scan.sh` — the CI tripwire; it cannot tell a comment from a call site

### Phase 5 work this phase builds directly on
- `agent/parallel_client.py` — the existing Search/Extract call sites (currently reachable from a CLI entry point; D-96 governs where they must be reachable from)
- `agent/gemini_client.py`, `agent/schema.py`, `agent/telemetry.py` — the `PRODFIN_SDK_CALL` log line (D-84)
- `agent/job1.py` — the FIXED-sequence job. D-90 makes Job 2 a different shape; do not copy this one's structure.
- `agent/taxonomy.py`, `agent/numbers.py` — classification and locale-aware money parsing
- `engine/` — the pricing spine; a live-researched jurisdiction flows through the identical engine with no separate code path (AGT-07, and D-85 from Phase 5)

### Governing brief
- `.planning/PROJECT.md` — the honesty constraint D-94 enforces
