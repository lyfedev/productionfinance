# Parallel SDK — verified signatures for the Job 2 research loop

Introspected from the **actually installed** `parallel-web` package on 2026-09-09, not from
documentation or memory. Trust this file over any prose; re-introspect if the version moves.

## `parallel.Parallel(api_key=...).search(...)`

Keyword-only. Returns `SearchResult`.

| Parameter | Type | Relevance to the D-90 loop |
|---|---|---|
| `search_queries` | `Sequence[str]` **required** | "Concise keyword search queries, **3-6 words each**. At least one required, **provide 2-3 for best results**." Each refinement round issues a fresh small set, not one long query. |
| `objective` | `Optional[str]` | "Natural-language description of the underlying question or goal driving the search... **should be self-contained** with enough context to understand the intent." **This is where the sufficiency gap goes** — D-91's unmet fields (rate / qualifying base / caps / payout mechanism / availability) become the refined objective on the next round. |
| `session_id` | `Optional[str]` | "Session identifier to **track calls across separate search and extract calls, to be used as part of a larger task**. Specifying it may give **better contextual results for subsequent API calls**." **Purpose-built for a multi-round agent.** Mint one session id per Job 2 run and pass it on every search and extract call in that run. |
| `mode` | `'turbo' \| 'fast' \| 'basic' \| 'advanced'` | Latency lever, and a visitor is waiting. Turbo = fastest. Fast = high quality inside a ~1s latency budget. Basic = low latency, best with 2-3 high-quality queries. Advanced = higher quality, more advanced retrieval and compression. |
| `max_chars_total` | `Optional[int]` | Caps total returned characters — bounds what the reasoning call has to read. |
| `advanced_settings` | `AdvancedSearchSettingsParam` | "May impact result quality and latency unless used carefully." |
| `client_model` | `Optional[str]` | Declares the model consuming the results so Parallel can tailor defaults. |
| `timeout` | `float \| httpx.Timeout` | Per-call timeout. |

## Design consequences

1. **`session_id` is the spine of the loop.** One id per Job 2 run, threaded through every
   round's search and extract. It is what makes round N+1 aware of rounds 1..N, and it ties
   the persisted iteration record (D-92) to what Parallel actually saw.
2. **Refinement is expressed through `objective`, not by string-mangling the query.** The
   agent restates its goal in natural language including what it still lacks, and supplies
   2-3 fresh short keyword queries alongside.
3. **`mode` is a real dial** between a visitor waiting and answer quality. Worth starting at
   `base`/`fast` for early rounds and escalating only if sufficiency is not reached.
4. Queries must be **3-6 words**. A long natural-language question belongs in `objective`.

## Call sites as of this writing (D-96 audit input)

`agent/parallel_client.py:78` (`client.search`) and `agent/parallel_client.py:108`
(`client.extract`). Reachable from `agent/job1.py:449`, a CLI `__main__` entry point.
**A CLI entry point does not satisfy D-89** — Job 2 must reach these from a request handler,
and the D-96 audit must show the endpoint that does.
