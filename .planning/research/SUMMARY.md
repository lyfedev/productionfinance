# Research Summary — ProductionFinance

*Synthesized: 2026-08-24*
*Sources: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md, PROJECT.md*

## Executive Summary

ProductionFinance prices one identical film production across cities and reports the true landed cost — labour, housing, stages, equipment, travel, currency, and the production incentive net of fees, discount, tax, and timing — with every figure sourced, dated, and provably matching a government disclosure. No incumbent in this category (EP, Cast & Crew, Wrapbook, Olsberg·SPI) makes a to-the-dollar reproduction claim against a government document, computes net cash/timing, or models landed cost rather than headline rate — this is a genuinely open competitive lane, not an incremental improvement. The build is a deterministic Python pipeline (budget → localize → qualifying base → credit → net cash → rank → gap) wrapped by two thin agentic jobs (Job 1: validation against government disclosures; Job 2: live research for uncurated cities), both built as `google-adk` `SequentialAgent`/`ParallelAgent` pipelines calling Gemini (`google-genai`, which ADK pulls in as a hard dependency) and Parallel Search/Extract/Task. The engine is additive by construction — new jurisdictions are YAML data, not new code — which is what makes 4 curated jurisdictions plus open-ended live research tractable in 17 days.

The single greatest risk is not the incentive arithmetic (which is well-understood and already partly resolved in prior research) but process discipline under deadline pressure: the AI-vendor boundary (Google Cloud + Parallel only, zero AWS AI services, zero disallowed transitive packages), the "never fake progress" honesty constraint, and the requirement that the hosted URL genuinely work cold for an anonymous visitor. Recommended mitigation is mechanical, not procedural: pre-submission greps of the resolved dependency tree, production log traces proving each SDK call fires on a real deployed request, and a cold/logged-out/different-network test as the literal last step before submission.

Hosting has moved from a from-scratch AWS/GCP choice to co-hosting on the already-provisioned vockell.com Lightsail instance, which changes several STACK/ARCHITECTURE recommendations (Docker Compose + Caddy is not viable — Apache already owns 80/443) and reframes the deploy path as infrastructure surgery (Python upgrade, instance resize, reverse proxy, subdomain DNS) that must start on day 2-3 regardless of application progress, because TLS and DNS propagation run on their own clock.

---

## Resolved Conflicts

### 1. google-adk vs google-genai vs the litellm/openai transitive-dependency risk (RESOLVED)

**Conflict:** STACK.md recommended `google-genai` directly and explicitly argued against `google-adk`, reasoning both agent jobs are fixed-sequence pipelines, not autonomous agent loops. ARCHITECTURE.md designed both jobs as `google-adk` `SequentialAgent`/`ParallelAgent` pipelines regardless. PITFALLS.md (G7) separately warned that `google-adk`'s `LiteLlm` multi-model wrapper can pull in `litellm`, and transitively `openai` — a Stage One disqualification risk.

**Resolution — verified against PyPI JSON metadata on 2026-08-24:** `google-adk` 2.7.1 has 25 hard (non-extra) dependencies. None is `litellm`, `openai`, `anthropic`, `langchain`, `langgraph`, `crewai`, or `llama-index`. Every disallowed package is gated behind an optional extra (`google-adk[all]`, `[extensions]`, or `[test]`).

- **DECISION: use `google-adk` (bare install only). Never `google-adk[all]`, `[extensions]`, or `[test]`.** PITFALLS' concern is real but bounded entirely to the extras, which are simply never installed.
- `google-adk` hard-depends on `google-genai>=2.12.1`, so ADK brings STACK's recommended SDK with it — the two recommendations are not mutually exclusive, ADK is a superset. STACK's verified `client.models.generate_content(..., response_json_schema=...)` pattern remains usable underneath ADK.
- ARCHITECTURE's `SequentialAgent`/`ParallelAgent` design stands, and scores better on the "Technological Implementation" judging criterion, which favors Agent Builder-style construction.
- `google-genai` 2.19.0 and `parallel-web` 1.3.0 are independently clean (10 and 6 hard deps respectively, no disallowed packages).
- **Mandatory gate:** the pre-submission compliance check must grep the *resolved lockfile* (not just `requirements.txt`) for `litellm`, `openai`, `anthropic`, `langchain`, `langgraph`, `crewai`, `llama-index` and fail the build if any appears. This subsumes and sharpens PITFALLS' G7 check.

