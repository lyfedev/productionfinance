"""The Phase 5 agent package — Job 1: reproduce one New York government

disclosure end to end through the mandated pipeline (Parallel Search ->
Parallel Extract -> google-genai structured extraction -> the existing
pricing engine, D-82).

This package imports neither `parallel` nor `google.genai` at module load
time (see `agent.parallel_client` and `agent.gemini_client`) — both SDKs are
imported lazily inside the functions that call them, so importing this
package (or `app.main`, which never imports it either) leaves the FastAPI
process footprint on the 472 MB host unchanged until a run is actually
triggered.
"""

from __future__ import annotations

__all__: list[str] = []
