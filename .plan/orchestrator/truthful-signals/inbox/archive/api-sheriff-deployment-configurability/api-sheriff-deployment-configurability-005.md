envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:47Z

component=plan-marshall:phase-5-execute
category=bug

# A lost return path is logged as a command `error`: frozen step_execution_tier still wins in practice, and the outcome vocabulary cannot say "the envelope stopped listening"

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Filed in **API-Sheriff's** store, whose
repo does not own the `plan-marshall` bundle. Written here first and removed there second
(integrate-then-remove), `deployment-configurability` epic lessons intake 2026-09-11.

Origin id: `2026-09-05-07-001` (created 2026-09-05).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| runner reads the frozen manifest stamp (`"verify:module-tests",per_task`) while the live resolve says `orchestrator` | PARTIALLY FIXED — **prose only** | since #980 (2026-07-22) `phase-5-execute/standards/canonical_verify.md:83` says "When the stamp and this resolve disagree, **this resolve wins**", echoed at `SKILL.md:224`; no script cross-checks stamp vs resolver, and the observed run (PLAN-15, API-Sheriff) did not follow the rule | related PLAN-TRUTH-091 (staged, auto-background wording) |
| a zero-token / zero-tool / over-budget row is recorded as `error`, naming the command as the culprit | STILL-VALID | outcome set `('executed','skipped','loop_back','failed','error')` at `_manifest_core.py:320`; `manifest-schema.md:80` defines `error` as raised, "timed out, or was cut short" — a lost return after host auto-backgrounding lands there | related PLAN-TRUTH-089 (shipped #1399, split `loop_back`/`failed` out of `error`) |

**What this message adds:** evidence that the documented "live resolve wins" rule does not hold in
practice (it is an instruction, not a mechanism — the script-emitted-survives / prose-instructed-does-not
pattern), and the case for a distinct outcome (e.g. `return_lost`) keyed on the `0 tokens + 0 tool_uses +
duration > tier budget` signature, so the row names the dispatch rather than the work.

---

## Original lesson `2026-09-05-07-001` (verbatim)

id=2026-09-05-07-001
component=findings-triage
category=anti-pattern
status=active
created=2026-09-05

# An execution-log error row can name the wrong culprit - a zero-token zero-tool row with an impossible duration is a lost return path, not a failed command

## Observation

PLAN-15's phase-5 execution log recorded:

```
"verify:module-tests",5-execute,error,0,0,1355000,"2026-09-04T18:19:32.728279+00:00"
```

`outcome: error` — but **the module tests were fine**. The run completed, every phase reached `done`,
and PR #267 merged as `558a38b`.

The real cause was a routing stamp. The plan's frozen execution manifest carried
`step_execution_tier` with `"verify:module-tests",per_task`, while the live architecture resolve for
the same command answers `orchestrator`. The manifest is what the phase-5 runner reads. A `per_task`
tier runs the call synchronously inside the current dispatch on a per-task timeout budget; the real
command is a multi-minute orchestrator-tier build. Given an inadequate synchronous budget, the host
platform auto-moved it to the background, the dispatch lost its synchronous return path, and the
lost return was recorded as `error`.

## The signature to recognise

Read the row's three numbers together — they are what identify it:

| Field | Value | What it means |
|---|---|---|
| `duration_ms` | `1355000` (~22.6 min) | Impossible against a `per_task` budget |
| `total_tokens` | `0` | Nothing was accounted to the dispatch |
| `tool_uses` | `0` | The dispatch never saw a tool result |

⛔ **A genuine command failure does not look like this.** A failing build burns tokens, records tool
uses, and finishes inside its budget. **Zero-token, zero-tool, over-budget is the signature of a
result that never came back** — the work ran, and the envelope that issued it was no longer listening.

## Why it matters more than a mislabelled row

1. **It names the wrong culprit.** A reader chasing `verify:module-tests,error` opens the build first
   and finds nothing wrong, because nothing is.
2. **The recovery is silent-lossy.** The auto-background is a host-platform heuristic, not a
   plan-marshall decision, so nothing in the plan's own logs announces it. The impossible
   `duration_ms` is the only tell.
3. **It is a snapshot-versus-resolver drift, so it recurs.** The manifest is frozen at compose time;
   the architecture resolve is live. Every plan composed from the same stale snapshot inherits the
   same wrong stamp — a cross-plan defect wearing a per-plan costume.

## Directive

1. **Before attributing an `error` row to its command, check `duration_ms` against the step's
   declared tier.** A duration that could not have fit the budget means the row is about the
   dispatch, not the work.
2. **Cross-check the manifest's `step_execution_tier` against the live resolve** when a long-running
   step is stamped `per_task`. `manage-execution-manifest read --plan-id <id>` shows the stamp;
   disagreement with the resolver is the defect.
3. **Do not re-run the command on the strength of such a row.** The work most likely completed; a
   re-run pays the full cost again to learn nothing.

⚠ The durable fix is upstream in plan-marshall — either the compose step re-derives the tier at fire
time, or the runner cross-checks the stamp against the resolver and fails loudly on disagreement
rather than letting the platform silently re-tier the work. This repository cannot make that change;
this lesson is about reading the symptom correctly until it lands.
