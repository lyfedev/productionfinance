# ProductionFinance — Track B deploy runbook

This is the deploy-path runbook for co-hosting ProductionFinance on the
existing `vockell.com` Lightsail instance. It records the topology, the
DNS/mount facts, the ordering decided in D-21, and the rollback position
at each step, so no later plan (01-07 through 01-09) has to re-derive any
of this.

Host facts referenced throughout this document live in
[`deploy/hosting.env`](./hosting.env) — source it with
`set -a && . ./deploy/hosting.env && set +a` before running any command
below that uses a `$PRODFIN_*` variable.

## D-14 resolution — path mount, not a subdomain (2026-08-24)

CONTEXT.md D-14 flagged the subdomain label `prodfin.vockell.com` as an
assumption requiring explicit developer confirmation before any DNS
record was created. At the 01-06 checkpoint the developer's answer was:

> "this is not critical path -- just put it at vockell.com/finance and
> not worry about devops."

This is a **path-based mount on the existing `vockell.com` site**, not a
new subdomain. The public URL for the hackathon submission is:

**`https://vockell.com/finance`**

Consequences that ripple through this runbook and the remaining Track B
plans:

- **No new DNS record.** `vockell.com` already resolves to the static IP
  (see below). There is nothing to create, and therefore no propagation
  clock in this phase. Task 3 of plan 01-06 ("Create the subdomain A
  record in the Register.com DNS panel") is **not applicable** and was
  not performed — see "Task 3 — not applicable" below.
- **No new subdomain vhost.** Plan 01-09 was written assuming a dedicated
  Apache vhost (`ServerName prodfin.vockell.com`) and its own Let's
  Encrypt certificate via `bncert-tool`. Under the path-mount decision,
  that plan's approach needs revision to instead add a reverse-proxy
  *location* rule (e.g. Apache `ProxyPass /finance` /
  `ProxyPassReverse /finance`) inside the **existing** `vockell.com`
  vhost, reusing the vhost's existing TLS certificate. See "Downstream
  impact on plan 01-09" below. This runbook does not edit 01-09 itself —
  that revision is left for whoever executes it, flagged here so it is
  not missed.
  **RESOLVED 2026-08-25 — see "Apache path mount (plan 01-09, D-14
  revision) — executed 2026-08-25" below for the actual host edit,
  verification, and result.**
- **No new certificate issuance.** The existing `vockell.com` certificate
  already covers the apex host; a path mount under that same host needs
  no new cert, no new `bncert-tool` run.

## Topology

Restated from `01-RESEARCH.md`'s Track B architecture:

- **Register.com DNS** resolves `vockell.com` to the Lightsail static IP.
  (Unchanged by this plan — no new record was added.)
- **Bitnami Apache** holds ports 80 and 443 on the box and reverse-proxies
  requests under `/finance` to a local uvicorn process
  (`http://127.0.0.1:$PRODFIN_APP_PORT`).
- **systemd** supervises the uvicorn process as `$PRODFIN_SERVICE`,
  running as the dedicated `$PRODFIN_SERVICE_USER` user, so it starts on
  boot and restarts on failure (D-23: this is tested, not assumed).
- **`uv`-managed Python 3.12**, isolated under `$PRODFIN_APP_ROOT/.venv`,
  never touches the system Python 3.9.2 that Bitnami and Apache depend
  on (D-18).

```
judge's browser
      |
      v
https://vockell.com/finance  ──(Register.com DNS, unchanged)──> 35.165.60.123
      |
      v
Bitnami Apache :443  (existing vhost, existing cert)
      |  ProxyPass /finance -> http://127.0.0.1:8000
      v
uvicorn (systemd: prodfin.service, user: prodfin)
      |
      v
uv-managed Python 3.12 venv at /opt/prodfin/.venv
(system Python 3.9.2 untouched)
```

## DNS facts (from live lookup, 01-RESEARCH.md § SHP-03)

