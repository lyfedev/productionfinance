# Agentic Cinema: The Blockbuster Hackathon — brief

*Google Cloud, run by Devpost. https://agentic-cinema.devpost.com/*
*Captured 2026-08-20/22.*

---

## THE BASICS

- **Deadline:** Sep 9, 2026, 2:00pm PDT. Contest opened July 27.
- **Judging:** Sep 23 – Oct 7. Winners ~Oct 7, must respond within 2 business days.
- **Prize pool:** $75,000, but it's **five separate contests** — each partner track has its own $7,500 / $4,500 / $3,000. You compete only against others in your track. 15 winners total.
- **Participants:** 7,466 registered as of Aug 20. Track distribution is **not visible** — the project gallery is unpublished and likely stays that way until after judging.
- **Teams:** max 4.
- **Ford's-eye caveat:** AZ residents eligible. Excluded: Italy, Brazil, Quebec, China, Russia and others.

## WHAT TO BUILD

A functional AI agent or multi-agent network, powered by Gemini and Google Cloud Agent Builder, integrating one Partner's product or MCP server, solving bottlenecks in the entertainment and media value chain — specifically for **filmmakers, screenwriters, studio crews, or fans.**

The overview copy asks for a **"deterministic, multi-step agent."** That phrase is marketing, not binding rules — but it signals the judges want *workflow automation*, not creative generation. Worth heeding: the resources guide pushes Imagen/Lyria/TTS hard, and pure generative output scores badly against that word.

## SUBMISSION REQUIREMENTS

- Hosted project URL (web, Android, or iOS)
- Text description — features, technologies, data sources, findings and learnings
- Public repo (GitHub/GitLab/Bitbucket) with **OSI license detectable in the About section**
- Google Cloud SDK **imported and actually called** at runtime. Accepted: `google-adk`, `google-genai`, `google-generativeai`, `google-cloud-aiplatform`
- Partner requirement met (see below)
- Demo video, **≤3 min**, public on YouTube/Vimeo, English or subtitled, showing the thing *functioning* — explicitly not a cinematic trailer
- Track selected
- **New project**, created inside the contest window. No extending prior work.

## 🚩 THE AI RESTRICTION

> "Projects may only use Google Cloud artificial intelligence tools... and the built-in AI-powered features of the specific Partner's product relevant to your chosen track. **No other AI models, agent frameworks, or AI APIs are permitted, regardless of vendor** — this includes but is not limited to AWS, Microsoft, OpenAI, and Anthropic AI tools."

Non-AI third-party services (hosting, databases, web frameworks) are unrestricted.

## THE FIVE TRACKS

| Partner | What it is | Requirement | Capability it lends an agent |
|---|---|---|---|
| **IBM** | Bob — agentic coding environment. VS Code fork + Bob Shell CLI | **Built using IBM Bob.** Confluent optional | **None at runtime.** Dev tool only |
| **Grafana** | Observability — metrics, logs, traces | Query the **Grafana MCP server** at runtime. AI Observability alone does NOT satisfy | Sees your own systems |
| **Parallel** | Web research API built for agents (Parag Agrawal, $2B val.) | Call the **Search API** at runtime | Sees the outside world |
| **ClickHouse** | Columnar OLAP database | Use **`mcp-clickhouse`** against a real cluster | Memory at scale |
| **Replit** | Replit Agent + hosting | Built **with Replit Agent** AND deployed on `replit.app`/`replit.dev` | Builds and ships software |

**Structural note:** IBM and Replit are *development-process* requirements because their products aren't things an agent calls. That makes their partner bar far lower — your product architecture is unconstrained. The other three constrain what you build.

**Our track: IBM.** Bob installed and tested; imports VS Code settings and extensions, five-minute setup. Low actual friction, high *perceived* friction (enterprise branding, mainframe positioning) — which likely thins the field, since the people deterred never discover they were wrong.

**Open question:** the general rule demands partner services at runtime, but IBM's bar is dev-process. If Bob is only the IDE, no IBM code runs in the shipped product. Unresolved — worth asking the organizers.

