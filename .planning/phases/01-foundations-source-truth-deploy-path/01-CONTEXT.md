# Phase 1: Foundations — Source Truth & Deploy Path - Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Two concurrent, state-independent tracks:

**Track A — Source verification (SRC-01, 02, 03, 05).** Open the primary documents. Reconcile New York's annual cap, confirm the Connecticut open-data CSV column headers, confirm the Georgia loan-out withholding rate, and lock all 11 production/award validation pairs into committed test fixtures carrying source URL and disclosure stage. SRC-04 (partner track) is already resolved — Parallel, owner-confirmed 2026-08-24.

**Track B — Host and deploy path (SHP-01, 02, 03, 04, 07, 08, 09, 10).** Resize the vockell.com Lightsail instance to 2 GB via snapshot-and-restore, install a modern Python isolated from the system interpreter, create the subdomain DNS record, run the app under systemd behind Apache's reverse proxy with valid TLS, and arm the compliance gates in CI — forbidden-package scanning, secret scanning, commit-window checking — with an OSI licence detectable in the GitHub About section.

**Not in this phase:** no incentive engine, no jurisdiction rule schema, no rule files, no cost localization, no UI treatment, no agent jobs. Phase 1 produces confirmed facts, committed fixtures, and a reachable HTTPS URL serving a skeleton — nothing that computes a number.

</domain>

<decisions>
## Implementation Decisions

The user delegated all four gray areas ("you make your best guess"). Every decision below is Claude's call, made against PROJECT.md, ROADMAP.md, REQUIREMENTS.md and the research documents. Each carries its rationale so it can be overturned on sight rather than re-derived.

### Validation Pair Contract (SRC-03)

- **D-01:** One YAML file per pair at `tests/fixtures/validation_pairs/{jurisdiction}_{slug}.yaml` — e.g. `ny_anora.yaml`. Matches the pattern already named in `.claude/CLAUDE.md`'s Testing section, and gives each pair its own `git log --follow` audit trail. — **Reversibility:** costly — Phase 3's CI suite and Phase 5's Job 1 both parametrize directly over this layout; changing it later touches both consumers plus every fixture.

- **D-02:** **A validation pair proves the incentive interpreter only, never cost localization.** Government disclosures publish qualified spend and the award, but *not* the production's input vector — `feasibility-incentives.md:263` states this explicitly ("the disclosures give total qualified spend and top-line labor/hours/wages — **not the full input vector**"). Fixtures therefore feed qualified spend *in* as a given and assert on net cash *out*. The inputs→qualified-spend half of the pipeline has no government ground truth and must never be described as validated. — **Reversibility:** one-way — this boundary is the honesty claim of the entire product; the proof panel (Phase 8, PRV-06) and every "validated" label in the UI are built on it. Blurring it later would mean retracting a public accuracy figure.

- **D-03:** Each fixture records, at minimum: `production_title`, `jurisdiction_id`, `program_id`, `production_type` (feature | series), `season` where applicable, `qualified_spend`, `credit_amount`, `disclosure_stage` (issued | allocated | estimated), `source_url`, `source_document_sha256`, `report_period`, `date_checked`. All money as strings, parsed to `Decimal` — never float.

- **D-04:** Each fixture carries an `assertion` block: `mode: exact` or `mode: bounded`. `bounded` additionally requires `tolerance_bps` and a mandatory free-text `variance_reason` naming the specific unobservable (e.g. "uplift claimed but not itemised in ESD disclosure"). **`exact` is the default; `bounded` must be argued for in writing.** Rationale: `feasibility-incentives.md:266` warns that big studio productions layering multiple bonuses "degrade the test from *matches to the dollar* to *lands in the right zone*" — Gilded Age's 26.3% vs Succession's 25.0% is the visible residue. Without a declared tier, that degradation is invisible and the accuracy figure becomes decorative. — **Reversibility:** costly — the tier field is read by Phase 5's mismatch taxonomy (AGT-04); retrofitting it is what ROADMAP Phase 5 explicitly warns against.

- **D-05:** **At least three pairs must be `mode: exact` and must be small productions with no uplift claims.** Anora ($3,964,760 → $991,190, clean 25.0%) is the archetype and the anchor. This is the Definition-of-Done bar; small indies are the best test cases precisely because there is nothing to reverse-engineer.