- The `vockell.com` zone is hosted at **Register.com** (Network
  Solutions), nameservers `dns105.register.com` and
  `dns106.register.com`, registrar "Register.com - Network Solutions,
  LLC".
- It is **not** in Route 53 and is **not** managed through the AWS
  account at all — no `aws route53` command applies to this domain.
- The apex `vockell.com` A record already resolves to `35.165.60.123`,
  matching the Lightsail static IP recorded in `.claude/CLAUDE.md` and in
  `deploy/hosting.env` as `PRODFIN_STATIC_IP`.
- Because the D-14 resolution is a path mount on this existing apex host,
  **no new A record was needed and none was created.** The DNS facts
  above are recorded for completeness and because they still govern the
  one DNS record ProductionFinance depends on (the apex itself, which
  must keep resolving to the box).

## Task 3 — not applicable

Plan `01-06-PLAN.md` Task 3 ("Create the subdomain A record in the
Register.com DNS panel") is recorded here as **NOT APPLICABLE**, not
silently skipped and not marked complete:

- **Reason:** the developer's D-14 answer resolved to a path-based mount
  (`vockell.com/finance`) on the existing apex host, not a new subdomain.
  A path mount requires no new DNS record — `vockell.com` already
  resolves to the target IP.
- **What was NOT done, deliberately:** no record was created, modified,
  or deleted in the Register.com panel. The apex record and the zone's
  nameservers are exactly as `01-RESEARCH.md` § SHP-03 found them.
- **What replaces it:** nothing — there is no equivalent action required.
  The reverse-proxy path rule in plan 01-09 is the only remaining step
  that makes `/finance` reachable, and it needs no DNS action of its own.

## D-21 ordering and rollback position

D-21 originally set the Track B order as: DNS record → resize → Python →
systemd → Apache proxy + TLS, reasoning that DNS propagation is the one
clock outside operator control and should start first. With the path-
mount decision, the DNS step drops out entirely (see above), so the
ordering collapses to:

| Step | Plan | What it does | Rollback position |
|------|------|---------------|--------------------|
| 1. ~~DNS record~~ | ~~01-06~~ | **Not applicable** — path mount needs no new record | N/A — nothing was changed |
| 2. Instance resize | 01-07 | Snapshot-and-restore to `small_3_0` (2 GB / 2 vCPU), preserving the static IP | The pre-resize snapshot is the rollback: restore from it to return to the original 472 MB instance. Snapshot taken before any change. |
| 3. Python install | 01-07/01-08 | `uv python install 3.12`, isolated venv under `$PRODFIN_APP_ROOT/.venv` | Fully additive — deleting `$PRODFIN_APP_ROOT` and the `uv`-installed Python removes it cleanly; system Python 3.9.2 is never touched (D-18). |
| 4. systemd unit | 01-08 | Install and enable `$PRODFIN_SERVICE`, running as `$PRODFIN_SERVICE_USER` | `systemctl disable --now $PRODFIN_SERVICE` and remove the unit file; no effect on Apache or the existing site. |
| 5. Apache proxy + TLS | 01-09 (**done 2026-08-25** — see "Apache path mount" below) | Added `ProxyPass /finance` + a targeted `RewriteCond` exclusion to the **existing** vockell.com vhost; no new certificate | Rollback is either of the two timestamped file backups taken before editing, restored per the command in that section. No Lightsail snapshot was taken for this step — see note below the table. |

**Note on the Lightsail-snapshot recommendation above:** the row and
section below recommended a fresh Lightsail snapshot before editing the
live vhost. The 01-09 executor's actual instructions explicitly forbade
provisioning, resizing, or snapshotting any AWS resource for this step —
read-only AWS/DNS queries only. This is a deliberate, session-level
override, justified because this step (unlike the certificate issuance
`01-09-PLAN.md` originally called for) never touches TLS state: it is a
config-only edit to routing directives inside an existing vhost, covered
instead by a file-level backup, a mandatory `configtest` before every
reload, and immediate external re-verification of the live site after
each change — see "Apache path mount" below for exactly what that looked
like in practice.

## Downstream impact on plan 01-09 (flag for the orchestrator) — RESOLVED

**Resolved 2026-08-25 — see "Apache path mount (plan 01-09, D-14
revision) — executed 2026-08-25" below for what actually ran.** The
recommendation text below is preserved as the historical record of what
01-06 flagged; the executed approach differs in the two respects noted
inline (no Lightsail snapshot, and the app-side `root_path` question was
resolved with a simpler `PRODFIN_PUBLIC_PATH`-prefixed link rather than
ASGI `root_path`/`X-Forwarded-Prefix` machinery, since this skeleton has
no router mounted under the prefix).

