---
phase: 01-foundations-source-truth-deploy-path
plan: 09
subsystem: infra
tags: [apache, reverse-proxy, tls, path-mount, deploy]

# Dependency graph
requires:
  - phase: 01-foundations-source-truth-deploy-path (plan 01-06)
    provides: "D-14 resolved to a path mount (https://vockell.com/finance), deploy/hosting.env, deploy/README.md runbook, the explicit downstream-impact flag for this plan"
  - phase: 01-foundations-source-truth-deploy-path (plan 01-08)
    provides: "prodfin.service (systemd) running the FastAPI app on 127.0.0.1:8000, deploy/deploy.sh idempotent deploy path"
provides:
  - "https://vockell.com/finance reachable by an anonymous, off-box visitor over a valid, unmodified Let's Encrypt TLS chain"
  - "The existing vockell.com vhost (/opt/bitnami/apache/conf/bitnami/bitnami-ssl.conf) extended with a ProxyPass /finance location and a targeted non-www-redirect exclusion, in place of the new subdomain vhost 01-09-PLAN.md originally specified"
  - "app/main.py PRODFIN_PUBLIC_PATH handling so the holding page's generated link resolves correctly under the /finance mount"
  - "deploy/prodfin-finance-location.conf — reviewable (not Apache-loaded) copy of the exact directives added to the live vhost"
affects: []

actuals:
  tokens: 9800
  tasks: 1
  commits: 2

tech-stack:
  added: []
  patterns: ["Apache path-mount ProxyPass with a non-trailing-slash target to avoid the doubled-slash bug on a non-trailing-slash Local pattern", "PRODFIN_PUBLIC_PATH env var read at app startup for path-prefix-aware link generation, in place of ASGI root_path/X-Forwarded-Prefix machinery"]

key-files:
  created: [deploy/prodfin-finance-location.conf]
  modified: [app/main.py, deploy/README.md]

key-decisions:
  - "Plan 01-09 as literally written (dedicated subdomain vhost, new bncert-tool certificate) was NOT executed. Per the executor's explicit scope override, this plan instead added a ProxyPass /finance location to the EXISTING vockell.com vhost, reusing the existing TLS certificate. 01-09-PLAN.md itself was left unedited; this divergence is recorded here per instruction."
  - "No AWS Lightsail snapshot was taken before editing the live vhost, contrary to both 01-09-PLAN.md's must_haves and deploy/README.md's own 'Downstream impact' note (both written for the certificate-issuance scenario). The executor's session instructions explicitly forbade any AWS provisioning/resize/snapshot for this step. Substituted: a file-level backup (two, timestamped) before every edit, mandatory apachectl configtest before every reload, graceful (not stop/start) reload, and immediate external re-verification after each change — appropriate because this step never touches TLS/certificate state, only routing directives inside an existing vhost."
  - "Two real bugs were found and fixed live during Task 1's own verification pass, before the task was called done: (1) the vhost's pre-existing 'non-www redirect' rule unconditionally 301'd every /finance request to www.vockell.com, which does not currently resolve — fixed with one added RewriteCond exclusion, same pattern already used for /.well-known; (2) the first ProxyPass used a trailing-slash target against a non-trailing-slash Local pattern, doubling the slash on every proxied request (/finance/health -> //health on the backend, a distinct 404'ing path) — fixed by removing the trailing slash from the target."
  - "app/main.py's holding-page link (<a href=\"/health\">) was an absolute server-root path that a browser resolves against the origin, not the current /finance/... location -- a dead link on the one page an anonymous visitor lands on first. Fixed via a PRODFIN_PUBLIC_PATH env var read at startup (empty for local/dev, /finance in production), rather than ASGI root_path/X-Forwarded-Prefix, since this skeleton has no router mounted under the prefix and generates no other absolute link."
  - "SHP-03's literal wording ('A subdomain DNS record exists and resolves') does not describe what actually happened -- there is no subdomain and no new DNS record, per the D-14 path-mount decision already recorded in 01-06-SUMMARY.md. Marked complete anyway because the underlying goal the requirement stands in for -- the app reachable at a public, valid-TLS URL without disturbing vockell.com -- is fully and verifiably met at https://vockell.com/finance. 01-06-SUMMARY.md explicitly deferred this exact call to whichever plan 'demonstrates the app actually reachable' -- this plan is that demonstration."