### 2. Hosting: AWS Lightsail "new instance" vs co-hosted vockell.com box (RESOLVED, post-research)

STACK.md and ARCHITECTURE.md were written assuming a dedicated or newly-provisioned Lightsail instance, and both recommend Docker Compose + Caddy for automatic TLS. That path is now **invalid**: the actual box is the existing `vockell_dot_com_LAMP` instance, where Apache already holds ports 80/443 for the live vockell.com site. Caddy cannot bind those ports alongside Apache. See the Hosting Update section below for the reconciled plan. Not a genuine disagreement between documents — an assumption that was overtaken by a fact discovered after they were written.

### 3. Data layer: STACK's SQLite-cache-plus-YAML recommendation vs ARCHITECTURE's Postgres-plus-S3 design — reassessed under the memory budget

STACK.md recommends versioned YAML in the repo for curated rules (git as the audit trail) plus SQLite for the live-research cache, explicitly rejecting Postgres/RDS as unjustified provisioning overhead at this data volume. ARCHITECTURE.md instead designs a self-hosted or RDS Postgres for curated-store mirroring, live-cache/job-state, and Balances' `index_runs` history, plus S3 mirroring for immutable snapshots and source documents — reasoning that time-series movement queries want SQL and durable job-state wants a real table.

**This is not fully resolved by either document and the hosting update tips the balance:** the box has 2 GB RAM after resize, shared with Apache and MySQL (already running), plus the FastAPI process, plus Gemini/ADK's import footprint. A second full Postgres server adds real steady-state memory overhead (connection handling, shared buffers) that this box may not comfortably carry alongside everything else — MySQL is already present and unused for this project, so a *second* database engine is pure additional footprint, not shared infrastructure.