`01-09-PLAN.md` was written under the original subdomain assumption: a
dedicated Apache vhost with `ServerName prodfin.vockell.com` and its own
Let's Encrypt certificate obtained via `sudo /opt/bitnami/bncert-tool`.
That approach **does not apply** under the path-mount decision recorded
here. The corrected approach for whoever executes 01-09:

- Do **not** create a new vhost or run `bncert-tool` for a new domain.
- Add a `ProxyPass /finance http://127.0.0.1:$PRODFIN_APP_PORT/` and
  `ProxyPassReverse /finance http://127.0.0.1:$PRODFIN_APP_PORT/` pair
  (plus whatever header-forwarding directives FastAPI needs for correct
  URL generation under a path prefix, e.g. `X-Forwarded-Prefix`) inside
  the vhost that already serves `vockell.com` on port 443.
- Reuse the existing certificate — no new TLS issuance is needed for a
  path added to an already-covered host.
- Take a fresh Lightsail snapshot immediately before editing the live
  vhost config, per the standing rule below — this touches a config file
  that also serves the live personal site on the same box.
- FastAPI itself may need `root_path="/finance"` (or equivalent ASGI
  `SCRIPT_NAME`/`X-Forwarded-Prefix` handling) so that OpenAPI docs and
  any generated links resolve correctly under the path prefix rather than
  assuming the app is mounted at `/`.

This runbook does not edit `01-09-PLAN.md` — that revision is explicitly
left to whoever plans/executes it next, per the 01-06 resume
instructions. This section exists so the impact is visible in this
plan's own history rather than discovered mid-execution of 01-09.

## Standing rule — vockell.com is a live personal site sharing this box

`vockell.com` serves someone's live personal site on this same instance.
No step in Track B may modify an existing DNS record, an existing vhost,
or an existing certificate binding **except where a task says so
explicitly and takes a snapshot first.** The path-mount decision makes
this rule *more* load-bearing than the original subdomain plan, not
less: 01-09 now edits the vhost that serves the live site directly
(adding a location block) rather than creating an isolated new one.

## Host bootstrap (executed 2026-08-25, plan 01-08 Task 1)

Run as `bitnami` over SSH, `PRODFIN_STATIC_IP` from `deploy/hosting.env`. This is
the un-resized `nano_2_0` box — 01-07 (snapshot-and-restore to `small_3_0`) was
**deferred, not completed**, per `.planning/phases/01-foundations-source-truth-deploy-path/01-07-DEFERRED.md`.
The developer chose to attempt deployment on the existing 472 MB instance first
and resize only if it actually runs out of memory. Everything below happened on
that box, not a resized one.

1. **Service account.** `sudo useradd --system --no-create-home --shell /usr/sbin/nologin prodfin`
   — a dedicated non-login system user, uid/gid 997, no home directory. The
   service runs as this user, never as `bitnami` and never as `root`.
2. **App root.** `sudo mkdir -p /opt/prodfin`, temporarily owned by `bitnami`
   while `uv` writes the venv into it, then `chown -R prodfin:prodfin` once the
   venv exists (see step 4).
