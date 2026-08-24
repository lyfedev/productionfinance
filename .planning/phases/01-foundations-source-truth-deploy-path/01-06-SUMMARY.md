---
phase: 01-foundations-source-truth-deploy-path
plan: 06
subsystem: infra
tags: [deploy, dns, apache, path-mount, runbook]

# Dependency graph
requires:
  - phase: 01-foundations-source-truth-deploy-path (plan 01)
    provides: "Relocated SSH key at ~/.ssh/LightsailDefaultKey-us-west-2.pem, referenced by PRODFIN_SSH_KEY"
provides:
  - "deploy/hosting.env — shell-sourceable host facts (PRODFIN_HOST, PRODFIN_PUBLIC_PATH, PRODFIN_PUBLIC_URL, PRODFIN_STATIC_IP, instance/AWS/SSH/app facts) consumed by every later Track B task (01-07 through 01-09)"
  - "deploy/README.md — the Track B runbook: topology, DNS facts, collapsed D-21 ordering, rollback positions, the Task 3 not-applicable record, and the downstream-impact flag for 01-09"
  - "D-14 resolved: public URL is https://vockell.com/finance, a path mount on the existing vockell.com apex — not a new subdomain"
affects: ["01-07 (resize)", "01-08 (systemd/Python)", "01-09 (Apache proxy + TLS — needs revision, see Deviations)"]

actuals:
  tokens: 3250
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns: ["shell-sourceable KEY=value host-facts file, one source of truth for hostname/IP/paths read by every later deploy task"]

key-files:
  created: [deploy/hosting.env, deploy/README.md]
  modified: []

key-decisions:
  - "D-14 resolved by the developer at the 01-06 checkpoint: path-based mount at vockell.com/finance, not a new subdomain — 'this is not critical path -- just put it at vockell.com/finance and not worry about devops'"
  - "Consequently: no new DNS record was created (Task 3 recorded as not-applicable), and PRODFIN_HOST records the existing apex (vockell.com) plus a new PRODFIN_PUBLIC_PATH (/finance) rather than a new subdomain label"
  - "Flagged, not fixed here: plan 01-09 (Apache proxy + TLS) was written for a dedicated subdomain vhost and a new bncert-tool certificate — under the path-mount decision it needs to become a ProxyPass /finance location inside the existing vockell.com vhost, reusing the existing certificate. This plan does not edit 01-09."

requirements-completed: []

coverage:
  - id: D1
    description: "deploy/hosting.env and deploy/README.md record the confirmed host facts (path-mount at vockell.com/finance) that every later Track B task reads — hostname, static IP, instance, AWS profile/region, SSH user/key, app port/root, service name/user"
    requirement: "SHP-03"
    verification:
      - kind: other
        ref: "set -a && . ./deploy/hosting.env && set +a && test -n \"$PRODFIN_HOST\" && test \"$PRODFIN_STATIC_IP\" = \"35.165.60.123\" && test \"$PRODFIN_APP_PORT\" = \"8000\" && test -f \"$(eval echo $PRODFIN_SSH_KEY)\" && ! git check-ignore -q deploy/hosting.env"
        status: pass
      - kind: other
        ref: "credential-shape scan: no assignment >60 chars, no key/secret/token/password on RHS other than PRODFIN_SSH_KEY"
        status: pass
      - kind: other
        ref: "grep section checks on deploy/README.md (Topology, DNS facts, D-21 ordering, How to verify, Register.com, no Route 53)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Task 3 (create the subdomain A record) is correctly recorded as NOT APPLICABLE — not silently skipped, not marked complete — with the reason (path mount needs no new DNS record) documented in deploy/README.md and this SUMMARY, and the downstream impact on plan 01-09 flagged for the orchestrator"
    verification:
      - kind: other
        ref: "dig +short A vockell.com == 35.165.60.123 (apex unchanged); dig +short NS vockell.com == dns105/dns106.register.com (zone unchanged); curl -I https://vockell.com returns 301 to www (live site unaffected)"
        status: pass
    human_judgment: true
    rationale: "Whether the 01-09 downstream-impact note is complete/accurate enough for that plan's next executor to act on without re-deriving the ProxyPass approach is a documentation-quality judgment, not something a grep can assert."

duration: 12min
completed: 2026-08-24
status: complete
---

# Phase 1 Plan 6: Host Facts + Deploy Runbook (Path-Mount Resolution) Summary

**Resolved D-14 to a path mount at `https://vockell.com/finance` (no new subdomain, no new DNS record), recorded every host fact later Track B plans need in `deploy/hosting.env`, wrote `deploy/README.md` as the runbook, and explicitly recorded DNS record creation as not-applicable rather than skipping it silently.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-24T22:47:00Z
- **Completed:** 2026-08-24T22:59:52Z
- **Tasks:** 2 of 3 executed (Task 1 decided by user at checkpoint; Task 3 recorded not-applicable)
- **Files modified:** 2 created (deploy/hosting.env, deploy/README.md)

