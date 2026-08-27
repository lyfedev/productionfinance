---
status: testing
phase: 04-cost-localization-landed-cost-outputs
source: [04-VERIFICATION.md]
started: 2026-08-27T13:45:00Z
updated: 2026-08-27T13:45:00Z
---

## Current Test

number: 1
name: Judge whether COST-02's "localized against published union rate cards (IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA)" is genuinely met given the actual data coverage
expected: |
  A reviewer decision on whether the committed data honestly satisfies the roadmap's
  Success Criterion 1, or whether it should be treated as a documented, accepted scope
  reduction (an override) pending further sourcing.

  The mechanism is verified correct and well-tested: dated rate-row selection, a
  mandatory sibling fringe Figure, raise-on-no-covering-row, raise-on-overlapping-bands,
  and a sourced-requires-source_url validator. COST-03 (fringe and payroll burden
  included, never compared against published rates) is fully and unconditionally met.

  What is in question is COVERAGE, not mechanism:

  - IATSE Local 600 camera department is `basis: sourced` for New York and Los Angeles
    — 15% of `crew_share` per data/crew_tiers.yaml
  - The other 9 of 10 below-the-line departments price at a flat $450/day `general_crew`
    row that is `basis: estimated` industry commentary, not transcribed from any named
    union's published card
  - SAG-AFTRA (data/union_rates/sag-aftra.yaml) has ZERO rate rows — principal cast is
    not priced as a labour line at all; only its imported headcount feeds travel/housing
  - DGA and WGA have zero CONSUMED rows — director and writer are above-the-line roles
    that crew_tiers.yaml explicitly excludes from below-the-line pricing; their rows
    exist but are inert
  - ACTRA is absent entirely — no Canadian city is in the floor set (D-54: NY/LA/London),
    a legitimate scope match rather than a gap
  - London's BECTU coverage mirrors NY/LA: one dated, sourced grip-branch row stands in
    for 9 of 10 departments

  All of this is honestly disclosed in .planning/WINDOWS.md entries 6-10, 19, 21, and
  nothing was silently promoted to `sourced`.

  The question to answer: can "localized against published union rate cards" be said to
  hold when roughly 85% of below-the-line labour cost per city is priced from an
  unattributed flat estimate rather than any of the six named unions' actual cards?

  Three defensible answers:
  a) PASS — the labelling is honest, the mechanism is right, and coverage is a data
     backlog item rather than a criterion failure
  b) PASS WITH OVERRIDE — record it as an accepted, documented scope reduction with the
     sourcing gap tracked to a later phase
  c) FAIL — criterion 1 is not met until material below-the-line coverage is sourced

  Note for context: SAG-AFTRA sourcing was attempted and is blocked by DataDome bot
  protection on sagaftra.org (confirmed with both curl and headless Chromium), so
  closing that particular gap is not simply a matter of more effort.
awaiting: user response

## Tests

### 1. Judge whether COST-02 union-rate-card coverage genuinely satisfies Success Criterion 1
expected: A reviewer decision — PASS, PASS WITH OVERRIDE, or FAIL — on whether ~15% sourced below-the-line labour coverage (IATSE Local 600 camera only, with SAG-AFTRA at zero rows) honestly satisfies "localized against published union rate cards", or whether it should be recorded as an accepted scope reduction pending further sourcing.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
