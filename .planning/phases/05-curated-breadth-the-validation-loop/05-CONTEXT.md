# Phase 5: Curated Breadth & the Validation Loop - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Phase Boundary

**COMPRESSED SCOPE — deadline-driven.** The hackathon deadline is 2026-09-09 14:00 PDT,
roughly 14 hours from this file's timestamp. Phases 5, 6, 7 and 8 are all unstarted. The
roadmap's full Phase 5 ("four jurisdictions modelled and an agent proves the models against
published government disclosures") cannot land in the time remaining, and attempting it
would leave the submission ineligible rather than merely incomplete.

This phase therefore delivers the **eligibility spine plus the Anora proof**, and nothing
else:

Job 1 runs end-to-end against **one** published government disclosure document — the New
York ESD source already curated in Phase 3 — through the pipeline CLAUDE.md mandates:
Parallel Search locates the document, Parallel Extract returns clean text, `google-genai`
extracts production/award pairs into typed Pydantic models, the existing engine re-prices
each pair, and the run reports a real accuracy figure with an explicit mismatch
classification.

That single path satisfies both hard eligibility requirements at once — SHP-05 (a permitted
Google SDK imported and genuinely called at runtime) and SHP-06 (Parallel's Search API
genuinely called at runtime) — because Parallel-then-Gemini *is* the mandated extraction
pipeline, not two integrations bolted together for compliance.

**Explicitly deferred out of this phase:** JUR-02 (California), JUR-03 (New Jersey), JUR-04
(Connecticut), the multi-jurisdiction breadth those imply, durable job queues, restart
recovery, and any caching layer. They return only if time remains after Phase 6 and Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Scope compression — what this phase is and is not

- **D-79 — Phase 5 is compressed to the eligibility spine and the Anora proof; jurisdictional breadth is deferred wholesale.** JUR-02, JUR-03 and JUR-04 are cut from this phase. Rationale: SHP-05 and SHP-06 are Stage One disqualifiers — without them the submission is not judged at all, regardless of how many jurisdictions are modelled. Breadth is a quality axis; eligibility is a binary gate. With ~14 hours left, the gate wins. New York alone already clears the roadmap's "at least three published government award figures reproduced exactly" bar (AGT-03), because the ESD disclosure carries many production/award pairs — three exact reproductions do not require three *jurisdictions*. — **Reversibility:** reversible — each deferred jurisdiction is an additive YAML rule file plus a validation-pair fixture, exactly as New York already is; nothing in this phase's code is jurisdiction-specific.

- **D-80 — SHP-06 (Parallel Search at runtime) is pulled forward from Phase 7 into this phase.** The roadmap assigns SHP-06 to Phase 7's live-research path, but CLAUDE.md's forbidden-dependencies section already mandates Parallel Extract as the *only* permitted way to turn a government PDF into text before `google-genai` reads it. Job 1 parses a government PDF. Therefore Job 1 must call Parallel regardless, and deferring SHP-06 to a phase that may never be built puts the partner-track requirement at risk for no benefit. — **Reversibility:** reversible — Phase 7's live-research path reuses the same client and call site; pulling it forward makes Phase 7 cheaper, not redundant.

- **D-81 — REJECTED: satisfying SHP-05 and SHP-06 with a token call whose result is discarded.** A logged call that no product surface depends on is the "sleep() behind a progress bar" failure the brief names as a Stage One death, and the repo is public and inspectable. Both SDK calls must sit on the real path whose output reaches a real number on the page. This is recorded as rejected because it is the fastest way to make the greps pass under deadline pressure and will look defensible to a later agent at 3am. — **Reversibility:** one-way — a fake integration discovered by a judge ends the submission, and the repo history would show it.

### Job 1 — the pipeline shape

- **D-82 — The pipeline is Parallel Search, then Parallel Extract, then `google-genai` structured extraction, in that order, with no substitutions.** Search locates the ESD disclosure URL; Extract returns clean markdown (it handles PDFs, which is the whole reason it is in the stack); `google-genai` turns that markdown into typed production/award pairs. AWS Textract and every other AWS AI endpoint are forbidden by name — this is the specific trap CLAUDE.md flags for this project because per-diem files and rate cards are PDFs. — **Reversibility:** reversible.

- **D-83 — The Gemini extraction schema is an existing Pydantic model's `model_json_schema()`, passed as `response_json_schema`.** One schema definition serves both the API contract and the LLM extraction contract, which is the stack doc's stated best trick. Do not hand-write a second JSON schema that can drift from the model. — **Reversibility:** reversible.

- **D-84 — Both SDK call sites emit a timestamped log line naming the SDK, the target, and the elapsed time.** SHP-05 and SHP-06 are both verified "by a timestamped log line at the call site", and Phase 8's re-verification sweep greps production logs for one real Gemini call and one real Parallel call fired by a live logged-out session within 24 hours of submission. The log line is therefore a deliverable, not debug output — it must survive to production and must not be behind a debug flag that is off by default. — **Reversibility:** reversible.

