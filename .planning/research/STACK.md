# Stack Research

**Domain:** Python-backend web system pricing film production landed cost + incentive net across cities, with live agentic research over unstructured government sources (hackathon, hard vendor/hosting constraints, 17-day deadline)
**Researched:** 2026-08-23
**Confidence:** HIGH on constrained-package resolution and hosting; MEDIUM on Parallel pricing figures (docs page renders inconsistently across fetches — verify exact numbers at `docs.parallel.ai/getting-started/pricing` before writing any cost-sensitive code); HIGH on everything else.

---

## READ THIS FIRST — the AI-vendor line

Two things can fail Stage One automatically: (1) not calling one of the four accepted Google packages at runtime, (2) calling *any* AI-backed AWS service anywhere in the stack, even transitively. The project owner has confirmed an **AWS Lightsail instance** is available and AWS is fair game for **non-AI** infrastructure (hosting, storage, cron, secrets). This changes the hosting recommendation from the original Google-only framing but does **not** loosen the AI-vendor rule at all. See "Forbidden dependencies" below before writing any PDF-parsing or extraction code — Textract is the single most likely accidental disqualification in this specific project, because it is the obvious tool for parsing NY ESD PDFs and it is exactly the wrong one.

---

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

---

## The ADK / genai / aiplatform decision — resolved, not hedged

**Use `google-genai`. Do not use `google-adk` as the primary SDK for this project.**