3. **`uv` install**, as the `bitnami` user (not root, not system-wide):
   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Installed **uv 0.12.5** to `/home/bitnami/.local/bin`, modifying only
   `bitnami`'s own shell profile (adds `~/.local/bin` to `PATH`). No system-wide
   profile was touched.
4. **Isolated Python 3.12 + venv:**
   ```
   uv python install 3.12
   uv venv --python 3.12 /opt/prodfin/.venv
   ```
   Resolved and downloaded **CPython 3.12.14** (32.6 MiB), installed under uv's
   own managed directory `/home/bitnami/.local/share/uv/python/cpython-3.12.14-linux-x86_64-gnu/`
   — never under `/usr/bin` or `/opt/bitnami`. The venv was created at
   `/opt/prodfin/.venv`, then `chown -R prodfin:prodfin /opt/prodfin` handed the
   whole tree to the service account.
5. **Isolation verified immediately**, per D-18/SHP-02, before anything else was
   installed:
   - `/opt/prodfin/.venv/bin/python --version` → `Python 3.12.14`
   - `python3 --version` (system) → `Python 3.9.2`, unchanged from the preflight
     inventory recorded earlier in this document
   - `which python3` → `/usr/bin/python3` (unchanged symlink to `python3.9`)
   - `ls -la /usr/bin/python*` → only the pre-existing `python3 -> python3.9`
     symlink and `python3.9` binary; nothing added or modified
   - `find /opt/bitnami -maxdepth 1 -newer /opt/prodfin` → empty (no top-level
     entry under `/opt/bitnami` newer than the moment `/opt/prodfin` was created)
   - `tail -5 /var/log/apt/history.log` → last entry dated 2026-08-21
     (`unattended-upgrade`, pre-existing, before this session) — no apt
     operation ran as part of this bootstrap
   - `sudo /opt/bitnami/ctlscript.sh status` → `apache already running`,
     `mariadb already running`, `php-fpm already running`, both before and after
     every step above
   - `curl -sSI https://vockell.com` → `301 Moved Permanently` to
     `https://www.vockell.com/`, identical before and after this bootstrap (see
     "Known pre-existing redirect" note below)

### Known pre-existing redirect (not caused by this plan)

`curl -I https://vockell.com` returns **301 → `https://www.vockell.com/`**, not
200 — the vhost redirects the apex to a `www` host that does not currently
resolve (`curl: (6) Could not resolve host: www.vockell.com`). This is
pre-existing site configuration, unrelated to ProductionFinance, and unaffected
by this plan: the 301 was observed identically before and after every step in
this bootstrap and in Task 2/3. Treat "Apache still answers with its normal
response for this vhost" (a `Server: Apache` header present) as the live-site
health signal for this box, not a literal 200 — a strict `curl ... | grep -q
200` check against the bare apex will not pass on this host as currently
configured, and that is a pre-existing condition out of this plan's scope, not
a regression it introduced.

### Post-install memory measurement (D-22)

Taken immediately after `uv python install 3.12` + `uv venv` completed, before
anything else was installed into the venv — see `.planning/STATE.md` Blockers/Concerns
for the number and its read on the Milestone 2 data-layer decision. Verbatim:

```
$ free -h
               total        used        free      shared  buff/cache   available
Mem:           472Mi       106Mi        18Mi       0.0Ki       347Mi       353Mi
Swap:          634Mi        96Mi       538Mi

$ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/xvda1       20G  5.5G   14G  30% /
```

## Deploying (plan 01-08 Task 2)

The whole deploy path is one command, run on the host as `bitnami` (needs
passwordless sudo to restart the systemd unit; git and `uv` operations run as
`prodfin` internally via `sudo -u prodfin`):

```bash
cd /opt/prodfin
bash deploy/deploy.sh
```