- **D-06:** A pair whose fields cannot be confirmed is still committed, with `status: blocked` and an explicit `blocker` string. It counts toward the 11 but is excluded from the accuracy denominator until resolved — **and the exclusion is visible in the output, never silent.** Guessing a field or quietly dropping the pair are both forbidden.

- **D-07:** Disclosure stages are never averaged together. `issued` (NY), `allocated` (CA) and `estimated` (NJ) are reported as separate cohorts with separate accuracy figures. No blended mean-error number — ROADMAP Phase 5 success criterion 4 requires this and it starts at the fixture schema. — **Reversibility:** costly — a blended number is the specific failure ROADMAP names as "silently absorbing a real bug".

### Source Archival & Answer Location (SRC-01, 02, 05)

- **D-08:** **Raw source documents are archived byte-for-byte in the repository**, at `sources/{jurisdiction}/{yyyy-mm-dd}-{slug}.{pdf,csv,html}` — not in S3. Rationale: an S3 bucket is a new cloud resource requiring explicit per-resource approval under the PROJECT.md hosting constraint, and repo-as-audit-trail is already the stated data strategy. A handful of government PDFs is not a repo-size problem. `research/ARCHITECTURE.md` Q8's S3 mirroring recommendation is **deliberately not adopted in Milestone 1** — see Deferred. — **Reversibility:** reversible — adding an S3 mirror later is additive; the in-repo copy remains the citation target either way.

- **D-09:** Escape hatch for D-08: if a single document exceeds ~25 MB, store its SHA-256, URL and a text/markdown extraction instead of the binary, and record the omission explicitly in the manifest. Do not silently skip it.

- **D-10:** `sources/MANIFEST.yaml` records, per archived document: `url`, `retrieved_at`, `sha256`, `jurisdiction`, and what figures it is cited for. This is what makes "we extracted this figure from *this exact byte-identical document*" structurally true rather than aspirational.

- **D-11:** **SRC-01, SRC-02 and SRC-05 answers land in `.planning/SOURCE-TRUTH.md`**, one entry per question, each carrying: the question, the answer, the primary-source URL, `date_checked`, confidence, and what was refuted. Rationale: the Phase 2 jurisdiction YAMLs do not exist yet so writing into them is impossible, and the reconciliation *reasoning* (e.g. "$700M base plus a separate $100M independent-film pool, not a $700M/$800M dispute") is not rule data — it is the argument for the rule data. Phase 2's rule files then cite both the `SOURCE-TRUTH.md` entry and the primary URL.

- **D-12:** **A refuted hypothesis is recorded, not deleted.** SRC-01 and SRC-05 both ship with stated working hypotheses (`$700M + $100M indie pool`; `4.99% current vs 5.75% pre-2024-reform`). If a hypothesis turns out wrong, that is a finding worth keeping — it explains why the encoded value is what it is.

- **D-13:** Where two authoritative sources genuinely conflict and cannot be reconciled, record an explicit unresolved-conflict entry rather than picking one. This feeds PRV-07 (Phase 8: "conflicting authoritative sources appear as an unresolved conflict rather than being silently resolved") directly, and `research/PITFALLS.md` §D2/D3 already specifies the precedence ordering to apply first.

### Deploy Path & Subdomain (SHP-01, 02, 03, 04)

- **D-14:** ⚠️ **`prodfin.vockell.com` is an assumption, not a confirmed decision.** The user did not name a subdomain. Confirm before the DNS record is created — it is one word and it is the only Phase 1 item with a propagation clock.

- **D-15:** The DNS zone host for vockell.com (Route 53 vs the registrar) is **unknown and must be established as the very first task in Track B.** Not guessable from the planning documents; a two-minute lookup that gates everything else in the track.

- **D-16:** **TLS via certbot with the Apache plugin — not Caddy.** `research/STACK.md` recommends Caddy, but that recommendation assumed a clean box. ROADMAP and PROJECT.md both commit to Apache retaining ports 80/443 and reverse-proxying to uvicorn, and Caddy's entire advantage is automatic TLS *when it owns 443* — which it cannot here. Running Caddy on an inner port means two web servers on a 2 GB box for no gain. **This is an explicit overrule of STACK.md.** — **Reversibility:** reversible — swapping the TLS terminator is a vhost-level change, not a code change.

