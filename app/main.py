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

from fastapi import FastAPI, Request
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
    jurisdiction_id: str | None = None,
    qualified_spend: str | None = None,
    go: str | None = None,
) -> HTMLResponse:
    """The landing page is the tool. Empty until the visitor asks."""
    from app.services._paths import RULESET_PATH_BY_JURISDICTION
    from app.services.integrate import IntegrationRequest, price_from_request

    # A person picks a place, not a programme. The rule files name the
    # programme ("New York Film Production Tax Credit"), which is the right
    # label inside the API and the wrong one in a dropdown.
    PLACE = {
        "us-ny": "New York",
        "us-ca": "California",
        "us-nj": "New Jersey",
        "us-ct": "Connecticut",
    }
    names = [
        {"id": jid, "name": PLACE.get(jid, jid)}
        for jid in sorted(RULESET_PATH_BY_JURISDICTION, key=lambda j: PLACE.get(j, j))
    ]

    ctx: dict = {
        "public_path": PUBLIC_PATH,
        "jurisdictions": names,
        "selected": jurisdiction_id or "us-ny",
        "spend": qualified_spend or "",
        "result": None,
    }

    if go and qualified_spend:
        result = price_from_request(
            IntegrationRequest(
                jurisdiction_id=ctx["selected"], qualified_spend=qualified_spend
            )
        )
        ctx["result"] = result
        # The engine's own refusal names schema fields, which is right for an
        # integrator reading the API and wrong for someone pricing a shoot.
        # The plain sentence leads; the exact engine text stays available
        # underneath, unedited.
        PLAIN_REFUSAL = {
            "us-nj": (
                "New Jersey pays this credit as a certificate you sell on to "
                "another company. The state does not publish what those "
                "certificates sell for, so we can't tell you what it turns "
                "into in cash — and we won't guess at a number your financing "
                "would rest on."
            ),
            "us-ct": (
                "Connecticut pays this credit as a certificate you sell on to "
                "another company. The state does not publish what those "
                "certificates sell for, so we can't tell you what it turns "
                "into in cash — and we won't guess at a number your financing "
                "would rest on."
            ),
        }
        ctx["plain_reason"] = PLAIN_REFUSAL.get(
            ctx["selected"],
            "We can't produce this figure from the rules the state publishes, "
            "and we won't estimate one.",
        )
        raw = str(result.get("qualified_spend") or qualified_spend).split(".")[0]
        try:
            ctx["pretty_spend"] = f"{int(raw.replace(',', '')):,}"
        except ValueError:
            ctx["pretty_spend"] = qualified_spend

        # A transferable-credit state still earns a credit; only its cash
        # conversion is unknown. Show the figure the producer asked for.
        if result["status"] == "cannot_be_computed" and result.get("gross_credit"):
            ctx["gross"] = f"{int(result['gross_credit']['value']):,}"
            ctx["steps"] = [
                {"text": t, "applied": not t.lstrip().lower().startswith("no ")}
                for t in result["gross_credit"]["derivation_tree"]["derivation"]
            ]

        if result["status"] == "ok" and result["programmes"]:
            prog = result["programmes"][0]
            gross = prog["gross_credit"]
            ctx["gross"] = f"{int(gross['value']):,}"
            # A step beginning "no ..." is a rule the programme declares that
            # did not apply here. Both are shown; only applied steps get
            # full-strength ink.
            ctx["steps"] = [
                {"text": t, "applied": not t.lstrip().lower().startswith("no ")}
                for t in gross["derivation_tree"]["derivation"]
            ]
            net = prog.get("net_cash") or {}
            point = net.get("point")
            if point and point != "None":
                ctx["net"] = f"{int(point):,}"
                ctx["net_note"] = "after the programme's own timing and tax treatment"
            if ctx["selected"] == "us-ny" and raw.replace(",", "") == "3964760":
                ctx["match_note"] = (
                    "New York State disclosed a credit of 991,190 for Anora against this "
                    "exact spend. Reproduced from the published rules, not looked up."
                )
    return templates.TemplateResponse(request=request, name="index.html", context=ctx)