What it does, in order: `git pull --ff-only origin main` as `prodfin` (fails
loudly rather than silently merging if `main` was ever rewritten) → `uv sync
--frozen` against the committed `uv.lock`, so the host resolves exactly what
CI's `lockfile-scan` already scanned, never a fresh resolution → records the
newly-checked-out short SHA into `/opt/prodfin/.env` as `PRODFIN_GIT_SHA` →
`systemctl restart prodfin` → polls `systemctl is-active` until the unit
reports active (or fails after 10s) → health-checks
`http://127.0.0.1:8000/health` and exits non-zero if it does not return 200.
A restart that does not come back is a failed deploy, not a silent one.

Idempotent: re-running it with no new commits and an already-active service
is a no-op that still re-verifies health — safe to run twice.

**How to read a failure:** the script's own `==>` lines show which stage it
was in; if it fails at the health check, `sudo systemctl status prodfin
--no-pager` and `sudo journalctl -u prodfin -n 50 --no-pager` on the host are
the next two commands to run (see "Reboot test" below for the same diagnostic
pattern applied to a boot-time failure).

One-time host setup, not part of `deploy.sh` itself: `uv` is installed to
`/home/bitnami/.local/bin/{uv,uvx}` (per "Host bootstrap" above) and exposed
on the system `PATH` via `/usr/local/bin/uv` → `/usr/local/bin/uvx` symlinks,
so `sudo -u prodfin uv ...` resolves regardless of which user's shell
invokes it — `/usr/local/bin` is the standard place for locally-installed
tools on Debian and is never touched by `apt`, unlike `/usr/bin`.

## Reboot test (executed 2026-08-25, plan 01-08 Task 3, D-23)

Executed, not assumed: `systemctl enable` alone proves nothing about boot
behaviour until the box is actually rebooted and observed coming back
unaided (SHP-04). This was a real `sudo reboot` over SSH on the live
`vockell.com` host — the site was offline for the duration, deliberately.

**Pre-reboot state recorded:** `prodfin.service` active, Apache/MariaDB/
php-fpm all running via `sudo /opt/bitnami/ctlscript.sh status`, `curl -I
https://vockell.com` returning the same baseline `301` documented above.
No pre-resize snapshot exists to check as a rollback position — 01-07's
resize was deferred (see `01-07-DEFERRED.md`); this is still the single,
original `vockell_dot_com_LAMP` instance (`nano_2_0`), confirmed via `aws
lightsail get-instance` immediately before the reboot.

**Reboot issued:** `2026-08-25T06:59:25Z`. The SSH connection returned
normally (the `sudo reboot` command itself exits before the box actually
goes down) and polling began immediately, without touching the box —
specifically, without starting `prodfin` by hand.

**Recovery, in order, no manual intervention:**
- SSH answered again within one 5-second poll interval (roughly 5-10s after
  the reboot command).
- `uptime -s` on the host reported a new boot timestamp: `2026-08-25
  06:59:38`, confirming a genuine reboot occurred (not a stale SSH session)
  — `06:59:38 > 06:59:25`, after the reboot command.
- `systemctl is-active prodfin` → `active`, with no manual start. `systemctl
  status` showed the unit started by `systemd[1]` itself at `06:59:42`
  (`WantedBy=multi-user.target` working as intended).
- `curl -fsS http://127.0.0.1:8000/health` → 200, body: `{"status":"ok",
  "version":"0.1.0","git_sha":"a99e4f6","boot_time":
  "2026-08-25T06:59:44.869996+00:00"}`. The app's own `boot_time`
  (`06:59:44`) is later than the host's `uptime -s` boot timestamp
  (`06:59:38`) — this is the evidence distinguishing "survived a reboot"
  from "was started again after a reboot": a process that predated the
  reboot cannot report a `boot_time` after it.