requirements-completed: [SHP-03, SHP-04]

coverage:
  - id: D1
    description: "An anonymous, off-box visitor reaches https://vockell.com/finance/health and https://vockell.com/finance/ over a valid TLS chain (no -k, no warning) and gets the application's real response"
    requirement: "SHP-04"
    verification:
      - kind: other
        ref: "curl -fsS https://vockell.com/finance/health (200, status/version/git_sha/boot_time, git_sha=3b7fb04, run from this developer machine, not the box)"
        status: pass
      - kind: other
        ref: "curl -fsS https://vockell.com/finance/ (200, holding page, href now /finance/health)"
        status: pass
      - kind: other
        ref: "curl -v https://vockell.com/finance/health 2>&1 | grep -i 'subject:\\|issuer:\\|verify ok' -> subject CN=vockell.com, issuer Let's Encrypt, 'SSL certificate verify ok' (no verification-skipping flag anywhere)"
        status: pass
      - kind: e2e
        ref: "SMOKE_BASE_URL=https://vockell.com/finance bash scripts/smoke.sh (exit 0, all 4 checks PASS)"
        status: pass
    human_judgment: true
    rationale: "The plan's own verification requires a real-browser check from outside the development machine's network per the prohibitions/success criteria; performed via gstack browse (real Chromium, real TLS validation) rather than a phone on mobile data, which a human should independently spot-check before this is treated as fully discharging the eventual Phase 8 cold-network requirement (noted explicitly as not discharged by this plan's check, same as the original plan's own verification note)."
  - id: D2
    description: "vockell.com continues serving normally with its own valid certificate and unchanged behaviour on every path other than /finance"
    requirement: "SHP-04"
    verification:
      - kind: other
        ref: "curl -sI https://vockell.com before and after every edit -> identical 301 Moved Permanently to https://www.vockell.com/, matching the pre-existing baseline documented in 01-08-SUMMARY.md"
        status: pass
      - kind: other
        ref: "sudo diff -u <original backup> <final bitnami-ssl.conf> -- only the two intended blocks differ (one RewriteCond line, one new Proxy block); every other line byte-identical"
        status: pass
      - kind: other
        ref: "echo | openssl s_client -servername vockell.com -connect vockell.com:443 | openssl x509 -noout -dates -ext subjectAltName -> DNS:vockell.com, DNS:www.vockell.com unchanged, notAfter=Oct 23 2026 (59 days out, >30-day floor)"
        status: pass
      - kind: other
        ref: "gstack browse: navigated to https://vockell.com/ -> net::ERR_NAME_NOT_RESOLVED resolving www.vockell.com, identical to the pre-existing documented behavior, not a regression"
        status: pass
    human_judgment: false
  - id: D3
    description: "The application process remains bound to 127.0.0.1 only; the reverse proxy did not expose it externally"
    requirement: "SHP-04"
    verification:
      - kind: other
        ref: "nc -z -w 5 35.165.60.123 8000 (exit 1, connection refused/timed out, from off the box)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Plain HTTP for the mounted path either redirects to HTTPS or is refused -- not served unencrypted"
    requirement: "SHP-04"
    verification:
      - kind: other
        ref: "curl -sI http://vockell.com/finance/health -> 302 Found, Location: https://vockell.com/finance/health"
        status: pass
    human_judgment: false
  - id: D5
    description: "Certificate renewal exists as a real, verified job on the host (not modified by this plan, since no new certificate was issued)"
    requirement: "SHP-04"
    verification:
      - kind: other
        ref: "crontab -l (as bitnami): pre-existing bncert-autorenew entry, daily 00:43 UTC, sudo /opt/bitnami/letsencrypt/lego ... --domains=vockell.com ... renew && apache graceful reload -- discovered, not created, by this plan"
        status: pass
    human_judgment: false
  - id: D6
    description: "The config change is committed and reviewable in the public repo, even though the actual edit lives on the host inside an existing vhost file rather than a new installed vhost"
    requirement: "SHP-03"
    verification:
      - kind: other
        ref: "deploy/prodfin-finance-location.conf committed (commit b347521), containing the exact directives added and the rationale for the non-trailing-slash target; deploy/README.md 'Apache path mount' section records both backup paths, configtest output, and every verification command run"
        status: pass
    human_judgment: false

