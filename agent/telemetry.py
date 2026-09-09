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
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

__all__ = ["SDK_CALL_LOG_PREFIX", "sdk_call"]

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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@contextmanager
def sdk_call(sdk: str, op: str, target: str, **extra: object) -> Iterator[None]:
    """Time a block and emit exactly one `PRODFIN_SDK_CALL` line on both
    success and failure. Re-raises the original exception after logging an
    `outcome=error` line — a failed call is still evidence a real call was
    attempted, and swallowing it would be dishonest (D-84).
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
        extra_str = " ".join(f"{key}={value}" for key, value in extra.items())
        line = (
            f"{SDK_CALL_LOG_PREFIX} sdk={sdk} op={op} target={target} "
            f"elapsed_ms={elapsed_ms} outcome={outcome} at={_utc_now_iso()}"
        )
        if extra_str:
            line = f"{line} {extra_str}"
        _logger.info(line)