---

## JUDGING

**Stage One — pass/fail viability.** All requirements present, reasonably addresses the challenge, reasonably applies both partner and Google Cloud. **Partly automated.**

**Stage Two — four equally weighted criteria:**

1. **Technological Implementation** — how well built, how effectively it uses Google Cloud *and the Partner services*
2. **Design** — a complete, coherent product experience, not just a technical proof of concept
3. **Potential Impact** — a credible, specific case for solving a real problem for a real audience, and whether the solution addresses it *based on what's demonstrated*
4. **Quality of the Idea** — creative, non-obvious use of the services; genuine understanding of the problem space

**🚩 Ties are broken by comparing criteria in the order listed — Technological Implementation first.**

---

## OUR SCORECARD

| Criterion | Score | Reasoning |
|---|---|---|
| **Technological Implementation** | **8.5** *(within track)* | Google side is a 9 — Gemini for script analysis, Imagen for panels, Veo for motion, multi-speaker TTS for every part, Lyria for the phonograph cue, ADK and Agent Engine underneath. **Nothing decorative; every service load-bearing.** Partner side is near zero — but that's true of every IBM submission, so it washes out within the track. |
| **Design** | **7** | Fidelity ladder is a coherent product idea; temp art means a stranger gets output from a script alone. **Entirely contingent on a real interface** — a notebook caps this at 3. |
| **Potential Impact** | **7** | "Know whether the script works before spending two years and forty million dollars" is legible to anyone. Risk: judges are cloud/AI engineers, not film people. Pain must land in 15 seconds. |
| **Quality of the Idea** | **9** | Strongest column. Most submissions will be a chatbot over a document or a dashboard. "Watch a drawing become a movie" is memorable; the replacement mechanic is genuinely non-obvious. |

### What moves the needle, ranked

1. **Build a real interface.** Scores Design and Impact simultaneously.
2. **Solve the Bob evidence question.** Stage One gate.
3. **Land the pain in the first 15 seconds** of the video. Impact is scored on what's *demonstrated*.
4. **Surface the reasoning behind every generated artifact** (see below). Cheapest points available.

### The judge's-eye read on the two sub-tests

**MULTI-STEP ✓** — Genuine chain, not an LLM wrapper. Real decisions at several nodes. *Reservation: I'm taking it on faith that beat selection is reasoned rather than fixed-interval.*

**DETERMINISTIC ✓** — At the pipeline level. Same script yields the same beats, manifest, shot count and assembly order. Generated frames aren't bit-reproducible, but that's inherent and correctly bounded. *Ingestion is deterministic by deliberate design and carries no intelligence — the agentic weight is all on the generation side.*

### 🎯 The single cheapest scoring move

**Every generated artifact carries its reason.**

- Beat boundary → *"new beat: location change"*
- Panel count → *"scene 7: 1 beat — establishing, no action"*
- Hold duration → *"3.2s = dialogue length + 0.5"*
- Motion selection → *"beat 12: physical action, no dialogue"*
- Asset priority → *"Rocky: 8 scenes, 2 costumes — replace first"*

Costs a string per decision. Converts a faith claim into an audited one — and a visible rule proves determinism as well as reasoning. **Lands on all four criteria.**

---

## SUBMISSION STRUCTURE

- **Main video (3 min):** explains the process. Pain in the first 15 seconds.
- **Supplemental:** the same scene at each rung — all panels, then with motion, then with footage. Same length, same cuts. The comparison *is* the product. Plus a video of other scripts being processed (answers "does it generalize" without letting a stranger break it). Plus the asset manifest as a document — least flashy output, most convincing evidence it read the script.
- **Hosted URL:** Rocky only, fixed. Media cached and labeled. Beat parse and swap run live. **No open input.** Zero variability in what a stranger touches.
- **Never fake progress.** The repo is public and inspectable; a `sleep()` behind a progress bar is a Stage One death.
