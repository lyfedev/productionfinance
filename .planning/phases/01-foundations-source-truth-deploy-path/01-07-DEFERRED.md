---
plan: 01-07
status: deferred
decided_by: user
decided_on: 2026-08-24
supersedes_plan_as_written: true
---

# 01-07 Lightsail resize — DEFERRED (not complete, not abandoned)

## Decision

The user declined the snapshot-and-restore resize of `vockell_dot_com_LAMP` from
`nano_2_0` (0.5 GB, 1 vCPU) to `small_3_0` (2 GB, 2 vCPU) at this time, choosing
instead to attempt deployment on the existing instance and resize later only if
the box actually runs out of memory.

## Why

1. **Recurring cost.** `small_3_0` is $12/mo against the current bundle's ~$5 —
   roughly +$7/mo ongoing. Cloud spend requires explicit per-resource approval.
2. **The resize premise is an estimate, not a measurement.** `.claude/CLAUDE.md`
   justifies the resize as "472 MB cannot hold FastAPI + the Google SDK import
   footprint + a database alongside the existing Apache and MySQL." Phase 1
   deploys none of the heavy parts: no `google-genai`, no database — only the
   bare FastAPI skeleton from plan 01-01. The stated premise is not yet under test.
3. **Downtime.** The resize takes vockell.com offline for a measured window. The
   user classified this work as off the critical path.

## What this changes downstream

- **01-08** proceeds against the existing 0.5 GB box rather than a resized one.
  Its memory headroom is genuinely uncertain — that is the point of the experiment.
- **01-09** was already mis-specified (see 01-06-SUMMARY.md): written for a
  dedicated subdomain vhost plus its own certificate, superseded by the user's
  path-mount decision (`https://vockell.com/finance`).

## When this must be revisited

If 01-08 or any later phase hits memory pressure on the box, this deferral is the
first thing to reverse. The hosted URL is a Stage One submission requirement with a
hard deadline of 2026-09-09, so this cannot be deferred indefinitely — only until
there is evidence about the real memory footprint.

## Explicitly NOT done

No snapshot was taken. No instance was resized. No AWS resource was created,
modified, or deleted. The requirement this plan was to satisfy remains open.
