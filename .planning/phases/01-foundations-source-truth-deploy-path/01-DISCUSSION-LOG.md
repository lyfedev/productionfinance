# Phase 1: Foundations — Source Truth & Deploy Path - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 1-Foundations — Source Truth & Deploy Path
**Areas discussed:** Validation pair contract, Source archival & answer location, Deploy path & subdomain, CI gate & repo posture — all four delegated to Claude in a single turn

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Validation pair contract | What each of the 11 fixtures records, and what it's allowed to prove. Disclosures give spend+award but not the input vector — so pairs test the incentive interpreter, not cost localization. Exact-match for all, or tiered? | ✓ (delegated) |
| Source archival & answer location | Archive raw bytes (in-repo / S3 / hash-only) or URL+date only? Do SRC-01/02/05 answers land in a decision log or straight into jurisdiction YAML? | ✓ (delegated) |
| Deploy path & subdomain | Which subdomain, DNS host, TLS mechanism under Apache, how code reaches the box, what the URL serves on day 2. | ✓ (delegated) |
| CI gate & repo posture | Which OSI licence, when the repo goes public, how hard CI blocks, which scanning tools. | ✓ (delegated) |

**User's choice:** "you make your best guess" — free-text response delegating all four areas in full.

**Notes:** The user did not select a subset; they handed the whole set to Claude in one turn. No follow-up questions were asked, per the delegation. Decisions were made against PROJECT.md, ROADMAP.md, REQUIREMENTS.md, the four research documents and `feasibility-incentives.md`, with rationale recorded inline in CONTEXT.md so any of them can be overturned on sight.

---

## Claude's Discretion

All four areas. Thirty decisions (D-01 through D-30) recorded in CONTEXT.md `<decisions>`.

Headline calls and the alternative rejected in each case:

| Decision | Chosen | Alternative rejected | Why |
|---|---|---|---|
| D-02 | Pairs validate the incentive interpreter only | Pairs validate the full inputs→net-cash pipeline | `feasibility-incentives.md:263` — disclosures publish no input vector, so the cost-localization half has no ground truth and cannot honestly be called validated |
| D-04 | Tiered assertions (`exact` default, `bounded` requires written reason) | Uniform exact-match on all 11 | `feasibility-incentives.md:266` — uplift-layered studio productions degrade to "right zone"; an undeclared degradation makes the accuracy figure decorative |
| D-07 | Issued / allocated / estimated reported as separate cohorts | One blended accuracy number | ROADMAP Phase 5 SC-4 forbids a blend that can silently absorb a real bug |
| D-08 | Raw documents archived in-repo | S3 bucket per `research/ARCHITECTURE.md` §Q8 | S3 is a new cloud resource needing per-resource approval; repo-as-audit-trail already the stated strategy |
| D-11 | Answers to `.planning/SOURCE-TRUTH.md` | Written directly into jurisdiction YAML | Those YAMLs do not exist until Phase 2, and the reconciliation reasoning is not rule data |
| D-16 | certbot + Apache plugin | Caddy, per `research/STACK.md` | Caddy's only advantage is automatic TLS when it owns 443, which Apache retains; two web servers on a 2 GB box buys nothing — **explicit STACK.md overrule** |
| D-17 | `uv` venv + systemd, no Docker | Docker Compose, per `research/STACK.md` dev tools | Docker daemon + image layers is real memory on a 2 GB box already running Apache and MySQL |
| D-20 | Real FastAPI skeleton on day 2 | Static holding page | ROADMAP SC-3 says "a response from **the app**"; a static file proves the vhost but not the venv→uvicorn→systemd→proxy chain, which is the whole point of Track B |
| D-24 | MIT licence | Apache-2.0 | Both OSI-approved and both detected in About; Apache's patent grant buys nothing here and MIT is shorter to explain |
| D-25 | Repo public from the start of Phase 1 | Public at submission | PROJECT.md's honesty constraint is "public and inspectable"; going public late asserts provenance rather than demonstrating it, and front-loads secret-scan risk while there is time to fix it |
| D-26 | CI blocking on red | Report-only | SHP-07/09/10 are Stage One disqualification conditions; a red report-only gate on day 9 gets scrolled past |

**Explicitly withheld from discretion** — the planner must not guess these:

- **D-14** — the subdomain name. `prodfin.vockell.com` is a placeholder awaiting one word from the user. It is the only Phase 1 item with a propagation clock.
- **D-15** — the DNS zone host for vockell.com (Route 53 vs registrar). Not determinable from the planning documents; a lookup, and Track B's first task.

## Findings surfaced during the codebase scout

Not decisions, but discovered facts that shaped several of the above:

- No git remote is configured and no `LICENSE` file exists — SHP-08 is entirely unbuilt, not a partially-satisfied precondition.
- The four strategy briefs are untracked in git despite PROJECT.md citing all four by name (→ D-29).
- `LightsailDefaultKey-us-west-2 (2).pem` sits in the repo root, correctly gitignored and untracked (→ D-30).
- All ten existing commits fall inside the contest window, so SHP-09 passes on current history and only needs its guard armed.
- `research/ARCHITECTURE.md` assumes nginx and Postgres throughout, contradicting ROADMAP/PROJECT.md (Apache; data layer deferred to Phase 9). Flagged inline in CONTEXT.md `<canonical_refs>` so downstream agents read it with the correction attached.

## Deferred Ideas

- **S3 mirroring** of source documents and index snapshots (`research/ARCHITECTURE.md` §Q8) — needs per-resource approval; revisit at Phase 9 for IDX-08 permanent data-point URLs.
- **Step-level job resumption** — named post-Milestone-1 in `research/ARCHITECTURE.md` §Q5; durable job-state table lands in Phase 7.
- **EventBridge Scheduler** — already rejected for Milestone 1 in §Q8; only relevant if scheduling must survive an instance rebuild.
- **Postgres as the data layer** — ROADMAP Phase 9 defers SQLite-vs-MySQL to that phase, gated on the free-memory measurement taken here (D-22). Phase 1 provisions no database.