- **D-17:** **No Docker.** `uv`-managed virtualenv under `/opt/prodfin`, systemd unit checked into `deploy/`. Rationale: 2 GB with Apache and MySQL already resident; a Docker daemon plus image layers is real memory and disk for a single-process Python app. `research/STACK.md` lists Docker under Development Tools — not adopted for the host. — **Reversibility:** reversible — containerising later is additive.

- **D-18:** **Python 3.12 installed via `uv`**, never touching the system Python 3.9.2 that Bitnami and Apache depend on. `google-adk` and `google-genai` both require >=3.10, so the system interpreter cannot serve. — **Reversibility:** costly — the isolation boundary is what keeps the live vockell.com site safe; breaking it risks the existing LAMP stack.

- **D-19:** **Code reaches the box by `git pull` plus a `deploy/deploy.sh`** — no CI push, no rsync from the dev machine. Simplest thing that is reproducible and auditable from the public repo.

- **D-20:** **Day-2 payload is a real FastAPI skeleton, not a static placeholder.** `GET /health` returns version, git SHA and boot time; `GET /` returns a minimal holding page. Rationale: ROADMAP success criterion 3 says the visitor "receives a response from **the app**" — a static file proves the vhost works but proves nothing about the venv → uvicorn → systemd → proxy chain, and proving that chain end-to-end is the entire reason Track B runs on day 2. It also creates the Python package skeleton Phase 2 fills. **This is a skeleton only — no engine, no rule schema, no UI treatment.**

- **D-21:** **Track B internal ordering: DNS record → resize → Python → systemd → Apache proxy + TLS.** DNS first because it is the only step with propagation delay. Resize before TLS so the certificate is not issued against a box about to be replaced by a restored snapshot. The resize takes vockell.com briefly offline — a discrete, deliberately scheduled task, not something to stumble into.

