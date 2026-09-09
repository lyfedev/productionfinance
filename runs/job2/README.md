# `runs/job2/` — the one committed, human-verified Job 2 run

This directory is committed to the repository. It is deliberately **NOT**
under the gitignored `var/` tree, where `agent/research_runs.py` writes
every ordinary run to `var/job2/{job_id}.json`.

Mirrors `agent/runs.py`'s `COMMITTED_RUNS_DIR` convention for Job 1
(`runs/job1/`): **nothing is written here automatically.** A record is
copied in by hand, from `var/job2/{job_id}.json`, only after a human has
verified the run it describes — a real Parallel Search call and a real
`google-genai` sufficiency judgment, executed inside a live
`POST /research` request, with the `PRODFIN_SDK_CALL` log lines to prove
it (D-84).

## Why this exists

D-92 requires the agent's round-by-round reasoning trail to be a product
surface that both the running application and the written submission can
show. The application reads live records from `var/job2/`; the written
submission needs one that survives independently of whatever is currently
running on the host. This directory is that one artifact.

## How a record gets here

1. Start the app with both `PARALLEL_API_KEY` and `GEMINI_API_KEY` (or
   `GOOGLE_API_KEY`) set.
2. Submit a real city through `POST /research` (or `GET /research` and the
   form) and let the run reach a terminal state — `GET /research/{job_id}`
   shows a terminal page with no auto-refresh once it has.
3. A human reads that page (and, if desired,
   `cat var/job2/{job_id}.json | python -m json.tool`) and confirms the
   record is genuine: real source URLs, a real `google-genai` summary per
   round, and `PRODFIN_SDK_CALL` lines for every SDK call the run made.
4. Only then is `var/job2/{job_id}.json` copied into this directory by
   hand — `cp var/job2/{job_id}.json runs/job2/{job_id}.json` — and
   committed.

## What is unverified today

As of this plan (07-03), no API key is configured in this environment, so
no record has been produced or copied in yet. This directory currently
holds only this README. The steps above are the runbook for the human
verification pass once keys exist — see the phase SUMMARY for the honest,
current state of what has and has not been exercised against a real SDK
response.
