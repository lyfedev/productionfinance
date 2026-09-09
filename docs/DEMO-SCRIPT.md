# ProductionFinance — Demo Script (SHP-11)

**This document is the shot list for a ≤3-minute demo video. The video
itself is a human deliverable** — nobody in this repository can operate a
screen recorder or a microphone. What follows is exact enough that
recording it is mechanical: which URL, what to click, what to say, how
long to linger.

Record against the hosted URL (`https://vockell.com/finance/`) once
`.planning/SHIP-CHECKLIST.md` items 1–2 are done (credentials installed,
current `HEAD` deployed) — recording against a stale deploy or a
localhost dev server would show a different product than the one being
submitted. If item 1 is not done by recording time, Beat 4 below has an
honest fallback; do not skip recording waiting for it.

**Every beat below is a real page computed fresh on load — never a mock,
never a pre-recorded clip presented as live, never a `sleep()` behind a
spinner.** All four beats live together, in this exact order, on one
page: `/demo`. The shot list below walks that page top to bottom, then
detours to `/compare` for the map. If `/demo` is not yet deployed at
recording time (check `curl -s -o /dev/null -w '%{http_code}' <hosted-url>/demo`
— a 404 means the box is still behind `HEAD`), use the per-page URLs
listed under each beat instead; the content is identical, just spread
across separate pages.

## Total runtime budget: 2:55 (5-second margin under the 3:00 cap)

| Time | Shot | Says |
|---|---|---|
| 0:00–0:15 | **The pain, landed.** Open on `/compare` already loaded with the default three-city comparison (New York, Los Angeles, London). Point at the ranked list's headline-rate column, then at the net-cash column next to it — they don't agree, and the ranking would flip if you only read the first one. | "A producer picking a city usually compares headline incentive rates. Those two numbers rank cities in different orders — for the exact same production. This is what actually lands in the bank." |
| 0:15–0:50 (35s) | **Beat 1 — reproduce a government figure.** Scroll to `/demo`'s first section, or open `/proof` directly. Click into one pair (Anora, New York). Show the reproduced figure next to the archived government PDF itself — not a link to a page that might 404, the document. Point at the sha256 hash line. | "This is Anora's real New York film tax credit, reproduced by the engine, sitting next to the actual government disclosure document we archived — byte-for-byte, hash and all. Not a citation. The document." |
| 0:50–1:25 (35s) | **Beat 2 — naive arithmetic is wrong.** `/demo` section 2 (or the naive-arithmetic panel). Show the naive "spend × headline rate" figure, then the engine's real net-cash figure next to it, and the overstatement percentage. | "Apply the headline rate to the whole spend by hand and you get this number. The real net cash — after the ceiling split, the cap, the tax — is meaningfully lower. Every step of that gap is shown, not asserted." |
| 1:25–2:05 (40s) | **Beat 3 — the ranking inverts.** `/demo` section 3, or back to `/compare` with the map visible. Show the "ordered by headline rate" table, then the "ordered by real net cash" table right beside it — same spend, same computation, different order. Drag the start-date slider once on `/compare` to show the map and ranked list update live. | "Same spend, same four jurisdictions, two orderings from the same computation. The city that led on headline rate is not the city that leads on real net cash. And this isn't a one-time chart — drag the date, and it recomputes live." |
| 2:05–2:45 (40s) | **Beat 4 — live research, labelled unvalidated.** See the two recording paths below — use whichever matches the credential state at recording time. | — |
| 2:45–2:55 (10s) | **Close.** Cut to `/` or `/export`, show the hosted URL in the address bar. | "Every figure sourced, dated, and provably matching what a government actually paid. [hosted URL]." |

### Beat 4 — the two honest recording paths

Check which applies **before** recording this segment; do not guess.

**Path A — credentials installed (`.planning/SHIP-CHECKLIST.md` item 1
done).** Open `/research`, type a city with no curated rule model (e.g. a
city not among NY/CA/NJ/CT), submit, and let the page render at least one
real round: Parallel Search running, then `google-genai` judging
sufficiency, shown live with the SDK call evidence on the page. Say:
"Now a city we've never modeled. Watch it research live — real search,
real reasoning about whether it has enough — and the result is labelled
researched, not validated, the moment it renders." Do not fast-forward
past a wait — if a round takes visible time, either accept the real wait
in the recording or cut to the resulting page once it terminates; never
speed up footage to imply speed that wasn't real.

**Path B — credentials not yet installed at recording time.** Open
`/research` (or `/demo`'s fourth section) and show the honest
unavailable state: the page names which environment variable is missing
and states plainly that this beat cannot run. Say: "This beat needs a
live API credential this environment doesn't have installed yet. Rather
than fake it, the product says so — plainly, on the page itself." This is
not a weaker demo; it is the same honesty discipline the rest of the
product enforces (D-101), shown instead of just claimed.

**Never:** record Path A once and re-use the footage after credentials
expire or rotate. Never pre-record a "live" run and cut it in later.
Never narrate a capability the page itself is not currently showing.

## Pre-recording checklist (mechanical, run once before hitting record)

1. Confirm the hosted URL is reachable and shows the intended `HEAD` commit
   (`.planning/SHIP-CHECKLIST.md` item 2).
2. Confirm which Beat 4 path applies (`.planning/SHIP-CHECKLIST.md`
   item 1's state) and rehearse that path once, silently, so timing is
   known before recording starts for real.
3. Clear browser cache / use a private window so no cached page state
   confuses the recording with a prior session's numbers.
4. Have the exact URLs above open in tabs, in order, so no address-bar
   typing eats into the 3-minute budget.