- **D-22:** **Measure free memory immediately after the Python install and write the number into STATE.md.** STATE.md already flags this as gating the Milestone 2 data-layer decision (SQLite vs reusing the box's MySQL). Taking the measurement and not recording it wastes the one moment it is cheap to take.

- **D-23:** **The reboot test is executed, not assumed.** ROADMAP success criterion 4 requires the app to survive a host reboot. Reboot the box and confirm the service comes back on its own.

### CI Gate & Repo Posture (SHP-07, 08, 09, 10)

- **D-24:** **MIT licence.** OSI-approved and recognised unambiguously by GitHub's licence detector, so the About section renders it without argument — SHP-08 requires detection in About, not merely a LICENSE file. Apache-2.0's patent grant buys nothing for a hackathon submission.

- **D-25:** **The repository goes public at the start of Phase 1, not at submission.** PROJECT.md's honesty constraint is "the repo is public and inspectable"; going public late means the provenance story is asserted rather than demonstrated. It also surfaces any secret-scanning problem while there is still time to fix it. — **Reversibility:** one-way — once public, a leaked secret is leaked; this is exactly why the secret-scan gate (D-27) is armed in the same phase rather than later.

- **D-26:** **GitHub Actions, blocking on red** — required status checks, not report-only. SHP-07/09/10 are Stage One disqualification conditions; a report-only gate that goes red on day 9 and gets scrolled past is precisely the failure mode. The checks run in seconds.

- **D-27:** Three CI jobs:
  - `lockfile-scan` — assert the *resolved* lockfile contains none of `openai`, `anthropic`, `langchain*`, `langgraph`, `crewai`, `llama-index`, `litellm`; and assert `google-adk` appears with no extras marker (never `[all]`, `[extensions]`, `[test]` — the extras pull disallowed vendors transitively).
  - `secret-scan` — gitleaks in CI, plus GitHub native push protection enabled on the repository.
  - `commit-window` — assert every commit's author date is on or after 2026-07-27.

- **D-28:** **Also grep the source tree, not only the lockfile**, for `textract|bedrock|comprehend|rekognition|transcribe|polly|kendra|sagemaker`. `.claude/CLAUDE.md` names this as the pre-submission gate; arming it in CI on day 1 means it cannot be forgotten on day 16, and AWS Textract is the single most likely accidental disqualification on this project. Note the false-positive trap: `translate` is too common an English word to grep bare — match `boto3`-qualified call sites for that one instead of the raw string.

- **D-29:** **Commit the four strategy briefs** (`productionfinance-brief.md`, `idea-2-incentives.md`, `feasibility-incentives.md`, `hackathon-brief.md`). They are currently untracked. PROJECT.md cites all four by name as strategy notes and `feasibility-incentives.md` holds the validation-pair table the fixtures derive from — they are the provenance of the project, not scratch.

- **D-30:** **Move `LightsailDefaultKey-us-west-2 (2).pem` out of the repository root.** It is correctly gitignored and untracked today, but a `.gitignore` is one `git add -f` away from failing, and the repo is going public (D-25). Relocate rather than rely on the ignore rule.

### Claude's Discretion

The user answered "you make your best guess" to the gray-area selection, delegating **all four areas** in full. Every decision above is therefore Claude's discretion. Downstream agents should treat them as working decisions with stated rationale — overturn any of them on the user's word without needing to re-argue the case.

Two items are **not** discretion and must not be guessed by the planner:
- **D-14** — the subdomain name (`prodfin.vockell.com` is a placeholder awaiting one-word confirmation).
- **D-15** — the DNS zone host, which must be established by lookup as Track B's first task.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § "Phase 1: Foundations — Source Truth & Deploy Path" — goal, the five success criteria, the two-track split, gate notes and compliance notes
- `.planning/REQUIREMENTS.md` lines 16-20 — SRC-01 through SRC-05 verbatim, including the stated working hypotheses for SRC-01 and SRC-05
- `.planning/REQUIREMENTS.md` lines 117-130 — SHP-01 through SHP-14; note SHP-05/06/11/12/13/14 map to *later* phases and are out of Phase 1 scope
- `.planning/PROJECT.md` — constraints block (hosting, host preparation, AI-vendor boundary, honesty), and the Key Decisions table
- `.planning/STATE.md` — Blockers/Concerns section; carries the resize-downtime warning and the post-resize free-memory measurement that gates Milestone 2

### Validation pairs and source truth
- `feasibility-incentives.md` §lines 243-266 — the production/award table (Anora, Succession S4, The Gilded Age S2, Clueless S1, Joker) and, critically, the statement at line 263 that disclosures do **not** give the full input vector, plus line 266 on uplift-layered productions degrading exactness
- `.planning/research/PITFALLS.md` §D1 — the NY $700M/$800M reconciliation, likely not a conflict at all; read before starting SRC-01
- `.planning/research/PITFALLS.md` §A1.10 — the Georgia loan-out withholding 4.99% vs 5.75% resolution; read before starting SRC-05
- `.planning/research/PITFALLS.md` §B1, §B3, §B5 — allocation vs issued figures, the same production appearing in multiple disclosure batches, and what a legitimate mismatch looks like versus a model bug; these shape the fixture schema
- `.planning/research/PITFALLS.md` §D2, §D3 — the source-precedence ordering and displaying an unresolved conflict rather than silently picking one

### Deploy path and architecture
- `.planning/research/ARCHITECTURE.md` §Q5 "Deployment topology and background execution" — the systemd-supervised single-FastAPI-process topology. **Read with a correction: it assumes nginx and Postgres; ROADMAP and PROJECT.md govern and specify Apache reverse-proxy with the data layer deferred to Phase 9.**
- `.planning/research/ARCHITECTURE.md` §Q7 "Build Order and Critical Path" — confirms instance provisioning runs parallel to source verification and is non-blocking
- `.planning/research/STACK.md` — versions and rationale. **Its Caddy recommendation is overruled by D-16 and its Docker recommendation by D-17**, both because the Apache-retains-443 and 2 GB constraints postdate it.
- `.claude/CLAUDE.md` — the AI-vendor boundary, the forbidden-dependency list, and the pre-submission grep gate that D-28 arms early

### Governing brief
- `productionfinance-brief.md` — governs wherever the two briefs disagree (PROJECT.md states this explicitly)
- `hackathon-brief.md` — read only for the judging scorecard; its "Our track: IBM" line refers to the sibling animatic project and does **not** apply here

</canonical_refs>

<code_context>
## Existing Code Insights

**There is no source code.** The repository contains planning documents, four strategy briefs, and a `.gitignore` — nothing else. Phase 1 writes the first code in the project.

### Reusable Assets
- `.gitignore` — already correct and protective: blocks `.env`, `.env.*` (with an `!.env.example` escape), `*.pem`, `*.key`, `credentials.json`, `service-account*.json`, `secrets/`, plus the Python/Node/SQLite caches. Written 2026-08-24 in commit `674c088` with the comment "NEVER commit. This repository is public per hackathon rules." Extend it; do not rewrite it.
- Ten existing commits with clean conventional-commit messages, all dated 2026-08-23/24 — comfortably inside the contest window opened 2026-07-27, so SHP-09 passes on existing history and only needs its CI guard armed.

### Established Patterns
- Documentation-first: every planning artifact is committed with a `docs(...)` conventional-commit message. Phase 1's own outputs (`SOURCE-TRUTH.md`, fixtures, `sources/MANIFEST.yaml`) should follow the same convention.
- `git.branching_strategy` is `none` in `.planning/config.json` — work commits directly, no phase branches. `create_tag` is true.

### Integration Points
- **No git remote is configured.** `git remote -v` is empty and there is no `LICENSE` file. SHP-08 (public repo, OSI licence detectable in About) is entirely unbuilt — creating the GitHub remote is a Phase 1 task, not an assumed precondition.
- The four strategy briefs are untracked (`git status` shows them as `??`) — see D-29.
- `LightsailDefaultKey-us-west-2 (2).pem` sits in the repo root, correctly untracked — see D-30.
- The `tests/fixtures/validation_pairs/` directory created here is the integration point Phase 3's CI suite (SHP-14) and Phase 5's Job 1 (AGT-01..04) both consume.
- The FastAPI package skeleton created by D-20 is the integration point Phase 2's engine spine plugs into.

</code_context>

<specifics>
## Specific Ideas

- **The anchor figure, exact:** Anora / New York — `$3,964,760` qualified spend → `$991,190` credit issued, a clean 25.0%. This is the pair that must match to the dollar. It is the demo's opening beat and the first real cited number on a hosted URL.
- **Named pairs already sourced** (from `feasibility-incentives.md:245-250`): Succession S4 (NY, $102,920,384 → $25,747,913 issued, 25.0%), The Gilded Age S2 (NY, $134,340,015 → $35,318,864 issued, 26.3%), Clueless S1 reboot (CA, $46,522,000 → $16,335,000 allocated, 35.1%), Joker (NJ, $6,133,257 → $1,962,642 estimated, 32.0%). Six more to locate to reach 11.
- **Stated hypotheses to confirm or refute, not assume:** SRC-01 — "$700M base plus a separate $100M independent-film pool, not a $700M/$800M dispute." SRC-05 — "5.75% is pre-2024-reform, 4.99% is current."
- The Gilded Age's 26.3% against Succession's 25.0% is the concrete illustration of D-04: that 1.3-point spread is an unlisted uplift, and it is why a tier field exists on every fixture.

</specifics>

<deferred>
## Deferred Ideas

- **S3 mirroring of source documents and index snapshots** — `research/ARCHITECTURE.md` §Q8 recommends `s3://prodfin-index/...` for immutable, content-addressable artifacts. Deferred: an S3 bucket is a new cloud resource requiring explicit per-resource approval, and the in-repo archive (D-08) satisfies Milestone 1's auditability need at zero provisioning cost. Revisit at Phase 9 if the index needs permanent public data-point URLs (IDX-08).
- **Step-level job resumption** — `research/ARCHITECTURE.md` §Q5 names true resume-from-last-completed-step as a post-Milestone-1 enhancement. Not Phase 1; the durable job-state table lands in Phase 7.
- **EventBridge Scheduler** as a managed alternative to a systemd timer — explicitly rejected for Milestone 1 in `research/ARCHITECTURE.md` §Q8; revisit only if scheduling must survive the instance being rebuilt.
- **Postgres as the data layer** — `research/ARCHITECTURE.md` assumes it throughout, but ROADMAP Phase 9 defers the SQLite-vs-MySQL decision to that phase's planning, gated on the free-memory measurement taken here (D-22). Phase 1 provisions no database.

</deferred>

---

*Phase: 1-Foundations — Source Truth & Deploy Path*
*Context gathered: 2026-08-24*
