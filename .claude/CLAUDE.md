<!-- GSD:project-start source:PROJECT.md -->

## Project

**ProductionFinance**

A system that prices the same film production in every city a producer is considering, and reports the true landed cost of each — labour, housing, stages, equipment, travel, currency, and the production incentive net of audit fees, transfer discount, tax and timing. The headline output is the cost gap between two cities, decomposed into its components. A second mode runs the same engine on a fixed reference production, on a schedule, and publishes the result as a public index.

Primary user: a producer or line producer choosing where to shoot. Secondary: film commissions, unions, state economic development bodies and trade press — consumers of the published index.

**Core Value:** Total landed cost of one identical production, priced per city, with every figure sourced, dated, and provably matching what a government actually paid.

### Constraints

- **Deadline**: Hackathon submission 2026-09-09, 14:00 PDT — 17 days from project start (2026-08-23). Both milestones must land inside it. Hard.
- **Partner track**: Parallel. Parallel's Search API must be called at runtime, via the official SDK or a supported integration.
- **AI services**: Google Cloud only, plus Parallel. No other AI models, agent frameworks or AI APIs — explicitly including AWS, Microsoft, OpenAI and Anthropic tools.
- **Language**: Google Cloud SDK must be imported and called at runtime. Accepted packages are `google-adk`, `google-genai`, `google-generativeai`, `google-cloud-aiplatform` — PyPI names, and eligibility screening is partly automated, so the agent and backend must be Python. Front-end language is unconstrained.
- **Deployment**: Must run on web. A hosted URL is required and must work for an anonymous visitor.
- **Licensing**: Public repository with an OSI-approved license detectable in the repository About section.
- **Provenance**: New code only, authored within the contest window (opened 2026-07-27). No extending prior work.
- **Hosting / infrastructure**: Co-hosted on the existing **vockell.com** Lightsail instance (`vockell_dot_com_LAMP`, AWS profile `newaccount`, us-west-2, static IP 35.165.60.123, key `LightsailDefaultKeyPair` = `~/Downloads/LightsailDefaultKey-us-west-2.pem`, SSH user `bitnami`). AWS may be used for any infrastructure resource needed. Permitted because the hackathon restricts AI services only; non-AI third-party services (hosting, databases, web frameworks, storage, schedulers) are explicitly unrestricted. **Do not provision new cloud resources without explicit per-resource approval.**
- **Host preparation required before deploy** (measured on the live box 2026-08-24): it is a Bitnami LAMP blueprint on Debian bullseye with **472 MB RAM (95 MB already in swap at idle), 1 vCPU, 20 GB disk (14 GB free), and Python 3.9.2**. Two blockers: (a) `google-adk` 2.7.1 and `google-genai` 2.19.0 both require Python >=3.10, so a modern Python must be installed via `uv` or pyenv; (b) 472 MB cannot hold FastAPI + the Google SDK import footprint + a database alongside the existing Apache and MySQL — **DECIDED: resize the instance to `small_3_0` (2 GB, 2 vCPU) via snapshot-and-restore**, which preserves the static IP so no DNS propagation is required. Apache retains ports 80/443, so ProductionFinance is reverse-proxied to uvicorn on a subdomain; that subdomain's DNS record is the one item carrying propagation delay and must be created early.
- **No AWS AI services — absolute**: Every AWS AI service is a Stage One disqualification. **AWS Textract is the specific trap on this project**: it parses government PDFs, which is exactly what the validation ingest does, so it is the most likely accidental violation. All PDF and document extraction must go through Gemini via a permitted Google package. Also forbidden: Bedrock (including Anthropic models hosted there), SageMaker, Comprehend, Rekognition, Transcribe, Polly, Translate, Kendra, Amazon Q. `boto3` itself is fine — what matters is which endpoints are called.
- **Honesty**: The repo is public and inspectable. Never fake progress; a `sleep()` behind a progress bar is a Stage One death. Never present a researched figure as validated.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## READ THIS FIRST — the AI-vendor line

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `google-genai` | **2.19.0** (PyPI, released 2026-08-19) | Gemini calls for structured extraction (Job 1: parse award PDFs into production/award pairs; Job 2: normalize live-researched incentive rules into a common schema) | Satisfies the mandated-import constraint directly. Both jobs in this project are **fixed-sequence pipelines** (search → extract → normalize → compute), not autonomous tool-selecting agents — the product doc itself says "delete the agent, what's left: a good calculator" and names the two jobs as deterministic steps. `google-genai` gives direct, debuggable control over each call with structured JSON output (`response_json_schema`), which is what a reproduce-exactly validation loop needs. `google-adk`'s value-add (multi-agent orchestration, session/runner abstraction, autonomous tool loops, one-command deploy to Vertex AI Agent Engine) solves a problem this project doesn't have, and adds a framework to learn inside a 17-day window. See "The ADK/genai/aiplatform decision" below — this is not hedged. |
| `parallel-web` | **≥1.0.1** (official Python SDK; import as `from parallel import Parallel`) | Search API calls for live jurisdiction research (Job 2) and for locating government disclosure documents (Job 1 source discovery) | This is the partner-track requirement. Official SDK, Python 3.9+, sync and async clients over `httpx`. See "Parallel Search API" section below for exact call signature. |
| FastAPI | **0.141.1** (PyPI, 2026-07-29) | Python backend: pricing engine API, jurisdiction rule endpoints, agent job endpoints | Async-native, Pydantic-integrated request/response models map directly onto "normalized jurisdiction rule models" and "every figure carries source + date + confidence tier" — those become typed Pydantic fields, not ad-hoc dicts. Auto-generated OpenAPI docs are a free credibility signal for a judge poking at the API. Fastest Python framework to stand up a working endpoint in hours, not days. |
| React 19 + Vite 8 + TypeScript 5.9 | React 19.x / **Vite 8.0.9** (2026-04-20) / TS 5.9+ | Frontend SPA: map, slider, ranked list, source-click panels | Frontend language is unconstrained; React+Vite is chosen for raw build velocity — HMR, huge component ecosystem, and every AI coding assistant (including this one) has the deepest training data on it, which matters when 17 days includes zero slack for framework-learning time. Vite's dev server + `vite build` produces a static bundle the Python backend can serve directly (see Hosting), avoiding a second server process. |
| MapLibre GL JS | **6.5.0** (npm, current) | The hero map — 10-20 cities as markers, colored/sized by total net cost, live-updating on slider drag | Compared against deck.gl and D3/react-simple-maps below. MapLibre wins for this exact spec: a real interactive basemap (pan/zoom, professional look — this is a Design-judged criterion) with GeoJSON circle layers whose color/radius are driven by a `interpolate` style expression against a numeric property. Updating that GeoJSON source on slider change re-renders instantly with no re-mount — exactly the "one slider reorders everything live" requirement. No API key, no vendor account needed (see basemap tiles below), so there's zero signup friction inside the 17-day window. |
| OpenFreeMap tiles | n/a (hosted service) | Free vector basemap tiles for MapLibre | No API key, no rate limit, no signup, open-source (BSD/ODbL data). Point at `https://tiles.openfreemap.org/styles/liberty` as the MapLibre `style` URL and you have a full basemap in one line. This removes the one setup step (get a Mapbox/MapTiler API key) that would otherwise cost real minutes. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic v2 | ships with FastAPI 0.141.1 (installs `pydantic>=2`) | Jurisdiction rule model schemas, validation-pair fixtures, Gemini structured-output schemas | Use `model_json_schema()` directly as the `response_json_schema` passed to `google-genai` — one schema definition serves both the API contract and the LLM extraction contract. This is the single best trick for keeping Job 1/Job 2 outputs typed and auditable. |
| `decimal.Decimal` (stdlib) + a small in-repo `Money` dataclass | stdlib | All monetary arithmetic, all six currencies (USD, GBP, CAD, EUR, CZK, HUF) | See "Money and dates" section — do **not** add `py-moneyed` as a dependency (see What NOT to Use). |
| `httpx` | pulled in transitively by `parallel-web` and usable directly | Calling the Frankfurter FX API and any other plain HTTP fetch (GSA per diem CSV, State Dept per diem, government pages not covered by Parallel) | Already a dependency via Parallel's SDK; reuse it rather than adding `requests`. |
| `pyyaml` | latest (6.x) | Reading/writing the versioned YAML jurisdiction rule files and validation-pair fixtures (see Data layer) | Core to the "repo as audit trail" data strategy. |
| Gunicorn + `uvicorn.workers.UvicornWorker` | latest | Production process manager for FastAPI on the Lightsail instance | Never run `uvicorn` alone in production — no worker recycling, no graceful multi-process handling under load. Gunicorn supervises N uvicorn workers. |
| Caddy | latest (2.x) | Reverse proxy + automatic TLS on the Lightsail instance | See Hosting — replaces nginx+certbot with a single-file config that gets you HTTPS with zero manual certificate handling. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest **9.1.1** (PyPI, 2026-06-19) | Test framework, all Python tests including the golden validation-pair loop | See Testing section for the parametrized-fixture pattern. |
| Docker + Docker Compose | Packaging the FastAPI app (+ built frontend) for deployment to Lightsail | One `docker compose up -d` on the instance; identical image can be rebuilt locally, removing "works on my machine" risk 17 days before a demo. |
| `ruff` | Lint/format | Fast, single binary, zero-config-friendly — do not spend hackathon time on flake8+black+isort config. |