## Accomplishments
- **D-14 resolved** — the checkpoint that halted the prior executor is answered: the public URL is `https://vockell.com/finance`, a path mount on the existing `vockell.com` apex, not a new subdomain. No propagation clock in this phase anymore.
- `deploy/hosting.env` created: `PRODFIN_HOST=vockell.com`, plus a new `PRODFIN_PUBLIC_PATH=/finance` and `PRODFIN_PUBLIC_URL=https://vockell.com/finance` (additions beyond the plan's original field list, needed because the path-mount decision requires recording a path prefix the plan's subdomain-only design didn't anticipate — Rule 2), and the remaining fields exactly as specified: `PRODFIN_STATIC_IP=35.165.60.123`, `PRODFIN_INSTANCE=vockell_dot_com_LAMP`, `PRODFIN_AWS_PROFILE=newaccount`, `PRODFIN_AWS_REGION=us-west-2`, `PRODFIN_SSH_USER=bitnami`, `PRODFIN_SSH_KEY=~/.ssh/LightsailDefaultKey-us-west-2.pem`, `PRODFIN_APP_PORT=8000`, `PRODFIN_APP_ROOT=/opt/prodfin`, `PRODFIN_SERVICE=prodfin.service`, `PRODFIN_SERVICE_USER=prodfin`
- `deploy/README.md` created: topology diagram, DNS facts (Register.com, not Route 53), the collapsed D-21 ordering table with rollback positions, the Task 3 not-applicable record with reasoning, the downstream-impact note for plan 01-09, the standing "don't touch existing DNS/vhost/cert" rule, and a "How to verify" command reference
- **Task 3 (create subdomain A record) recorded as NOT APPLICABLE** in `deploy/README.md` and here — not silently dropped. Verified live that nothing changed: apex `vockell.com` still resolves to `35.165.60.123`, the zone's nameservers are still `dns105`/`dns106.register.com`, and `curl -I https://vockell.com` still returns a normal response (301 to `www.vockell.com`)
- Downstream impact on plan 01-09 flagged explicitly (not edited): that plan was written for a dedicated subdomain vhost + new Let's Encrypt certificate via `bncert-tool`; under the path-mount decision it needs to become a `ProxyPass /finance` location inside the **existing** vockell.com vhost, reusing the existing certificate — no new TLS issuance

## Task Commits

1. **Task 1: Confirm the subdomain label** — resolved by the user's checkpoint answer ("vockell.com/finance, not critical path, don't worry about devops"); no separate file change, folded into the Task 2 commit below since the decision only manifests as recorded values.
2. **Task 2: Record the host facts and write the deploy runbook** — `2b14422` (feat)
3. **Task 3: Create the subdomain A record** — **NOT APPLICABLE**, no commit. Path mount needs no new DNS record; see `deploy/README.md` "Task 3 — not applicable" section for the full reasoning.

_No separate plan-metadata commit was made beyond the task commit above; STATE.md/ROADMAP.md/REQUIREMENTS.md updates below are committed together after this SUMMARY, per the standard close-out sequence._

## Files Created/Modified
- `deploy/hosting.env` - shell-sourceable host facts every later Track B task reads (hostname, static IP, instance, AWS profile/region, SSH user/key, app port/root/service)
- `deploy/README.md` - Track B runbook: topology, DNS facts, D-21 ordering + rollback, Task 3 not-applicable record, 01-09 downstream-impact flag, How-to-verify commands

## Decisions Made
- **D-14 resolved (developer, via checkpoint):** path mount at `vockell.com/finance`, not a new subdomain. Recorded verbatim in `deploy/hosting.env`'s header comment and in `deploy/README.md`'s "D-14 resolution" section.
- **PRODFIN_HOST set to the existing apex `vockell.com`**, not a new label — because there is no new subdomain to name. This is the closest honest reading of the plan's original acceptance criterion ("PRODFIN_HOST equals the label confirmed at Task 1, fully qualified under vockell.com") under the changed decision: the confirmed value literally is `vockell.com`.
- **Added `PRODFIN_PUBLIC_PATH` and `PRODFIN_PUBLIC_URL`** as new fields beyond the plan's original field list — necessary so the path prefix isn't lost; later plans (especially 01-09's FastAPI `root_path`/`X-Forwarded-Prefix` handling) need this value and it has no other home.
- **Did not mark SHP-03 complete.** The phase requirement as literally worded ("A subdomain DNS record exists and resolves") no longer describes what this plan did — there is no subdomain and no new DNS record. The underlying goal (app reachable at a public URL) isn't actually met until plan 01-09 adds the `ProxyPass /finance` location; `requirements.ready-ids` also confirms SHP-03 is blocked pending 01-09's own SUMMARY, since both plans declare it. Recorded here rather than force-marking it to make the checklist look further along than it is.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `PRODFIN_PUBLIC_PATH` and `PRODFIN_PUBLIC_URL` to `deploy/hosting.env`**
- **Found during:** Task 2 (writing host facts)
- **Issue:** The plan's field list was designed around a subdomain-only URL (`PRODFIN_HOST` alone was sufficient). The user's actual decision is a path-based mount, so a hostname alone is insufficient — later plans (especially 01-09's Apache `ProxyPass` config and FastAPI's `root_path` handling) need the path prefix, and there was no field to hold it.
- **Fix:** Added `PRODFIN_PUBLIC_PATH=/finance` and a derived `PRODFIN_PUBLIC_URL=https://vockell.com/finance` alongside the plan's original fields.
- **Files modified:** `deploy/hosting.env`
- **Verification:** Sourcing the file exposes both new variables; the plan's original automated verify script still passes unchanged since it only asserts the original field set.
- **Committed in:** `2b14422` (Task 2 commit)

**2. [Rule 4 — surfaced, not auto-fixed] Plan 01-09's subdomain-vhost approach no longer matches the D-14 decision**
- **Found during:** Task 2 (writing the runbook, working through D-21's ordering)
- **Issue:** `01-09-PLAN.md` (not read in full by this executor, per the resume instructions — only its role in the topology was needed) was written under the original subdomain assumption: a dedicated `ServerName prodfin.vockell.com` vhost and a new Let's Encrypt certificate via `bncert-tool`. Under the path-mount decision, that approach is wrong — there is no new hostname to certify.
- **Correct approach (not implemented here):** a `ProxyPass /finance` + `ProxyPassReverse /finance` location inside the **existing** vockell.com vhost, reusing its existing certificate, plus FastAPI `root_path="/finance"` (or `X-Forwarded-Prefix`) handling so generated links/OpenAPI docs resolve correctly under the path prefix.
- **Why not auto-fixed:** this is an architectural change to a plan this executor was explicitly instructed not to edit ("Do NOT edit plan 01-09 yourself; just record clearly that it needs revision and why, so the orchestrator can surface it"). Editing another plan file is out of this plan's scope regardless.
- **Action taken:** Documented in full in `deploy/README.md` under "Downstream impact on plan 01-09" and here, so the orchestrator/next planner sees it before 01-09 executes.
- **Resolution owner:** whoever plans or executes 01-09 next — likely needs a `/gsd-plan-phase` revision pass on that plan before it runs.

---

**Total deviations:** 2 (1 auto-fixed — Rule 2, missing field; 1 surfaced not auto-fixed — Rule 4, architectural change in a sibling plan, flagged per explicit instruction rather than edited)
**Impact on plan:** The auto-fix (new env fields) is additive and necessary for correctness — no scope creep, since without it later plans would have no source of truth for the path prefix. The surfaced item is a real blocker for 01-09 as currently written, but resolving it belongs to that plan's own execution/planning pass, not this one.

## Issues Encountered
None. The prior executor's halt was a checkpoint (Task 1, `gate="blocking-human"`), not an error — this continuation resumed cleanly from the user's answer with no code or state to repair.

## User Setup Required
None - no external service configuration required. (No DNS panel action was taken or needed, per the path-mount decision.)

## Next Phase Readiness
- `deploy/hosting.env` and `deploy/README.md` are ready for plans 01-07 (resize) and 01-08 (Python/systemd) to consume as-is — those plans' host-facts dependencies are unaffected by the path-mount decision.
- **Blocker for 01-09:** that plan needs a revision pass (subdomain vhost + new cert → path-mount ProxyPass + existing cert) before it can execute correctly. This is now recorded in both `deploy/README.md` and STATE.md's blockers.
- SHP-03 remains `Pending` in REQUIREMENTS.md, correctly — it will not be markable complete until 01-09 (the other plan declaring it) also finishes and demonstrates the app actually reachable at `https://vockell.com/finance`.

---
*Phase: 01-foundations-source-truth-deploy-path*
*Completed: 2026-08-24*

## Self-Check: PASSED

- `deploy/hosting.env` exists on disk
- `deploy/README.md` exists on disk
- `.planning/phases/01-foundations-source-truth-deploy-path/01-06-SUMMARY.md` exists on disk
- Commit `2b14422` (Task 2: host facts + runbook) present in git log
- Commit `8279754` (SUMMARY) present in git log