duration: 16min
completed: 2026-08-25
status: complete
---

# Phase 1 Plan 9: Apache Path-Mount Reverse Proxy for /finance (D-14 Revision) Summary

**`https://vockell.com/finance` is now the live, anonymous-visitor-reachable hackathon submission URL — a `ProxyPass /finance` location added inline to the existing `vockell.com` Apache vhost (not a new subdomain vhost, not a new certificate), with two real bugs (a redirect-loop-to-unreachable-www and a doubled-slash proxy mapping) caught and fixed during the plan's own verification pass, before it was called done.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-25T07:10:00Z
- **Completed:** 2026-08-25T07:26:00Z
- **Tasks:** 1 (of the plan-as-written; Task 2's TLS-issuance checkpoint and Task 3's certificate work were both superseded — see Deviations)
- **Files modified:** 3 (`app/main.py`, `deploy/README.md` modified; `deploy/prodfin-finance-location.conf` created)

## Accomplishments

- **Executed a revised plan, not the plan as written.** `01-09-PLAN.md` was authored for a dedicated `prodfin.vockell.com` subdomain vhost with its own `bncert-tool`-issued certificate — an approach already superseded before this plan ran by the D-14 path-mount decision (`01-06-SUMMARY.md`: `https://vockell.com/finance`, no new subdomain). Per explicit scope-override instructions, this plan instead added a reverse-proxy location to the **existing** live `vockell.com` vhost, reusing its existing TLS certificate. `01-09-PLAN.md` itself was left unedited, per instruction; the divergence is recorded here and in `deploy/README.md`.
- **Located the live vhost** through direct SSH inspection rather than assumption: `/opt/bitnami/apache2` is a symlink to `/opt/bitnami/apache` (closing the "apache vs apache2" open item from `01-RESEARCH.md`), and the vhost that actually answers for `vockell.com` is `/opt/bitnami/apache/conf/bitnami/bitnami-ssl.conf` (`<VirtualHost _default_:443>`) — not the sample-only `conf/vhosts/` directory the research had expected. `mod_proxy`/`mod_proxy_http` were already loaded.
- **Backed up before every edit** (two timestamped copies, md5sum-verified against the live file at the moment of each backup), ran `apachectl -t` (`Syntax OK`) before every reload, and reloaded gracefully (`apachectl -k graceful`) rather than restarting — verifying `https://vockell.com`'s unchanged baseline behaviour immediately after each change, before checking `/finance`.
- **Found and fixed two real, live bugs during the plan's own verification pass** (not deferred, not silently worked around):
  1. The vhost's pre-existing "non-www redirect" rule unconditionally 301'd every request — including `/finance` — to `https://www.vockell.com/...`, which does not currently resolve. Fixed with one added `RewriteCond %{REQUEST_URI} !^/finance`, using the same exclusion pattern the rule already applied to `/.well-known`.
  2. The first `ProxyPass /finance http://127.0.0.1:8000/` (trailing slash on the target, matching the shape `01-RESEARCH.md`'s subdomain-oriented pattern used) produced a doubled slash on every proxied request — `GET /finance/health` reached uvicorn as `GET //health`, a distinct, 404'ing path. Caught via `curl` returning `404` with a `Server: uvicorn` header (proof the proxy was reaching the app with the wrong path), confirmed directly against the backend (`curl http://127.0.0.1:8000//health` → `404`), and fixed by removing the trailing slash from both `ProxyPass` and `ProxyPassReverse` targets.
- **Fixed a real bug in the application itself**: the holding page's `<a href="/health">` is an absolute server-root path, which a browser resolves against the domain root, not the current `/finance/...` page — a dead link on the first page an anonymous visitor sees. Fixed in `app/main.py` by reading `PRODFIN_PUBLIC_PATH` (set to `/finance` on the host, empty for local/dev) and prefixing the generated link with it; deployed via the existing `git pull`-based `deploy/deploy.sh` after pushing and confirming CI green.
- **No AWS resource touched.** No Lightsail snapshot, resize, or any write AWS call — an explicit session-level constraint that overrides both `01-09-PLAN.md`'s own `must_haves` and `deploy/README.md`'s prior "take a snapshot first" note (both written for the certificate-issuance scenario this plan did not execute). Substituted with file-level backups, mandatory configtest, and immediate external re-verification, appropriate because this step never touches TLS/certificate state.
- **Full anonymous, off-box, cert-validation-on verification**: `curl` (TLS chain valid, no `-k`, subject/issuer/expiry all confirmed), the repository's own `scripts/smoke.sh` run against the public URL (all 4 checks pass), and a real headless-browser pass (gstack `browse`: zero console errors, screenshot captured, clicked the health link and confirmed it lands on `https://vockell.com/finance/health` without leaving the domain, and separately confirmed `https://vockell.com/` still hits the identical pre-existing unresolvable-`www` behaviour — not a regression).
- **Discovered, did not create, the certificate renewal job**: a pre-existing `bncert-autorenew` cron entry (daily, 00:43 UTC) already renews the shared certificate via `lego renew` and gracefully reloads Apache — unaffected by, and unmodified by, this plan, since no new certificate was issued.

## Task Commits

Each committed atomically:

1. **[Deviation-driven fix, app-side] `PRODFIN_PUBLIC_PATH`-aware holding-page link** — `3b7fb04` (fix) — deployed to the host before the Apache change so both halves could be verified together
2. **Task 1 (revised): Apache path-mount + full documentation** — `b347521` (feat) — includes the vhost edit record, the reviewable config snippet, and the complete verification transcript in `deploy/README.md`

**Plan metadata:** committed alongside this SUMMARY (see below)

## Files Created/Modified

- `app/main.py` — reads `PRODFIN_PUBLIC_PATH` (env var) and prefixes the holding page's generated `/health` link with it, so the link resolves correctly whether the app is served at the root (local/dev) or under `/finance` (production)
- `deploy/prodfin-finance-location.conf` — **not read by Apache** (no `Include` references it); a reviewable copy of the exact directives added by hand to the live vhost, with the full rationale for the trailing-slash fix and the RewriteCond exclusion, so the host-side edit is inspectable in the public repo the way the original `deploy/prodfin-vhost.conf` artifact would have been
- `deploy/README.md` — new "Apache path mount (plan 01-09, D-14 revision) — executed 2026-08-25" section: vhost discovery, both backup paths, configtest/reload commands, both bugs found and fixed with verbatim repro, full external verification transcript, and the renewal-job discovery; existing forward-looking sections annotated `RESOLVED` with pointers rather than rewritten, preserving the historical record of what 01-06 originally flagged

## Decisions Made

See `key-decisions` in frontmatter above — summarized: (1) executed a revised plan (existing-vhost `ProxyPass`, no new subdomain/certificate), not `01-09-PLAN.md` as written, per explicit scope-override instructions; (2) no AWS snapshot was taken, per explicit session-level prohibition, substituted with file-level backup + configtest + graceful reload + immediate re-verification; (3) two live Apache bugs (www-redirect swallowing `/finance`, doubled-slash proxy target) found and fixed during the plan's own verification pass, not deferred; (4) one app-code bug (absolute-path link breaking under the mount) fixed via a `PRODFIN_PUBLIC_PATH` env var; (5) SHP-03 marked complete despite its literal "subdomain" wording no longer matching reality, because the underlying reachability goal is met and `01-06-SUMMARY.md` explicitly deferred that exact call to this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 → user-directed scope override, not this executor's own call] Entire plan approach revised: existing-vhost path mount instead of new subdomain vhost + new certificate**
- **Found during:** Plan start (already flagged by `01-06-SUMMARY.md` before this plan began)
- **Issue:** `01-09-PLAN.md`'s tasks, `must_haves`, and threat model all assume a dedicated `prodfin.vockell.com` subdomain vhost and a fresh `bncert-tool` certificate. That premise was superseded by the developer's own D-14 answer (path mount) before this plan ever ran.
- **Fix:** Executed the revised approach directed explicitly in this executor's scope-override instructions (not decided independently): `ProxyPass /finance` added to the existing `vockell.com` vhost, existing certificate reused, no new DNS/subdomain/certificate work.
- **Files modified:** `app/main.py`, `deploy/README.md`, `deploy/prodfin-finance-location.conf` (not `deploy/prodfin-vhost.conf` as the original plan's artifact list specified — no such file was ever going to exist under the revised approach; explained in the new file's own header comment)
- **Verification:** Full external verification transcript in `deploy/README.md`; see coverage block above.
- **Committed in:** `3b7fb04`, `b347521`

