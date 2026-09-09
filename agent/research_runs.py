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

AGT-11: `BOOT_ID` is minted once at import and is stamped onto every record
this process writes (`save_run`/`append_round` do the stamping centrally, so
no caller can forget it). `reclassify_interrupted_jobs()` is the restart
recovery: on the NEXT process's startup it rewrites every record still
`status == "running"` whose `boot_id` names a process that is gone — the
process that would have finished it no longer exists, so `interrupted` is
the only honest classification. This is a boot-identity comparison, never a
timeout: a heuristic staleness clock would either declare a slow live job
dead or leave a genuinely dead job spinning, which is exactly AGT-11's
failure mode.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.services._paths import REPO_ROOT

__all__ = [
    "BOOT_ID",
    "COMMITTED_RESEARCH_RUNS_DIR",
    "RESEARCH_RUNS_DIR",
    "SCHEMA_VERSION",
    "InvalidJobIdError",
    "append_round",
    "boot_id",
    "load_run",
    "new_job_id",
    "reclassify_interrupted_jobs",
    "save_run",
]

# T-07-20: exists ONLY for test isolation, so a subprocess-isolated test can
# point a child process at a `tmp_path` it shares with its parent. Read once
# at import; production sets no such variable and gets the real `var/job2/`
# directory under `REPO_ROOT`.
_RUNS_DIR_ENV_VAR = "PRODFIN_JOB2_RUNS_DIR"
_runs_dir_override = os.environ.get(_RUNS_DIR_ENV_VAR)
RESEARCH_RUNS_DIR: Path = (
    Path(_runs_dir_override) if _runs_dir_override else REPO_ROOT / "var" / "job2"
)
COMMITTED_RESEARCH_RUNS_DIR: Path = REPO_ROOT / "runs" / "job2"

SCHEMA_VERSION = 1

# T-07-04: `job_id` from a URL path segment must never reach `open()`
# unvalidated. `uuid4().hex` is always exactly 32 lowercase hex characters,
# so this single pattern is both the id format AND the sole membership
# check performed before any path is built.
_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# Minted once at import — identifies the process that last wrote a record.
# AGT-11's restart recovery is a comparison against THIS name, never a
# timer: a record whose boot_id does not match the CURRENT process's
# BOOT_ID was written by a process that is no longer running.
BOOT_ID: str = uuid.uuid4().hex


class InvalidJobIdError(ValueError):
    """Raised when `job_id` is not exactly 32 lowercase hex characters —
    checked BEFORE any path is built (T-07-04)."""


def boot_id() -> str:
    """The `boot_id` minted once at import time for this process. Thin
    accessor kept for existing call sites; `BOOT_ID` is the module-level
    constant itself."""
    return BOOT_ID


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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

    `record` must already carry `job_id`, `schema_version`, and `status` —
    this module fixes the record SHAPE; callers (the router and
    `agent/job2.py`) build the dict content. `boot_id` and `updated_at` are
    stamped HERE, centrally, on every write — AGT-11's restart recovery
    depends on every write genuinely carrying the writing process's own
    `BOOT_ID`, and fixing that in one place means no caller can forget it
    (a second, ad-hoc stamp elsewhere would let AGT-11 and D-92 drift, which
    is exactly what this module's docstring rules out).
    """
    stamped = dict(record)
    stamped["boot_id"] = BOOT_ID
    stamped["updated_at"] = _utc_now_iso()
    path = _path_for(stamped["job_id"])
    _atomic_write(path, stamped)


def append_round(job_id: str, round_record: dict) -> dict:
    """Re-read the persisted record, append `round_record` to its `rounds`
    list, bump `round_count`, stamp `boot_id`/`updated_at`, and rewrite
    atomically — called after EVERY round, before the next round starts
    (D-92). Returns the updated (stamped) record."""
    path = _path_for(job_id)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["rounds"].append(round_record)
    record["round_count"] = len(record["rounds"])
    record["boot_id"] = BOOT_ID
    record["updated_at"] = _utc_now_iso()
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


def reclassify_interrupted_jobs() -> list[str]:
    """AGT-11's restart-recovery sweep. Scans `RESEARCH_RUNS_DIR` and, for
    every record still `status == "running"` whose `boot_id` names a
    DIFFERENT process than this one, rewrites it to `status: "interrupted"`
    with `terminal_reason: "interrupted_by_restart"` and a message naming
    the round it reached. Returns the list of reclassified job ids.

    Decided by `boot_id` comparison, never a timeout (AGT-11's own
    requirement): a record whose last writer no longer exists cannot be
    resumed by anyone, so `interrupted` is the honest classification the
    moment a fresh process can observe it — not after some elapsed-seconds
    guess. A record carrying THIS process's own `BOOT_ID` is left
    untouched — a job this process is currently running must never be
    reclassified out from under itself. A record already `terminal` or
    already `interrupted` is left untouched. Running the sweep twice
    reclassifies zero records the second time (idempotent).

    Intended to run once, cheaply, from a FastAPI `lifespan` hook before the
    first request is served (`app/main.py`). Never imports either SDK,
    never touches the network, and reads only small JSON files in one
    directory. A malformed or unreadable JSON file is skipped — it must
    never abort the sweep and must never stop the app from booting
    (T-07-16): a corrupt record is exactly the kind of thing a crash
    mid-write can leave behind, and the sweep exists to make crashes
    legible, not to be brought down by one.
    """
    reclassified: list[str] = []
    if not RESEARCH_RUNS_DIR.is_dir():
        return reclassified

    for path in sorted(RESEARCH_RUNS_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        if record.get("status") != "running":
            continue
        if record.get("boot_id") == BOOT_ID:
            continue

        round_count = record.get("round_count") or 0
        if round_count > 0:
            reached = f"after reaching round {round_count}"
        else:
            reached = "before completing its first round"
        record["status"] = "interrupted"
        record["terminal_reason"] = "interrupted_by_restart"
        record["message"] = (
            "This research run was interrupted when its process stopped "
            f"{reached}. It cannot be resumed and no further rounds will run."
        )
        record["boot_id"] = BOOT_ID
        record["updated_at"] = _utc_now_iso()

        try:
            _atomic_write(path, record)
        except OSError:
            continue

        job_id = record.get("job_id") or path.stem
        reclassified.append(job_id)

    return reclassified
