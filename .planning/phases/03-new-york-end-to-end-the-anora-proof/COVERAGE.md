# API Coverage — Phase 3 (New York End-to-End — The Anora Proof)

No external API integration: Phase 3 serves local FastAPI routes over committed YAML rule files
and validation-pair fixtures already in the repository — no outbound HTTP client, no SDK, no
third-party service is called at runtime by anything this phase builds.

## Why the detector fired

`api-coverage.cjs --json` returned `detected: true` on a single signal — the noun `sdk` in the
phrase *"no AI SDK import lands in this phase"* (`03-CONTEXT.md` § Phase Boundary, "Not in this
phase"). The matched sentence is the phase's own **exclusion** of every external AI surface, not
an integration statement:

> **No agent jobs.** Neither Job 1 (validation loop) nor Job 2 (live research) is touched. No
> `google-genai` call, no `parallel-web` call, no AI SDK import lands in this phase.

Re-read of the full phase scope (ROADMAP § Phase 3, `03-CONTEXT.md`, `03-RESEARCH.md` § Standard
Stack) confirms it: the only two new dependencies are `jinja2` (a local templating library) and
`python-multipart` (a local form-body parser). Neither is a service; neither has a remote
capability surface to enumerate. Every data read in this phase is a local file:
`jurisdictions/us-ny.yaml`, `tests/fixtures/validation_pairs/*.yaml`, `data/crew_tiers.yaml`.

Parallel Search (`parallel-web`) and Gemini (`google-genai`) are the project's real external
API integrations and are scoped to Phases 5 and 7. Their capability matrices belong to those
phases, where a matrix can be enumerated against a real surface rather than fabricated here.

## Fabrication refused

Per the checkpoint protocol, no matrix row was invented for a capability that does not exist in
this phase. This reasoned declaration stands in place of a matrix and is what the
`api-coverage.verify-pre` seal gate accepts.
