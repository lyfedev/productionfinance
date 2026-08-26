"""ProductionFinance FastAPI skeleton.

Phase 1 scope only: proves the venv -> uvicorn -> systemd -> Apache -> TLS
chain carries a real application (D-20). No engine, no rule schema, no
jurisdiction data, no UI treatment — computing a figure here would be the
exact dishonesty PROJECT.md forbids.
"""

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import __version__
from app.routers import validate as validate_router

# Captured once at import so every request in this process reports the
# same boot time.
BOOT_TIME: str = datetime.now(timezone.utc).isoformat()


def _resolve_git_sha() -> str:
    """Resolve the short git SHA for this deployment.

    Never raises: an unresolvable SHA on the host must not stop the
    service from booting (T-01-05 / D-20).
    """
    env_sha = os.environ.get("PRODFIN_GIT_SHA")
    if env_sha:
        return env_sha

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if sha:
                return sha
    except Exception:
        pass

    return "unknown"


GIT_SHA: str = _resolve_git_sha()

# The path prefix this deployment is reverse-proxied under, e.g. "/finance"
# when served at https://vockell.com/finance via Apache ProxyPass. Empty for
# local/dev runs where the app is served at the root. Used only to build
# correct absolute links in server-rendered HTML (T-01-51-adjacent: a
# generated link that omits the prefix silently 404s once proxied) — this
# app has no router mounted under the prefix, so no ASGI root_path is set.
PUBLIC_PATH: str = os.environ.get("PRODFIN_PUBLIC_PATH", "").rstrip("/")

app = FastAPI(title="ProductionFinance", version=__version__)

# Anchored to this module's own directory, not the process CWD, for the
# same WorkingDirectory reason PUBLIC_PATH is documented above (D-46).
# HTML autoescaping is Jinja2Templates' default (jinja2.select_autoescape())
# and is never disabled here — free-text fixture values reach these
# templates (T-03-04).
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

app.include_router(validate_router.router)


@app.get("/health")
def health() -> dict:
    """Liveness contract: exactly status, version, git_sha, boot_time.

    No environment variable dump, no filesystem path, no dependency
    inventory (T-01-03).
    """
    return {
        "status": "ok",
        "version": __version__,
        "git_sha": GIT_SHA,
        "boot_time": BOOT_TIME,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Holding page. Computes no figure, states no incentive value."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ProductionFinance</title>
</head>
<body>
  <h1>ProductionFinance</h1>
  <p>
    ProductionFinance will price the same film production in every city a
    producer is considering, and report the true landed cost of each —
    every figure sourced, dated, and provably matching what a government
    actually paid.
  </p>
  <p>This is a skeleton deployment. No pricing engine is live yet.</p>
  <p><a href="{PUBLIC_PATH}/health">{PUBLIC_PATH}/health</a></p>
</body>
</html>"""