- **D-85 — Extracted pairs re-run through the existing engine with no new code path.** A live-extracted production/award pair lands in the same shape as a committed validation-pair fixture and flows through the identical pricing call. This is the JUR-05 jurisdiction-agnostic guarantee applied to provenance: the engine must not know or care whether a pair came from a YAML fixture or from Gemini. — **Reversibility:** costly — a forked "extracted vs curated" pricing path would have to be unwound before Phase 7 could reuse any of it.

- **D-86 — The mismatch taxonomy is built in now, not retrofitted.** AGT-04 explicitly requires exact match, explained variance, and unexplained as a from-the-start classification. It is a three-value enum on the result record and costs minutes now; retrofitting it means re-running every comparison later. Accuracy is reported as the honest counts across those three buckets, never as a single percentage that hides unexplained mismatches. — **Reversibility:** costly — the requirement names retrofitting as the failure mode.

- **D-87 — An extraction that returns nothing usable is a legitimate reported outcome, not a fallback to invented pairs.** If Search finds no document, or Gemini extracts zero pairs, the run reports that plainly. Never synthesize a pair to make the accuracy figure exist. This mirrors `engine.net_cash.transferable` refusing to convert at an unsourced discount rate. — **Reversibility:** one-way — a fabricated award pair inside a validation accuracy figure is the precise dishonesty PRV-02 and the Phase 8 proof panel exist to prevent.

### Deferred with intent

- **D-88 — AGT-08's guardrails are reduced to the two that protect the accuracy figure.** Keep primary-government-domain preference in the Search query and locale-aware number parsing on extracted figures. Defer groundedness re-checking of quotes and enacted-versus-proposed-bill classification — both matter for uncurated live research (Phase 7), and neither changes a New York number whose correct answer is already known and committed. — **Reversibility:** reversible.

### Scope reversal — D-79 and D-88 are VOID

- **D-97 — REVERSES D-79 and D-88. Nothing in this phase is cut or deferred.** The project owner has instructed directly that scope must not be cut or deferred. JUR-02 (California), JUR-03 (New Jersey) and JUR-04 (Connecticut) are **restored to this phase in full**, as is AGT-08's complete guardrail set — groundedness checks on extracted quotes, primary-government-domain preference, locale-aware number parsing, and classification of proposed bills versus enacted law. D-79's reasoning (that eligibility is a binary gate and breadth is a quality axis) was sound as far as it went, but it was used to justify a reduction the owner did not authorize and has now explicitly rejected. Treat D-79 and D-88 as struck from this file: no downstream agent may cite either as grounds for omitting work. — **Reversibility:** reversible — this restores the roadmap's original Phase 5 scope, which every later phase was already written against.

### Claude's Discretion

Task decomposition, module and file naming, how the Parallel client is constructed and
configured, retry and timeout policy on both SDK calls, test structure, and how the accuracy
result is surfaced to the existing Jinja templates. Prefer reusing what Phases 1-4 already
built over introducing anything new.

</decisions>

<specifics>
## Specific Ideas

The frontend decision for the whole remaining build: **extend the existing FastAPI + Jinja2
app in `app/`**. It is live and serving at `https://vockell.com/finance` (verified HTTP 200
on 2026-09-08). Do not stand up the roadmap's React 19 + Vite 8 SPA — the build pipeline
alone costs hours that eligibility needs, and no judged criterion distinguishes a
server-rendered page from an SPA at this scope.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 5 and Phase 7 sections (Phase 7's SHP-06 note is now this phase's, per D-80)
- `.planning/REQUIREMENTS.md` — AGT-01, AGT-02, AGT-03, AGT-04, AGT-09, SHP-05, SHP-06

### Non-negotiable vendor constraints — read before writing any extraction code
- `.claude/CLAUDE.md` — "READ THIS FIRST — the AI-vendor line", "Forbidden dependencies", and the `google-genai` / `parallel-web` version and call-signature notes
- `.planning/phases/04-cost-localization-landed-cost-outputs/COVERAGE.md` — the capability matrix this phase must extend, since it now integrates two capabilities Phase 4 opted out of

### Prior-phase work this phase reuses rather than rebuilds
- `engine/` — the pricing spine; D-85 forbids a second path through it
- `jurisdictions/us-ny.yaml` — the curated New York rule set
- `tests/fixtures/validation_pairs/` — the committed pair shape extracted pairs must match
- `app/` — the live FastAPI + Jinja2 surface

### Governing brief
- `.planning/PROJECT.md` — the honesty constraint that D-81 and D-87 enforce

</canonical_refs>
