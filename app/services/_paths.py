"""Shared filesystem-path anchoring for the `app/services/` layer.

`REPO_ROOT` and `RULESET_PATH_BY_JURISDICTION` were previously declared
identically in both `app/services/spec.py` and `app/services/validate.py`
(03-REVIEW.md WR-04) — a Phase 4+ jurisdiction addition required
remembering to update both dicts in lockstep, with no test guarding they
stayed in sync. Both modules now import from this one shared module
instead.

Every filesystem path is anchored to `REPO_ROOT`, never a CWD-relative
literal — `deploy/prodfin.service` sets `WorkingDirectory=/opt/prodfin` on
the host, and pytest runs from the repo root; only a module-anchored path
is correct in both.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["REPO_ROOT", "RULESET_PATH_BY_JURISDICTION"]

REPO_ROOT = Path(__file__).resolve().parents[2]

# New York only in Phase 3 — every other jurisdiction_id a fixture may
# declare (us-ct, us-ma, us-ca, us-nj, us-pa) is real data but has no
# curated rule model wired into either route yet.
RULESET_PATH_BY_JURISDICTION: dict[str, Path] = {
    "us-ny": REPO_ROOT / "jurisdictions" / "us-ny.yaml",
}
