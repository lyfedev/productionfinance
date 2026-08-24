# Phase 1: Foundations — Source Truth & Deploy Path - Research

**Researched:** 2026-08-24
**Domain:** Primary-source fact verification (film incentive figures) + AWS Lightsail/Bitnami deploy path + GitHub compliance CI
**Confidence:** HIGH for everything directly tool-verified this session (curl, `dig`, `pdftotext`, `pip index`, `Read` on fetched PDFs); MEDIUM for WebFetch/WebSearch-sourced claims from official docs; explicitly flagged where a genuine gap or conflict remains open

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

The user delegated all four gray areas ("you make your best guess") to Claude's discretion. All of D-01 through D-30 below are Claude's own working decisions, made against PROJECT.md/ROADMAP.md/REQUIREMENTS.md, and stated with rationale so they can be overturned on sight. This research treats them as binding inputs to plan against, **except where this session's direct verification work surfaces a correction** (flagged inline, most notably D-16's tool choice).

- **D-01:** One YAML file per validation pair at `tests/fixtures/validation_pairs/{jurisdiction}_{slug}.yaml`. Reversibility: costly.
- **D-02:** A validation pair proves the incentive interpreter only, never cost localization — qualified spend is fed IN as a given; only net-cash-out is asserted. Reversibility: one-way (the product's honesty claim).
- **D-03:** Each fixture records at minimum: `production_title`, `jurisdiction_id`, `program_id`, `production_type`, `season`, `qualified_spend`, `credit_amount`, `disclosure_stage`, `source_url`, `source_document_sha256`, `report_period`, `date_checked`. Money as strings parsed to `Decimal`, never float.
- **D-04:** Each fixture carries `assertion.mode: exact | bounded`. `bounded` requires `tolerance_bps` + mandatory `variance_reason`. `exact` is the default; `bounded` must be argued for in writing.
- **D-05:** At least three pairs must be `mode: exact`, small productions, no uplift claims. Anora is the anchor.
- **D-06:** A pair whose fields cannot be confirmed is still committed with `status: blocked` and an explicit `blocker` string — counts toward the 11, excluded from the accuracy denominator, exclusion always visible.
- **D-07:** Disclosure stages (`issued` / `allocated` / `estimated`) are never averaged together — separate cohorts, separate accuracy figures.
- **D-08:** Raw source documents archived byte-for-byte in-repo at `sources/{jurisdiction}/{yyyy-mm-dd}-{slug}.{pdf,csv,html}` — not S3 (new cloud resource requires per-resource approval).
- **D-09:** Escape hatch: documents >~25MB store SHA-256 + URL + text/markdown extraction instead of the binary, omission recorded explicitly.
- **D-10:** `sources/MANIFEST.yaml` records per document: `url`, `retrieved_at`, `sha256`, `jurisdiction`, and which figures it's cited for.
- **D-11:** SRC-01/02/05 answers land in `.planning/SOURCE-TRUTH.md`, one entry per question, with question/answer/URL/date_checked/confidence/what-was-refuted.
- **D-12:** A refuted hypothesis is recorded, not deleted.
- **D-13:** Genuinely conflicting authoritative sources → explicit unresolved-conflict entry, never silently picked.
- **D-14 (NOT discretion — needs user confirmation):** `prodfin.vockell.com` is an assumption. Confirm the subdomain name before the DNS record is created.
- **D-15 (NOT discretion — was unresolved, now resolved by this research):** The DNS zone host for vockell.com. **This research directly answers it — see SHP-03 below.**
- **D-16:** TLS via certbot with the Apache plugin, not Caddy. **This research finds the concrete tool should be `bncert-tool`, not a bare `certbot` invocation — see SHP-03 correction below. The "not Caddy" decision itself stands.**
- **D-17:** No Docker. `uv`-managed virtualenv under `/opt/prodfin`, systemd unit checked into `deploy/`.
- **D-18:** Python 3.12 via `uv`, never touching system Python 3.9.2.
- **D-19:** Code reaches the box by `git pull` + `deploy/deploy.sh` — no CI push, no rsync.
- **D-20:** Day-2 payload is a real FastAPI skeleton (`GET /health` returns version/git SHA/boot time; `GET /` returns a minimal holding page) — no engine, no rule schema, no UI treatment.
- **D-21:** Track B internal ordering: DNS record → resize → Python → systemd → Apache proxy + TLS.
- **D-22:** Measure free memory immediately after the Python install; write the number into STATE.md.
- **D-23:** The reboot test is executed, not assumed.
- **D-24:** MIT licence.
- **D-25:** Repository goes public at the start of Phase 1, not at submission.
- **D-26:** GitHub Actions, blocking on red — required status checks, not report-only.
- **D-27:** Three CI jobs: `lockfile-scan` (forbidden packages + google-adk bare-only), `secret-scan` (gitleaks + push protection), `commit-window` (author date ≥ 2026-07-27).
- **D-28:** Also grep the source tree for `textract|bedrock|comprehend|rekognition|transcribe|polly|kendra|sagemaker`; match `boto3`-qualified call sites for `translate` (too common a word to grep bare).
- **D-29:** Commit the four strategy briefs (currently untracked).
- **D-30:** Move `LightsailDefaultKey-us-west-2 (2).pem` out of the repo root.

### Claude's Discretion

All of D-01–D-13 (source archival/fixture contract) and D-16–D-30 (deploy path/CI) are explicitly delegated discretion — overturn any of them on the user's word without re-arguing the case. D-14 (subdomain name) and D-15 (DNS zone host) were explicitly flagged as **not** discretion; D-15 is now answered by direct lookup in this research, D-14 still needs one word of user confirmation before the DNS task runs.

### Deferred Ideas (OUT OF SCOPE)

- S3 mirroring of source documents/index snapshots — deferred to avoid a new cloud resource; revisit at Phase 9 if IDX-08 needs it.
- Step-level job resumption — post-Milestone-1.
- EventBridge Scheduler — rejected for Milestone 1; a systemd timer is Phase 9's mechanism.
- Postgres as the data layer — Phase 9 decision, gated on the free-memory measurement this phase takes (D-22).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRC-01 | NY annual cap reconciled against primary source | $700M base program VERIFIED via two ESD PDFs (2025-04-18 Guidelines + current esd.ny.gov page); $100M independent-film pool VERIFIED via esd.ny.gov ($20M/$80M split); $800M press figure explained as combined total — **but a third official ESD document (May 2026 AUP) states $800M for what reads as the base program alone, a genuine unresolved inconsistency flagged for Track A to run down against the enacted budget bill text.** See "SRC-01" section. |
| SRC-02 | CT CSV column headers confirmed by opening the endpoint | VERIFIED via direct `curl` of the live CSV export. Exact 7-column header + data-quality gotchas documented. See "SRC-02" section. |
| SRC-03 | 11 validation pairs locked into fixtures with source URL + disclosure stage | 3 NY pairs VERIFIED byte-for-byte against the actual ESD Q3 2025 PDF via `pdftotext`. **Critical scope finding: 4 of the 11 named pairs (MA×2, PA×2) have no disclosed qualifying spend and no curated jurisdiction rule file — they cannot be exact-match targets and should be `status: blocked`. Zero of the 11 are Connecticut — Track A must select at least one CT row from the open-data CSV as a 12th pair (or a CT replacement) to give JUR-04 any validation coverage at all.** See "SRC-03" section. |
| SRC-04 | Partner track (Parallel) | Already resolved before planning — see CONTEXT.md. Not exercised in Phase 1 (Phase 5/7 concern); Phase 1's `pyproject.toml` does not need `parallel-web`/`google-genai`/`google-adk` as runtime deps yet. |
| SRC-05 | GA loan-out withholding rate confirmed | VERIFIED via direct `curl` of dor.georgia.gov: current rate is 4.99% (effective 2026-01-01), with a declining year-by-year schedule back to 5.75% (pre-2023). Confirms and refines the working hypothesis. See "SRC-05" section. |
| SHP-01 | Lightsail resize to 2GB via snapshot-and-restore, preserving static IP | AWS CLI procedure documented (snapshot → create-instances-from-snapshot with bundle small_3_0 → detach/attach static IP). Cannot resize down from a snapshot, only same-or-larger. See "SHP-01" section. |
| SHP-02 | Python 3.10+ installed, isolated from system Python | `uv python install 3.12` + `uv venv` pattern documented; standard, non-invasive. See "SHP-02" section. |
| SHP-03 | Subdomain DNS record exists and resolves | DNS zone host VERIFIED via direct `dig`: Register.com (Network Solutions), NOT Route 53 — resolves D-15. Current A record confirmed (35.165.60.123, matches static IP). TLS mechanism correction: `bncert-tool`, not bare `certbot`, is the Bitnami-correct tool. See "SHP-03" section. |
| SHP-04 | App runs under systemd, reverse-proxied through Apache, valid TLS, survives reboot | systemd unit pattern + Bitnami vhost pattern documented, with an open item on the exact `/opt/bitnami/apache/` vs `/opt/bitnami/apache2/` path for this specific box. See "SHP-04" section. |
| SHP-07 | Lockfile contains no forbidden packages; google-adk installed bare | `uv.lock` scanning pattern documented; **the google-adk-bare-only assertion is vacuously true in Phase 1 since google-adk isn't a Phase 1 dependency — write the check to pass on "absent," not just "present-and-bare."** See "SHP-07/09/10" section. |
| SHP-08 | Public repo, OSI licence detectable in About section | LICENSE file placement rules documented; **an automatable verification exists** — `GET /repos/{owner}/{repo}/license` returns `spdx_id` once GitHub's Licensee has processed it. See "SHP-08" section. |
| SHP-09 | All commits within contest window (≥2026-07-27) | Existing 10 commits already comply (dated 2026-08-23/24). CI script pattern (git log + date compare) documented, no suitable off-the-shelf Action found. |
| SHP-10 | No secret ever committed | gitleaks-action VERIFIED free for personal-account public repos (no license key needed); GitHub push protection VERIFIED as free-and-default-on for public repos as of 2026. See "SHP-07/09/10" section. |

</phase_requirements>

## Summary

This phase has two genuinely independent tracks, and this session's research materially de-risks both.

**Track A (source verification)** turned out to have three real findings beyond simple confirmation. First, the New York cap "conflict" is *not* fully explained by the working hypothesis (base $700M + new $100M indie pool = $800M combined) — that explanation is well-corroborated for the *press* figure, but one official ESD document itself (a May 2026 Agreed-Upon-Procedures PDF) states $800M using language that reads as the base program's own figure, contradicting the Guidelines PDF and the live esd.ny.gov page, both of which say $700M for that same base program. This is a genuine three-way document inconsistency that needs the enacted budget bill text to fully resolve, not just a reconciliation of press coverage. Second, three of the NY validation pairs (Anora, Succession S4, The Gilded Age S2) are now directly verified byte-for-byte against the actual government PDF, which is as strong a confidence tier as this project can produce. Third, and most important for planning: four of the eleven named validation pairs (the two Massachusetts and two Pennsylvania productions) cannot function as validation pairs at all in this milestone — they lack a disclosed qualifying-spend base, and MA/PA aren't even curated jurisdictions — while zero of the eleven are Connecticut, the fourth curated jurisdiction. The plan needs to account for both gaps explicitly rather than treat "11 pairs" as a simple checklist.

**Track B (deploy path)** benefits from three concrete, directly-verified facts that were previously open questions. The DNS zone host for vockell.com is Register.com (Network Solutions) — not Route 53 — confirmed by a live `dig` lookup, which resolves D-15 immediately and tells the planner the DNS task is a manual login to Register.com's panel, not an AWS CLI call. The TLS approach in D-16 needs a small but important correction: Bitnami stacks are not well-served by a bare `certbot --apache` invocation because Apache lives at a non-standard path; Bitnami's own `bncert-tool` (which itself wraps the Lego ACME client, not literally certbot) is the tool that actually works with this box's layout and self-installs renewal. Finally, GitHub's compliance posture has shifted since STACK.md was written: push protection is now free and on by default for all public repos, and license detection is independently checkable via a GitHub REST API call (`spdx_id`), not just an eyeball check of the About sidebar.

**Primary recommendation:** run Track A and Track B fully in parallel as already planned, but insert two explicit tasks the existing decisions don't cover — (1) resolve the NY $700M/$800M AUP-document inconsistency against the actual enacted budget bill before writing `.planning/SOURCE-TRUTH.md`, and (2) select at least one Connecticut production from the open-data CSV to serve as a validation pair, since none of the pre-sourced 11 cover Connecticut at all.

## Architectural Responsibility Map

Phase 1 is a foundations/infrastructure phase, not an application-feature phase — most standard app tiers (Browser/Client, CDN/Static, Database/Storage) don't apply yet. The table below maps this phase's actual capabilities onto the tiers that do apply, plus two infra-specific tiers this phase is unusually concentrated in.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Source-of-truth fact verification (NY cap, CT schema, GA rate, validation pairs) | Documentation / Data layer (`.planning/SOURCE-TRUTH.md`, `sources/`, `tests/fixtures/`) | — | Not a runtime capability at all — output is committed text and fixtures, consumed by Phase 2+ engine, not executed this phase. |
| DNS resolution for the subdomain | External registrar (Register.com) | — | Outside both the app and the host — a third-party control plane the plan must treat as a manual, credentialed step, not automatable infra-as-code without further access confirmation. |
| TLS termination | Frontend Server (Apache, Bitnami-managed) | — | Apache retains ports 80/443 per PROJECT.md; the app process never sees TLS directly. |
| Reverse proxy / request routing | Frontend Server (Apache) | API/Backend (uvicorn) | Apache is the entry point; it forwards to the API process on localhost. |
| App process supervision, isolated Python runtime | API/Backend (systemd + uv-managed venv) | — | The one genuine "backend" capability in this phase — a skeleton FastAPI process, not the engine. |
| CI compliance gates (lockfile scan, secret scan, commit-window) | Build/CI (GitHub Actions) | — | Runs outside any deployed tier; gates what's allowed to merge, not runtime behavior. |
| Repository licensing/visibility posture | Build/CI + GitHub platform metadata | — | Partially runtime-checkable via GitHub's REST API (`/license` endpoint), partially a one-time repo-settings action. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | **0.141.1** [VERIFIED: PyPI registry, `pip index versions fastapi`, checked 2026-08-24] | `GET /health`, `GET /` skeleton endpoints (D-20) | Matches CLAUDE.md's already-chosen stack; async-native, auto OpenAPI docs. |
| `uv` | **0.12.5** [VERIFIED: PyPI registry, `pip index versions uv`, checked 2026-08-24] | Installs isolated Python 3.12, manages the venv at `/opt/prodfin/.venv`, resolves `uv.lock` | D-17/D-18 already mandate `uv`; this is the exact current version to pin against. |
| pytest | **9.1.1** [VERIFIED: PyPI registry, `pip index versions pytest`, checked 2026-08-24] | Parametrized validation-pair fixture tests (D-01) | Matches CLAUDE.md; standard. |
| PyYAML | **6.0.3** [VERIFIED: PyPI registry, `pip index versions pyyaml`, checked 2026-08-24] | Reading/writing `sources/MANIFEST.yaml` and validation-pair fixture YAML | CLAUDE.md specifies "6.x" without a pinned patch — 6.0.3 is current. |
| ruff | **0.16.4** [VERIFIED: PyPI registry, `pip index versions ruff`, checked 2026-08-24] | Lint/format | Matches CLAUDE.md; zero-config-friendly. |

**Not required as Phase 1 runtime dependencies** (deferred to their owning phases even though they're project-wide constraints): `google-genai` (2.19.0, Phase 5), `google-adk` (2.7.1, Phase 5/7), `parallel-web` (**1.3.0** [VERIFIED: PyPI registry, checked 2026-08-24] — newer than CLAUDE.md's `>=1.0.1` floor, still satisfies it, Phase 7). SRC-04/SHP-05/SHP-06 are not exercised until those later phases per ROADMAP.md's own requirement mapping — do not add these as unused Phase 1 dependencies just to make the CI forbidden-package gate feel more real; see "SHP-07/09/10" below for how to write the gate so it isn't vacuous either way.

**Installation:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # on the Lightsail box, once
uv python install 3.12
uv venv --python 3.12 /opt/prodfin/.venv
uv pip install fastapi uvicorn pytest pyyaml ruff   # or: uv sync from pyproject.toml
```

## Package Legitimacy Audit

Ran `gsd-tools query package-legitimacy check --ecosystem pypi` against every Phase-1-relevant package plus the two later-phase mandated packages, for completeness. All returned verdict `SUS`, driven entirely by two heuristics that are known false positives for actively-maintained, high-release-cadence packages: `too-new` (the tool checks the *latest version's* publish timestamp, not package age) and `unknown-downloads` (the tool has no download-stats data source configured in this environment). None returned `SLOP`/`does-not-exist`. Cross-checked manually via `pip index versions <pkg>` (a direct tool call, not the legitimacy seam) for every package — all show deep, multi-year version histories, which is the concrete evidence overriding the `too-new` false positive:

| Package | Registry | Version history depth (VERIFIED via `pip index versions`) | Repo URL | Verdict (seam) | Disposition |
|---------|----------|---------------------------------------------------------|----------|---------|-------------|
| fastapi | PyPI | 0.1.0 → 0.141.1 (250+ releases) | github.com/fastapi/fastapi | SUS (too-new, unknown-downloads) | **Approved** — false positive, overridden by manual version-history check |
| pytest | PyPI | 2.0.0 → 9.1.1 (150+ releases) | github.com/pytest-dev/pytest | SUS (too-new, unknown-downloads) | **Approved** — false positive, overridden |
| pyyaml | PyPI | 3.10 → 6.0.3 | pyyaml.org | SUS (unknown-downloads) | **Approved** — false positive, overridden |
| ruff | PyPI | 0.0.14 → 0.16.4 (200+ releases) | docs.astral.sh/ruff | SUS (too-new, unknown-downloads) | **Approved** — false positive, overridden |
| uv | PyPI | 0.0.5 → 0.12.5 (200+ releases) | pypi.org/project/uv | SUS (too-new, unknown-downloads) | **Approved** — false positive, overridden |
| google-genai | PyPI | 0.0.1 → 2.19.0 | github.com/googleapis/python-genai | SUS (too-new, unknown-downloads) | **Approved, not a Phase 1 dep** — mandated package, Phase 5 |
| google-adk | PyPI | 0.0.1 → 2.7.1 | *(not surfaced by seam — no-repository signal)* | SUS (too-new, unknown-downloads, no-repository) | **Approved with a note** — mandated package (Phase 5/7); confirm on-PyPI repo link resolves to `google/adk-python` when it's actually added, since the automated seam couldn't find it this session |
| parallel-web | PyPI | 0.1.0 → 1.3.0 | github.com/parallel-web/parallel-sdk-python | SUS (too-new, unknown-downloads) | **Approved, not a Phase 1 dep** — mandated partner-track package, Phase 7 |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]` requiring a `checkpoint:human-verify`:** none carried a genuine risk signal (no low-downloads-with-no-repo, no postinstall-script red flag, no does-not-exist). The blanket `SUS` verdict here is a tooling artifact of this environment's `too-new`/`unknown-downloads` heuristics against fast-releasing, well-established projects — every package above has an independently verifiable, multi-year public release history and (except google-adk, noted above) a linked source repository. Treat as `OK` for planning purposes; no extra install-time human-verify gate is warranted.

**Separate note on `gitleaks-action` (not a PyPI/npm package):** this is a GitHub Marketplace Action (`uses: gitleaks/gitleaks-action@v3` in workflow YAML), not installed via a package registry — the ecosystem-specific legitimacy check does not apply to it. Verified directly instead by reading its README (see "SHP-07/09/10" section below).

## Architecture Patterns

### System Architecture Diagram — Track B deploy topology

```
                          ┌─────────────────────────────┐
   Anonymous visitor  ──▶ │  Register.com DNS            │  prodfin.vockell.com → A record
   (browser, HTTPS)       │  (dns105/106.register.com)   │  → 35.165.60.123 (static IP,
                          └──────────────┬───────────────┘     preserved across resize)
                                         │ resolves to
                                         ▼
                          ┌─────────────────────────────────────────────┐
                          │  Lightsail instance (small_3_0, 2GB/2vCPU)  │
                          │  Bitnami LAMP blueprint, Debian bullseye     │
                          │                                               │
                          │  ┌─────────────────────────────────────┐    │
                          │  │ Apache (Bitnami-managed,             │    │
                          │  │ /opt/bitnami/apache[2]/)             │    │
                          │  │ :80/:443 — TLS via bncert-tool        │    │
                          │  │ (Lego/Let's Encrypt, NOT Caddy,       │    │
                          │  │  NOT bare certbot)                    │    │
                          │  │                                       │    │
                          │  │ vhosts/prodfin-vhost.conf:            │    │
                          │  │  ServerName prodfin.vockell.com       │    │
                          │  │  ProxyPass / http://localhost:8000/   │    │
                          │  │  ProxyPassReverse (same)              │    │
                          │  └───────────────┬───────────────────────┘    │
                          │                  │ localhost:8000              │
                          │                  ▼                             │
                          │  ┌─────────────────────────────────────┐     │
                          │  │ systemd unit: prodfin.service         │     │
                          │  │ ExecStart=/opt/prodfin/.venv/bin/     │     │
                          │  │           uvicorn app.main:app        │     │
                          │  │ User=prodfin (non-root)               │     │
                          │  │ Restart=on-failure                    │     │
                          │  │ WantedBy=multi-user.target             │     │
                          │  │  (survives reboot — D-23 tests this)   │     │
                          │  │                                        │     │
                          │  │  FastAPI skeleton (D-20):              │     │
                          │  │   GET /health → {version, git_sha,     │     │
                          │  │                  boot_time}            │     │
                          │  │   GET /       → holding page           │     │
                          │  └────────────────────────────────────────┘    │
                          │                                                │
                          │  Isolated Python 3.12 via uv — system         │
                          │  Python 3.9.2 (Bitnami/Apache) untouched      │
                          │                                                │
                          │  vockell.com (existing site) continues on     │
                          │  Apache's default vhost, unaffected            │
                          └───────────────────────────────────────────────┘

Deploy path (D-19): dev machine → git push → SSH to box → git pull →
deploy/deploy.sh (uv sync, systemctl restart prodfin) — no CI push, no rsync.
```

### System Architecture Diagram — Track A source-verification data flow

```
Government primary source (PDF/CSV/HTML)
   │  e.g. esd.ny.gov Q3-Film-Report-2025.pdf,
   │       data.ct.gov CSV export, dor.georgia.gov page
   ▼
Fetch + archive byte-for-byte (D-08)  ──▶  sources/{jurisdiction}/{date}-{slug}.{ext}
   │                                            │
   │                                            ▼
   │                                   sources/MANIFEST.yaml
   │                                   {url, retrieved_at, sha256,
   │                                    jurisdiction, cited_for[]}
   ▼
Read/extract figures (pdftotext / curl / direct read — NOT a summarizing
fetch tool alone, since a summary can silently drop or misquote a digit)
   │
   ├──▶ SRC-01/02/05 answers  ──▶  .planning/SOURCE-TRUTH.md (D-11)
   │                                {question, answer, url, date_checked,
   │                                 confidence, what_was_refuted}
   │
   └──▶ SRC-03 validation pairs ──▶ tests/fixtures/validation_pairs/
                                     {jurisdiction}_{slug}.yaml (D-01/D-03)
                                     status: active | blocked (D-06)
```

### Component Responsibilities (Track B)

| Component | Responsibility | Concrete implementation this session verified |
|-----------|----------------|------------------------------------------------|
| Register.com DNS panel | Owns the `vockell.com` zone; the subdomain A/CNAME record is created here, not in AWS | [VERIFIED: `dig +short NS vockell.com` + `whois vockell.com`, run this session] — nameservers `dns105.register.com`/`dns106.register.com`, registrar "Register.com - Network Solutions, LLC" |
| Apache (Bitnami) | TLS termination, reverse proxy, keeps vockell.com serving unmodified | [CITED: docs.bitnami.com/virtual-machine/infrastructure/lamp/configuration/configure-custom-application/] — custom vhosts live in `/opt/bitnami/apache/conf/vhosts/` (or `apache2/` — exact path is box-version-dependent, confirm on the actual instance before writing the plan's exact path) |
| `bncert-tool` | Obtains and renews the Let's Encrypt certificate for the new subdomain | [CITED: docs.bitnami.com/virtual-machine/how-to/understand-bncert/, aws re:Post SSL-on-Bitnami articles] — run as `sudo /opt/bitnami/bncert-tool`, prompts for a space-separated domain list, self-installs a renewal cron job |
| `uv` | Installs isolated Python 3.12, manages `/opt/prodfin/.venv`, resolves/locks dependencies | [CITED: docs.astral.sh/uv] `uv python install 3.12`; `uv venv --python 3.12 <path>` |
| systemd | Supervises the uvicorn process, restarts on crash, starts on boot | Standard unit pattern — see Code Examples below |
| GitHub Actions | Three blocking CI jobs (D-27) gating every push | See "SHP-07/09/10" below for concrete job bodies |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TLS cert issuance/renewal on this specific Bitnami box | A custom certbot-plus-cron script targeting `/etc/apache2` paths | `bncert-tool` (ships with the Bitnami image) | Bitnami's Apache lives at a non-standard path; the standard `certbot --apache` plugin's auto-detection is built for `/etc/apache2`/`/etc/httpd` and is a documented source of failed/broken configs on Bitnami stacks [CITED: docs.bitnami.com, aws re:Post]. `bncert-tool` already knows Bitnami's layout and self-renews. |
| Secret scanning in CI | A custom regex-grep script for API-key-shaped strings | `gitleaks/gitleaks-action@v3` | Purpose-built, actively maintained, free for personal-account public repos [VERIFIED: github.com/gitleaks/gitleaks-action README, fetched this session], catches far more secret shapes than a hand-rolled regex ever will, and is exactly the tool D-27 already specifies. |
| License-detection verification | Manually reloading the GitHub repo page and eyeballing the About sidebar every time | `GET /repos/{owner}/{repo}/license` REST call, assert `spdx_id == "MIT"` | [CITED: docs.github.com/en/rest/licenses/licenses] — this is a genuinely automatable check, not just a manual pre-submission glance; can run as a post-push verification step or even inside the same CI workflow with a short delay for Licensee to process. |
| Commit-window enforcement | Trying to find a marketplace Action for this narrow, project-specific rule | A ~5-line bash step: `git log --pretty=format:"%ai"` piped through a date comparison against `2026-07-27` | No well-fitting off-the-shelf Action was found this session for "reject any commit authored before date X" — this is genuinely simpler to write directly than to adopt and configure a generic commit-linting Action for. |
| DNS zone lookup / management automation | Assuming Route 53 and reaching for `aws route53` commands | Manual login to the Register.com account panel (no confirmed public API in this session's research) | The zone is provably not in Route 53 [VERIFIED: `dig`/`whois` this session] — building Terraform/CLI automation against the wrong provider would simply fail; confirm whether Register.com/Network Solutions exposes an API for this account before assuming a manual step is required forever. |

**Key insight:** every "don't hand-roll" item in this phase is really the same lesson twice — this box (Bitnami-managed Apache, a non-AWS-managed DNS zone) doesn't match the generic tutorials for "deploy FastAPI behind Apache with Let's Encrypt," and the fix in both cases is to use the tool the *actual* platform owner (Bitnami, Register.com) provides rather than the tool a generic guide assumes.

---

## SRC-01 — New York annual cap

**Working hypothesis under test (CONTEXT.md D-12):** "$700M base plus a separate $100M independent-film pool, not a $700M/$800M dispute."

**Finding: the hypothesis is largely correct but does not fully resolve a genuine three-document inconsistency. Do not code a final number until the gap below is closed.**

### Documents read directly this session

1. **NY State Film Tax Credit Program Guidelines**, dated 2025-04-18 (filename `Film_Credit_Guidelines_W_Appendix_20250418_0.pdf`), fetched from `https://esd.ny.gov/sites/default/files/media/document/Film_Credit_Guidelines_W_Appendix_20250418_0.pdf`, read directly with the `Read` tool (PDF text extraction), page 1 and 2. [VERIFIED: esd.ny.gov PDF, read directly this session, 2026-08-24]
   - Page 1, "Amount of Credits Available": *"Program credits of $700 million per year can be allocated and used to encourage companies to produce film projects in New York and help create and maintain film industry jobs. Up to $45 million of the $700 million may be dedicated to supporting and growing the post-production industry in the State. There are no per project caps for credits, and there is rollover in the annual $700 million allocation going forward until 2034."*
   - Page 2: *"Changes to the Film Tax Credit Program which are effective April 1, 2023 are as follows: Base tax credit rate has increased to 30%. Annual Allocation has increased to $700 million, of which $45 million is allocated to Post Production Tax Credit Program. Allocation for the program continues through 2034."*
   - This document describes the **combined Film Production + Post-Production Tax Credit Program** (one program with two components) — it does not mention the Independent Film Production Tax Credit Program at all, consistent with that program not existing yet as of this document's 2025-04-18 date (it launched later in 2025).

2. **esd.ny.gov live page**, `https://www.esd.ny.gov/new-york-state-film-tax-credit-program-production`, fetched this session (WebFetch, LLM-summarized — not raw-byte read). [CITED: esd.ny.gov, fetched 2026-08-24]
   - Quoted verbatim by the fetch: *"This tax credit is funded at $700 million a year through 2036."*
   - Note the extension from "until 2034" (the April-2025 Guidelines PDF) to "through 2036" — consistent with press reporting (below) of a 2-year extension enacted in the FY2026 budget (approved ~May 2025).

3. **NYS Film Tax Credit Program – Agreed Upon Procedures**, dated **May 2026** (filename `Film-Prod-CPA-AUP-May2026.pdf`), fetched from `https://esd.ny.gov/sites/default/files/media/document/Film-Prod-CPA-AUP-May2026.pdf`, read directly with the `Read` tool. [VERIFIED: esd.ny.gov PDF, read directly this session, 2026-08-24]
   - Page 1, "Background": *"The New York State Film Tax Credit Program is administered by the ESD Economic Incentives Tax Benefit Program (Film) Dept... Program credits of $800 million per year can be allocated and used to encourage companies to produce projects in New York which help create and maintain industry jobs."*
   - **This is the anomaly.** This sentence uses the same construction as the Guidelines PDF's $700M sentence, describing what reads as the same base "Film Tax Credit Program" (the AUP document is specifically about CPA inspection procedures for the Film Production Tax Credit, not the Independent Film program) — but states $800 million where the Guidelines PDF and the current esd.ny.gov page both state $700 million for that same base program.

4. **esd.ny.gov Independent Film Production Tax Credit Program page**, `https://www.esd.ny.gov/new-york-state-independent-film-production-tax-credit-program`, fetched this session (WebFetch, LLM-summarized). [CITED: esd.ny.gov, fetched 2026-08-24]
   - Quoted verbatim: *"Pool 1 with approximately $20 million annually is for productions with $10 million or less in qualified costs."* / *"Pool 2 with approximately $80 million annually is for productions with more than $10 million in qualified costs."*
   - Confirms the $100M independent-film pool and its $20M/$80M internal split, matching `feasibility-incentives.md`'s already-recorded figures exactly.

5. **Press corroboration** (multiple independent outlets — Entertainment Partners, Hollywood Reporter, Wrapbook — via WebSearch, not independently primary-sourced this session): the FY2026 NY budget (approved May 2025) is reported to have (a) extended the existing $700M base program by two years (to 2036, matching finding #2 above) and (b) created the new, separately-named $100M Independent Film Production Tax Credit Program — with the two summed as "$800 million" **in press shorthand for total annual film-incentive capacity**, not as a restatement of the base program's own cap. [CITED: multiple secondary sources, WebSearch, 2026-08-24 — MEDIUM confidence per D2's precedence policy, corroboration not primary text]

### What this means for the plan

- The **best-supported answer** for "the base NY Film Production + Post-Production Tax Credit Program's own annual cap" is **$700 million**, confirmed by two ESD sources (the April-2025 Guidelines PDF and the current live program page), both more directly on-topic for that specific figure than the AUP document.
- The **$800 million figure is well-explained as the combined total** (base $700M + new $100M independent pool) in press coverage, and D-12's working hypothesis is directionally right.
- **However, the AUP document (finding #3) is dated more recently (May 2026) than the Guidelines PDF (April 2025) and is an official ESD document, not a press summary** — under PITFALLS.md §D2's precedence policy ("more recent over older, when both are dated and comparably authoritative"), this is not a case Track A should wave away as a press-rounding artifact. Two explanations remain open, and this research cannot distinguish between them from the documents fetched this session:
  1. The AUP document's author reused the Guidelines PDF's boilerplate sentence structure but substituted the *combined* figure by mistake or informal convention (internal document imprecision, not a policy change) — in which case $700M remains the correct base-program figure to encode.
  2. A further budget action between April 2025 and May 2026 (e.g., an FY2027 budget passed ~April/May 2026) raised the *base* program's own cap from $700M to $800M, independent of the Independent Film pool — in which case $800M (or some other newer figure) is now the correct base-program figure, and the live esd.ny.gov page (finding #2, "funded at $700 million... through 2036") would itself be stale and need a fresh re-check.
- **This must be resolved against the actual enacted budget bill text (the FY2026 or, if applicable, FY2027 New York State budget bill, the "Amount of Credits Available" statutory language) before `.planning/SOURCE-TRUTH.md` is finalized — that is the top of D2's precedence ordering and neither of this session's two ESD PDFs is itself the statute.** Recommend Track A search `nysenate.gov` or `assembly.state.ny.us` for the FY2026 budget bill (approved ~May 2025) and, if the AUP document's May 2026 date suggests a newer action, also check for an FY2027 budget bill (would be approved ~April 2026).
- Per D-13, if this cannot be fully reconciled in the time available, **it should be recorded as an explicit unresolved-conflict entry in `.planning/SOURCE-TRUTH.md`** — do not silently pick $700M or $800M without the reasoning above being visible.

**Confidence:** HIGH (VERIFIED) for the $700M base-program figure, the $100M/$20M/$80M independent-pool figures, and the existence of the AUP-document anomaly itself. MEDIUM/open for which figure is actually correct as of "today" if a further budget action occurred between April 2025 and May 2026 — flagged, not resolved.

---

## SRC-02 — Connecticut CSV column headers

**Endpoint:** `https://data.ct.gov/api/v3/views/kjsu-mdny/export.csv?accessType=DOWNLOAD` (dataset landing page: `https://data.ct.gov/d/kjsu-mdny`)

**Method:** `curl -s -m 20 "<url>"` run directly this session, 2026-08-24 — raw bytes read, not LLM-summarized. [VERIFIED: data.ct.gov CSV export, direct `curl`, checked 2026-08-24]

**Exact header row, verbatim:**
```
"Production Company","Qualified CT Expenditures","Date Issued","Amount of Tax Credit Issued","Program Name","Statutory Reference","Municipality"
```
Seven columns, in this order: `Production Company`, `Qualified CT Expenditures`, `Date Issued`, `Amount of Tax Credit Issued`, `Program Name`, `Statutory Reference`, `Municipality`.

**Data-quality gotchas found by inspecting the raw CSV directly** (all [VERIFIED: same curl fetch]):
- **A blank row immediately follows the header row** (`,,,,,,`) — a naive parser reading row 2 as the first data row will get an empty record; must be skipped.
- **Monetary values are quoted text strings with `$` and thousands commas**, e.g. `"$175,772.00"` — not raw numeric, requires stripping `$`/`,` before `Decimal()` parsing.
- **At least one inconsistent trailing-period formatting artifact observed** in the sampled rows (e.g. a value ending `.00.` rather than `.00`) — a strict parser should tolerate/strip a trailing period rather than fail outright.
- **`Municipality` is blank for some rows** (observed for early World Wrestling Entertainment / WWE entries from 2007) — must be nullable in the fixture/ingestion schema, not required.
- **Dates in `Date Issued` are ISO 8601 with a time component** (`YYYY-MM-DDTHH:MM:SS.sss`), even though these are calendar-date events — parse as datetime and truncate to date.
- **`Program Name` covers at least three distinct statutory programs sharing this one CSV**, confirmed via the sampled rows plus `feasibility-incentives.md`'s own note: "Film and Digital Media Production Tax Credit" (CGS §12-217jj), "Film Infrastructure Tax Credit" (CGS §12-217kk), and "Digital Animation Production Company Tax Credit" (CGS §12-217ll). **The CT `JurisdictionRuleSet` (Phase 2/5) needs to decide explicitly whether it models all three or scopes to just the production credit (§12-217jj) — this file does not distinguish them by column, only by row value, so ingestion logic must filter on `Program Name`.**
- **Row count:** at least 1000+ rows observed (file was not fully downloaded/counted this session — the `curl` output was truncated for inspection purposes); earliest observed row dated 2007-08-10 (Orange Lion Productions, LLC).
- **Disclosure stage implied by the schema itself:** `Date Issued` + `Amount of Tax Credit Issued` describes **issued** credits (like NY), not allocation/estimate-stage figures (like CA/NJ) — this is a genuinely strong validation source if a suitable row is selected (see SRC-03 below for why none has been selected yet).

**Confidence:** HIGH (VERIFIED, direct tool read of the live endpoint).

---

## SRC-03 — The 11 validation pairs

**Source list:** `feasibility-incentives.md` lines ~243-260, "Named validation test cases — 11 sourced production/amount pairs."

### Per-pair status

| Production | Jurisdiction | Qualified spend | Credit amount | Disclosure stage | Source | Status this session |
|---|---|---|---|---|---|---|
| Anora | NY | **$3,964,760** | **$991,190** | issued | ESD Q3 2025 report | **VERIFIED byte-for-byte** — see below |
| Succession S4 | NY | **$102,920,384** (NYS Spend $152,802,059) | **$25,747,913** | issued | ESD Q3 2025 report | **VERIFIED byte-for-byte** — see below |
| The Gilded Age S2 | NY | **$134,340,015** (NYS Spend $169,214,898) | **$35,318,864** | issued | ESD Q3 2025 report | **VERIFIED byte-for-byte** — see below |
| Clueless S1 (reboot) | CA | $46,522,000 | $16,335,000 | allocated | CA Film Commission approved-projects list, dated 7/27/2026 | Not re-verified this session (time-boxed) — sourced only, per `feasibility-incentives.md` |
| Disney's Hexed | CA | $47,538,000 | $16,638,000 | allocated | CA Film Commission approved-projects list, dated 6/22/2026 | Not re-verified this session — sourced only |
| Joker | NJ | $6,133,257 (estimated) | $1,962,642 | estimated | NJEDA activity report, approved 8/13/2019 | Not re-verified this session — sourced only |
| The Trial of the Chicago 7 | NJ | $17,906,613 (estimated) | $5,371,983 | estimated | NJEDA activity report, approved 7/14/2020 | Not re-verified this session — sourced only |
| Don't Look Up | MA | *not disclosed* | $46,000,000 | — | WBUR / MA DOR records request | **Not usable as a validation pair — see below** |
| Madame Web | MA | *not disclosed* | $23,688,438 | — | WBUR / MA DOR records request | **Not usable as a validation pair — see below** |
| Creed II | PA | *not disclosed* | $16,000,000 | — | PA DCED via Philadelphia Inquirer | **Not usable as a validation pair — see below** |
| Knock at the Cabin | PA | *not disclosed* | $5,000,000 | — | PA DCED via Philadelphia Inquirer | **Not usable as a validation pair — see below** |

### NY pairs — directly verified this session

**Source document:** `https://esd.ny.gov/sites/default/files/media/document/Q3-Film-Report-2025.pdf` ("Film Tax Credit – Quarterly Report, Calendar Year 2025: Third Quarter, September 30, 2025"). Fetched, saved locally, and extracted with `pdftotext -layout` run directly via Bash — **raw text extraction, not an LLM summary of the PDF.** [VERIFIED: esd.ny.gov PDF, direct `pdftotext` extraction this session, 2026-08-24]

**Exact table column headers** (table titled "Film Tax Credit Program - Credits Issued", under section "FINAL APPLICATIONS – CREDITS ISSUED – FILM PRODUCTION AND POST-PRODUCTION"), verbatim, 12 columns: `PROJECT`, `Studio`, `Company`, `State of Inc.`, `County`, `Qualified Costs`, `NYS Spend`, `Total Hires`, `Credit Eligible Hours`, `Credit Eligible Wages`, `Credit Issued Amount`, `Diversity Credit Amount`.

**Note the 12th column, `Diversity Credit Amount`, is a separate line item from `Credit Issued Amount`** — not previously called out in `feasibility-incentives.md`. Fixture design (D-03) should decide explicitly whether to fold it into `credit_amount` or track it separately; folding it in silently would make the fixture's `credit_amount` not equal the table's own `Credit Issued Amount` column, which is the actual "did we reproduce the government's number" test.

**Extracted rows, verbatim (money/counts as shown in the source table):**
- **Anora**: Qualified Costs `$3,964,760`, NYS Spend `$5,676,019`, Total Hires `417`, Credit Eligible Hours `36,513`, Credit Eligible Wages `$1,453,503`, Credit Issued Amount `$991,190`, Diversity Credit Amount `$4,956`. County: New York. State of Inc.: NY.
- **The Gilded Age S2** (row label "Gilded Age, The-S2"): Qualified Costs `$134,340,015`, NYS Spend `$169,214,898`, Total Hires `3248`, Credit Eligible Hours `1,022,506`, Credit Eligible Wages `$56,206,180`, Credit Issued Amount `$35,318,864`, Diversity Credit Amount `$176,594`. State of Inc.: DE.
- **Succession S4** (row label "Succession-S4"): Qualified Costs `$102,920,384`, NYS Spend `$152,802,059`, Total Hires `5062`, Credit Eligible Hours `751,550`, Credit Eligible Wages `$42,680,975`, Credit Issued Amount `$25,747,913`, Diversity Credit Amount `$128,740`. State of Inc.: DE.

**All three figures match `feasibility-incentives.md`'s already-recorded numbers exactly** — this is a genuine independent confirmation, not a re-transcription of the same secondary source. These three pairs can be committed as `mode: exact`, `status: active`, `disclosure_stage: issued`, with `source_url` = the PDF above and `source_document_sha256` computed from the archived copy (D-08/D-09).

### Critical scope finding #1 — four of the 11 pairs cannot function as validation pairs in Milestone 1

`feasibility-incentives.md`'s own table marks "Qualified spend disclosed?" as **"No"** for all four of: Don't Look Up (MA), Madame Web (MA), Creed II (PA), Knock at the Cabin (PA). Per CONTEXT.md's own D-02 ("a validation pair proves the incentive interpreter only... fixtures feed qualified spend IN as a given and assert on net cash OUT"), a pair with no disclosed qualifying-spend figure has nothing to feed into the engine — there is no re-derivation test possible, only a bare credit-amount number with no input.

**Compounding this: Massachusetts and Pennsylvania are not among the four curated jurisdictions** (NY/CA/NJ/CT — confirmed in `PROJECT.md`/`STATE.md`/`ROADMAP.md` JUR-01..04). No `JurisdictionRuleSet` for MA or PA is planned anywhere in Milestone 1 (Phases 2-8). Even if a qualifying-spend figure were later found for these four productions, there would be no rule file to test it against.

**Recommendation:** commit all 4 as fixtures with `status: blocked` per D-06, with a `blocker` string naming both reasons explicitly, e.g.: *"qualifying spend not publicly disclosed (only the awarded credit amount is, via a public-records request), and no curated JurisdictionRuleSet exists for Massachusetts in Milestone 1 scope (JUR-01..04 covers NY/CA/NJ/CT only)."* This satisfies the literal "commit all 11" instruction in SRC-03/ROADMAP.md while being honest, per D-06, that they are excluded from the accuracy denominator.

### Critical scope finding #2 — zero of the 11 pairs are Connecticut

Connecticut is the fourth curated jurisdiction (JUR-04), and Track A's own CONTEXT.md scope explicitly includes "confirm the Connecticut CSV column headers... before CT's rule model or ingestion logic is written" — but **none of the 11 named pairs in `feasibility-incentives.md`'s validation-pair table are Connecticut productions.** The CT open-data CSV (SRC-02, confirmed 1000+ rows going back to 2007) is a bulk disclosure feed, not a pre-selected pair — nobody has yet picked a specific CT production/credit row to serve as a validation pair.

**Recommendation:** add an explicit task to Track A (not currently named in any locked decision): select at least one Connecticut production from the open-data CSV — ideally a small, single-programme (`§12-217jj` only), no-uplift production similar in spirit to the Anora anchor (D-05's principle applies here too) — and commit it as a 12th fixture (or, if the plan prefers to keep "11" as a hard cap, treat it as a replacement for one of the four blocked MA/PA pairs). Without this, JUR-04 (Connecticut) ships with **zero** validation coverage, which directly undercuts ROADMAP.md's Phase 5 success criterion that CA/NJ/CT each "price correctly against their own government disclosure."

**Confidence:** HIGH (VERIFIED) for the three NY pairs' figures and column schema. MEDIUM (CITED, not independently re-verified this session — recommend Track A apply the same `curl`/`pdftotext` pattern demonstrated here) for the four CA/NJ pairs. The two scope findings above (MA/PA unusable, zero CT coverage) are structural facts about the existing source list, not confidence-tier questions — they are certain, not probabilistic.

---

## SRC-05 — Georgia loan-out withholding rate

**Working hypothesis under test (CONTEXT.md D-12):** "5.75% is pre-2024-reform, 4.99% is current."

**Source:** `https://dor.georgia.gov/film-tax-credits/film-tax-credit-resources`, fetched via direct `curl -A "Mozilla/5.0"` this session — raw HTML read, not LLM-summarized. [VERIFIED: dor.georgia.gov, direct `curl`, checked 2026-08-24]

**Exact table, under the page's `<h2>Withholding Rate</h2>` heading, verbatim:**
```
The withholding rate is as follows:
January 1, 2026 - Current = 4.99%
January 1, 2025 - December 31, 2025 = 5.19%
January 1, 2024-December 31, 2024 = 5.39%
January 1, 2023 -December 31, 2023 = 5.49%
December 31. 2022 - Prior = 5.75%
```

**Finding: the hypothesis is directionally correct but imprecise — it is not a single pre/post-2024 step, it is a five-year declining schedule.** The current effective rate as of any date checked in 2026 is **4.99%**, reached via four annual steps down from 5.75% (the rate through 2022), consistent with Georgia's broader 2022 individual-income-tax-rate-reduction legislation applying to this withholding rate as well. `5.75%` is confirmed as the correct "prior/pre-reform" figure, just with three intermediate values (5.49%, 5.39%, 5.19%) not previously recorded anywhere in the project's planning docs.

**One caveat worth flagging to the executor:** the fetched page fragment presents this table under a generic "Withholding Rate" heading on the **film-tax-credit-resources** page — the fragment captured this session does not contain an explicit sentence tying it specifically to *loan-out* withholding (as opposed to some other film-tax-credit-related withholding). This is the exact page the project's own source briefs (`feasibility-incentives.md` line 83) already cite as the primary for this figure, and it is contextually the correct page (Georgia's general personal income tax rate and its film-loan-out withholding rate are understood to be the same figure), but Track A should also open the specifically-linked "Film Tax Credit Withholding Instructions and Forms" page (`https://dor.georgia.gov/film-tax-credit-withholding-instructions-and-forms`, linked from the same page, not fetched this session) to get an explicit sentence naming loan-out withholding before writing the final `SOURCE-TRUTH.md` entry.

**Confidence:** HIGH (VERIFIED) for the rate figures and year-by-year schedule. MEDIUM for the precise "this table specifically governs loan-out withholding" framing — contextually strong, not 100% explicit in the exact text fragment captured this session.

---

## SHP-01 — Lightsail resize (snapshot-and-restore, preserve static IP)

**Constraint confirmed:** [CITED: docs.aws.amazon.com/lightsail/latest/userguide/how-to-create-larger-instance-from-snapshot-using-console.html and the AWS-CLI variant of the same doc] — Lightsail can only create an instance **the same size or larger** from a snapshot; it cannot resize down. Since D-01 already targets `small_3_0` (2GB/2vCPU) from the current smaller bundle, this is a strict upsize and is supported.

**Procedure (AWS CLI, profile `newaccount`, region `us-west-2` per PROJECT.md):**
```bash
# 1. Snapshot the current instance (do this first, always — it's the rollback path)
aws lightsail create-instance-snapshot \
  --instance-name vockell_dot_com_LAMP \
  --instance-snapshot-name vockell-pre-resize-$(date +%Y%m%d) \
  --profile newaccount --region us-west-2

# 2. Wait for snapshot to complete (poll get-instance-snapshot for state: available)

# 3. Create a new, larger instance from that snapshot
aws lightsail create-instances-from-snapshot \
  --instance-names vockell_dot_com_LAMP_2gb \
  --availability-zone us-west-2a \
  --instance-snapshot-name vockell-pre-resize-$(date +%Y%m%d) \
  --bundle-id small_3_0 \
  --profile newaccount --region us-west-2

# 4. Detach the static IP from the OLD instance, attach to the NEW one
aws lightsail detach-static-ip --static-ip-name <static-ip-name> --profile newaccount --region us-west-2
aws lightsail attach-static-ip --static-ip-name <static-ip-name> --instance-name vockell_dot_com_LAMP_2gb --profile newaccount --region us-west-2

# 5. Verify Apache/MySQL/vockell.com serve correctly on the new instance before
#    deleting the old one — keep the old instance stopped (not deleted) for a
#    rollback window rather than deleting immediately.
```
[CITED: docs.aws.amazon.com/lightsail — the general shape of this sequence is documented across the console-based and CLI-based versions of the same guide; the exact `create-instance-snapshot`/`create-instances-from-snapshot`/`detach-static-ip`/`attach-static-ip` command names are the documented AWS Lightsail API operations]

**Failure modes to plan for:**
- **This takes vockell.com offline for the swap window** (D-21 already flags this as a discrete, schedulable task — confirmed necessary, not avoidable, since the static IP can only be attached to one instance at a time).
- If the new instance from snapshot fails to boot cleanly (a known general risk with any snapshot-restore), the static IP re-attach step to the OLD instance is the rollback — this is why the old instance should be *stopped*, not deleted, until the new one is confirmed healthy.
- IPv6: [CITED: AWS Lightsail docs via WebSearch summary] static IP binding via this mechanism applies to the IPv4 address only — if the instance also has an IPv6 address, it is not preserved the same way (likely not relevant here since PROJECT.md only references the IPv4 static IP, `35.165.60.123`, confirmed live via `dig` this session).

**Confidence:** HIGH (CITED, official AWS docs) for the mechanism and command shapes; the exact current instance name (`vockell_dot_com_LAMP` per CLAUDE.md) and static-IP resource name were not independently re-confirmed via the AWS console/CLI this session (no AWS credentials available in this research environment) — the executor should run `aws lightsail get-instances` / `get-static-ips` first to get the exact current resource names before running the sequence above.

---

## SHP-02 — Python 3.12 via `uv`, isolated from system Python 3.9.2

**Tool:** `uv` **0.12.5** [VERIFIED: PyPI registry, `pip index versions uv`, checked 2026-08-24]. [CITED: docs.astral.sh/uv]

**Install (on the Lightsail box, once, as a non-root or root one-time step — does not touch `apt`/system Python):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Install an isolated Python 3.12 interpreter** (uv downloads and manages its own Python builds — it does not invoke `apt install python3.12` and does not touch `/usr/bin/python3` or the Bitnami-bundled interpreter Apache depends on):
```bash
uv python install 3.12
```

**Create the project venv at the target path** (D-17 already specifies `/opt/prodfin`):
```bash
uv venv --python 3.12 /opt/prodfin/.venv
```

**Isolation guarantee:** [CITED: docs.astral.sh/uv, cross-corroborated via multiple independent sources this session] `uv`-managed Python interpreters are downloaded into `uv`'s own managed directory (typically under the invoking user's home, e.g. `~/.local/share/uv/python/`) and are entirely separate from the system package manager's Python — installing or using them does not modify, upgrade, or remove the system Python that Bitnami/Apache depend on (D-18's isolation boundary). The systemd unit (see SHP-04) should reference the venv's binaries by absolute path (`/opt/prodfin/.venv/bin/uvicorn`), never relying on `source activate` inside `ExecStart`, which is unreliable under systemd's non-interactive shell.

**D-22 reminder (not new research, restating the locked decision for planner visibility):** measure free memory (`free -h`) immediately after this install step completes and record the number in `STATE.md` — it gates the Milestone 2 SQLite-vs-MySQL decision.

**Confidence:** HIGH (CITED, `uv` official docs + general current practice, cross-corroborated across multiple independent sources this session).

---

## SHP-03 — DNS zone host and TLS mechanism

### DNS zone host — resolves D-15

**This was flagged in CONTEXT.md as "unknown and must be established as the very first task in Track B — not guessable from the planning documents." It is answered directly by this research, via live lookup, not guesswork.**

```
$ dig +short NS vockell.com
dns106.register.com.
dns105.register.com.

$ whois vockell.com | grep -i "registrar\|name server"
Registrar WHOIS Server: whois.register.com
Registrar URL: http://www.register.com
Registrar: Register.com - Network Solutions, LLC
Registrar IANA ID: 9
Name Server: DNS105.REGISTER.COM
Name Server: DNS106.REGISTER.COM

$ dig +short A vockell.com
35.165.60.123
```
[VERIFIED: direct `dig` and `whois` commands run against the live public DNS this session, 2026-08-24]

**The DNS zone for vockell.com is hosted at Register.com (part of the Network Solutions/Web.com group) — it is NOT in Route 53, and it is not managed through the AWS account at all.** The current `A` record (`vockell.com` → `35.165.60.123`) matches the static IP already documented in `.claude/CLAUDE.md`, confirming the box's identity is correctly understood.

**Practical consequence for the plan:** creating the `prodfin.vockell.com` (pending D-14 confirmation) subdomain `A` record is **a manual step in the Register.com web account panel**, not an `aws route53` CLI call and not Terraform-automatable without further access research. [CITED: general registrar DNS-management pattern, via WebSearch this session — no Register.com-specific API was confirmed available; Network Solutions/Web.com's broader product line does offer some API products for enterprise accounts, but this was not confirmed for this specific account] The planner should:
1. Treat this as a task requiring the account owner (Dave) to personally log in to the Register.com account.
2. Trigger it as the very first Track B action (D-21 already specifies DNS first), since propagation is the one clock the plan doesn't control.
3. Not assume this can be scripted — flag it explicitly as a manual/human step in the plan, distinct from the AWS CLI steps elsewhere in Track B.

### TLS mechanism — correction to D-16

**D-16 states:** "TLS via certbot with the Apache plugin — not Caddy," explicitly overruling STACK.md's Caddy recommendation because Apache retains ports 80/443. **The "not Caddy" reasoning is sound and stands unchanged.** This research finds a refinement to the *specific tool* named ("certbot"):

- [CITED: docs.bitnami.com/virtual-machine/how-to/understand-bncert/, aws re:Post SSL-on-Bitnami-Lightsail knowledge center articles, fetched via WebSearch this session] A bare `certbot --apache` invocation is a documented source of failure/misconfiguration on Bitnami stacks, because Bitnami's Apache installation lives at a non-standard filesystem path (`/opt/bitnami/apache2/` or `/opt/bitnami/apache/`, not `/etc/apache2` or `/etc/httpd`) that the standard certbot Apache plugin's auto-detection logic is not built to find.
- **Bitnami ships and recommends its own tool for exactly this: `bncert-tool`**, invoked as `sudo /opt/bitnami/bncert-tool`. It prompts interactively for a space-separated list of domains to secure, correctly configures Bitnami's own Apache layout, and **self-installs a renewal cron job** (no separate renewal automation needed, unlike a raw certbot setup). Under the hood it uses Bitnami's own ACME client integration (documented elsewhere as using the Lego client, not literally the `certbot` package) — so "certbot" in D-16 is best read as shorthand for "Let's Encrypt via the Apache-integrated path" rather than a literal instruction to `apt install certbot`.
- **One noted limitation:** `bncert-tool` does not support wildcard certificates (not relevant here — a single named subdomain is sufficient) [CITED: same sources].
- **Open item not resolved this session:** whether re-running `bncert-tool` to add the new `prodfin.vockell.com` subdomain requires re-specifying vockell.com's existing domains in the same invocation (risk of disrupting the existing site's certificate) or can be run incrementally/additively. Recommend the executor check `sudo /opt/bitnami/bncert-tool --help` and/or `/opt/bitnami/letsencrypt/` (where bncert-tool-issued certs are typically stored) on the actual box before running it, and take a fresh Lightsail snapshot immediately before this step regardless (cheap insurance given it touches the live vockell.com TLS config).

**Recommendation for the plan:** update the task description from "install certbot, run `certbot --apache -d prodfin.vockell.com`" to "run `sudo /opt/bitnami/bncert-tool`, add `prodfin.vockell.com` to the domain list" — same outcome (Let's Encrypt cert, Apache-integrated, auto-renewing), correct tool for this specific host.

**Confidence:** HIGH (VERIFIED) for the DNS zone host and current A record. HIGH (CITED, official Bitnami docs + AWS knowledge-center articles) for the bncert-tool-over-bare-certbot correction. MEDIUM (open item) on the exact incremental-domain re-run behavior.

---

## SHP-04 — systemd unit + Apache reverse proxy

### systemd unit pattern

```ini
# /etc/systemd/system/prodfin.service
[Unit]
Description=ProductionFinance FastAPI service
After=network.target

[Service]
Type=simple
User=prodfin
Group=prodfin
WorkingDirectory=/opt/prodfin
ExecStart=/opt/prodfin/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/prodfin/.env

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable prodfin.service   # survives reboot — required by SHP-04/D-23
sudo systemctl start prodfin.service
```
[CITED: general systemd + `uv`-managed-venv deployment pattern, cross-corroborated across multiple sources this session] — reference the venv's binaries by **absolute path** in `ExecStart` (never `source .venv/bin/activate` inside the unit — that pattern does not reliably work under systemd's non-login, non-interactive shell). Run as a dedicated **non-root** system user (`prodfin`), not `bitnami` or `root` — least-privilege is not explicitly required by any locked decision but is a standard, cheap hardening step worth doing while the unit is first being written (see Security Domain below).

**D-23 reminder (not new research, restating the locked decision):** the reboot test must be *executed*, not assumed — `sudo reboot`, wait, then confirm `systemctl status prodfin` shows active/running and `curl localhost:8000/health` responds, without any manual intervention.

### Bitnami Apache vhost pattern

[CITED: docs.bitnami.com/virtual-machine/infrastructure/lamp/configuration/configure-custom-application/, fetched via WebSearch this session]

```apache
# /opt/bitnami/apache[2]/conf/vhosts/prodfin-vhost.conf
# (exact directory name — "apache" vs "apache2" — is Bitnami-image-version-
#  dependent; confirm which exists on THIS box with `ls /opt/bitnami/ | grep apache`
#  before writing the final path into the plan or deploy script)

<VirtualHost *:80>
    ServerName prodfin.vockell.com

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
```
```bash
sudo /opt/bitnami/ctlscript.sh restart apache
```
`bncert-tool` (see SHP-03) will subsequently rewrite/add the `:443` `VirtualHost` block for this `ServerName` once the certificate is issued — do not hand-write the HTTPS vhost block first; let `bncert-tool` generate it against the working `:80` vhost.

**Open item, not resolved this session:** the exact vhost directory (`/opt/bitnami/apache/conf/vhosts/` vs `/opt/bitnami/apache2/conf/vhosts/`) is reported differently across different Bitnami doc pages and community articles found this session — this is a Bitnami-image-version detail that must be confirmed by listing the actual directory on the box (`ls -la /opt/bitnami/`) rather than assumed from documentation alone. Flag as a first-step verification inside the SHP-04 task, not a blocking unknown for planning purposes (the fix, once discovered, is a one-line path substitution).

**Forward-looking note (not this phase's scope, but worth planning around):** Phase 7 (Live Research) streams progress via SSE. A plain `ProxyPass`/`ProxyPassReverse` pair generally passes SSE through correctly over HTTP/1.1, but if buffering issues appear later, Apache's `mod_proxy` may need `SetEnv proxy-sendchunked 1` or a longer `ProxyTimeout` — not a Phase 1 concern, noted here only so Phase 1's vhost isn't written in a way that has to be torn up later.

**Confidence:** MEDIUM (CITED, official Bitnami docs) — the pattern is standard and well-documented; the one specific unknown (exact directory name on this box) is explicitly flagged rather than guessed.

---

## SHP-07 / SHP-09 / SHP-10 — CI compliance gates

All three are D-27's blocking GitHub Actions jobs, required-status-check, not report-only (D-26).

### `lockfile-scan` (SHP-07)

`uv` resolves dependencies into `uv.lock` (TOML). Two viable scanning approaches:
```bash
# Option A: export a flat list and grep it
uv export --no-hashes -o /tmp/requirements-frozen.txt
grep -Ei '^(openai|anthropic|langchain|langgraph|crewai|llama-index|litellm)([=<> ]|$)' /tmp/requirements-frozen.txt && exit 1

# Option B: parse uv.lock's [[package]] entries directly for name = "..." matches
```
[CITED: general `uv` lockfile-export behavior — the `uv export` subcommand and `uv.lock` TOML shape are documented `uv` features; the exact TOML field layout for a package's resolved extras was not independently confirmed against a real `uv.lock` sample this session, since Phase 1 does not yet add `google-adk`]

**Important nuance not explicit in D-27 as written:** the check "assert `google-adk` appears with no extras marker" is **vacuously about a package that will not exist in the lockfile in Phase 1** — `google-adk`/`google-genai`/`parallel-web` are Phase 5/7 dependencies (see Standard Stack above; SRC-04/SHP-05/SHP-06 map to those later phases in ROADMAP.md, not Phase 1). Write the CI check so it:
- **Passes cleanly when `google-adk` is absent from the lockfile** (true today).
- **Fails only if `google-adk` is present AND carries an extras marker** (`google-adk[all]`, `[extensions]`, `[test]`) — this becomes meaningful once Phase 5 adds it.
- A check hard-coded to assume `google-adk` is always present would either be a false failure today or, worse, silently never actually assert anything if written defensively in the wrong direction — be explicit about which of the two states ("absent" vs "present-bare") is passing.

### `commit-window` (SHP-09)

No well-fitting off-the-shelf GitHub Action was found this session for "reject any commit authored before date X" (searched the GitHub Marketplace via WebSearch — closest matches were generic commit-message-format checkers, not date-window checkers). Recommend a plain script step:
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0   # full history required — a shallow checkout can't see all commits
- name: Verify all commits are within the contest window
  run: |
    CUTOFF="2026-07-27"
    BAD=$(git log --all --pretty=format:"%ad|%H" --date=short | awk -F'|' -v cutoff="$CUTOFF" '$1 < cutoff {print $2}')
    if [ -n "$BAD" ]; then
      echo "Commit(s) authored before the contest window ($CUTOFF):"
      echo "$BAD"
      exit 1
    fi
```
[Reasoning from first-principles git plumbing, MEDIUM confidence sourcing since no existing tool was found and this is a custom script — the `git log --pretty --date=short` flag combination itself is standard, well-documented git behavior]. Existing repo history (10 commits, all dated 2026-08-23/24 per STATE.md) already satisfies this check — it exists to catch a *future* accidental import of pre-window history (e.g. a reused boilerplate repo), per PITFALLS.md §G6.

### `secret-scan` (SHP-10)

```yaml
- uses: gitleaks/gitleaks-action@v3
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    # GITLEAKS_LICENSE: only required for ORGANIZATION-owned repos, not personal accounts
```
[VERIFIED: github.com/gitleaks/gitleaks-action README, fetched directly this session] — quoted verbatim: *"If you are scanning repos that belong to a personal account, then no license key is required."* / *"If you are scanning repos that belong to an organization account, you will need to obtain a free license key."* **Confirm the repo will live under a personal GitHub account (not a GitHub organization) before assuming license-free operation** — if it turns out to be org-owned, a free license key is still obtainable, just an extra one-time signup step.

**GitHub-native push protection**, the other half of D-27's `secret-scan` requirement: [CITED: WebSearch of GitHub's 2026 changelog posts (github.blog/changelog), specific post URLs not independently re-fetched this session] as of 2026, GitHub secret scanning and push protection are **free and enabled by default for all public repositories** — this is a change from earlier years when it required manual enabling in repo Settings. This means D-27's "plus GitHub native push protection enabled" may already be true automatically the moment the repo goes public (D-25) — the remaining task is a **verification step** (check Settings → Code security → confirm "Push protection: Enabled"), not necessarily an active "turn it on" action. Recommend the plan keep this as an explicit checklist item regardless, since "should already be on" is not the same evidentiary bar as "confirmed on."

### Cross-cutting: source-tree grep (D-28, not a separate requirement ID but arms alongside SHP-07)

```bash
grep -rniE "textract|bedrock|comprehend|rekognition|transcribe|polly|kendra|sagemaker" --include="*.py" --include="*.toml" --include="*.yaml" --include="*.yml" . \
  && exit 1
# "translate" is deliberately excluded from the bare-word grep above (too common an
# English word — "Translate.md", a UI string, etc.) — match boto3-qualified call
# sites specifically instead:
grep -rniE "boto3.*\.client\(\s*['\"]translate['\"]" --include="*.py" . && exit 1
```
This is the same gate `.claude/CLAUDE.md` already specifies as the pre-submission check — D-28 just arms it in CI from day one instead of leaving it to a day-16 manual review.

**Confidence:** MEDIUM overall — the gitleaks-action license-free-for-personal-accounts claim is VERIFIED (direct README read); the push-protection-default-on-in-2026 claim is CITED (WebSearch summary of official changelog posts, not independently re-fetched); the commit-window and lockfile-scan scripts are original constructions based on standard, well-understood tool behavior rather than found off-the-shelf.

---

## SHP-08 — Licence detection in the GitHub About section

**Requirement, as stated:** "detectable in the GitHub About section, not merely a LICENSE file" — this is explicitly not satisfied by file-existence alone (PITFALLS.md §G3 already names this exact trap).

**File placement rules:** [CITED: docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-a-license-to-a-repository, docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository, via WebSearch this session]
- File must be named exactly `LICENSE` or `LICENSE.md`, **at the repository root** (not a subdirectory).
- GitHub uses **Licensee** (vendored from choosealicense.com) to detect the license — it works best against the **standard, unmodified** MIT template text. Adding extra preamble/boilerplate text to the file is a documented cause of detection failing even though the file exists (PITFALLS.md §G3's exact failure mode) — use the plain choosealicense.com MIT template verbatim, save any project-specific notes for the README instead.

**An automatable verification exists** — not just an eyeball check of the repo's About sidebar: [CITED: docs.github.com/en/rest/licenses/licenses, via WebSearch this session]
```bash
curl -s https://api.github.com/repos/<owner>/<repo>/license | jq -r '.license.spdx_id'
# expect: "MIT"
```
This REST endpoint "returns the contents of the repository's license file, if one is detected" and its `license.spdx_id` field reflects **GitHub's own Licensee detection result** (not merely file presence) — it works unauthenticated for public repos. Recommend adding this as a post-push verification step (either a manual pre-submission command, or a scheduled/delayed CI step, since Licensee's detection runs server-side after a push and may not be instantaneous) rather than relying solely on a human glancing at the repo's web page.

**Confidence:** MEDIUM (CITED, official GitHub docs summarized via WebSearch, not independently re-fetched with a raw request against the live API this session — recommend the executor run the `curl`/`jq` command above directly once the LICENSE file is pushed, as the real verification step).

---

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json` (not absent, explicitly enabled) — this section is required.

Phase 1 has no application test framework yet (no `pytest.ini`/`conftest.py` exists in the repo today — confirmed by directory listing this session). Its "tests" are a mix of (a) genuine `pytest`-parametrized fixture tests over the validation-pair YAMLs, and (b) infrastructure facts that can only be confirmed by directly probing the live host, which is not something a CI test suite can do (CI runs in GitHub's runners, not on the Lightsail box).

### Test framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 — no config file exists yet; Phase 1 is where it's introduced |
| Config file | none yet — Wave 0 creates `pyproject.toml`'s `[tool.pytest.ini_options]` or a plain `pytest.ini` |
| Quick run command | `uv run pytest tests/fixtures/ -x` (once fixtures exist) |
| Full suite command | `uv run pytest` |

### Phase Requirements → Evidence Map

| Req ID | Behavior | Evidence type | How it's actually checked | Automatable in CI? |
|--------|----------|---------------|----------------------------|---------------------|
| SRC-01 | NY cap answer has a primary-source URL + date checked | Document review | `.planning/SOURCE-TRUTH.md` entry exists, contains a URL, a date, and (per this research) the unresolved-conflict note if the AUP-document inconsistency isn't fully closed | No — human/agent document review, not a runtime test |
| SRC-02 | CT CSV headers confirmed | Document review | `.planning/SOURCE-TRUTH.md` entry records the exact header row (this research already has it verbatim — see SRC-02 above) | No |
| SRC-03 | 11 pairs committed as fixtures with source URL + disclosure stage | `pytest` parametrized test | `tests/test_validation_pair_fixtures.py::test_fixture_has_required_fields` parametrized over every file in `tests/fixtures/validation_pairs/`, asserting `source_url`, `disclosure_stage`, `status` are all present and non-empty. A **second** test should assert the *set* of committed fixtures matches an expected count/jurisdiction spread (catches the "zero CT pairs" gap from recurring silently) | Yes — this is a real, automatable pytest suite from day one |
| SRC-04 | Partner track resolved | Document review | Already `[x]` in REQUIREMENTS.md/STATE.md — no further test needed this phase | N/A — already complete |
| SRC-05 | GA rate confirmed | Document review | `.planning/SOURCE-TRUTH.md` entry (this research already has the full rate schedule verbatim — see SRC-05 above) | No |
| SHP-01 | Instance resized, static IP preserved | Live host probe | `curl -I https://vockell.com` returns 200 post-resize; `dig +short A vockell.com` still resolves to the same static IP | No — requires the live host; a human/agent runs this once, post-resize, not a CI job |
| SHP-02 | Python 3.10+, isolated | Live host probe | SSH in, run `/opt/prodfin/.venv/bin/python3 --version` (expect ≥3.10) and `python3 --version` (system, expect still 3.9.2, unchanged) | No — live host |
| SHP-03 | Subdomain resolves over TLS | Live + external probe | `curl -v https://prodfin.vockell.com/health` from a machine outside the Lightsail box, confirm valid cert chain (no `-k` needed) and a 200 response | No — live host, and ideally from a genuinely external network per PITFALLS.md §G4's "test cold, from a stranger's vantage point" discipline (this phase doesn't need the full anonymous-cold-browser test yet — that's SHP-13 in Phase 8 — but a basic external `curl` is a cheap Phase 1 sanity check) |
| SHP-04 | systemd-supervised, survives reboot, reverse-proxied | Live host probe | `systemctl is-enabled prodfin` (expect `enabled`), then the actual reboot test (D-23): `sudo reboot`, wait, `systemctl is-active prodfin` (expect `active`) with no manual restart | No — live host, and destructive (reboots the box), so this is a one-time verification step in the plan, not a repeatable CI check |
| SHP-07 | Lockfile clean, google-adk bare | CI job | `lockfile-scan` GitHub Actions job — genuinely automatable per-commit (see SHP-07 section above) | **Yes** |
| SHP-08 | Licence detectable in About | API check | `GET /repos/{owner}/{repo}/license` → `spdx_id == "MIT"` (see SHP-08 section above) | Yes, as a post-push step (not meaningfully checkable pre-push since Licensee runs server-side) |
| SHP-09 | Commits within contest window | CI job | `commit-window` GitHub Actions job (see above) | **Yes** |
| SHP-10 | No secret committed | CI job + platform feature | `secret-scan` GitHub Actions job (gitleaks) + GitHub native push protection (verify enabled, likely default-on) | **Yes** (gitleaks job) + platform-level (push protection acts at push time, outside the Actions run itself) |

### Sampling rate

- **Per commit:** `lockfile-scan`, `commit-window`, `secret-scan` — all three run on every push (D-26, required status checks).
- **Per fixture added:** the `test_validation_pair_fixtures.py` suite runs as part of the normal `pytest` job whenever fixtures change.
- **Once, at the end of Track B:** the live-host probes (SHP-01 through SHP-04) are inherently one-time manual/agent verification steps against the actual box — they cannot be part of the repeating CI suite because CI runners don't have SSH access to the Lightsail instance in this project's design (D-19 explicitly rules out CI push/deploy). Treat these as an explicit checklist in the plan's verification section, not as automated tests.
- **Phase gate:** all CI jobs green, all four live-host probes manually confirmed, before this phase is marked done.

### Wave 0 gaps

- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` (or `pytest.ini`) — none exists yet.
- [ ] `tests/fixtures/validation_pairs/` directory + `tests/test_validation_pair_fixtures.py` — the parametrized fixture-shape test, built from day one per D-01/D-03 (not retrofitted — this is also what SHP-14's Phase-3 CI suite will build on).
- [ ] `.github/workflows/ci.yml` — the three D-27 jobs, none exist yet.
- [ ] `sources/MANIFEST.yaml` — none exists yet, needed before the first archived source document.

---

## Open Questions & Risks

1. **D-14 — the subdomain name is still unconfirmed.** `prodfin.vockell.com` is explicitly a placeholder per CONTEXT.md, not a locked decision. This is the single item on the critical path with a propagation clock (D-21 puts DNS first) — **the plan must surface this as a blocking question to the user before the DNS task can execute**, not proceed on the assumption.
   - What we know: the name must live under the `vockell.com` zone (confirmed hosted at Register.com, not Route 53).
   - What's unclear: the exact subdomain label the user wants.
   - Recommendation: ask directly, one word, before Track B's first task fires.

2. **The NY $700M/$800M three-document inconsistency (SRC-01) is not fully closed.** Two ESD PDFs and the live esd.ny.gov page agree on $700M for the base program; a third, more recently dated ESD document (May 2026 AUP) states $800M using language that reads as the same base program. This needs the actual enacted budget bill text (FY2026, approved ~May 2025, or possibly a subsequent FY2027 action if one occurred by May 2026) to fully resolve per D2's precedence policy.
   - What we know: $700M (base) + $100M (new independent pool, $20M/$80M split) = $800M combined is well-corroborated by press coverage and is very likely the correct overall story.
   - What's unclear: why an official ESD document uses $800M for what reads as the base program alone — internal document imprecision, or a genuine further cap increase this session didn't find evidence of either way.
   - Recommendation: Track A searches `nysenate.gov`/`assembly.state.ny.us` for the actual budget bill text before finalizing `.planning/SOURCE-TRUTH.md`; if still unresolved, record per D-13 as an explicit unresolved-conflict entry rather than picking a number.

3. **Zero of the 11 pre-sourced validation pairs cover Connecticut**, the fourth curated jurisdiction. This is a scope gap in the existing source material, not something this research can resolve without picking a specific CT production — that selection is itself a Track A task not currently named in any locked decision. Recommend the plan add it explicitly (see SRC-03 above for the concrete recommendation).

4. **Four of the 11 pre-sourced pairs (MA×2, PA×2) cannot function as validation pairs** — no disclosed qualifying spend, and no curated jurisdiction rule file exists for either state in Milestone 1. Recommend `status: blocked` fixtures per D-06 (concrete blocker text proposed in SRC-03 above) rather than silently omitting them or forcing them into the active accuracy denominator.

5. **CA and NJ validation pairs were not independently re-verified this session** (time-boxed to demonstrating the pattern on NY, CT, and GA, which had the more contested/uncertain figures). Recommend Track A apply the same `curl` + `pdftotext`/direct-read pattern demonstrated in this research (see SRC-03) to the CA Film Commission approved-projects list and the two NJEDA activity report PDFs before treating those four pairs as `mode: exact`.

6. **DNS record creation at Register.com may be a purely manual step** — no public API was confirmed available for this specific account in this session's research. If the account owner has API access (Network Solutions/Web.com do offer some enterprise API products), that would allow scripting the record creation; otherwise this is a login-and-click task that only the account owner can perform, and should be scheduled with that in mind (not assumed to be agent-executable end-to-end).

7. **Exact Bitnami paths (`/opt/bitnami/apache/` vs `/opt/bitnami/apache2/`) and `bncert-tool`'s incremental-domain behavior** are not confirmed for this specific box — flagged as first-step, low-risk verification items inside the SHP-03/SHP-04 tasks (a five-second `ls` resolves the path question; the domain-list question is answered by reading `--help` or checking `/opt/bitnami/letsencrypt/` before the first `bncert-tool` run).

8. **Register.com/Network Solutions and Bitnami's exact current Apache version-path** were the two genuinely host-specific facts this research could not verify without SSH access to the actual Lightsail instance (this research environment has no AWS credentials or SSH access to the box). Everything else host-specific (DNS zone, static IP, package versions, CI mechanics) was verified from outside the box via public lookups and package registries.

---

## Sources

### Primary (HIGH confidence — directly tool-verified this session)
- `https://esd.ny.gov/sites/default/files/media/document/Film_Credit_Guidelines_W_Appendix_20250418_0.pdf` — read directly via `Read` tool (PDF extraction), 2026-08-24
- `https://esd.ny.gov/sites/default/files/media/document/Film-Prod-CPA-AUP-May2026.pdf` — read directly via `Read` tool, 2026-08-24
- `https://esd.ny.gov/sites/default/files/media/document/Q3-Film-Report-2025.pdf` — extracted via `pdftotext -layout`, 2026-08-24
- `https://data.ct.gov/api/v3/views/kjsu-mdny/export.csv?accessType=DOWNLOAD` — read directly via `curl`, 2026-08-24
- `https://dor.georgia.gov/film-tax-credits/film-tax-credit-resources` — read directly via `curl`, 2026-08-24
- `dig`/`whois` against `vockell.com` — run directly this session, 2026-08-24
- `pip index versions` for fastapi, pytest, pyyaml, ruff, uv, google-genai, google-adk, parallel-web — run directly this session, 2026-08-24
- `github.com/gitleaks/gitleaks-action` README — read directly via WebFetch, quoted verbatim, 2026-08-24

### Secondary (MEDIUM confidence — WebFetch/WebSearch of official sources, not raw-byte-verified)
- `https://www.esd.ny.gov/new-york-state-film-tax-credit-program-production` and `.../new-york-state-independent-film-production-tax-credit-program`
- `docs.aws.amazon.com/lightsail` (resize-from-snapshot, static IP handling)
- `docs.bitnami.com/virtual-machine/how-to/understand-bncert/` and `.../configure-custom-application/`
- `docs.astral.sh/uv`
- `docs.github.com/en/rest/licenses/licenses`, `docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-a-license-to-a-repository`
- GitHub secret-scanning/push-protection 2026 changelog posts (github.blog/changelog)

### Tertiary (LOW confidence — press/secondary corroboration only)
- Entertainment Partners, Hollywood Reporter, Wrapbook coverage of the NY FY2026 budget's film-credit changes (used only to corroborate the $700M+$100M=$800M combined-total explanation, not as the primary figure)

## Metadata

**Confidence breakdown:**
- SRC-01 (NY cap): MEDIUM-HIGH — base figure and indie-pool figures VERIFIED; one genuine unresolved document inconsistency flagged, not silently resolved
- SRC-02 (CT CSV): HIGH — VERIFIED via direct fetch
- SRC-03 (validation pairs): HIGH for 3 NY pairs (VERIFIED byte-for-byte); MEDIUM for 4 CA/NJ pairs (sourced, not re-verified); structural gaps (MA/PA unusable, zero CT) are certain findings, not confidence questions
- SRC-05 (GA rate): HIGH — VERIFIED via direct fetch, with one MEDIUM caveat on loan-out-specificity
- SHP-01 through SHP-04 (deploy path): HIGH for DNS zone host and TLS-tool correction (VERIFIED/CITED); MEDIUM for exact on-box paths not independently confirmable without host access
- SHP-07/08/09/10 (CI gates): MEDIUM-HIGH — mechanisms are well-documented and in several cases VERIFIED directly; two items (push-protection default-on, exact `uv.lock` TOML shape for extras) are CITED, not independently re-verified against a live example

**Research date:** 2026-08-24
**Valid until:** Track A source-truth entries should be treated as valid until the enacted-budget-bill cross-check is done (this research is not itself the final SOURCE-TRUTH.md entry); Track B deploy-path findings are valid for the life of this Bitnami image/AWS account configuration — re-verify if the Lightsail blueprint or Bitnami version changes.