- Apache and MariaDB confirmed running as processes (`ps aux`: `httpd`
  workers and `mysqld`, both with post-reboot start timestamps `06:59`/
  `07:00`) and via `systemctl list-units` (`bitnami.service` active). One
  transient false negative during this check: `ctlscript.sh status` briefly
  reported "Cannot find any running daemon to contact" because Bitnami's
  `gonit` supervisor (pid confirmed started at `07:00`) had not finished its
  own startup yet, a few seconds behind Apache/MariaDB themselves; a 5-second
  wait and re-run of `ctlscript.sh status` then correctly reported all three
  services running. This is a gonit-startup-ordering artifact, not evidence
  of any actual outage — `httpd`/`mysqld` process timestamps and the
  externally-observed `vockell.com` response prove otherwise.
- `curl -I https://vockell.com` from off the box → `301 Moved Permanently`
  to `https://www.vockell.com/` (identical to the pre-reboot and
  pre-existing baseline, see "Known pre-existing redirect" above),
  `Server: Apache` header present, confirmed at `2026-08-25T07:00:04Z`.

**Elapsed recovery time:** approximately 19 seconds from the reboot command
to the application's own recorded `boot_time` (`06:59:25` → `06:59:44`);
full external confirmation (vockell.com + health both independently
verified) completed by `07:00:04Z`, about 39 seconds after the reboot
command. No fix to `deploy/prodfin.service` was required — the unit worked
on the first reboot.

## Apache path mount (plan 01-09, D-14 revision) — executed 2026-08-25

**This is a revision of plan `01-09-PLAN.md` as literally written, not the
plan as written.** `01-09-PLAN.md` was authored for a dedicated subdomain
(`prodfin.vockell.com`) with its own new Apache vhost and its own freshly
issued Let's Encrypt certificate via `bncert-tool`. That approach was
superseded by the D-14 path-mount decision recorded above and in
`01-06-SUMMARY.md`, before 01-09 ever executed. This section is the actual
record of what ran instead. `01-09-PLAN.md` was not edited — this
divergence is recorded here and in `01-09-SUMMARY.md` per the executor's
explicit instructions, so the gap between plan-as-written and
plan-as-built is visible rather than silently absorbed.

**What was NOT done, deliberately, per those instructions:**
- No new vhost file. No `bncert-tool` run. No new certificate issued,
  renewed, or replaced. No AWS resource created, resized, or snapshotted
  (read-only `aws`/`dig` queries only).
- The existing `vockell.com` / `www.vockell.com` certificate (Let's
  Encrypt, expires 2026-10-23, i.e. well over 30 days out at the time of
  this plan) was reused as-is.

### What was done