**2. [Rule 1 - Bug] Existing non-www redirect rule swallowed every `/finance` request**
- **Found during:** Task 1's own first-pass external verification, before the task was called done
- **Issue:** `curl -sI https://vockell.com/finance/health` returned `301` to `https://www.vockell.com/finance/health` — `www.vockell.com` does not currently resolve (pre-existing, documented in `01-08-SUMMARY.md`), so `/finance` would have been unreachable end-to-end for an anonymous visitor.
- **Fix:** Added `RewriteCond %{REQUEST_URI} !^/finance` to the vhost's existing redirect rule, mirroring the exclusion already used for `/.well-known`.
- **Files modified:** `/opt/bitnami/apache/conf/bitnami/bitnami-ssl.conf` (host only; documented, not committed — see `deploy/prodfin-finance-location.conf`)
- **Verification:** `curl -sI https://vockell.com/finance/health` after the fix returns `200` directly, no redirect; `curl -sI https://vockell.com` (bare apex) unchanged.
- **Committed in:** documented in `b347521` (the host edit itself is not a git-tracked file)

**3. [Rule 1 - Bug] Doubled slash in the `ProxyPass` target broke every proxied request**
- **Found during:** Same verification pass, immediately after fixing #2 above
- **Issue:** `ProxyPass /finance http://127.0.0.1:8000/` (trailing slash on target) mapped `/finance/health` to `http://127.0.0.1:8000//health` — a distinct path Starlette 404s on. `curl -sI https://vockell.com/finance/health` returned `404` with `Server: uvicorn`, proving the proxy reached the app but with the wrong path.
- **Fix:** Removed the trailing slash from both `ProxyPass` and `ProxyPassReverse` targets (`http://127.0.0.1:8000`, no trailing `/`).
- **Files modified:** same host file as #2, second backup taken first
- **Verification:** `curl -fsS https://vockell.com/finance/health` and `https://vockell.com/finance/` both return `200` with correct bodies after the fix.
- **Committed in:** documented in `b347521`

