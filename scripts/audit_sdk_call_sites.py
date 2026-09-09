#!/usr/bin/env python3
"""D-96: prove every search-SDK call site sits on a live request handler.

The owner's requirement, verbatim:

    Confirm every parallel-web call site sits on a request handler, not in a
    build or prep script. List the file and line of each call site and which
    endpoint reaches it.

Strategy: build a call graph from the AST of `agent/` and `app/`, seed it with
FastAPI route decorators, follow the `threading.Thread(target=...)` hop that
both background-job routes use, and report which endpoints reach each call
site. A call site with NO reaching endpoint is a FAIL (exit 1) — that is the
"build or prep script" case D-89 forbids.

Reachability via a CLI `__main__` is reported separately. It does not by
itself fail the audit: D-89 requires that the call EXECUTES on a live user
request, which a route satisfies. But a reader must be able to see that the
same code is reachable two ways, so it is disclosed rather than hidden.

Emits Markdown to stdout. `--check` compares against the committed artifact
and exits 1 on drift, so the table cannot go stale.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("agent", "app")
ARTIFACT = REPO_ROOT / "docs" / "sdk-call-sites.md"

# The search SDK whose call sites D-89/D-96 govern. Matched as an attribute
# call on a client object, e.g. `client.search(...)` / `client.extract(...)`,
# inside a module that imports the SDK.
SDK_MODULE = "parallel"
SDK_METHODS = ("search", "extract")


def _qualname(node: ast.AST) -> str | None:
    """Dotted name for a Name/Attribute node, else None."""
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


class ModuleIndex:
    """Functions, call edges, route decorators and thread hops for one module."""

    def __init__(self, path: Path, tree: ast.Module) -> None:
        self.path = path
        self.rel = path.relative_to(REPO_ROOT).as_posix()
        self.tree = tree
        self.module = self.rel.removesuffix(".py").replace("/", ".")
        self.imports: dict[str, str] = {}
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.calls: dict[str, set[str]] = {}
        self.routes: dict[str, list[str]] = {}
        self.sdk_calls: list[tuple[str, int, str]] = []
        self.has_main = False
        self._imports_sdk = False


def _collect_imports(idx: ModuleIndex) -> None:
    for node in ast.walk(idx.tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                idx.imports[a.asname or a.name.split(".")[0]] = a.name
                if a.name.split(".")[0] == SDK_MODULE:
                    idx._imports_sdk = True
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                idx.imports[a.asname or a.name] = f"{node.module}.{a.name}"
            if node.module.split(".")[0] == SDK_MODULE:
                idx._imports_sdk = True


def _route_paths(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """HTTP method + path for each FastAPI route decorator on `fn`."""
    found: list[str] = []
    for dec in fn.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        dotted = _qualname(dec.func) or ""
        tail = dotted.rsplit(".", 1)
        if len(tail) != 2:
            continue
        obj, method = tail
        if obj not in ("router", "app") or method not in (
            "get", "post", "put", "patch", "delete",
        ):
            continue
        if dec.args and isinstance(dec.args[0], ast.Constant):
            found.append(f"{method.upper()} {dec.args[0].value}")
    return found


def _index_module(path: Path) -> ModuleIndex | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    idx = ModuleIndex(path, tree)
    _collect_imports(idx)

    for node in ast.walk(idx.tree):
        if isinstance(node, ast.If):
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
            ):
                idx.has_main = True

    for fn in [
        n for n in ast.walk(idx.tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]:
        idx.functions[fn.name] = fn
        routes = _route_paths(fn)
        if routes:
            idx.routes[fn.name] = routes
        edges: set[str] = set()
        for sub in ast.walk(fn):
            # A function referenced as a VALUE is an edge too. This codebase
            # passes real implementations as injectable seams
            # (`search = search_fn or search_for_disclosure`), so a Call-only
            # scan would miss the real path and report a false FAIL.
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                edges.add(sub.id)
            if isinstance(sub, ast.Attribute):
                edges.add(sub.attr)
            if not isinstance(sub, ast.Call):
                continue
            dotted = _qualname(sub.func)
            if dotted:
                edges.add(dotted.rsplit(".", 1)[-1])
                # The threading.Thread(target=...) hop.
                if dotted.endswith("Thread"):
                    for kw in sub.keywords:
                        if kw.arg == "target":
                            tgt = _qualname(kw.value)
                            if tgt:
                                edges.add(tgt.rsplit(".", 1)[-1])
            if idx._imports_sdk and isinstance(sub.func, ast.Attribute):
                if sub.func.attr in SDK_METHODS:
                    base = _qualname(sub.func.value) or ""
                    if "client" in base.lower():
                        idx.sdk_calls.append((idx.rel, sub.lineno, sub.func.attr))
        idx.calls[fn.name] = edges
    return idx


def build() -> tuple[list[ModuleIndex], list[dict]]:
    modules: list[ModuleIndex] = []
    for d in SCAN_DIRS:
        for p in sorted((REPO_ROOT / d).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            idx = _index_module(p)
            if idx:
                modules.append(idx)

    by_module = {m.module: m for m in modules}

    def resolve(mod: ModuleIndex, name: str) -> tuple[ModuleIndex, str] | None:
        """Resolve a bare name to (defining module, function).

        Import-aware on purpose. A bare-name global match collides across
        modules (several define `search`/`_worker`) and produces confident
        WRONG endpoint attribution — the failure mode this audit exists to
        avoid. An edge is only followed when the calling module actually
        defines the name or imports it.
        """
        if name in mod.functions:
            return (mod, name)
        target = mod.imports.get(name)
        if target:
            owner_mod = target.rsplit(".", 1)[0]
            if owner_mod in by_module and name in by_module[owner_mod].functions:
                return (by_module[owner_mod], name)
        return None

    # Reverse graph over resolved (module, function) pairs.
    callers: dict[tuple[str, str], set[tuple[ModuleIndex, str]]] = {}
    for m in modules:
        for fn, edges in m.calls.items():
            for raw in edges:
                hit = resolve(m, raw)
                if hit:
                    callers.setdefault((hit[0].module, hit[1]), set()).add((m, fn))

    rows: list[dict] = []
    for m in modules:
        for rel, lineno, method in m.sdk_calls:
            enclosing = None
            for fn, node in m.functions.items():
                if node.lineno <= lineno <= (node.end_lineno or node.lineno):
                    if enclosing is None or node.lineno > m.functions[enclosing].lineno:
                        enclosing = fn
            endpoints: set[str] = set()
            seen: set[tuple[str, str]] = set()
            cli_modules: set[str] = set()
            q: deque[tuple[ModuleIndex, str]] = deque()
            if enclosing:
                q.append((m, enclosing))
            while q:
                mod, fn = q.popleft()
                if (mod.module, fn) in seen:
                    continue
                seen.add((mod.module, fn))
                for r in mod.routes.get(fn, []):
                    endpoints.add(r)
                if mod.has_main:
                    cli_modules.add(mod.rel)
                for up in callers.get((mod.module, fn), set()):
                    q.append(up)
            rows.append(
                {
                    "file": rel,
                    "line": lineno,
                    "method": method,
                    "function": enclosing or "<module>",
                    "endpoints": sorted(endpoints),
                    "cli": sorted(cli_modules),
                }
            )
    rows.sort(key=lambda r: (r["file"], r["line"]))
    return modules, rows


def render(rows: list[dict]) -> str:
    out: list[str] = []
    out.append("# Search-SDK call-site audit (D-96)")
    out.append("")
    out.append(
        "Generated by `scripts/audit_sdk_call_sites.py`. Do not edit by hand — "
        "CI regenerates this file and fails on drift."
    )
    out.append("")
    out.append(
        "**D-89:** the search SDK must execute on a live user request, not during "
        "data prep. A call site with no reaching endpoint is a FAIL."
    )
    out.append("")
    out.append("| # | Call site | Method | Enclosing function | Reaching endpoint(s) | Verdict |")
    out.append("|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        eps = "<br>".join(f"`{e}`" for e in r["endpoints"]) if r["endpoints"] else "— none —"
        verdict = "PASS" if r["endpoints"] else "**FAIL**"
        out.append(
            f"| {i} | `{r['file']}:{r['line']}` | `.{r['method']}()` | "
            f"`{r['function']}` | {eps} | {verdict} |"
        )
    out.append("")
    dual = [r for r in rows if r["cli"] and r["endpoints"]]
    if dual:
        out.append("## Dual reachability (disclosed, not a failure)")
        out.append("")
        out.append(
            "These call sites are reached by a request handler (satisfying D-89) "
            "and their defining module also exposes a command-line entry point, "
            "so the same code is reachable two ways:"
        )
        out.append("")
        for r in dual:
            mods = ", ".join(f"`{c}`" for c in r["cli"])
            out.append(f"- `{r['file']}:{r['line']}` — also reachable via a command-line entry point in {mods}")
        out.append("")
    failing = [r for r in rows if not r["endpoints"]]
    out.append(f"**{len(rows)} call site(s); {len(failing)} failing.**")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail on drift from the committed artifact")
    ap.add_argument("--write", action="store_true", help="write the artifact to docs/sdk-call-sites.md")
    args = ap.parse_args()

    _, rows = build()
    text = render(rows)
    failing = [r for r in rows if not r["endpoints"]]

    if args.check:
        if not ARTIFACT.exists():
            print(f"MISSING: {ARTIFACT.relative_to(REPO_ROOT)} has never been generated", file=sys.stderr)
            return 1
        if ARTIFACT.read_text(encoding="utf-8") != text:
            print(
                f"DRIFT: {ARTIFACT.relative_to(REPO_ROOT)} does not match the current tree. "
                "Regenerate it with: uv run --frozen python scripts/audit_sdk_call_sites.py --write",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {ARTIFACT.relative_to(REPO_ROOT)} matches the tree ({len(rows)} call sites).")
        return 1 if failing else 0

    if args.write:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(text, encoding="utf-8")
        print(f"wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    else:
        print(text)
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
