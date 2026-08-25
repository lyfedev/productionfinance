# Phase 3: New York End-to-End — The Anora Proof - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-25
**Phase:** 3-New York End-to-End — The Anora Proof
**Areas discussed:** None selected — all four gray areas delegated to Claude

---

## Gray Areas Presented

A single multi-select was offered. The user selected none, answering **"none. all good."** — delegating all four areas in full, the same posture taken in Phase 1 ("you make your best guess").

| Area | Description as presented | Selected |
|------|--------------------------|----------|
| The Anora proof path | How $3,964,760 reaches the engine without the visitor typing a budget. INP-08 refuses budget input; success criterion 3 needs the exact disclosed figure; D-02 says qualified spend is fed in as a given. Is the proof a separate "reproduce a disclosure" route, an Anora preset, or an expert qualified-spend field? Also: what the refusal actually looks like when someone tries to enter a dollar amount. | |
| Spec-to-spend boundary | Does describing a production actually return a number in Phase 3, or only capture the spec? Pricing it means building stage [1] BudgetModelBuilder — Phase 4's neighbourhood. Includes where INP-03's crew-tier department ratios come from and whether they're cited or labelled an internal modelling assumption. | |
| Form + result shape | Server-rendered HTML from FastAPI (Jinja/HTMLResponse) versus standing up the React 19 + Vite SPA now. ROADMAP says minimal, no UI hint, Phase 6 owns the interface — but Phase 6 is React, so a server-rendered form is throwaway. Also what the result page shows beside the number (source link, date checked, confidence tier). | |
| SHP-14 non-vacuity | How "deliberately corrupting a rule value makes the suite fail" gets proven and stays proven. An automated mutation job in CI that corrupts us-ny.yaml in a temp copy and asserts red, versus a one-time documented ritual with recorded evidence. Phase 8 has to re-prove this — whichever shape lands here is what gets re-run. | |

**User's choice:** "none. all good."
**Notes:** No areas selected; no follow-up questions asked. Full delegation.

---

## Claude's Discretion

All four areas. Decisions **D-31 through D-52** in `03-CONTEXT.md` are Claude's calls, each recorded with its rationale so it can be overturned on sight rather than re-derived.

Alternatives considered and explicitly rejected, recorded so they are not rediscovered as shortcuts:

| Rejected option | Recorded as | Why rejected |
|---|---|---|
| An "Anora preset" production spec whose derived spend is pinned to $3,964,760 | D-33 | Presents a modelled number as a reproduced one, at the exact place the product's central claim is staked. The repo is public — the pin would be visible in the diff. |
| An expert-mode "I already know my qualified spend" field on the spec form | D-34 | Reopens INP-08 through the door a producer reaches for first, and makes Route A's output indistinguishable from Route B's. |
| Pricing the described production in Phase 3 via a quick spec→spend model | D-36 | Produces a plausible qualified spend with no source, which would then render a credit figure beside a validated one. |
| React 19 + Vite 8 SPA started in Phase 3 | D-42 | Phase 6 is a rewrite regardless; a Vite build adds an npm toolchain to the deploy path on a 472 MB box whose resize (01-07) was deferred. |
| A one-time documented non-vacuity ritual instead of a CI job | D-49 | Proves the suite was non-vacuous once, on the day it ran. Suites go vacuous later and nobody notices. |

Two decisions were flagged in CONTEXT.md as load-bearing on the project's honesty claim, to be escalated rather than quietly reversed during planning or execution: **D-33** (no pinned preset) and **D-36 / D-39** (no unsourced qualified-spend figure rendered anywhere; no modelling assumption wearing a `validated` tier).

## Deferred Ideas

Captured in `03-CONTEXT.md` `<deferred>`. In brief: the spec→spend budget model and tier→department-ratio table (Phase 4); React/Vite, the map, slider, ranked list and design treatment (Phase 6); the full proof panel (Phase 8); CA/NJ/CT models and the Job 1 validation loop (Phase 5); live research for uncurated cities (Phase 7); extending the mutation table to CT's anchor (blocked on WINDOWS.md #3); and a separate labelled "unvalidated, self-supplied basis" route (rejected for Phase 3 per D-34).
