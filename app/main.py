"""ProductionFinance FastAPI skeleton.

Phase 1 scope only: proves the venv -> uvicorn -> systemd -> Apache -> TLS
chain carries a real application (D-20). No engine, no rule schema, no
jurisdiction data, no UI treatment — computing a figure here would be the
exact dishonesty PROJECT.md forbids.
"""

import os
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import __version__
from app.routers import compare as compare_router
from app.routers import integrate as integrate_router
from app.routers import export as export_router
from app.routers import job1 as job1_router
from app.routers import methodology as methodology_router
from app.routers import proof as proof_router
from app.routers import research as research_router
from app.routers import spec as spec_router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """AGT-11's restart-recovery sweep, run once before this process serves
    its first request. A `systemctl restart prodfin` (or an OOM kill
    followed by systemd's own restart) performs this with no operator
    action — every Job 2 record still `status: "running"` from a process
    that is now gone is reclassified `interrupted` here, before any visitor
    can hit a stale record. `agent.research_runs` imports neither SDK, so
    this import does not disturb the lazy-import contract this module's own
    docstring describes (D-20)."""
    from agent.research_runs import reclassify_interrupted_jobs

    reclassify_interrupted_jobs()
    yield


app = FastAPI(title="ProductionFinance", version=__version__, lifespan=lifespan)

# Anchored to this module's own directory, not the process CWD, for the
# same WorkingDirectory reason PUBLIC_PATH is documented above (D-46).
# HTML autoescaping is Jinja2Templates' default (jinja2.select_autoescape())
# and is never disabled here — free-text fixture values reach these
# templates (T-03-04).
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

# Module-anchored, never CWD-relative, matching `templates` above — serves
# only this project's own committed CSS/JS (T-06-06: never a repo root or
# a user-writable path).
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

app.include_router(spec_router.router)
app.include_router(validate_router.router)
app.include_router(job1_router.router)
app.include_router(research_router.router)
app.include_router(compare_router.router)
app.include_router(methodology_router.router)
app.include_router(proof_router.router)
app.include_router(export_router.router)
app.include_router(integrate_router.router)


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
def index(
    request: Request,
    state: list[str] | None = Query(default=None),
    qualified_spend: str | None = None,
    go: str | None = None,
) -> HTMLResponse:
    """Compare the states a production is actually considering."""
    from app.services._paths import RULESET_PATH_BY_JURISDICTION
    from app.services.integrate import IntegrationRequest, price_from_request

    PLACE = {
        "us-ny": "New York",
        "us-ca": "California",
        "us-nj": "New Jersey",
        "us-ct": "Connecticut",
    }
    # How the money actually reaches the production. A producer choosing
    # between states cares about this as much as the amount, and it is the
    # honest thing to say about a transferable credit — the credit is known;
    # only what a buyer will pay for it is not.
    PAYMENT = {
        "refundable": ("Paid to you", "The state pays the balance in cash."),
        "nonrefundable_credit": ("Cuts your tax bill", "Applied against state tax you owe."),
        "transferable": (
            "Certificate you sell",
            "Resale prices are not published, so the buyer sets what it fetches.",
        ),
    }

    chosen = [s for s in (state or []) if s in RULESET_PATH_BY_JURISDICTION]
    ctx: dict = {
        "public_path": PUBLIC_PATH,
        "places": [
            {"id": j, "name": PLACE.get(j, j), "checked": j in chosen}
            for j in sorted(RULESET_PATH_BY_JURISDICTION, key=lambda x: PLACE.get(x, x))
        ],
        "spend": qualified_spend or "",
        "rows": None,
        "error": None,
    }

    if go:
        if len(chosen) < 2:
            ctx["error"] = "Pick at least two places to compare."
        elif not qualified_spend:
            ctx["error"] = "Enter what the production will spend."
        else:
            rows = []
            for jid in chosen:
                result = price_from_request(
                    IntegrationRequest(jurisdiction_id=jid, qualified_spend=qualified_spend)
                )
                if result["status"] == "rejected":
                    ctx["error"] = result["reason"]
                    break
                gross = result.get("gross_credit") or (
                    (result.get("programmes") or [{}])[0].get("gross_credit")
                )
                if not gross:
                    continue
                label, note = PAYMENT.get(_mechanism(jid), ("", ""))
                rows.append(
                    {
                        "name": PLACE.get(jid, jid),
                        "credit": int(gross["value"]),
                        "credit_fmt": f"{int(gross['value']):,}",
                        "payment": label,
                        "payment_note": note,
                        "steps": [
                            {"text": t, "applied": not t.lstrip().lower().startswith("no ")}
                            for t in gross["derivation_tree"]["derivation"]
                        ],
                    }
                )
            if rows and not ctx["error"]:
                rows.sort(key=lambda r: -r["credit"])
                ctx["rows"] = rows
                ctx["spread"] = f"{rows[0]['credit'] - rows[-1]['credit']:,}"
                ctx["best"] = rows[0]["name"]
                ctx["worst"] = rows[-1]["name"]
                try:
                    ctx["pretty_spend"] = f"{int(str(qualified_spend).replace(',', '')):,}"
                except ValueError:
                    ctx["pretty_spend"] = qualified_spend
    return templates.TemplateResponse(request=request, name="index.html", context=ctx)


def _mechanism(jurisdiction_id: str) -> str:
    from app.services._paths import RULESET_PATH_BY_JURISDICTION
    from engine.models import load_ruleset

    try:
        return load_ruleset(RULESET_PATH_BY_JURISDICTION[jurisdiction_id]).programmes[0].mechanism
    except Exception:  # noqa: BLE001 - a bad rule file must not blank the page
        return ""