**1. Discovered the live vhost.** The Bitnami Apache directory on this
box is `/opt/bitnami/apache` (`/opt/bitnami/apache2` is a symlink to it —
both names resolve to the same tree, so the "apache vs apache2" open item
from `01-RESEARCH.md` is now closed: they're the same directory). The
vhosts-directory convention `01-RESEARCH.md` expected
(`/opt/bitnami/apache/conf/vhosts/`) turned out to contain only Bitnami's
own samples — the vhost that actually answers for `vockell.com` lives at
`/opt/bitnami/apache/conf/bitnami/bitnami-ssl.conf`
(`<VirtualHost _default_:443>`, the box's one and only HTTPS vhost,
matching any Host header) and its HTTP counterpart in
`/opt/bitnami/apache/conf/bitnami/bitnami.conf`
(`<VirtualHost _default_:80>`). `mod_proxy` and `mod_proxy_http` were
already loaded (`httpd -M`) — no module-enable step was needed.

**2. Backed up before any edit**, per the mandatory sequence:
```
sudo cp -p /opt/bitnami/apache/conf/bitnami/bitnami-ssl.conf \
  /opt/bitnami/apache/conf/bitnami/bitnami-ssl.conf.bak-20260825T071452Z
```
(md5sum-verified identical to the live file immediately after.) A second
backup was taken before the follow-up fix in step 4 below
(`bitnami-ssl.conf.bak-20260825T071628Z`) — both remain on the host as the
rollback position; restoring either is `sudo cp -p <backup> bitnami-ssl.conf
&& sudo /opt/bitnami/apache/bin/apachectl -t && sudo /opt/bitnami/apache/bin/apachectl -k graceful`.

**3. Edited the existing vhost** (not a new file — see
`deploy/prodfin-finance-location.conf` for the reviewable copy of exactly
what was added and why). Inside `<VirtualHost _default_:443>`:
- Added `RewriteCond %{REQUEST_URI} !^/finance` to the vhost's pre-existing
  "Enable non-www to www redirection" rule, using the same exclusion
  pattern the rule already used for `/.well-known`.
- Added `ProxyPreserveHost On`, `ProxyPass /finance http://127.0.0.1:8000`,
  `ProxyPassReverse /finance http://127.0.0.1:8000` (see exact rationale
  for the target having no trailing slash in
  `deploy/prodfin-finance-location.conf`).

Ran `sudo /opt/bitnami/apache/bin/apachectl -t` → `Syntax OK` before any
reload, both times this file was edited.

**4. Reloaded gracefully** — `sudo /opt/bitnami/apache/bin/apachectl -k
graceful` (not `ctlscript.sh restart`, which stops-then-starts) — then
verified from OFF the box, before anything else:
```
$ curl -sI https://vockell.com
HTTP/1.1 301 Moved Permanently
Location: https://www.vockell.com/
```
Identical to the pre-existing baseline recorded in `01-08-SUMMARY.md`.

**Bug found and fixed during this same verification pass, before Task 1
was called done:** the first version of the `ProxyPass` (target with a
trailing slash, matching the shape `01-RESEARCH.md`'s subdomain-oriented
pattern used) produced a doubled slash on every proxied request —
`GET /finance/health` reached uvicorn as `GET //health`, which
Starlette 404s on as a distinct path from `/health`:
```
$ curl -sI https://vockell.com/finance/health
HTTP/1.1 404 Not Found
Server: uvicorn
```
The `Server: uvicorn` header on a 404 was the tell: the proxy was
reaching the app, the path mapping was wrong. Confirmed directly on the
host (`curl 'http://127.0.0.1:8000//health'` → `404`, same problem, one
hop earlier). Fixed by removing the trailing slash from the `ProxyPass`/
`ProxyPassReverse` targets (backup taken first, configtest passed,
gracefully reloaded again) — full mechanism explained in
`deploy/prodfin-finance-location.conf`.

**5. A second bug, in the application, found by the same pass:** the
holding page's `<a href="/health">` is an absolute server-root path. Under
a path mount, a browser resolves that against the origin
(`https://vockell.com/health`), not the current `/finance/...` location —
a dead link on the one page an anonymous visitor lands on first
(`generated URLs must not break` per this plan's own scope). Fixed in
`app/main.py` (commit `3b7fb04`): the app now reads `PRODFIN_PUBLIC_PATH`
(set to `/finance` in `/opt/prodfin/.env` on the host, empty for
local/dev) and prefixes the generated link with it. No ASGI
`root_path`/`X-Forwarded-Prefix` machinery was needed — this skeleton has
no router mounted under the prefix and generates no other absolute link.
Deployed via the existing `deploy/deploy.sh` (`git pull` + `uv sync` +
restart) after pushing the commit and confirming CI green
(run `32820627620`, all 4 gates passed).

**6. Full external verification, from this developer machine (outside
the box), anonymous, certificate validation fully on:**
```
$ curl -fsS https://vockell.com/finance/health
{"status":"ok","version":"0.1.0","git_sha":"3b7fb04","boot_time":"2026-08-25T07:18:01.171623+00:00"}

$ curl -fsS https://vockell.com/finance/
<!doctype html> ... <a href="/finance/health">/finance/health</a> ...

$ curl -v https://vockell.com/finance/health 2>&1 | grep -i 'subject:\|issuer:\|verify ok'
*  subject: CN=vockell.com
*  issuer: C=US; O=Let's Encrypt; CN=YE1
* SSL certificate verify ok.

$ echo | openssl s_client -servername vockell.com -connect vockell.com:443 2>/dev/null \
  | openssl x509 -noout -dates -ext subjectAltName
notBefore=Jul 25 23:48:15 2026 GMT
notAfter=Oct 23 23:48:14 2026 GMT
X509v3 Subject Alternative Name:
    DNS:vockell.com, DNS:www.vockell.com

$ curl -sI http://vockell.com/finance/health
HTTP/1.1 302 Found
Location: https://vockell.com/finance/health

$ nc -z -w 5 35.165.60.123 8000; echo $?
1   # connection refused/timed out — port 8000 not reachable off the box

$ SMOKE_BASE_URL=https://vockell.com/finance bash scripts/smoke.sh
PASS: GET /health returned 200
PASS: /health body carries git_sha
PASS: /health body carries boot_time
PASS: GET / returned 200
Smoke test passed.
```
Headless-browser check (gstack `browse`, real Chromium, real TLS
validation — not curl): navigated to `https://vockell.com/finance/`, 200,
zero console errors; clicked the `/finance/health` link and confirmed
navigation landed on `https://vockell.com/finance/health` (same domain,
correct path) rendering the health JSON; separately navigated to
`https://vockell.com/` and got `net::ERR_NAME_NOT_RESOLVED` resolving
`www.vockell.com` — the identical pre-existing behaviour documented in
`01-08-SUMMARY.md`, not a regression from this change.

**7. Certificate renewal — pre-existing, unaffected, verified as a real
job on the host** (not modified, not newly added by this plan, since no
new certificate was issued):
```
$ crontab -l   # as bitnami
43 0 * * * sudo /opt/bitnami/letsencrypt/lego --path /opt/bitnami/letsencrypt \
  --email="dave@vockell.com" --http --http-timeout 30 \
  --http.webroot /opt/bitnami/apps/letsencrypt --domains=vockell.com \
  --user-agent bitnami-bncert/1.1.0 renew \
  && sudo /opt/bitnami/apache/bin/httpd -f /opt/bitnami/apache/conf/httpd.conf -k graceful
  # bncert-autorenew
```
Runs daily at 00:43 UTC, and itself uses a graceful reload — consistent
with the reload discipline used throughout this section.

### Result

- `https://vockell.com/finance` is the hosted URL for the hackathon
  submission — reachable by an anonymous visitor, valid TLS chain (the
  site's existing certificate), no certificate warning.
- `https://vockell.com` (every path other than `/finance`) is byte-for-byte
  unaffected: confirmed via diff of the vhost file against the very first
  backup (the only changed lines are the ones listed in step 3), and via
  live external `curl`/browser checks matching the documented pre-existing
  301-to-www baseline exactly.
- Rollback position: either backup listed in step 2, restored per the
  command shown there.

## How to verify

Commands each later plan uses, collected in one place:

```bash
# Source host facts
set -a && . ./deploy/hosting.env && set +a

# Apex still resolves correctly (unchanged by this plan)
dig +short A vockell.com

# Zone nameservers still Register.com (unchanged by this plan)
dig +short NS vockell.com

# Live site still serves (before and after any 01-09 vhost edit)
curl -I https://vockell.com

# The app itself, through the path mount (live since 01-09):
curl -fsS "$PRODFIN_PUBLIC_URL/health"

# SSH to the box
ssh -i "$PRODFIN_SSH_KEY" "$PRODFIN_SSH_USER@$PRODFIN_STATIC_IP"

# Process supervision status (run on the box, after 01-08)
systemctl is-active "$PRODFIN_SERVICE"
```
