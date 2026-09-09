"""JSON persistence for a Job 2 run — durable per-round records (D-92).

Modelled on `agent/runs.py`'s discipline. `job_id` arrives from a URL path
segment and is therefore untrusted input: `load_run` validates it against a
strict 32-hex-character pattern BEFORE building any path (T-07-04, the same
T-05-12 rule `agent/runs.py::load_run` already applies).

`append_round` writes to a sibling temp file in the same directory and
`os.replace`s onto the target, so a reader in another process never
observes a partial record (T-07-08) — this is what makes D-92's "durable
before the next round starts" claim true against a concurrent reader, not
just against this process's own memory.

The record never carries a key, a full prompt, or raw document text
(T-07-03, the same T-05-14 rule `agent/runs.py` already applies): round
evidence is stored as the result URLs/titles and the model's own findings
and summary — never the raw excerpt blob a Search call returned.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from app.services._paths import REPO_ROOT

__all__ = [
    "COMMITTED_RESEARCH_RUNS_DIR",
    "RESEARCH_RUNS_DIR",
    "SCHEMA_VERSION",
    "InvalidJobIdError",
    "append_round",
    "boot_id",
    "load_run",
    "new_job_id",
    "save_run",
]

RESEARCH_RUNS_DIR: Path = REPO_ROOT / "var" / "job2"
COMMITTED_RESEARCH_RUNS_DIR: Path = REPO_ROOT / "runs" / "job2"

SCHEMA_VERSION = 1

# T-07-04: `job_id` from a URL path segment must never reach `open()`
# unvalidated. `uuid4().hex` is always exactly 32 lowercase hex characters,
# so this single pattern is both the id format AND the sole membership
# check performed before any path is built.
_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# Minted once at import — identifies the process that last wrote a record.
# `agent/research_runs.py`'s own record format fixes this field now even
# though plan 07-03 is what consumes it (interrupted-job recovery).
_BOOT_ID = uuid.uuid4().hex


class InvalidJobIdError(ValueError):
    """Raised when `job_id` is not exactly 32 lowercase hex characters —
    checked BEFORE any path is built (T-07-04)."""


def boot_id() -> str:
    """The `boot_id` minted once at import time for this process."""
    return _BOOT_ID


def new_job_id() -> str:
    """A fresh `job_id`: always exactly 32 lowercase hex characters."""
    return uuid.uuid4().hex


def _path_for(job_id: str) -> Path:
    if not _JOB_ID_RE.match(job_id):
        raise InvalidJobIdError(job_id)
    return RESEARCH_RUNS_DIR / f"{job_id}.json"


def _atomic_write(path: Path, payload: dict) -> None:
    """Write `payload` to a sibling temp file in the same directory, then
    `os.replace` onto `path` — a reader in another process never observes a
    half-written file (T-07-08)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def save_run(record: dict) -> None:
    """Persist the whole record as JSON under `var/job2/{job_id}.json`.

    `record` must already carry `job_id`, `schema_version`, `status`, and
    `boot_id` — this module fixes the record SHAPE; callers (the router and
    `agent/job2.py`) build the dict content.
    """
    path = _path_for(record["job_id"])
    _atomic_write(path, record)


def append_round(job_id: str, round_record: dict) -> dict:
    """Re-read the persisted record, append `round_record` to its `rounds`
    list, bump `round_count`, and rewrite atomically — called after EVERY
    round, before the next round starts (D-92). Returns the updated
    record."""
    path = _path_for(job_id)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["rounds"].append(round_record)
    record["round_count"] = len(record["rounds"])
    _atomic_write(path, record)
    return record


def load_run(job_id: str) -> dict | None:
    """Load a persisted record by id, or None if none exists with that id.

    Raises `InvalidJobIdError` if `job_id` is not exactly 32 lowercase hex
    characters — checked BEFORE any path is built (T-07-04)."""
    path = _path_for(job_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