**Recommendation given the 2 GB budget: SQLite for both the live-research cache and job-state tables, YAML-in-repo for curated rules (per STACK), for Milestone 1 (Accounts).** SQLite has zero server process, zero steady-state memory footprint beyond the page cache, and Accounts' data volume (tens of jurisdictions, a handful of concurrent research jobs) does not need concurrent multi-writer access. Reassess for Milestone 2 (Balances): if the scheduled index truly needs SQL time-series aggregation across many runs, either (a) use the site's already-running MySQL instance (avoids adding a second database engine at all — schema differences from ARCHITECTURE's Postgres design are minor for this workload) or (b) confirm the resized instance has comfortable headroom before adding Postgres. **This is a genuine open question the source documents do not resolve — flagged in Open Questions below**, because it depends on measuring actual steady-state memory after the Python upgrade and ADK import, which has not been done yet.

S3 mirroring for immutable source-document/snapshot storage (ARCHITECTURE's recommendation) is unaffected by the hosting change and should proceed as designed — it is off-box storage and costs no local memory.

---

## Hosting Reconciliation (supersedes STACK.md "Hosting" section and ARCHITECTURE.md deployment topology diagrams)

**Target:** co-hosted on `vockell_dot_com_LAMP` (Bitnami LAMP blueprint, Debian bullseye, AWS profile `newaccount`, us-west-2, static IP 35.165.60.123, SSH user `bitnami`).

**Measured 2026-08-24:** 472 MB RAM (95 MB already in swap at idle), 1 vCPU, 20 GB disk (14 GB free), Python 3.9.2, Apache on 80/443, MySQL on 3306, no Docker.

**Two blockers, both decided:**
1. **Python too old.** `google-adk` and `google-genai` both require >=3.10; the box has 3.9.2. Install a modern Python via `uv` or `pyenv`, isolated from the system Python Bitnami/Apache depend on.
2. **472 MB is insufficient** to hold FastAPI + the Google SDK import footprint + any local database alongside Apache and MySQL, which are already consuming most of it (evidenced by swap already in use at idle). **DECIDED: resize to `small_3_0` (2 GB, 2 vCPU) via snapshot-and-restore**, scheduled into the deploy phase rather than run during planning (the resize takes vockell.com offline). The attached static IP is preserved through the resize, so the apex domain needs no DNS propagation.

**Reverse proxy, not Caddy/Docker Compose:** Apache retains 80/443 for vockell.com. ProductionFinance is reverse-proxied to uvicorn on a **subdomain** (e.g. `prodfin.vockell.com`), via an Apache virtual host (`mod_proxy`/`mod_proxy_http`) or, if preferred, Apache handling TLS termination via Certbot for the new subdomain and proxying to a local uvicorn port. **This invalidates STACK's Caddy-based Docker Compose deploy path outright** — Caddy cannot bind 80/443 while Apache holds them, and running a second TLS-terminating proxy on alternate ports defeats the purpose. Certbot for the new subdomain (via Apache's existing plugin, likely already present on a Bitnami LAMP box) is the correct substitute for Caddy's automatic-TLS convenience here.

**No Docker on the box.** Either install Docker (adds another memory-hungry daemon on an already memory-constrained instance — not recommended given the 2 GB budget is shared three ways) or **run uvicorn directly under systemd** (recommended — matches ARCHITECTURE's own systemd-supervised-uvicorn topology, which was already the design regardless of the Docker Compose framing in STACK's installation section). `systemd` for process supervision, `Gunicorn` + `UvicornWorker` for worker management (per STACK's supporting-libraries recommendation), fronted by Apache's reverse proxy.

**Critical path item — do this early:** the subdomain's DNS record is the only item in this entire hosting plan carrying propagation delay. Create it on day 2-3 alongside instance provisioning, per both STACK's and ARCHITECTURE's independent "stand up the deploy path early" flags — it has its own clock independent of build progress.

**Database at this memory budget:** see Resolved Conflicts #3 above — SQLite recommended for Milestone 1's cache/job-state; MySQL reuse or a measured Postgres decision deferred to Milestone 2 planning, pending an actual free-memory measurement after the Python upgrade lands.

---

## Key Findings

### From STACK.md
- **Language/SDK:** Python backend is mandated; `google-adk` (bare install, see Resolved Conflicts #1) for both agent jobs, which brings `google-genai` transitively for direct structured-extraction calls.
- **Partner SDK:** `parallel-web` (import as `from parallel import Parallel`), official SDK, `PARALLEL_API_KEY` env var. Search/Extract/Task are three distinct products — Extract turns a found URL (including PDFs) into clean markdown; Task does multi-hop cited research and is worth a spike for Job 2 if manual Search+Extract+Gemini chaining proves too slow to build.
- **Frontend:** React 19 + Vite 8 + TypeScript, MapLibre GL JS 6.5.0 direct (no wrapper) with free OpenFreeMap tiles — no API key friction, GPU-accelerated data-driven styling matches the "slider reorders live" requirement.
- **Money:** `decimal.Decimal` + a ~20-line in-repo `Money` dataclass, not `py-moneyed` (unmaintained since Nov 2022). FX via Frankfurter, no API key, no documented quota.
- **Testing:** pytest, parametrized directly over YAML validation-pair fixtures with exact-`Decimal`-match assertions — not snapshot testing, because the correct answer (a government-disclosed figure) is known in advance.
- **Forbidden dependency discipline:** AWS Textract is the single most likely accidental Stage One violation (it is the obvious tool for the exact PDF-parsing task Job 1 does). All extraction must route through Parallel Extract + Gemini.

### From FEATURES.md
- Every incumbent (EP, Cast & Crew, Wrapbook, Olsberg·SPI) is free, public, lead-gen-funded, and stops at headline rate/eligibility — none computes landed cost, net cash, or timing, and none makes a to-the-dollar government reproduction claim.
- Table stakes across the category: multi-jurisdiction comparison UI, a downloadable/printable takeaway artifact, a per-jurisdiction freshness stamp, a graceful fallback for the unknown case, and an output that always resolves to one dollar figure, not a bare rate.
- Nine specific feature gaps exist between PROJECT.md's Active requirements and category table-stakes — see Requirements Gaps below.
- Concrete anti-features beyond PROJECT.md's existing Out of Scope list: a conversational chatbot as primary interface (directly contradicts the anti-hallucination differentiator), chasing a large jurisdiction-count headline claim, opaque JS-rendered comparison widgets that can't be cited at the figure level, bulk-exporting the raw rule corpus (gives away the differentiator), sensitivity analysis that prescribes an action rather than displaying a delta, and a live-updating cap-consumption ticker presented without the caching-boundary caveat.

### From ARCHITECTURE.md
- Core pipeline is 8 strict, pure-function stages (Spec→Budget→Localize→QualifyingBase→Credit→NetCash→Rank→GapDecompose); only 2 of 8 stages ever touch jurisdiction-specific data, and even those consult *data* (YAML), not per-jurisdiction *code* — this is what makes adding a jurisdiction additive.
- Jurisdiction rules: hybrid schema, heavily declarative YAML interpreted by one generic engine, with a small named Python handler registry as escape hatch for genuinely irregular logic (e.g., cross-jurisdiction residency-pool mismatches) — a pure per-jurisdiction-subclass design was explicitly rejected as both an audit and a safety problem, especially since Job 2 output must land in the same schema without generating executable code.
- Provenance: an immutable `Figure` value object carrying its own derivation chain as a DAG (`inputs: tuple[Figure,...]`) — no global trace object, no event sourcing. This is what makes every number clickable back to its source without polluting function signatures.
- Both agent jobs are `google-adk` pipelines (see Resolved Conflicts #1); AI-services boundary is stated as non-negotiable at the exact point (Job 1's PDF ingest) it's most likely violated by habit.
- Deployment topology (durable job-state via a Postgres/now-SQLite `research_jobs` table, SSE progress streaming, staleness reclassification on process restart) is hosting-agnostic and unaffected by the vockell.com change — only the specific storage engine and TLS/proxy layer need updating (see Hosting Reconciliation above).

### From PITFALLS.md
- Top 3-5 pitfalls with prevention — see the dedicated Top Five section below (kept separate per task instructions, ranked and made mechanically verifiable).
- The NY $700M/$800M question and the GA loan-out withholding rate are both very likely recency/scope artifacts rather than genuine conflicts, but both still need primary-source confirmation before being coded as fact (see Open Questions).
- A defensible general policy for conflicting sources: check for "different scope, not actually contradictory" first (as with NY); otherwise apply precedence — enacted statutory text > primary regulator guidance > recency among comparably authoritative sources > multiple converging secondary sources (labelled as such) > display as genuinely unresolved if the primary source itself is ambiguous.
- A concrete mismatch taxonomy for Job 1 output (exact match / zone match, explained / unexplained mismatch) is required so the validation loop can't silently smooth over a real bug by folding it into a blended mean-error number.

---

## Open Questions

### Blocking

1. **Partner track ambiguity — Parallel vs IBM.** `productionfinance-brief.md` states the track is Parallel with the Search API called at runtime; `hackathon-brief.md` states "Our track: IBM," but its scorecard concerns a different sibling project. PROJECT.md treats Parallel as governing ("where the two disagree, `productionfinance-brief.md` governs") but flags the disagreement rather than resolving its source. **If IBM were in fact the correct track for this project, the partner requirement becomes dev-process rather than runtime, and Parallel becomes optional** — this would reshape the architecture materially (Job 2 could drop the Parallel Search/Extract dependency entirely and lean harder on Gemini's own retrieval/grounding, changing both the agent pipeline design in ARCHITECTURE.md and the SDK installation list in STACK.md). **Resolution needed:** confirm directly against the hackathon's official submission portal/rules for this specific project's track assignment before Job 2's architecture is locked in, not assumed from the brief documents alone.
2. **New York's $700M vs $800M cap.** Reconcile at tax.ny.gov or the enacted FY2026 budget bill text before coding the figure. PITFALLS' research found convergence across three independent secondary sources (Wrapbook, EP, Hollywood Reporter) on "$700M base + separate $100M independent-film pool," which is a strong lead but not yet a primary-source confirmation. **This is a named Phase 0 task in PROJECT.md's own Active requirements** — carrying it forward as blocking that phase specifically.
3. **Connecticut open-data CSV column headers.** Confirm the actual schema before CT's jurisdiction YAML or Job 1's ingestion logic can be built — also a named Phase 0 task in PROJECT.md.
4. **New Mexico HB 237 enacted/defeated status.** Introduced 2025 as a proposed repeal; no confirmed final outcome located in this research pass. Relevant primarily if NM is ever reached via Job 2 live research — verify against nmlegis.gov before any NM-adjacent live demo, per PITFALLS' C5 guardrail (extraction must distinguish bill-status language from enacted law).

### Non-blocking

5. **Georgia loan-out withholding rate: 4.99% vs 5.75%.** Working hypothesis (this research pass): 5.75% is the pre-2024-reform rate, 4.99% is current — a recency artifact, not a live disagreement. Confirm against a dated Georgia DOR primary source before coding as fact; low urgency since GA is not a curated jurisdiction and is only reached via Job 2.
6. **CA/NJ allocation-figure revision on production non-completion.** Consistent with how capped, application-based allocation programmes generally work, but not independently confirmed against a specific CA Film Commission statute clause. Affects Job 1's ingestion de-duplication/diffing logic (PITFALLS B2) — verify if time allows, otherwise state as a caveat in the written description.
7. **Exact Parallel Search/Extract/Task pricing and rate limits.** STACK.md flags the pricing page rendered inconsistent numbers across two fetch attempts (MEDIUM confidence). Not a design constraint at hackathon usage volume, but pull live numbers from `docs.parallel.ai/getting-started/pricing` before writing any cost-tracking or budget-alert code.
8. **Frankfurter FX API's CZK and HUF coverage.** Near-certain given both are actively-tracked European central-bank currencies, but STACK.md recommends a live sanity-check call against both codes during setup rather than assuming coverage from the general "201 currencies" claim.
9. **Actual free memory on the resized 2 GB instance after the Python 3.10+/ADK/genai install.** Not measured yet — this determines whether SQLite-only (recommended default, see Resolved Conflicts #3) is sufficient for Milestone 1 or whether MySQL reuse/a measured Postgres addition is needed for Milestone 2's time-series index-run queries. Measure immediately after the Python upgrade lands, before committing to a Balances-phase data-layer decision.

---

## Requirements Gaps

FEATURES.md identifies nine table-stakes-for-this-category features present in the competitive field but absent from PROJECT.md's Active requirement lists. Each is assigned to a milestone below for folding into REQUIREMENTS.md, ranked by FEATURES.md's own priority matrix.

| # | Gap | Milestone | Priority | Why it's missing matters |
|---|---|---|---|---|
| 1 | Export/share deliverable (PDF or spreadsheet a producer can hand upward) | Accounts | P1 | Every incumbent ships a takeaway artifact; every real line-producer workflow terminates in a document, not a live dashboard someone else has to load |
| 2 | Shareable/permalink URL encoding a comparison's inputs | Accounts | P1 | With no login (anonymous-visitor DoD), there is no other way to persist or hand off a specific comparison; also the prerequisite for #1 to reach anyone |
| 3 | Consolidated, printable assumptions panel (every rate used, each with its own source+date) | Accounts | P1 | PROJECT.md requires per-figure citation but not a consolidated view; every credible index reviewed (Case-Shiller, Big Mac, Tax Foundation) publishes one |
| 4 | Sensitivity display (which single input, if changed, moves the gap most) — display a delta only, never a prescriptive action | Accounts | P2 | Distinct from Balances' reverse mode; nothing currently surfaces which of the producer's own soft-guess inputs the answer is most sensitive to |
| 5 | Multi-currency / dual-currency display toggle | Accounts | P2 | FX is load-bearing (Budapest/Prague/London named candidate cities) yet PROJECT.md never mentions currency display; weakens the exact-reproduction proof for non-USD government documents (e.g. the UK worked example) without it |
| 6 | Per-department (ATL/BTL/Post-aligned) cost breakdown | Accounts (stretch) / Balances (full) | P3 | A line producer's trust model is built around the standard chart of accounts; the current four-component decomposition requires manual re-mapping |
| 7 | Persistent, linkable "How we compute this" methodology page inside the product | Accounts | P2 | DoD's written description is a submission artifact, not an in-product page a producer or judge lands on later; every credible index has a standing methodology URL |
| 8 | **Visible validation-loop accuracy figure surfaced inside Accounts itself** | Accounts | P1 | See inconsistency note below — this is the highest-severity gap |
| 9 | "What changed since I last looked" diff for a shared/linked scenario | Accounts (depends on #2) | P2 | Cheap once #2 exists; reinforces the freshness message without overclaiming daily research |

**Inconsistency in PROJECT.md, flagged explicitly by FEATURES.md:** Job 1 (the validation loop) runs *in Accounts* per PROJECT.md's own Key Decisions table, and Accounts alone must satisfy the hosted-URL Definition of Done — yet "publish the running accuracy figure" is currently listed only under Balances' Active requirements (line: "Publish the running accuracy figure from the validation loop"). If Accounts doesn't surface its own accuracy number on its own hosted page, the single strongest credibility asset the product has is invisible to anyone who only sees the Accounts URL — which, for the hackathon submission, is everyone. **This should be corrected when REQUIREMENTS.md is written: duplicate or move this requirement into Accounts' Active list, not only Balances'.**

---

## Implications for Roadmap — one reconciled build order

STACK.md, ARCHITECTURE.md, and PITFALLS.md each proposed a build sequence independently; they broadly agree on shape (source verification first, then a thin vertical slice, then parallelizable breadth, then the risky live-research agent, then polish). Merged into one ordered sequence below. Each item is marked:
- **[CRITICAL PATH]** — blocks everything downstream, cannot be skipped or meaningfully parallelized
- **[PARALLELIZABLE]** — can run alongside other same-tier items once its prerequisite lands
- **[CUTTABLE]** — the first thing to drop or minimize if the 2026-09-09 14:00 PDT deadline tightens

1. **Phase 0 — Source verification** [CRITICAL PATH]: reconcile the NY cap, confirm the CT CSV schema, lock the 11 validation pairs, resolve GA withholding if time allows. Blocks jurisdiction schema design and Job 1, because both need correct inputs, not merely plausible ones. Also resolve the **partner-track ambiguity (Open Question 1)** here — it changes Job 2's architecture if wrong.

2. **Infrastructure/deploy path stood up** [CRITICAL PATH for the deadline, PARALLELIZABLE with Phase 0's research work] — **do this day 2-3, not later.** Both STACK and ARCHITECTURE independently flag this: create the subdomain DNS record, snapshot-and-resize the Lightsail instance, install a modern Python, get a bare `systemd`-supervised uvicorn process reachable through Apache's reverse proxy with a real TLS cert. This has its own clock (DNS propagation, Let's Encrypt issuance) independent of application progress, and doing it late risks a working app with no way to reach it in time.

3. **Core engine spine** [CRITICAL PATH]: `JurisdictionRuleSet` YAML schema, the `Figure`/provenance pattern, the generic rule-engine interpreter (stages 3-5), the `CanonicalBudget` model skeleton (stages 1-2). Every jurisdiction, both agent jobs, and the API response shape all plug into this — nothing else can start meaningfully before it lands.

4. **Thinnest vertical slice: New York, end to end** [CRITICAL PATH]: one hardcoded jurisdiction wired from a minimal frontend form through the API, engine, and Figure output to a hosted URL showing the Anora figure ($3,964,760 → $991,190) with its citation. This is the first real cited number on a hosted URL and should be hit before anything broadens — it proves the core claim mechanically, not just on paper. PITFALLS' H1 explicitly recommends sequencing NY first and treating it as unmissable, since it is both the richest-documented curated jurisdiction and the demo's opening beat.

5. **Parallelizable breadth tier** — all three tracks depend only on step 3 landing, and can run concurrently across sessions or people:
   - **Track A — CA, NJ, CT jurisdiction YAMLs + validation pairs** [PARALLELIZABLE]. Per PITFALLS' H1: **CT is the most defensible item to cut/demote to live-researched-only if time is short** — its CSV schema is the least-verified of the four and its validation value is marginal once NY/CA/NJ already clear the three-award Definition of Done.
   - **Track B — Frontend build-out** [PARALLELIZABLE]: map, slider, ranked list, gap panel, proof panel, built against the API contract fixed in step 3/4, using NY plus mocked cities until Track A lands. Also fold in the Requirements Gaps items here where cheap: gap #2 (shareable URL) and gap #3 (assumptions panel) are low-cost, high-value additions to this same UI work.
   - **Track C — Job 1 (validation-loop agent)** [PARALLELIZABLE, lower risk than Job 2]: can start against NY alone while Track A finishes CA/NJ/CT. Build the B5 mismatch taxonomy (exact match / zone match-explained / unexplained) into its output from the start, not as a retrofit — this is what makes the "validation-loop accuracy figure" (Requirements Gap #8) trustworthy rather than decorative.

6. **Job 2 — live-research agent** [CRITICAL PATH for Definition of Done #2, but sequenced deliberately after Job 1 if solo]: reuses Job 1's extraction/structured-output machinery at materially higher risk (unknown jurisdiction, unknown correct answer). Building it second means integration problems with ADK/Parallel are found on the cheaper, known-answer case first. If two people are available, Job 1 and Job 2 can run concurrently — this is the one place team size changes the order. Bake in PITFALLS' Part C guardrails (groundedness check on extracted quotes, domain-tier bias toward `.gov`, locale-aware number parsing, bill-status classification) from the start, not as a later hardening pass — these are the difference between a live-research feature and a hallucination-risk feature.

7. **Caching boundary + durable job state + SSE progress streaming + full quarter-series wiring** [CRITICAL PATH]: the `DataFreshnessGate.get_or_refresh()` single enforcement point, the `research_jobs` table (SQLite per the reconciled data-layer decision), and the slider's pre-computed multi-quarter payload. This is also where Requirements Gap #5 (multi-currency toggle) is cheap to add, since FX becomes a live-cached data point here regardless.

8. **Demo-critical polish** [CRITICAL PATH for judging, but individually cuttable line items within it]: the UK naive-math-wrong worked example, the ranking-inversion case, the proof panel (Requirements Gap #8 — visible validation accuracy inside Accounts — belongs here), citation UI pass, demo video script. Requirements Gap #1 (export/share PDF) is a good candidate to build in this window since it needs no new modeling, only rendering of already-computed data.

9. **Ship gate — Milestone 1 (Accounts) complete.** This alone satisfies the hosted-URL Definition of Done and is the actual hackathon submission.

10. **Milestone 2 (Balances)** [CUTTABLE as a whole if Accounts slips — explicitly the next milestone, not part of the submission gate]: reference production definition, scheduled job (systemd timer, not EventBridge, per ARCHITECTURE), historical snapshot storage, change log, reverse mode. If time is short, PITFALLS' H4 minimum publishable version applies: a static/manually-triggered reference-production run, one real change-log entry, and the republished Job 1 accuracy figure — reverse mode is the correct first thing to drop entirely, since it is explicitly deferred in PROJECT.md's own Key Decisions and is the most computationally novel remaining piece.

**Research flags for phase planning:** Phase 0 (source verification) and the jurisdiction rule-encoding phases need continued research/verification work during planning (the open questions above are not fully closed). The core engine spine, Job 1, and the API contract follow well-documented, already-designed patterns in ARCHITECTURE.md and do not need fresh research during planning — implement against the schemas already specified.

---

## Top Five Project-Sinking Risks

Ranked by PITFALLS.md as (likelihood × blast radius); each prevention restated as something concretely verifiable.

1. **A validated jurisdiction produces a number that does not match the government's, and nobody notices before the demo.** Prevention, verifiable: a pytest suite parametrized directly over the 11 validation-pair YAML fixtures, asserting exact `Decimal` equality against the disclosed figure, run in CI on every commit — not eyeballed. Before submission, deliberately break one jurisdiction's rule value and confirm the test suite catches it (proves the test isn't vacuously passing).

2. **The Google Cloud SDK is imported but never actually exercised at runtime, or Parallel Search is stubbed for the demo.** Prevention, verifiable: add a timestamped log line at the exact call site of every real Gemini and Parallel API call; run a live, logged-out smoke test against the hosted URL within 24 hours of submission and grep production logs for at least one real call of each type fired by that session, not a local test run.

3. **Normalization scope expands without bound and nothing ships.** Prevention, verifiable: a written, dated scope-freeze note per jurisdiction (fixed list of modeled rule dimensions: base definition, per-person caps, tiers/uplifts with stacking rules, payout mechanism, named thresholds) checked off in the repo before moving to the next jurisdiction — a checklist artifact that exists in git history, not a verbal agreement.

4. **The hosted URL fails for the judge, who is by definition an anonymous, cold, unauthenticated visitor.** Prevention, verifiable: as the literal last pre-submission step, load the hosted URL from a fully logged-out browser session on a different network than the development machine (e.g. phone on cellular data or a fresh incognito window with cookies cleared) and confirm the full flow works — not "it worked when I built it."

5. **The live-research demo (Job 2) hangs, errors, or returns garbage in front of judges, live.** Prevention, verifiable: the hosted app's real Job 2 code path must genuinely call Parallel/Gemini (checked via the same log-trace method as risk #2) — but the demo video may legitimately use the best of several pre-recorded, genuinely-live takes selected after the fact (this is disclosed video editing, not the constraint-violating `sleep()`-behind-a-progress-bar dishonesty). For direct judge interaction with the hosted URL, verify explicit, informative loading/error states exist (not a spinner that can time out silently) by triggering Job 2 against a deliberately obscure or nonexistent city and confirming a legible terminal state is reached within the documented ~120s ceiling.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against live PyPI/GitHub metadata for the constrained-package resolution and the ADK/genai relationship; MEDIUM specifically on Parallel's exact pricing figures (page rendered inconsistently across fetches — verify live before cost-sensitive code) |
| Features | MEDIUM-HIGH | Competitor claims sourced to vendor pages and third-party reviews with dates where disclosed; absence-of-feature claims are as reliable as public marketing pages allow — an unadvertised enterprise tier cannot be fully ruled out |
| Architecture | MEDIUM-HIGH | Component design is HIGH confidence (standard patterns from tax/payroll rule engines and official ADK/Parallel docs, checked live); specific numeric rule values are inherited from prior feasibility research and carry that document's own caveats |
| Pitfalls | MEDIUM-HIGH | Domain pitfalls verified against primary/vendor sources this session; delivery pitfalls verified against the hackathon brief and general GitHub/Devpost mechanics; a few items (GA withholding, CA clawback mechanics) remain probabilistic and are flagged as such |
| Hosting reconciliation | HIGH on the blockers and their remedies (measured directly on the live box 2026-08-24); MEDIUM on the post-resize free-memory margin, which has not yet been measured and gates the Milestone 2 data-layer decision (Open Question 9) |

**Overall confidence: MEDIUM-HIGH.** The domain modelling, agentic architecture, and stack choices are well-founded and largely convergent across all four documents once the resolved conflicts above are applied. The remaining gaps are concrete, bounded, and already scheduled into Phase 0 or flagged as blocking — none require re-architecting, only confirmation.

**Gaps requiring attention during planning:** the partner-track ambiguity (Open Question 1) is the highest-leverage unresolved item, since its answer changes whether Parallel is required or optional in Job 2's design — this should be settled before Job 2's architecture is locked into a plan. The post-resize memory measurement (Open Question 9) should happen immediately once infrastructure work starts, since it gates the Milestone 2 data-layer decision described in Resolved Conflicts #3.