**4. [Rule 2 - Missing Critical] Generated link in the holding page broke under the path mount**
- **Found during:** Same verification pass, checking the plan's own "generated URLs must not break" success criterion
- **Issue:** `<a href="/health">` is an absolute server-root path; under `/finance` a browser resolves it to `https://vockell.com/health` (unproxied, dead), not `https://vockell.com/finance/health`.
- **Fix:** `app/main.py` now reads `PRODFIN_PUBLIC_PATH` (empty by default, `/finance` set on the host) and prefixes the link.
- **Files modified:** `app/main.py`
- **Verification:** `bash scripts/smoke.sh` (local, no env var) and `SMOKE_BASE_URL=https://vockell.com/finance bash scripts/smoke.sh` (production) both pass; `uv run pytest` 35/35 pass; live external `curl` and a headless-browser click-through both confirm the link resolves and stays on-domain.
- **Committed in:** `3b7fb04`

---

**Total deviations:** 1 scope-override (user-directed, not this executor's independent decision) + 3 auto-fixed bugs (2 in the live Apache config, 1 in the application). All four were necessary to make an anonymous visitor's actual experience of `https://vockell.com/finance` work at all — none were scope creep beyond what this plan's own (revised) success criteria required.
**Impact on plan:** None of the fixes touched anything outside `/finance`'s own reachability; `https://vockell.com`'s behaviour on every other path is confirmed byte-for-byte unchanged (diffed against the pre-edit backup).

## Issues Encountered

- **`.env.example` still does not exist in the repository** — carried forward from `01-01`/`01-08`, unrelated to and unaffected by this plan. `PRODFIN_PUBLIC_PATH` was added directly to `/opt/prodfin/.env` on the host (same workaround pattern `01-08` used for `PRODFIN_GIT_SHA` etc.), not to a repository template, because that template still cannot be created under the current permission policy. Logged previously in `.planning/WINDOWS.md`; not re-logged here as a new item.
- **Two pre-existing renewal-adjacent artifacts noted but not touched:** a `certbot.timer` systemd unit exists alongside the `bncert-autorenew` cron entry (`systemctl list-timers` showed both) — unclear if both are active renewal paths or one is vestigial; out of scope for this plan (no certificate work was performed), noted here only so a future certificate-related plan does not discover it cold. Also, the pre-existing `bncert-autorenew` cron job's `--domains=vockell.com` argument does not list `www.vockell.com` even though the certificate's SAN list covers both — pre-existing configuration, unrelated to and unaffected by this plan, not investigated further.

## User Setup Required

None — all steps executed directly (SSH, `git push`, `gh run watch`, direct `curl`/`openssl`/browser verification). No external service configuration is newly required.

## Next Phase Readiness

- `https://vockell.com/finance` is now the confirmed, live, anonymous-visitor-reachable hosted URL for the hackathon submission — ROADMAP Phase 1 success criterion 3 is met.
- Both `deploy/README.md` and `deploy/prodfin-finance-location.conf` carry enough detail (exact host path, both backup filenames, exact directives, exact bugs and fixes) that a future plan editing this vhost again (e.g. adding another path, or handling Phase 7's SSE streaming concern noted in `01-RESEARCH.md`) does not need to re-derive any of this from scratch.
- The Phase 8 pre-submission requirement (SHP-13: fully logged-out browser check on a foreign network) is NOT discharged by this plan's headless-browser check — noted explicitly, same caveat the original plan carried.
- Rollback, if ever needed: either timestamped `bitnami-ssl.conf.bak-*` backup on the host, restored per the one-line command recorded in `deploy/README.md`.

---
*Phase: 01-foundations-source-truth-deploy-path*
*Completed: 2026-08-25*

## Self-Check: PASSED

- FOUND: `app/main.py` contains `PRODFIN_PUBLIC_PATH`
- FOUND: `deploy/prodfin-finance-location.conf` exists on disk
- FOUND: `deploy/README.md` contains "Apache path mount (plan 01-09, D-14 revision)"
- FOUND commits in `git log --oneline --all`: `3b7fb04`, `b347521`
- Re-ran the plan's (revised) external verification live immediately before writing this SUMMARY: `/finance/health` 200 with correct body, `/finance/` 200 with corrected link, bare `vockell.com` unchanged 301, TLS chain valid with no `-k`, cert SANs/expiry unchanged, port 8000 unreachable off-box, plain-HTTP redirects to HTTPS, `scripts/smoke.sh` green against the public URL — all pass as documented above
