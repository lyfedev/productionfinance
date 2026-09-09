# Ship Checklist (SHP-13, D-102, D-103)

Every item below is a **human action**. No agent in this environment can
perform any of them — either they require a secret only the human holds,
require physical/network conditions an agent cannot fabricate (a
different network than the development machine), or are the literal
final judgment call before submission. **None of these are pre-ticked.**
An agent updating this file to mark one done without the human having
actually done it is exactly the dishonesty this checklist exists to
prevent — do not do that.

Check each box only after genuinely doing the thing, in order. Items are
ordered so each one's prerequisite is satisfied by the item before it.

- [ ] **1. Install `PARALLEL_API_KEY` and `GEMINI_API_KEY` in
      `/opt/prodfin/.env`, mode 600, owner `prodfin`, restart the
      service.**
      Why an agent can't: these are secrets that must come from the
      human — obtaining them from Parallel's and Google's own consoles is
      itself a human account action.
      How: SSH to the Lightsail box, `sudo -u prodfin vi /opt/prodfin/.env`
      (or equivalent), add both lines, `sudo chmod 600 /opt/prodfin/.env`,
      `sudo chown prodfin:prodfin /opt/prodfin/.env`,
      `sudo systemctl restart prodfin`.
      Confirmed still unset as of this writing:
      `sudo grep -oE '^[A-Z_]+=' /opt/prodfin/.env` on the box lists only
      `PRODFIN_GIT_SHA`, `PRODFIN_LOG_LEVEL`, `PRODFIN_APP_PORT`,
      `PRODFIN_PUBLIC_PATH` — neither key is present.

- [ ] **2. Deploy current `HEAD` to the box.**
      Why an agent can't: a deploy to production infrastructure, on this
      project's own stated constraint ("Do not provision new cloud
      resources without explicit per-resource approval" — and a deploy
      is a state-changing action on an already-approved resource, still
      warranting a human's explicit go-ahead at submission time), is a
      human-gated action.
      How: follow `deploy/README.md`'s deploy runbook.
      Confirmed as of this writing: production `PRODFIN_GIT_SHA=9af46b0`,
      which is **80 commits behind** this repository's `HEAD` — Phase 6,
      7, and 8 work (including `/demo`, `/export`, the proof panel, the
      start-date slider, and this very submission's product surfaces) is
      not live on the hosted URL until this item is done.

- [ ] **3. Trigger `/job1` and `/research` from a logged-out browser.**
      Why an agent can't: this is the live execution proof itself — a
      human must be the one to fire the real request the submission
      claims happened, from a session with no prior authentication state.
      How: open a private/incognito browser window, visit
      `https://vockell.com/finance/job1`, submit; separately visit
      `https://vockell.com/finance/research`, submit a city with no
      curated model.

- [ ] **4. Re-grep `journalctl -u prodfin` for `PRODFIN_SDK_CALL`.**
      Why an agent can't: confirming the production log line requires
      SSH access to the box at the moment after item 3's real request —
      it is the verification half of a human action, not a separate
      automatable step.
      How: `sudo journalctl -u prodfin --since "15 min ago" | grep PRODFIN_SDK_CALL`
      — expect one line with `sdk=parallel-web` and one with
      `sdk=google-genai`. Confirmed as of this writing:
      `sudo journalctl -u prodfin --since '7 days ago' | grep -c PRODFIN_SDK_CALL`
      returns `0` — zero live calls have ever fired.

- [ ] **5. Commit the resulting `runs/` artifacts and close
      `WINDOWS.md` #26 and #28.**
      Why an agent can't: this is the record of item 3/4 actually having
      happened — committing it before it happens would be exactly the
      "fake progress" this project's own honesty constraint forbids.
      How: copy the live run's JSON output into `runs/job1/` (and
      `runs/job2/` if the research beat also fired), `git add`, commit,
      then run `gsd-tools windows fixed 26` and `gsd-tools windows fixed 28`
      (or hand-edit `WINDOWS.md`'s status column) once the artifact is
      genuinely committed.

- [ ] **6. Spot-check the MapLibre map in a real desktop browser.**
      Why an agent can't: the headless browser tooling available in this
      environment lacks WebGL2, which MapLibre GL JS 6.5.0 requires as of
      its v6.0.0 release — the `/compare` map has never been visually
      confirmed to render correctly, only confirmed not to crash the page.
      How: open `https://vockell.com/finance/compare` in Chrome, Firefox,
      or Safari on a real desktop; confirm the map renders with colored
      city markers, pans/zooms, and updates when the start-date slider
      moves.

- [ ] **7. Record the demo video.**
      Why an agent can't: operating a screen recorder and a microphone
      is a physical human action.
      How: follow `docs/DEMO-SCRIPT.md` exactly — it is written to be
      mechanical. Confirm which Beat 4 path applies (item 1's state)
      before recording.

- [ ] **8. LAST — open the hosted URL from a logged-out browser on a
      different network than the development machine, and confirm it
      works.**
      Why an agent can't: this is the literal cold-verification step
      (D-102) — it must be a genuinely different network path (e.g. a
      phone on cellular data, not the same Wi-Fi the development machine
      used all week) to catch anything specific to the development
      machine's own network path, cached DNS, or session state.
      How: on a phone with cellular data (Wi-Fi off) or a different
      physical location's network, open a private browser tab, visit
      `https://vockell.com/finance/`, confirm the homepage loads and at
      least `/compare` and `/proof` work. This is the final step —
      nothing in this checklist comes after it.
