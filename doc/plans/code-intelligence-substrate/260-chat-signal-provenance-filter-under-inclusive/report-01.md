# Run report — 260-chat-signal-provenance-filter-under-inclusive (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/chat-signal-provenance-filter-agmptk`    **PR:** _pending_    **Outcome:** _pending_

## Skills loaded

Loaded by bundle path (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the `plan-marshall`
plugin is not installed in this cloud session, so the `Skill: {notation}` route was not used.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `plan-marshall:persona-implementer` | Production code |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

`pm-documents:ref-asciidoc` was **not** loaded: the only documentation touched is Markdown
(`references/chat-history-analysis.md`), not `.adoc`. No skill was unobtainable.

## Deliverables

### D1 — GATE: enumerate what actually survives, by provenance (mutates nothing)

**Done.** The plan records the six measured retention instances as machine-local and unreachable from
this clone, and directs the run to **reproduce** instead. One real transcript was reachable: this
session's own JSONL at `~/.claude/projects/-home-user-plan-marshall/{session}.jsonl`.

**Reproduction, first-party.** Running the pre-fix reducer over it:

| Measure | Value |
|---|---|
| Raw parseable turns | 74 (125 on a later re-read as the session grew) |
| Kept | 1 |
| Retention | 1.4% |
| Reported verdict | `no_signal: false` — a clean verdict |

This reproduces the plan's headline claim in shape: a fraction-of-one-percent retention reported as
clean. In this particular transcript the single survivor *was* the genuine operator turn, so this run
did not independently re-witness the "zero operator turns survived" case; that claim is carried
forward from the plan rather than re-established here, and is recorded as such.

**Claims confirmed first-party at HEAD** (by reading the pre-fix script):

| Claim | Confirmed |
|---|---|
| The verdict is a pure survivor count | Yes — `no_signal = len(turns) == 0` |
| The filter drops only a blank-turn class and one marker-matched injection shape | Yes — `_SKILL_LOAD_MARKER` plus the empty check |
| The docstring asserts "by construction" | Yes — twice: module docstring and the inline comment above `no_signal` |
| Operator decisions on a gated run arrive as tool results, so the reducer cannot see that channel | Yes — 33 `tool_result` blocks in the sample, every one yielding empty text via `extract_text`, hence dropped as "empty" |

**Marker inventory, derived from the real transcript.** The decisive D1 finding is that **the
inventory cannot be completed by enumeration from any transcript** — which is the evidence for the
positive predicate, not merely an argument for it:

| Class | Observed | Reaches the reducer as |
|---|---|---|
| Injected skill body (`Base directory for this skill:` + heading) | Yes — one, 73,694 chars | `user` text block |
| Empty / whitespace tool-result placeholder | Yes — 33 | `user` turn, empty text |
| Harness metadata (`deferred_tools_delta`, `agent_listing_delta`, `skill_listing`, `auto_mode`, `command_permissions`, `mcp_instructions_delta`, `task_reminder`) | Yes — 7 kinds, 11 events | `attachment` events with **no `message`** — already invisible to the reducer, not a defect |
| Tag-wrapped injections (`<system-reminder>`, `<task-notification>`, `<wake>`/`<event>`, command expansions) | Observed **in the rendered conversation**, but **absent from this JSONL** — this session surface persists them as attachments | `user` text in other harness surfaces |

⇒ The same logical injection is persisted differently by different harness surfaces and versions. An
enumeration keyed on whichever shapes one transcript happens to contain is a sample by construction —
the plan's own "a named list is a sample" rule, applied to the *previous* remediation. **Recorded as
settled: invert to a positive predicate; budget spent on the inventory, not on re-litigating.**

**D1's threshold call.** The plan leaves to D1 whether the routing threshold also changes. **Decision:
`no_signal` is re-keyed from survivor volume onto operator-authored counts.** This is not a discretionary
widening — the plan's Goal ("a reduction that dropped every operator-decision turn cannot render as
clean") and D4(c) ("a transcript with very low retention and zero turns passing the positive predicate
MUST report *no signal*") both require it. The numeric read budget (`DEFAULT_READ_BUDGET_BYTES`) is
**unchanged**, so the out-of-scope "changing the routing threshold" exclusion is respected in the sense
it was written.

### D2 — the provenance filter matches the positive-predicate shape

**Done.** `is_operator_authored` replaces the two-class negation list. It strips every harness envelope
via `_HARNESS_ENVELOPE_RE` — matched **generically over the tag name**, so a wrapper introduced later is
caught without editing the file — and keeps the turn only when prose residue remains. Re-entry notices
are matched as literal prefixes because they carry no tag.

The failure direction is inverted, which was the point: an unrecognised wrapper leaves no residue and
classifies as **synthetic**, rather than defaulting to "operator" and inflating the survivor count.

**The "by construction" claim was corrected in lock-step.** It appeared twice in the script and once in
the aspect contract. All three are gone; the aspect doc now states explicitly why the surviving set must
*never* be described that way (it retains marker-bearing `assistant` turns, which are not operator
signal). No over-claiming comment was left beside the corrected filter.

### D3 — the verdict stops being purely volume-derived

**Done.** The payload gains `operator_turn_count` (free-form corrections) and `gate_decision_count`
(gate decisions), both distinct from `reduced_turn_count`, and `no_signal` is derived from those two:

```
no_signal = operator_turn_count == 0 and gate_decision_count == 0
```

The previously invisible channel is now readable. Gate decisions are recovered from `tool_result`
blocks by two deliberately narrow tests — the answering `tool_use` id for `AskUserQuestion`
(structural, no phrasing dependency) and verbatim operator-refusal notices — and rendered under an
`operator-decision` role so a reader can tell a gate decision from a correction. The counter fails
toward *not* counting, so ordinary build output is never mistaken for a decision.

### D4 — tests

**Done.** New module `test/plan-marshall/plan-retrospective/test_extract_chat_signal_provenance.py`
(a separate module because the existing one is already 555 lines, over the 400-line budget).

| Plan requirement | Test |
|---|---|
| (a) fixture of harness-injected turns **using real block shapes** | `test_transcript_of_harness_injections_reports_no_signal` — `<system-reminder>`, `<task-notification>`, `<wake>`/`<event>`, the verbatim re-entry notice, and a skill body |
| (b) mirror false-positive guard | `test_genuine_operator_transcript_still_routes_normally`, `test_operator_turn_annotated_by_the_harness_still_routes` |
| (c) counters separate high-volume-low-signal from high-volume-high-signal | `test_high_volume_low_signal_is_distinguishable`, `test_high_volume_high_signal_is_distinguishable`, `test_survivor_count_alone_cannot_separate_the_two` |
| (d) the cheap discriminating regression | `test_low_retention_with_zero_operator_turns_reports_no_signal` |

Plus the predicate's own direction-of-failure guard,
`test_unrecognised_wrapper_fails_toward_synthetic`, which is the property an enumeration cannot have.

**The discriminating regression fails pre-fix — recorded.** Both scenarios were run against
`origin/main`'s reducer and against the fixed one:

| Scenario | Pre-fix | Post-fix |
|---|---|---|
| Transcript of pure harness injections (real block shapes) | kept **4 of 4**, `no_signal: false` — a clean verdict over pure instruction text | kept 0 of 4, `no_signal: true` |
| Low retention, zero operator turns (50 injections + 1 marker-bearing assistant turn) | kept **51 of 51**, `no_signal: false` | kept 1 of 51, `no_signal: true`, `operator=0`, `gate=0` |

The pre-fix numbers are the compounding failure stated as the plan's premise, measured: every
injection class the filter did not recognise *raised* the survivor count and drove the verdict further
from "no signal".

**The validation trap was respected.** No assertion validates by a retention ratio. Every test asserts
the **classification** of a known population of turns — the plan's single most important verification
instruction, and the ratio is treated as an output of the defect rather than a check on it.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py`
(`extract-chat-signal.py`, two test modules) ⇒ **Python changed, full `./pw verify` required and run.**

Per-commit gate: the one commit touching `*.py` was preceded by a clean `./pw quality-gate` —
`mypy … Success: no issues found in 408 source files`, `ruff … All checks passed!`,
`SPDX-header check passed`, `total_issues: 0`, `issues[0]` empty.

_Full `./pw verify` result: recorded below once concluded._

## Findings

_Recorded below._

## Reviewer participation

_Recorded below._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** single interactive cloud session; see PR commit timestamps.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ **Not
  comparable** to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent
  dispatch tree under plan-marshall's own per-task billing boundary. This run has no such boundary, so
  no comparable figure can be produced.

## Contract check (Step 9)

_Recorded below._

## What have we learned (Step 9)

_Recorded below._

## Residue

_Recorded below._
