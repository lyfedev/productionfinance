"""The D-84 SDK-call log line.

SHP-05 and SHP-06 are both verified "by a timestamped log line at the call
site" (05-CONTEXT.md D-84), and Phase 8's re-verification sweep greps
production logs for one real Gemini call and one real Parallel call fired
within 24 hours of submission. The line is therefore a deliverable, not
debug output: `sdk_call` emits it unconditionally on both success and
failure, with no environment-variable or verbosity guard, and this module
attaches a stdout handler at import time so the line survives uvicorn's own
logging reconfiguration.

The record never contains a key, a full prompt, or document text (T-05-03) —
only sdk/op/target/elapsed_ms/outcome/at, plus caller-supplied extra
key=value pairs that must themselves carry no secret or document text.

`collecting()` (plan 05-03) lets `agent.job1.run_job1` capture the SAME
records the log line prints, without changing the `sdk_call(...)` call
sites already inside `agent/parallel_client.py` and `agent/gemini_client.py`
— an ambient `contextvars.ContextVar` collector, activated only for the
duration of one `run_job1` call, is what makes the on-page evidence block
and the D-84 log line provably the same record rather than two
independently-produced claims.
"""

from __future__ import annotations

import contextvars
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

__all__ = ["SDK_CALL_LOG_PREFIX", "collecting", "sdk_call"]

SDK_CALL_LOG_PREFIX = "PRODFIN_SDK_CALL"

_LOGGER_NAME = "prodfin.sdk"
_logger = logging.getLogger(_LOGGER_NAME)
_logger.setLevel(logging.INFO)

# uvicorn reconfigures root logging on startup, which can leave a
# module-level logger with no *effective* handler if it relies on
# propagation to a root that uvicorn has since replaced. Attach a stdout
# handler directly, once, at import time, so the D-84 line survives that
# reconfiguration regardless of import order.
if not _logger.handlers:
    _handler = logging.StreamHandler(stream=sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.propagate = False

# contextvars (not a plain module global) so a threaded run_job1 call — see
# app/routers/job1.py, which starts run_job1 on a background thread — never
# leaks its collector into a concurrent request's call sites.
_active_collector: contextvars.ContextVar[list | None] = contextvars.ContextVar(
    "_active_collector", default=None
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@contextmanager
def collecting(collector: list) -> Iterator[None]:
    """Activate `collector` as the ambient `sdk_call` collector for the
    duration of this block. Every `sdk_call` invocation inside the block —
    regardless of which module or thread calls it — appends its record to
    `collector`, with no change needed at the call sites themselves."""
    token = _active_collector.set(collector)
    try:
        yield
    finally:
        _active_collector.reset(token)


@contextmanager
def sdk_call(
    sdk: str, op: str, target: str, collector: list | None = None, **extra: object
) -> Iterator[None]:
    """Time a block and emit exactly one `PRODFIN_SDK_CALL` line on both
    success and failure. Re-raises the original exception after logging an
    `outcome=error` line — a failed call is still evidence a real call was
    attempted, and swallowing it would be dishonest (D-84).

    `collector`, if given, receives the exact same record the log line
    reports (sdk, op, target, elapsed_ms, outcome, at) as a plain dict —
    never a key, a prompt, or document text. When `collector` is None, the
    ambient collector activated by `collecting()` (if any) is used instead.
    """
    start = time.monotonic()
    outcome = "ok"
    try:
        yield
    except BaseException:
        outcome = "error"
        raise
    finally:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        at = _utc_now_iso()
        extra_str = " ".join(f"{key}={value}" for key, value in extra.items())
        line = (
            f"{SDK_CALL_LOG_PREFIX} sdk={sdk} op={op} target={target} "
            f"elapsed_ms={elapsed_ms} outcome={outcome} at={at}"
        )
        if extra_str:
            line = f"{line} {extra_str}"
        _logger.info(line)

        effective_collector = collector if collector is not None else _active_collector.get()
        if effective_collector is not None:
            effective_collector.append(
                {
                    "sdk": sdk,
                    "op": op,
                    "target": target,
                    "elapsed_ms": elapsed_ms,
                    "outcome": outcome,
                    "at": at,
                }
            )