## The ADK / genai / aiplatform decision — resolved, not hedged

- **`google-generativeai` is dead.** Confirmed via the official GitHub archive notice: *"All support for this repository ended permanently on November 30, 2025."* It has no access to current models/features and receiving zero fixes. Do not use it, do not let a stale tutorial talk you into it. (Source: [github.com/google-gemini/deprecated-generative-ai-python](https://github.com/google-gemini/deprecated-generative-ai-python), HIGH confidence — official deprecation notice.)
- **`google-genai` is the GA, recommended, unified SDK** for the Gemini API across both the Gemini Developer API (API-key auth, fastest to start) and Vertex AI (ADC/service-account auth, enterprise/quota path) — same client class, a `vertexai=True` flag switches backend. Official docs state it reached General Availability May 2025 and is "the recommended libraries to access the Gemini API." (Source: [ai.google.dev/gemini-api/docs/libraries](https://ai.google.dev/gemini-api/docs/libraries), HIGH confidence.) Current version **2.19.0**, released 2026-08-19 (source: PyPI project page, HIGH confidence).
- **`google-adk` (Agent Development Kit) is the intended path for autonomous, multi-agent "Agent Builder"-style systems**, and it is genuinely the right tool when you need tool-selecting loops, sub-agent delegation, session/memory management, and a one-command path to deploy onto **Vertex AI Agent Engine** (the managed runtime). ADK is the build-time framework; Agent Engine is the production runtime they deploy to — "you build agents with ADK, then deploy them to Vertex AI Agent Engine with a single command." Current version **2.7.1**, released 2026-08-17 (source: PyPI project page). This project does not need that: Job 1 and Job 2 are named, fixed pipelines in the product spec, not open-ended agents deciding their own next tool call. Adopting ADK here would mean spending scarce build-time on session/runner scaffolding that buys nothing — the two agent jobs are two or three sequential function calls each (search → extract → normalize/compute), which is exactly what direct `google-genai` calls inside plain Python functions express with less code and more debuggability.
- **`google-cloud-aiplatform`** is the older, broader Vertex AI SDK (training, pipelines, feature store, the pre-unification generative interface). It is not deprecated, but for generative calls specifically it has been superseded by `google-genai`'s Vertex-mode client — using it here would mean carrying two ways to call Gemini for no benefit. Not recommended as the primary import; `google-genai` already satisfies the constraint and is the more current API surface.

## Parallel Search API — concrete enough to write code from

- **Extract API** — turns a specific URL (found via Search) into clean markdown, including PDFs and JS-rendered pages, up to 20 URLs per call. Use this to pull the full text of a specific government PDF (e.g. the NY ESD quarterly report) once Search has located its URL, before handing that text to `google-genai` for structured extraction.
- **Task API** — multi-hop, minutes-scale research producing cited structured output (`result.output.basis`), with processor tiers from `lite` to `ultra8x`. This is the closer fit if a single jurisdiction's rule normalization genuinely requires several rounds of "find X, then check Y implied by X" — worth prototyping Job 2 against Task API directly if Search+Extract+genai proves too manual, but start with the simpler Search+Extract+genai pipeline given the time budget.
- **MCP server** exists (`Parallel Task MCP Server`), but it targets MCP-client agent workflows (e.g. Claude Desktop, Cursor). Not relevant to this project's runtime — the requirement is calling the *SDK* at runtime from the Python backend, not wiring an MCP client into the product itself.

## Frontend + map — comparison and recommendation

| Option | Verdict for this project | Why |
|--------|---------------------------|-----|
| **MapLibre GL JS 6.5.0** (recommended) | ✅ Use this | Real interactive basemap, GPU-accelerated, data-driven styling (`interpolate` expressions for color-by-cost), instant re-render on GeoJSON source update — exactly the slider-reorders-live requirement. Free basemap via OpenFreeMap, zero signup. Open-source (BSD), no vendor lock-in, and explicitly not an AI service so raises zero eligibility questions. |
| deck.gl | ❌ Overkill | Built for large-scale WebGL data viz (thousands to millions of points, 3D layers, GPU aggregation). At 10-20 city markers this buys nothing over MapLibre's native circle/symbol layers and adds a second rendering framework (deck.gl is usually paired *on top of* MapLibre anyway) plus a steeper learning curve — pure risk for a 17-day build with no visual payoff at this data scale. |
| D3 / react-simple-maps (SVG projection) | ⚠️ Viable fallback, not preferred | Genuinely fine for a point map at this scale and arguably the fastest to get *a* map on screen (no tile loading, no WebGL context). The tradeoff: you lose the "real interactive map" feel (pan/zoom, familiar basemap texture) that scores on the Design judging criterion, and you own more projection/rendering code yourself. Fall back to this only if MapLibre's tile loading or styling proves to eat unexpected build time — it's a same-day pivot, not a dead end, since the underlying city-coordinate + color-scale data model is identical either way. |

## Hosting — AWS Lightsail instance (revised recommendation)

| Option | Time to public URL | Notes |
|--------|--------------------|-------|
| **AWS Lightsail instance (recommended)** | Fast — instance and static IP already exist; remaining work is app deploy + TLS, roughly 30-60 minutes | No new account, no new billing setup, no cold starts (unlike Cloud Run's scale-to-zero, which can add multi-second latency to the *first* request an anonymous visitor makes right when a judge is testing it — a real risk for a hackathon demo). Full control over the box; a static IP is either already attached or a one-click Lightsail action. |
| Lightsail **container service** (not the same product) | Fast, automatic HTTPS on a Lightsail-managed subdomain with zero cert setup | Only relevant if the owner's existing resource is this product rather than a VM instance — confirm which one exists before planning around it. If it is a container service, this is actually *faster* than the VM path (HTTPS is automatic, no nginx/Caddy step at all) and should be preferred. |
| Google Cloud Run | Fast from zero (`gcloud run deploy --source .` → public HTTPS URL in one command) | No longer the default recommendation now that a paid-for Lightsail instance exists — would mean standing up a second billing account/project purely for hosting when the constraint explicitly frees hosting from the Google-only rule. Still a reasonable fallback if the Lightsail instance turns out to be undersized or misconfigured. |
| Firebase Hosting + Cloud Run | Slower | Adds a second platform (Firebase project, hosting rewrites config) for no benefit over a single Cloud Run service serving both API and static frontend — never the right choice for this project's scope. |
| App Engine | Slower, more config surface (`app.yaml`, service structure) than Cloud Run for a plain container | Legacy relative to Cloud Run for this use case. Not recommended. |

### Minimal deploy path — AWS Lightsail instance

### AWS resources worth using for non-AI infrastructure

- **S3** — good fit for archiving cached government PDFs (immutable source-of-truth copies for the audit trail: "we extracted this figure from *this exact byte-identical document* on this date") and for periodic index snapshots once Milestone 2 exists. Not needed for Milestone 1's core data (see Data layer — that lives in the repo).
- **A cron job on the instance itself** (plain `cron` or a `systemd` timer) is sufficient for the scheduled reference-production re-run in Milestone 2; EventBridge is unnecessary added complexity for a single scheduled job on a box you already control. Reach for EventBridge only if the schedule needs to survive the instance being rebuilt, which is unlikely to matter inside the hackathon window.
- **Secrets:** plain `.env` file on the instance (excluded from the Docker build context, mounted at runtime) is adequate for a hackathon; Secrets Manager is legitimate but adds AWS IAM setup time for no functional gain at this scale.
- **RDS/Aurora:** not recommended — see Data layer, the volume doesn't justify a managed database, and Postgres-on-Lightsail-instance-via-Docker is available if a real database ever becomes necessary (unlikely for Milestone 1).

### Forbidden dependencies — read before writing any extraction code

- **AWS Textract** — the specific trap for *this* project. Parsing NY ESD quarterly PDFs, NJEDA reports, and film office rule pages is exactly Textract's use case, which is exactly why it must not be used. **All PDF/document extraction goes through Parallel's Extract API (get clean text/markdown) followed by `google-genai` structured extraction (turn that text into typed fields).** That pipeline is both compliant and, per the product doc's own reasoning, the right tool for genuine "reasoning about what a document says," which OCR alone doesn't do anyway.
- **Bedrock** (any model behind it, including third-party models Bedrock hosts), **SageMaker**, **Comprehend**, **Rekognition**, **Transcribe**, **Polly**, **Translate**, **Kendra**, **Amazon Q** (in any product it's embedded in) — forbidden by name, no exceptions.
- **Borderline cases, assessed:**
- **`boto3` itself is fine.** It's a plain AWS SDK — a generic RPC client. What's restricted is *which endpoint* you call through it. Using `boto3` to `put_object` into S3 or read a Secrets Manager value is unrestricted; using `boto3` to call `textract.analyze_document` or `bedrock-runtime.invoke_model` is not.
- **Forbidden Python packages** (would fail screening on their own, or indicate a disallowed vendor call is coming): `openai`, `anthropic`, `langchain*` (any langchain-\* package, including `langchain-google-genai` — it's a LangChain integration, not the official Google SDK, and the constraint names agent frameworks as restricted, not just model vendors), `llama-index`, `crewai`, `boto3` calls to any AI endpoint (see above — the package is fine, specific calls are not).
- **Pre-submission check:** before packaging the repo, run `pip freeze` (or inspect the lockfile) inside the actual deploy container and grep for the forbidden package names above, then separately `grep -rn` the source tree for `textract`, `bedrock`, `comprehend`, `rekognition`, `transcribe`, `polly`, `translate`, `kendra`, `sagemaker`, `openai`, `anthropic`, `langchain`, `llama_index`, `crewai`. A clean grep plus a clean lockfile is the concrete gate — don't rely on memory of what got added over 17 days.

## Data layer

| Data | Storage | Why |
|------|---------|-----|
| Curated jurisdiction rule models (NY, CA, NJ, CT) | YAML files in the repo, one file per jurisdiction | Tens of jurisdictions at most — this is not a scale problem, it's a provenance problem, and the project brief says provenance *is* the product ("the repo is public and inspectable"). A YAML file's git history **is** the audit trail for free: `git log --follow ny.yaml` shows exactly when a rate changed, by whom, in what commit, with what commit message as the reasoning. A database gives you none of that without building a separate audit-log table — which is strictly more work than the free version control already provides. |
| Validation pairs (production → qualified spend → credit issued, with source URL) | YAML/JSON fixtures in the repo, structured for direct pytest parametrization | Doubles as both the data and the test fixtures — see Testing section. One file per pair or one file per jurisdiction, human-readable and reviewable in a PR diff. |
| Per-figure metadata (source URL, date-checked, confidence tier) | Fields inside the same YAML records, not a separate table | Keeps "every figure is cited" structurally true rather than aspirational — the citation lives next to the number in the same file, not joined from elsewhere. |
| Live-research cache (uncurated cities researched on demand, FX rates, cap-consumption lookups) | SQLite, single file (e.g. `cache.db`), inside the container/instance filesystem | This data is explicitly *not* meant to be part of the public audit trail (it's ephemeral, refreshed per the tiered-refresh table), so it doesn't belong in git. SQLite needs zero provisioning, ships as one file, and Python's stdlib `sqlite3` needs no new dependency. A key-value or simple table schema (`cache_key`, `payload_json`, `fetched_at`) is more than sufficient at this volume. |

- **Postgres/Cloud SQL/RDS** — provisioning and networking (connection strings, security groups/VPC, credential management) is real setup time this project doesn't need to spend for tens of rows of curated data and a cache. Reach for this only if Milestone 2's scheduled index run needs concurrent multi-writer access, which it doesn't at this scale.
- **Firestore** — adds a GCP NoSQL SDK and its document-model mental overhead for data that is naturally tabular/structured (a jurisdiction rule with nested tiers is exactly what a typed Pydantic model over YAML represents cleanly). No advantage over flat files here, and it would be one more thing to explain in the "technologies used" write-up without a real technical reason for being there.

## Money and dates

## Testing

# tests/fixtures/validation_pairs/ny_anora.yaml

# tests/test_validation_pairs.py

## Installation

# Python backend

# Python dev/test

# Frontend

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `google-genai` | `google-adk` | If the product later grows genuinely autonomous multi-step research (the agent deciding its own next tool call rather than following a fixed pipeline), or if deployment specifically needs Vertex AI Agent Engine's managed runtime/session/memory features. Not this project, not in 17 days. |
| MapLibre GL JS | deck.gl | If the city set grows to hundreds/thousands of points, or 3D/aggregated visualization becomes a requirement (neither applies at "tens of jurisdictions"). |
| MapLibre GL JS | D3 / react-simple-maps | If MapLibre's tile-loading or WebGL setup unexpectedly eats build time — same-day pivot, not a redesign, since the city+cost data model doesn't change. |
| AWS Lightsail instance | Google Cloud Run | If the existing Lightsail instance turns out undersized, or cold-start-free serving genuinely can't be achieved there for some reason — Cloud Run remains a clean one-command fallback. |
| YAML-in-repo + SQLite cache | Postgres/Cloud SQL | If Milestone 2 needs concurrent multi-writer access to the scheduled index data — unlikely inside this scope. |
| In-repo `Money` dataclass | `stockholm` | If arithmetic needs grow past simple same-currency add/subtract and one FX conversion (e.g. correct-remainder splitting/allocation) — actively maintained, `Decimal`-backed. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `google-generativeai` | Dead — all support ended 2025-11-30, no new features since Gemini 2.0 launched the unified SDK | `google-genai` |
| `google-adk` as the *primary* Google SDK for this project | Solves an autonomous-multi-agent problem this project doesn't have; costs build-time this project doesn't have | `google-genai` direct calls |
| AWS Textract (or any AWS AI/ML-inference endpoint) | Stage One disqualification — AI services restricted to Google Cloud + Parallel only | Parallel Extract API → `google-genai` structured extraction |
| `py-moneyed` | Unmaintained since Nov 2022; adds dependency-graph risk in a public, judged repo for functionality a 20-line dataclass covers | Stdlib `decimal.Decimal` + in-repo `Money` dataclass |
| Postgres/Cloud SQL/RDS/Firestore for the curated rule data | Provisioning/auth overhead with zero benefit at tens-of-rows scale; destroys the free git-history audit trail that flat files give you | Versioned YAML in the repo |
| Snapshot testing (`syrupy`, `pytest-golden`) for validation pairs | Wrong tool — the correct answer is a known, sourced government figure, not "whatever the code currently produces, approved once" | Parametrized pytest fixtures with explicit expected-value assertions |
| `langchain-google-genai` or any `langchain-*` package | It's a LangChain integration wrapper, not the official Google SDK — the constraint restricts agent frameworks generally, and this package name alone is a red flag to automated screening even though it transitively imports an allowed package | Call `google-genai` directly |
| Redux/Zustand for frontend state | Single-screen app with a handful of pieces of state (selected date, ranked list, selected city pair, open source-panel) — added abstraction with no payoff | React `useState`/`useReducer` |
| nginx + certbot on the Lightsail instance | Works, but costs 40-60 minutes of manual cert/renewal-cron setup that Caddy eliminates | Caddy (automatic Let's Encrypt TLS, single-file config) |

## Stack Patterns by Variant

- Skip Caddy/nginx entirely — Lightsail container services provision HTTPS automatically on a Lightsail-managed subdomain.
- Because there is genuinely nothing to configure for TLS in that product; the VM-instance deploy path above only applies to a plain instance.
- Prototype the same jurisdiction lookup against Parallel's **Task API** directly, using its cited structured output.
- Because Task API is built exactly for "multi-hop research producing structured, cited output" and may collapse three manual steps into one call — worth a 30-minute spike before committing to the manual pipeline for Job 2 specifically (Job 1's PDF-parsing use case is a better fit for the simpler Search/Extract + `google-genai` path regardless, since the document is already known).
- Use the Lightsail instance's static IP directly for the hackathon submission URL; add a domain only if time permits.
- Because Caddy can still terminate TLS for an IP-only setup using a self-signed or Lightsail-provided certificate path, but the simplest robust option under time pressure is a real (even free, e.g. a subdomain from a service you already control) domain name — DNS propagation is the one step here with a wait time outside your control, so do it early, not on day 16.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `google-genai==2.19.0` | Python 3.9+ | No known conflicts with FastAPI/Pydantic v2 — both use standard `pydantic.BaseModel`, and `model_json_schema()` output is what `google-genai`'s `response_json_schema` expects directly. |
| `parallel-web>=1.0.1` | Python 3.9+, `httpx` | Reuse the `httpx` dependency it pulls in rather than adding `requests` for the Frankfurter FX calls. |
| MapLibre GL JS 6.5.0 | Requires WebGL2 (mandatory as of v6.0.0, released 2026-07-22) and is ESM-only | Verify the demo machine/browser supports WebGL2 (any current Chrome/Firefox/Safari does) — not a concern for a judged web demo, but worth knowing if testing on an unusual environment. |
| Vite 8 | Node 20+ | Standard current LTS Node; not a concern for a fresh setup. |

## Sources

- [pypi.org/project/google-genai](https://pypi.org/project/google-genai/) — version 2.19.0, release date 2026-08-19 (HIGH — official package index)
- [pypi.org/project/google-adk](https://pypi.org/project/google-adk/) — version 2.7.1, release date 2026-08-17, Vertex AI Agent Engine relationship (HIGH — official package index)
- [github.com/google-gemini/deprecated-generative-ai-python](https://github.com/google-gemini/deprecated-generative-ai-python) — end-of-support date 2025-11-30 for `google-generativeai` (HIGH — official deprecation notice)
- [ai.google.dev/gemini-api/docs/libraries](https://ai.google.dev/gemini-api/docs/libraries) — `google-genai` as recommended GA SDK (HIGH — official docs)
- [github.com/googleapis/python-genai](https://github.com/googleapis/python-genai) README — verified canonical `client.models.generate_content` / `response_json_schema` usage pattern (HIGH — official SDK source; caught and discarded a fabricated alternative API surface returned by a first-pass doc-summary fetch)
- [pypi.org/project/parallel-web](https://pypi.org/project/parallel-web/) and [github.com/parallel-web/parallel-sdk-python](https://github.com/parallel-web/parallel-sdk-python) — official Python SDK, install/import pattern (HIGH)
- [docs.parallel.ai/getting-started/overview](https://docs.parallel.ai/getting-started/overview) and [docs.parallel.ai/getting-started/pricing](https://docs.parallel.ai/getting-started/pricing) — Search/Extract/Task product distinctions, call signature, pricing (MEDIUM on exact pricing figures — inconsistent across fetches, verify live before cost-sensitive code)
- [parallel.ai/blog/parallel-task-mcp-server](https://parallel.ai/blog/parallel-task-mcp-server) — Task MCP server exists, targets MCP-client workflows not backend SDK usage (MEDIUM)
- [pypi.org/project/fastapi](https://pypi.org/project/fastapi/) — version 0.141.1, release date 2026-07-29 (HIGH)
- [pypi.org/project/pytest](https://pypi.org/project/pytest/) — version 9.1.1, release date 2026-06-19 (HIGH)
- npm `maplibre-gl` package / [github.com/maplibre/maplibre-gl-js releases](https://github.com/maplibre/maplibre-gl-js/releases) — version 6.5.0, v6.0.0 WebGL2/ESM-only change noted 2026-07-22 (HIGH)
- [openfreemap.org](https://openfreemap.org/) and [github.com/hyperknot/openfreemap](https://github.com/hyperknot/openfreemap) — free, no-key vector tiles for MapLibre (HIGH)
- [vite.dev/releases](https://vite.dev/releases) — Vite 8.0.9, release date 2026-04-20 (HIGH)
- [frankfurter.dev](https://frankfurter.dev/) — no-key FX API, endpoint pattern, rate-limit policy, currency coverage (HIGH on endpoint/key claims, MEDIUM on exact currency-count framing)
- Snyk package health / PyPI release history for `py-moneyed` — last release November 2022, effectively unmaintained (MEDIUM-HIGH)
- [github.com/kalaspuff/stockholm](https://github.com/kalaspuff/stockholm) — actively maintained `Decimal`-backed money library, noted as fallback alternative (MEDIUM)
- AWS Lightsail official docs (`docs.aws.amazon.com/lightsail/...`) — static IP requirement, container-service automatic HTTPS vs instance manual Let's Encrypt/Certbot setup, load balancer TLS option (HIGH — official AWS docs)
- General search corroboration on AWS Textract's document-extraction use case and Bedrock/SageMaker/Comprehend/etc. as AI-inference services — treated as HIGH confidence based on well-established, non-controversial product categorization rather than any single source

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