- **`google-generativeai` is dead.** Confirmed via the official GitHub archive notice: *"All support for this repository ended permanently on November 30, 2025."* It has no access to current models/features and receiving zero fixes. Do not use it, do not let a stale tutorial talk you into it. (Source: [github.com/google-gemini/deprecated-generative-ai-python](https://github.com/google-gemini/deprecated-generative-ai-python), HIGH confidence — official deprecation notice.)
- **`google-genai` is the GA, recommended, unified SDK** for the Gemini API across both the Gemini Developer API (API-key auth, fastest to start) and Vertex AI (ADC/service-account auth, enterprise/quota path) — same client class, a `vertexai=True` flag switches backend. Official docs state it reached General Availability May 2025 and is "the recommended libraries to access the Gemini API." (Source: [ai.google.dev/gemini-api/docs/libraries](https://ai.google.dev/gemini-api/docs/libraries), HIGH confidence.) Current version **2.19.0**, released 2026-08-19 (source: PyPI project page, HIGH confidence).
- **`google-adk` (Agent Development Kit) is the intended path for autonomous, multi-agent "Agent Builder"-style systems**, and it is genuinely the right tool when you need tool-selecting loops, sub-agent delegation, session/memory management, and a one-command path to deploy onto **Vertex AI Agent Engine** (the managed runtime). ADK is the build-time framework; Agent Engine is the production runtime they deploy to — "you build agents with ADK, then deploy them to Vertex AI Agent Engine with a single command." Current version **2.7.1**, released 2026-08-17 (source: PyPI project page). This project does not need that: Job 1 and Job 2 are named, fixed pipelines in the product spec, not open-ended agents deciding their own next tool call. Adopting ADK here would mean spending scarce build-time on session/runner scaffolding that buys nothing — the two agent jobs are two or three sequential function calls each (search → extract → normalize/compute), which is exactly what direct `google-genai` calls inside plain Python functions express with less code and more debuggability.
- **`google-cloud-aiplatform`** is the older, broader Vertex AI SDK (training, pipelines, feature store, the pre-unification generative interface). It is not deprecated, but for generative calls specifically it has been superseded by `google-genai`'s Vertex-mode client — using it here would mean carrying two ways to call Gemini for no benefit. Not recommended as the primary import; `google-genai` already satisfies the constraint and is the more current API surface.

**Verified canonical usage pattern** (confirmed against the official SDK README, not paraphrased documentation — a first fetch attempt against a doc-summarization page returned a fabricated `client.interactions.create()` method that does not exist in the SDK; cross-checked directly against `github.com/googleapis/python-genai` README, HIGH confidence):

```python
from google import genai
from google.genai import types
from pydantic import BaseModel

class IncentiveRule(BaseModel):
    jurisdiction: str
    base_definition: str          # e.g. "total local spend", "labour only", "lesser of 80% core spend or local spend"
    headline_rate: float
    payout_mechanism: str         # refundable | transferable | rebate | nonrefundable
    per_project_cap: float | None
    annual_program_cap: float | None
    effective_date: str
    source_url: str

client = genai.Client(api_key="...")  # or genai.Client(vertexai=True, project=..., location=...) for Vertex-mode

response = client.models.generate_content(
    model="gemini-2.5-flash",  # check ai.google.dev/gemini-api/docs/models for current model IDs at build time
    contents=f"Extract the incentive rule structure from this text:\n\n{search_result_text}",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=IncentiveRule.model_json_schema(),
    ),
)
rule = IncentiveRule.model_validate_json(response.text)
```

This is the pattern to build both Job 1 (extract production/award pairs from a government PDF's text) and Job 2 (normalize a live-researched jurisdiction's rule set) around — same schema mechanism, different input text and different Pydantic model.

---

## Parallel Search API — concrete enough to write code from

**Package:** `parallel-web` on PyPI, `pip install "parallel-web>=1.0.1"`, imported as `from parallel import Parallel`. Official Python SDK, Python 3.9+, both sync and async clients over `httpx`. (Source: [pypi.org/project/parallel-web](https://pypi.org/project/parallel-web/), [github.com/parallel-web/parallel-sdk-python](https://github.com/parallel-web/parallel-sdk-python), HIGH confidence.)

**Auth:** `PARALLEL_API_KEY` environment variable (or passed to the client constructor). Treat like any other secret — `.env` locally, a secret file or env var on the Lightsail instance, never committed.

**Call signature (Search API):**

```python
from parallel import Parallel

client = Parallel(api_key="...")  # or reads PARALLEL_API_KEY from env

result = client.search(
    objective="Find the current film production tax incentive program for Bristol, England and the wider UK national scheme it sits under",
    search_queries=[
        "UK film tax incentive AVEC 2026",
        "Bristol England regional film incentive",
    ],
    mode="advanced",             # turbo | fast | basic | advanced — advanced for jurisdiction research, turbo for cheap lookups
    max_chars_total=None,        # optional cap on total returned excerpt characters
)

for r in result.results:        # ordered by decreasing relevance
    print(r.url, r.title, r.publish_date)
    for excerpt in r.excerpts:  # markdown-formatted, citation-ready
        print(excerpt)
```

This response shape (`url`, `title`, `publish_date`, `excerpts[]`) maps directly onto the "every figure carries a source link and date-checked" requirement — store `url` and `publish_date` alongside every rule field extracted from that result.

**Distinct products beyond Search — use these too:**
- **Extract API** — turns a specific URL (found via Search) into clean markdown, including PDFs and JS-rendered pages, up to 20 URLs per call. Use this to pull the full text of a specific government PDF (e.g. the NY ESD quarterly report) once Search has located its URL, before handing that text to `google-genai` for structured extraction.
- **Task API** — multi-hop, minutes-scale research producing cited structured output (`result.output.basis`), with processor tiers from `lite` to `ultra8x`. This is the closer fit if a single jurisdiction's rule normalization genuinely requires several rounds of "find X, then check Y implied by X" — worth prototyping Job 2 against Task API directly if Search+Extract+genai proves too manual, but start with the simpler Search+Extract+genai pipeline given the time budget.
- **MCP server** exists (`Parallel Task MCP Server`), but it targets MCP-client agent workflows (e.g. Claude Desktop, Cursor). Not relevant to this project's runtime — the requirement is calling the *SDK* at runtime from the Python backend, not wiring an MCP client into the product itself.

**Rate limits:** approximately 600 Search requests/minute, 2,000 Task runs/minute (MEDIUM confidence — figures vary slightly across secondary sources; the numbers in this project's actual usage — tens of jurisdictions, occasional live lookups — are nowhere near these limits, so this is not a design constraint here).

**Pricing:** Search is priced per-1,000-requests at a low fixed rate that varies by `mode` (turbo/fast cheapest, basic/advanced more expensive per request but higher quality), with signup credit typically available. **MEDIUM confidence on exact figures** — the pricing page rendered different numbers across two fetch attempts in this research pass. Before writing any cost-tracking or budget-alert code, pull the live numbers from `https://docs.parallel.ai/getting-started/pricing` directly. For a hackathon demo (dozens of Search calls, single-digit Extract/Task calls) cost is a non-issue regardless of exact per-call figures.

---

## Frontend + map — comparison and recommendation

| Option | Verdict for this project | Why |
|--------|---------------------------|-----|
| **MapLibre GL JS 6.5.0** (recommended) | ✅ Use this | Real interactive basemap, GPU-accelerated, data-driven styling (`interpolate` expressions for color-by-cost), instant re-render on GeoJSON source update — exactly the slider-reorders-live requirement. Free basemap via OpenFreeMap, zero signup. Open-source (BSD), no vendor lock-in, and explicitly not an AI service so raises zero eligibility questions. |
| deck.gl | ❌ Overkill | Built for large-scale WebGL data viz (thousands to millions of points, 3D layers, GPU aggregation). At 10-20 city markers this buys nothing over MapLibre's native circle/symbol layers and adds a second rendering framework (deck.gl is usually paired *on top of* MapLibre anyway) plus a steeper learning curve — pure risk for a 17-day build with no visual payoff at this data scale. |
| D3 / react-simple-maps (SVG projection) | ⚠️ Viable fallback, not preferred | Genuinely fine for a point map at this scale and arguably the fastest to get *a* map on screen (no tile loading, no WebGL context). The tradeoff: you lose the "real interactive map" feel (pan/zoom, familiar basemap texture) that scores on the Design judging criterion, and you own more projection/rendering code yourself. Fall back to this only if MapLibre's tile loading or styling proves to eat unexpected build time — it's a same-day pivot, not a dead end, since the underlying city-coordinate + color-scale data model is identical either way. |

**Recommendation:** React 19 + Vite 8 + TypeScript, MapLibre GL JS 6.5.0 directly (no `react-map-gl` wrapper needed — a single `useRef` + `useEffect` around the vanilla MapLibre `Map` object is less code and less to learn than adopting a second abstraction layer), OpenFreeMap `liberty` or `positron` style as the basemap, a GeoJSON `FeatureCollection` of cities as a `source` whose `total_net_cost` property drives an `interpolate` `circle-color`/`circle-radius` paint expression. The start-date slider updates that GeoJSON source's data and updates a plain React state list for the ranked sidebar — no separate state library needed at this scale (`useState`/`useReducer` is enough; do not add Redux/Zustand for a single-screen app).

---

## Hosting — AWS Lightsail instance (revised recommendation)

The project owner has an existing, paid-for AWS Lightsail **instance** (a VM, not the separate "Lightsail container service" product) and AWS is permitted for non-AI infrastructure. This changes the calculus from a from-scratch comparison: the fastest path to a working public URL is now the platform that's already provisioned and paid for, not the platform that's theoretically fastest from zero.

| Option | Time to public URL | Notes |
|--------|--------------------|-------|
| **AWS Lightsail instance (recommended)** | Fast — instance and static IP already exist; remaining work is app deploy + TLS, roughly 30-60 minutes | No new account, no new billing setup, no cold starts (unlike Cloud Run's scale-to-zero, which can add multi-second latency to the *first* request an anonymous visitor makes right when a judge is testing it — a real risk for a hackathon demo). Full control over the box; a static IP is either already attached or a one-click Lightsail action. |
| Lightsail **container service** (not the same product) | Fast, automatic HTTPS on a Lightsail-managed subdomain with zero cert setup | Only relevant if the owner's existing resource is this product rather than a VM instance — confirm which one exists before planning around it. If it is a container service, this is actually *faster* than the VM path (HTTPS is automatic, no nginx/Caddy step at all) and should be preferred. |
| Google Cloud Run | Fast from zero (`gcloud run deploy --source .` → public HTTPS URL in one command) | No longer the default recommendation now that a paid-for Lightsail instance exists — would mean standing up a second billing account/project purely for hosting when the constraint explicitly frees hosting from the Google-only rule. Still a reasonable fallback if the Lightsail instance turns out to be undersized or misconfigured. |
| Firebase Hosting + Cloud Run | Slower | Adds a second platform (Firebase project, hosting rewrites config) for no benefit over a single Cloud Run service serving both API and static frontend — never the right choice for this project's scope. |
| App Engine | Slower, more config surface (`app.yaml`, service structure) than Cloud Run for a plain container | Legacy relative to Cloud Run for this use case. Not recommended. |

### Minimal deploy path — AWS Lightsail instance

1. **Confirm/attach a static IP** to the instance (Lightsail console → Networking → Attach static IP). Without this the public IP changes on every stop/start.
2. **Point DNS** (a subdomain you control, or use the instance's public IP directly for the hackathon if no domain is needed — but a domain makes TLS trivial, see next step).
3. **Install Docker + Docker Compose** on the instance (`curl -fsSL https://get.docker.com | sh`).
4. **Ship one `docker-compose.yml`** with two services:
   - `app`: the FastAPI backend, built from a `Dockerfile` that also copies the pre-built Vite `dist/` output and serves it via FastAPI's `StaticFiles` mount — one container, one process, one internal port (e.g. 8000).
   - `caddy`: official `caddy:2` image, mounted with a `Caddyfile` of essentially:
     ```
     yourdomain.example {
         reverse_proxy app:8000
     }
     ```
     Caddy obtains and renews a Let's Encrypt certificate automatically on first request to that domain — no certbot, no manual renewal cron, no nginx config to hand-write. This is materially faster than the nginx+certbot path most tutorials describe, and it is the single highest-leverage substitution in this whole hosting plan for a 17-day deadline.
5. **Open ports 80/443** in the Lightsail firewall (console → Networking tab on the instance).
6. `docker compose up -d` on the instance. Public URL live.
7. Redeploy on each change: `git pull && docker compose build && docker compose up -d` (or wire a short GitHub Actions workflow that SSHes in and runs this — optional polish, not required for Definition of Done).

This serves the entire product — API plus built frontend — from one process behind one TLS-terminating proxy, which is the simplest topology that satisfies "hosted URL an anonymous visitor can use."

### AWS resources worth using for non-AI infrastructure

- **S3** — good fit for archiving cached government PDFs (immutable source-of-truth copies for the audit trail: "we extracted this figure from *this exact byte-identical document* on this date") and for periodic index snapshots once Milestone 2 exists. Not needed for Milestone 1's core data (see Data layer — that lives in the repo).
- **A cron job on the instance itself** (plain `cron` or a `systemd` timer) is sufficient for the scheduled reference-production re-run in Milestone 2; EventBridge is unnecessary added complexity for a single scheduled job on a box you already control. Reach for EventBridge only if the schedule needs to survive the instance being rebuilt, which is unlikely to matter inside the hackathon window.
- **Secrets:** plain `.env` file on the instance (excluded from the Docker build context, mounted at runtime) is adequate for a hackathon; Secrets Manager is legitimate but adds AWS IAM setup time for no functional gain at this scale.
- **RDS/Aurora:** not recommended — see Data layer, the volume doesn't justify a managed database, and Postgres-on-Lightsail-instance-via-Docker is available if a real database ever becomes necessary (unlikely for Milestone 1).

### Forbidden dependencies — read before writing any extraction code

**AWS AI services — absolute no.** Any of these called anywhere in the stack, even once, even in a throwaway script that ships in the repo, is a Stage One disqualification:

- **AWS Textract** — the specific trap for *this* project. Parsing NY ESD quarterly PDFs, NJEDA reports, and film office rule pages is exactly Textract's use case, which is exactly why it must not be used. **All PDF/document extraction goes through Parallel's Extract API (get clean text/markdown) followed by `google-genai` structured extraction (turn that text into typed fields).** That pipeline is both compliant and, per the product doc's own reasoning, the right tool for genuine "reasoning about what a document says," which OCR alone doesn't do anyway.
- **Bedrock** (any model behind it, including third-party models Bedrock hosts), **SageMaker**, **Comprehend**, **Rekognition**, **Transcribe**, **Polly**, **Translate**, **Kendra**, **Amazon Q** (in any product it's embedded in) — forbidden by name, no exceptions.
- **Borderline cases, assessed:**
  - **OpenSearch with semantic/neural search plugins** — avoid. Those features route through a model (often Bedrock-backed) under the hood. Plain OpenSearch/Elasticsearch lexical search would be fine but isn't needed at this data volume anyway (a YAML/SQLite dataset of tens of jurisdictions doesn't need a search engine).
  - **RDS/Aurora ML integrations** (`aws_ml`, SageMaker-invoking SQL functions) — avoid; irrelevant anyway since RDS isn't recommended for this data volume.
  - **S3 Object Lambda invoking an AI model on read** — avoid if ever considered; not needed for this project (S3 here is just archival storage, plain GET/PUT).
  - **CloudWatch anomaly detection** — this is a statistical (not generative-AI) feature for metric alerting; safe if used, but not needed for a hackathon submission.
- **`boto3` itself is fine.** It's a plain AWS SDK — a generic RPC client. What's restricted is *which endpoint* you call through it. Using `boto3` to `put_object` into S3 or read a Secrets Manager value is unrestricted; using `boto3` to call `textract.analyze_document` or `bedrock-runtime.invoke_model` is not.
- **Forbidden Python packages** (would fail screening on their own, or indicate a disallowed vendor call is coming): `openai`, `anthropic`, `langchain*` (any langchain-\* package, including `langchain-google-genai` — it's a LangChain integration, not the official Google SDK, and the constraint names agent frameworks as restricted, not just model vendors), `llama-index`, `crewai`, `boto3` calls to any AI endpoint (see above — the package is fine, specific calls are not).
- **Pre-submission check:** before packaging the repo, run `pip freeze` (or inspect the lockfile) inside the actual deploy container and grep for the forbidden package names above, then separately `grep -rn` the source tree for `textract`, `bedrock`, `comprehend`, `rekognition`, `transcribe`, `polly`, `translate`, `kendra`, `sagemaker`, `openai`, `anthropic`, `langchain`, `llama_index`, `crewai`. A clean grep plus a clean lockfile is the concrete gate — don't rely on memory of what got added over 17 days.

---

## Data layer

**Recommendation: versioned YAML files in the repo for curated rule models and validation pairs; SQLite for the live-research cache; nothing else.**

| Data | Storage | Why |
|------|---------|-----|
| Curated jurisdiction rule models (NY, CA, NJ, CT) | YAML files in the repo, one file per jurisdiction | Tens of jurisdictions at most — this is not a scale problem, it's a provenance problem, and the project brief says provenance *is* the product ("the repo is public and inspectable"). A YAML file's git history **is** the audit trail for free: `git log --follow ny.yaml` shows exactly when a rate changed, by whom, in what commit, with what commit message as the reasoning. A database gives you none of that without building a separate audit-log table — which is strictly more work than the free version control already provides. |
| Validation pairs (production → qualified spend → credit issued, with source URL) | YAML/JSON fixtures in the repo, structured for direct pytest parametrization | Doubles as both the data and the test fixtures — see Testing section. One file per pair or one file per jurisdiction, human-readable and reviewable in a PR diff. |
| Per-figure metadata (source URL, date-checked, confidence tier) | Fields inside the same YAML records, not a separate table | Keeps "every figure is cited" structurally true rather than aspirational — the citation lives next to the number in the same file, not joined from elsewhere. |
| Live-research cache (uncurated cities researched on demand, FX rates, cap-consumption lookups) | SQLite, single file (e.g. `cache.db`), inside the container/instance filesystem | This data is explicitly *not* meant to be part of the public audit trail (it's ephemeral, refreshed per the tiered-refresh table), so it doesn't belong in git. SQLite needs zero provisioning, ships as one file, and Python's stdlib `sqlite3` needs no new dependency. A key-value or simple table schema (`cache_key`, `payload_json`, `fetched_at`) is more than sufficient at this volume. |

**Explicitly not recommended:**
- **Postgres/Cloud SQL/RDS** — provisioning and networking (connection strings, security groups/VPC, credential management) is real setup time this project doesn't need to spend for tens of rows of curated data and a cache. Reach for this only if Milestone 2's scheduled index run needs concurrent multi-writer access, which it doesn't at this scale.
- **Firestore** — adds a GCP NoSQL SDK and its document-model mental overhead for data that is naturally tabular/structured (a jurisdiction rule with nested tiers is exactly what a typed Pydantic model over YAML represents cleanly). No advantage over flat files here, and it would be one more thing to explain in the "technologies used" write-up without a real technical reason for being there.

---

## Money and dates

**Recommendation: `decimal.Decimal` (stdlib) plus a small in-repo `Money` value type. Do not add `py-moneyed` as a dependency.**

`py-moneyed` does exactly what you'd want (a `Money` class over `Decimal`, ISO 4217 currency data) but its last PyPI release was **November 2022** — effectively unmaintained (confirmed via Snyk package health analysis and PyPI release history, MEDIUM-HIGH confidence). For a public hackathon repo where "provenance is part of the product," a maintained-looking dependency graph matters too, and the actual functionality needed here is narrow: six fixed currency codes, same-currency arithmetic, and one FX conversion function. A ~20-line in-repo dataclass:

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

Currency = Literal["USD", "GBP", "CAD", "EUR", "CZK", "HUF"]

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"cannot add {self.currency} to {other.currency} — convert first")
        return Money(self.amount + other.amount, self.currency)
```

...is more auditable to a judge reading the source than a third-party class hierarchy, has zero dependency risk, and is trivial to unit test. If richer arithmetic (allocation/splitting with correct remainder distribution, formatted display per locale) becomes genuinely needed, `stockholm` (actively maintained, 100% test coverage, `Decimal`-backed) is the better-maintained alternative to reach for — not `py-moneyed`.

**Decimal discipline:** use `Decimal` for every monetary value from the moment a rate card or per diem figure enters the system — never `float`. Only quantize (round) at the final display/output boundary, and match each jurisdiction's own stated rounding convention where documented (this matters directly for the "reproduce a government figure exactly" requirement — an extra rounding step in the wrong place is the most likely reason a validation-pair test fails by a cent).

**FX source: Frankfurter** — `https://api.frankfurter.dev/v2/rates` (and `?date=YYYY-MM-DD` for historical/date-of-quote rates). No API key required, no documented quota ("rate-limited to prevent abuse, no monthly/daily caps"), open-source, wraps European Central Bank and other central-bank reference rates across 201 currencies (Source: [frankfurter.dev](https://frankfurter.dev/), HIGH confidence on the endpoint/no-key claims; MEDIUM confidence on the exact "201 currencies / 84 central banks" framing since it reflects a newer v2 architecture — but CZK and HUF are both actively-tracked European central-bank currencies and near-certain to be covered; do one live sanity-check call against both codes during setup, not at demo time). Not an AI service, so it raises no eligibility question at all. Note ECB-sourced rates are business-day, once-daily (published ~16:00 CET) — fine for this project since FX only needs to be "current as of date-checked," not intraday.

---

## Testing

**Recommendation: pytest 9.1.1, parametrized directly over YAML/JSON fixture files, exact-match assertions on `Decimal` values. Not snapshot testing.**

The requirement is to reproduce a *specific, already-known, government-published number exactly* — this is the opposite of the problem snapshot testing (`syrupy`, `pytest-golden`) solves. Snapshotting is for "approve this new output as the new correct baseline" workflows, where the correct answer isn't known in advance. Here the correct answer *is* known in advance (Anora: $3,964,760 → $991,190) and is itself the assertion, sourced from a government PDF. The right pattern is the plainest possible one:

```python
# tests/fixtures/validation_pairs/ny_anora.yaml
production: "Anora"
jurisdiction: "NY"
qualified_spend: "3964760.00"
expected_credit_issued: "991190.00"
source_url: "https://esd.ny.gov/.../quarterly-report-2024-q..."
source_date_checked: "2026-08-20"

# tests/test_validation_pairs.py
import yaml
from pathlib import Path
from decimal import Decimal
import pytest
from productionfinance.engine import compute_credit

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "validation_pairs"

def load_fixtures():
    for f in sorted(FIXTURE_DIR.glob("*.yaml")):
        yield yaml.safe_load(f.read_text())

@pytest.mark.parametrize("case", load_fixtures(), ids=lambda c: f"{c['jurisdiction']}_{c['production']}")
def test_reproduces_government_award_exactly(case):
    result = compute_credit(
        jurisdiction=case["jurisdiction"],
        qualified_spend=Decimal(case["qualified_spend"]),
    )
    assert result.credit_issued == Decimal(case["expected_credit_issued"]), (
        f"{case['production']}: expected {case['expected_credit_issued']}, "
        f"got {result.credit_issued} — source: {case['source_url']}"
    )
```

This gives: (1) every validation pair as one file, git-diffable and independently reviewable against its `source_url`, (2) the same files double as both documentation of the validation record ("tested against N government-disclosed awards") and the executable test suite — no drift possible between the claim and the test, (3) a new fixture file is the entire cost of Job 1 ingesting a new disclosure and adding it to the loop, (4) failure messages that point straight at the source document, which is exactly what you want on stage when a judge asks "how do you know this is right."

For the mean-error metric mentioned in the project's success criteria, add one aggregate test/report step that runs after the parametrized suite and computes `abs(actual - expected) / expected` across all fixtures — this becomes the "tested against N pairs, mean error X%" number.

---

## Installation

```bash
# Python backend
pip install "fastapi[standard]"==0.141.1 \
            "google-genai"==2.19.0 \
            "parallel-web>=1.0.1" \
            pyyaml \
            httpx \
            gunicorn

# Python dev/test
pip install pytest==9.1.1 ruff

# Frontend
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install maplibre-gl
```

---

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

**If the Lightsail resource turns out to be a Container Service, not a VM instance:**
- Skip Caddy/nginx entirely — Lightsail container services provision HTTPS automatically on a Lightsail-managed subdomain.
- Because there is genuinely nothing to configure for TLS in that product; the VM-instance deploy path above only applies to a plain instance.

**If Job 2 (live research) proves too manual with Search + Extract + `google-genai` chained by hand:**
- Prototype the same jurisdiction lookup against Parallel's **Task API** directly, using its cited structured output.
- Because Task API is built exactly for "multi-hop research producing structured, cited output" and may collapse three manual steps into one call — worth a 30-minute spike before committing to the manual pipeline for Job 2 specifically (Job 1's PDF-parsing use case is a better fit for the simpler Search/Extract + `google-genai` path regardless, since the document is already known).

**If the demo needs a custom domain and DNS isn't set up yet:**
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

---
*Stack research for: ProductionFinance (film production landed-cost + incentive pricing engine, hackathon submission)*
*Researched: 2026-08-23*
