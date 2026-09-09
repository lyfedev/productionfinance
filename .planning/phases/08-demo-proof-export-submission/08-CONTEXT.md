# Phase 8: Demo Proof, Export & Submission — Context

**Gathered:** 2026-09-09
**Status:** Ready for planning

<domain>
## Phase Boundary

The SHIP GATE. Everything above this line in ROADMAP.md is the submission.

Four demo beats showable on the hosted URL, the proof visible in-product, and
the submission verified working for a cold anonymous visitor.

Delivered in FULL. Nothing here is cut, deferred, staged, or reduced.

</domain>

<decisions>
## Implementation Decisions

- **D-98 — The proof panel shows the government document itself, not a citation of it.** UI-07 and DMO-01 both require a reproduced government figure displayed *alongside the government document*. The repo already archives source documents byte-for-byte with re-derivable sha256 under `sources/`, so the panel serves the archived artifact rather than linking out to a URL that may 404 (Connecticut's DECD page already does). A link to a live government page may accompany it; it may not replace it. — **Reversibility:** reversible.

- **D-99 — PRV-07's source conflict is surfaced, never resolved.** Where two authoritative sources disagree, the product shows both with their citations and states that the conflict is unresolved. It must not pick a winner, average them, or silently prefer the more recent. This is the same refusal discipline as `engine.net_cash.transferable` declining to convert at an unsourced discount rate. — **Reversibility:** one-way — silently resolving a conflict destroys the evidence that there was one.

- **D-100 — The accuracy figure shown in-product (PRV-06) is the honest bucket-count summary, never a single blended percentage.** `agent/taxonomy.py::AccuracySummary` deliberately has no percentage field, and a test enforces its absence. The page shows exact-match / explained-variance / unexplained counts. A headline percentage that folds unexplained mismatches into an average is precisely what D-86 ruled out. — **Reversibility:** one-way — the requirement's whole point is that unexplained mismatches stay visible.

- **D-101 — DMO-04 (a city researched live and priced, labelled unvalidated) depends on API credentials that are not yet installed.** It must not be faked, pre-recorded and presented as live, or stubbed. If credentials are absent at submission time, the beat is reported as unavailable and the reason stated — the honest outcome — rather than simulated. A `sleep()` behind a progress bar is named in the project brief as a Stage One death. — **Reversibility:** one-way — a faked live demo discovered by a judge ends the submission.

- **D-102 — SHP-13 (cold verification from a logged-out browser on a different network) is a HUMAN action and the literal final pre-submission step.** No agent can perform it. It is recorded as an explicit handoff with a checklist, not silently marked done. — **Reversibility:** reversible.

- **D-103 — The re-verification sweep re-runs gates armed earlier rather than trusting their earlier passes.** Re-prove SHP-14's suite non-vacuous by breaking a rule value and confirming the suite catches it; grep production logs for one real Gemini call and one real Parallel call fired by a live logged-out session; re-confirm the lockfile is clean (SHP-07) and the About-section licence is detectable (SHP-08). A gate that passed a week ago is not evidence about today's tree. — **Reversibility:** reversible.

### Claude's Discretion

Export document format for UI-09, the proof panel's layout, how the four demo
beats are sequenced on the page, and the written description's structure.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 8 section, its five Success Criteria and the re-verification sweep
- `.planning/REQUIREMENTS.md` — DMO-01..04, PRV-06, PRV-07, UI-07, UI-09, SHP-11, SHP-12, SHP-13
- `.planning/WINDOWS.md` — the unmet-truth register; entries #26 and #28 are the credential gap
- `.claude/CLAUDE.md` — the AI-vendor line, the honesty constraint, the pre-submission grep checklist
- `docs/sdk-call-sites.md` — the D-96 audit table, evidence for the write-up
- `sources/MANIFEST.yaml` — archived government documents with sha256, the proof panel's material
- `agent/taxonomy.py` — `AccuracySummary`, the honest accuracy shape PRV-06 must render
