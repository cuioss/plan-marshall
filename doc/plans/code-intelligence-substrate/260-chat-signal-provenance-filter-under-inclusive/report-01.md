# Run report — 260-chat-signal-provenance-filter-under-inclusive (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/chat-signal-provenance-filter-agmptk` (harness-assigned, kept as-is)    **PR:** _see Residue_    **Outcome:** completed

## Skills loaded

Loaded by bundle path (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the `plan-marshall`
plugin is not installed in this cloud session, so the `Skill: {notation}` route was not used. No skill
was unobtainable by both routes.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `plan-marshall:persona-implementer` | Production code |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

`pm-documents:ref-asciidoc` was **not** loaded: the only documentation touched is Markdown, not `.adoc`.

## Deliverables

### D1 — GATE: enumerate what actually survives, by provenance (mutates nothing)

**Done.** The plan records its six measured retention instances as machine-local and unreachable from
this clone and directs the run to reproduce instead. One real transcript was reachable: this session's
own JSONL under `~/.claude/projects/`.

**Reproduction, first-party, re-measured at the end of the run** (the session grew throughout, so the
figures below are the ones current at the moment of this claim, not the first reading):

| Measure | Pre-fix reducer | Post-fix reducer |
|---|---|---|
| Raw parseable turns | 457 | 457 |
| Kept | 8 | 2 |
| Retention | 1.8 % | — |
| `operator_turn_count` | not computed | **1** |
| Verdict | `no_signal: false` — **clean** | `no_signal: false` (correctly — one real operator turn) |

The plan's headline shape reproduces: a fraction-of-one-percent retention reported as a clean verdict,
with the pre-fix code counting **8** turns as signal where only **1** is operator-authored.

⚠ **What this run did NOT re-establish.** In this transcript the genuine operator turn *did* survive,
so the plan's "zero operator-authored turns survived" case was not re-witnessed first-party. It is
carried forward from the plan, not confirmed here.

**Claims confirmed first-party at HEAD** by reading the pre-fix script:

| Claim | Confirmed |
|---|---|
| The verdict is a pure survivor count | Yes — `no_signal = len(turns) == 0` |
| The filter drops only a blank-turn class and one marker-matched injection shape | Yes |
| The docstring asserts "by construction" | Yes — twice: module docstring and the comment above `no_signal` |
| Operator decisions arrive as tool results, invisible to the reducer | Yes — every `tool_result` block yields empty text via `extract_text`, so the whole channel is dropped as "empty" |

**Marker inventory.** Derived from real transcripts and **published** in
`references/chat-history-analysis.md` § "The harness-injection marker inventory" — a run report is a
record, not publication, so it lives in the aspect contract.

The decisive D1 finding is recorded there: **the inventory cannot be completed by enumeration.** The
same logical injection is persisted differently by different harness surfaces — a block rendered
inline on one surface arrives as an `attachment` on another — so any list keyed on the shapes one
transcript happens to contain is a sample. That is the plan's own "a named list is a sample" rule
applied to the *previous* remediation, and it is the evidence for the positive predicate rather than
merely an argument for it.

**D1's threshold call.** The plan leaves to D1 whether the routing threshold changes. **Decision:
`no_signal` is re-keyed from survivor volume onto operator-authored counts.** Not discretionary — the
Goal ("a reduction that dropped every operator-decision turn cannot render as clean") and D4(c) both
require it. The numeric read budget (`DEFAULT_READ_BUDGET_BYTES = 2 * 1024 * 1024`) is **unchanged**,
so the out-of-scope exclusion on "changing the routing threshold" is respected as written.

### D2 — the provenance filter matches the positive-predicate shape

**Done.** `is_operator_authored` (`_chat_provenance.py`) replaces the two-class negation list. It
strips every harness envelope — matched **generically over the tag name**, so a wrapper introduced
later is caught without editing the file — and keeps the turn only when prose residue remains.

Three rules keep the residue trustworthy, each earned from a verification finding: only a **matched**
open/close pair is an envelope; only the **outermost** pair is stripped; and an envelope named in
`OPERATOR_BEARING_TAGS` contributes its **inner text**, because the wrapper is the harness's but the
words inside are the operator's.

**The "by construction" claim was corrected in lock-step.** It appeared twice in the script and once in
the aspect contract. All three are gone, and the contract now states explicitly why the surviving set
must never be described that way — it retains marker-bearing `assistant` turns, which are not operator
signal. No over-claiming comment was left beside the corrected filter.

**Published limit.** The structural guarantee covers **envelope-bearing** injections only. A tagless
harness notice leaves full residue and reads as operator unless its wording is listed in
`HARNESS_NOTICE_PREFIXES` — an enumeration, and therefore a sample. This is published as a residual
gap rather than papered over, because an inventory that hid an observed miss would repeat the defect it
documents.

### D3 — the verdict stops being purely volume-derived

**Done.** The payload gains `operator_turn_count` (free-form corrections) and `gate_decision_count`
(gate decisions), both distinct from `reduced_turn_count`, and the verdict reads only those two:

```
no_signal = operator_turn_count == 0 and gate_decision_count == 0
```

The previously invisible channel is now readable: gate decisions are recovered from `tool_result`
blocks by two deliberately narrow tests — the answering `tool_use` id for `AskUserQuestion`
(structural, no phrasing dependency) and verbatim operator-refusal notices anchored at the payload
start — and rendered under an `operator-decision` role. The counter fails toward *not* counting.

`reduced_turn_count + dropped_turn_count == raw_turn_count` still holds; recovered decisions were never
raw turns, so they are extra transcript entries counted by `gate_decision_count` alone.

### D4 — tests

**Done.** 91 tests across three modules (22 + 16 + 53 collected).

| Plan requirement | Test |
|---|---|
| (a) fixture of harness-injected turns **using real block shapes** | `test_transcript_of_harness_injections_reports_no_signal` — `<system-reminder>`, the real nested `<task-notification>`, `<wake>`/`<event>`, the verbatim re-entry notice, a skill body |
| (b) mirror false-positive guard | `test_genuine_operator_transcript_still_routes_normally`, `test_operator_turn_annotated_by_the_harness_still_routes`, `test_a_command_with_arguments_routes_normally` |
| (c) counters separate high-volume-low-signal from high-volume-high-signal | `test_high_volume_low_signal_is_distinguishable`, `test_high_volume_high_signal_is_distinguishable`, `test_survivor_count_alone_cannot_separate_the_two` |
| (d) the cheap discriminating regression | `test_low_retention_with_zero_operator_turns_reports_no_signal` |

Plus the property an enumeration cannot have: `test_unrecognised_wrapper_fails_toward_synthetic`.

**The discriminating regression fails pre-fix — recorded.** Measured against `origin/main`'s reducer
using the **shipped fixtures** (not a paraphrase of them):

| Scenario | Pre-fix | Post-fix |
|---|---|---|
| Transcript of pure harness injections (5 turns, real block shapes) | kept **4 of 5**, `no_signal: false` — a clean verdict over instruction text | kept 0 of 5, `no_signal: true` |
| Low retention, zero operator turns (50 injections + 1 marker-bearing assistant turn) | kept **51 of 51**, `no_signal: false` | kept 1 of 51, `no_signal: true`, `operator=0`, `gate=0` |

(The one skill body in the first fixture was already dropped pre-fix — it is one of the two originally
enumerated classes — hence 4 of 5, not 5 of 5.)

These numbers *are* the compounding failure the plan states as its premise, measured: every injection
class the filter did not recognise raised the survivor count and drove the verdict further from "no
signal".

**The validation trap was respected.** No assertion validates by a retention ratio. Every test asserts
the **classification of a known population of turns** — the plan's single most important verification
instruction — and the ratio is treated as an output of the defect, not a check on it. Independently
re-confirmed across all 91 assertions by two verification rounds.

## Build gate

`git diff --name-only origin/main...HEAD` includes six `*.py` files ⇒ **Python changed, full
`./pw verify` required and run.**

Final gate at `c77cdf4`, read in full (`cmd_verify` returns early on any failed sub-step, so the
printed summary proves all three ran):

| Sub-step | Result |
|---|---|
| quality-gate | mypy clean (410 source files), `ruff … All checks passed!`, `SPDX-header check passed` |
| test-compile | mypy clean (760 files) — the sub-step neither `quality-gate` nor `module-tests` performs |
| module-tests | **20310 passed, 14 skipped**, zero `FAILED`/`ERROR` lines |
| Overall | `=== verify: SUCCESS ===` |

Per-commit gate: every commit touching `*.py` was preceded by a clean `./pw quality-gate`.

## Findings

Four verification rounds. Each round targeted the **previous round's fixes** as a first-class surface,
which is what caught most of these — three of the four rounds found that the prior round's fix had
introduced or exposed a new defect. Recorded per instance.

### Round 1 (10 findings — 9 fixed, 1 rejected)

| # | Finding | Disposition |
|---|---|---|
| F1 | Test module docstring still described the retired two-class enumeration | **Fixed** |
| F2 | Same docstring stated the retired survivor-count `no_signal` | **Fixed** |
| F3 | **Critical.** `OPERATOR_REFUSAL_MARKERS` matched as an unanchored substring of any `tool_result`, so a plain `Read` of the module *declaring* those markers scored an operator gate decision and produced a clean verdict — a synthetic input raising an operator-signal counter, self-poisoning because the reducer runs over this project's own sessions | **Fixed** — anchored as a prefix of the whole payload |
| F4 | The module docstring's failure-direction claim, re-broken by this run's own tokenizer commit | **Fixed** |
| F5 | Same claim stale in the aspect contract (separate file, separate consumer kind) | **Fixed** |
| F6 | A slash command classified **synthetic**, discarding the `<command-args>` carrying the operator's instruction — the primary channel operators drive runs through here; a false refusal, the mirror of the defect being fixed | **Fixed** — `OPERATOR_BEARING_TAGS` |
| F7 | `reduced_turn_count` silently changed meaning, breaking `reduced + dropped == raw` for existing callers | **Fixed** |
| F8 | A stray top-level unmatched tag suppressed envelope stripping for the rest of a turn — a fail-toward-**operator** path, the direction that manufactures the false clean verdict | **Fixed** — outermost-matched-pair rule |
| F9 | Run report referenced a symbol the tokenizer commit had deleted | **Fixed** in this rewrite |
| F10 | `parse_turn` has no production callers | **Rejected** — a documented public parsing-seam helper whose twelve boundary tests assert real behaviour; removing it is undeclared collateral the plan did not request. Recorded so the next reviewer does not re-open it blind |

### Round 2 (8 findings — all fixed)

| # | Finding | Disposition |
|---|---|---|
| R2-1 | `reduced_transcript`'s "non-empty only when both flags are false" contract, true only while `no_signal` meant zero survivors — and this run's own shipped test pinned the contradicting state | **Fixed** |
| R2-2 | The published inventory said command expansions strip to empty residue, contradicting the allow-list three paragraphs above it — both written in the same commit | **Fixed** |
| R2-3 | `command-name` in `OPERATOR_BEARING_TAGS` (this run's round-1 addition) let a bare `/clear` or `/compact` score an operator turn and carry the verdict alone; undocumented, untested, and contradicting the contract's definition of `operator_turn_count` | **Fixed** — only `<command-args>` remains |
| R2-4 | The failure-direction guarantee stated unconditionally, though it holds only for envelope-bearing injections. On the real transcript, a tagless `Stop hook feedback:` turn was **1 of 2 survivors** | **Fixed** — claim scoped, gap published, notice added to the backstop |
| R2-5..7 | Three untested paths in the newly written pairing machinery (nested same-name envelopes, self-closing tags, notice anchoring) — all surviving mutants | **Fixed** — tests added |
| R2-8 | A provably unreachable secondary sort key | **Fixed** — removed; safety later confirmed by 40 000 fuzzed inputs |

### Round 3 (10 findings — all fixed)

| # | Finding | Disposition |
|---|---|---|
| N1 | `__all__` listed exactly the twelve re-exports and none of the module's own twelve names, declaring `cmd_run`, `Reduction` and `DEFAULT_READ_BUDGET_BYTES` private | **Fixed** — `__all__` dropped |
| N2 | Six of the twelve re-exports were dead, imported only so `__all__` could name them | **Fixed** — four used names imported; tests load the owning module |
| N3 | The notice check ran on the residue, and the residue carries text recovered from `<command-args>` — so a turn opening with a harness notice and continuing into a slash command was discarded, taking the operator's instruction with it. **A hole that grows: every prefix added to the backstop widens it**, so round 2's own fix enlarged it | **Fixed** — `partition_turn` returns recovered operator text separately |
| N4 | The argument-less-command narrowing was pinned at predicate level only, not at the verdict it produces | **Fixed** — verdict-level tests both ways |
| N5 | The aspect contract's definition bullet still called the notice class "re-entry" while naming three members elsewhere | **Fixed** |
| N6 | `reduce_transcript`'s docstring carried the same retired term | **Fixed** |
| N7 | Five report claims contradicted the tree | **Fixed** in this rewrite |
| N8 | `report-01.md` committed with mode `100755` | **Fixed** — `100644` |
| N9 | `doc/refactor/08-claude-coupling-inventory.md` cites coupling **by path**; the split left the harness recognisers unlisted | **Fixed** |
| N10 | The `TASK_NOTIFICATION` fixture was an invented flat shape while the real nested one was present in the clone — D4(a) asks for real block shapes. No bug masked, but the nested-envelope-containing-prose case went unexercised | **Fixed** — real shape adopted |

### Round 4

_Recorded below._

### Accepted, not fixed

| Item | Reason |
|---|---|
| `test_extract_chat_signal.py` is 566 lines, over the 400-line `test-module-line-budget` | **Pre-existing** (555 at merge-base). This run added 11 lines to it while splitting the *new* tests into modules that are within budget. The rule is warning-severity and does not gate the build. Splitting a pre-existing over-budget module is unrelated maintenance the plan did not request — carried to Residue |

## Reviewer participation

Population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc, not a
list transcribed here: **`sourcery-ai`, `coderabbitai`, `cuioss-review-bot`** (M = 3).

_Verdicts recorded below once the PR review cycle has run._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** one interactive cloud session; see the PR's commit timestamps. Four `./pw verify`
  runs at ~6–8 minutes each, and four verification sub-agents.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ **Not
  comparable** to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent
  dispatch tree under plan-marshall's own per-task billing boundary. This run has no such boundary, so
  no comparable figure can be produced, and none is offered.

## Contract check (Step 9)

_Recorded below._

## What have we learned (Step 9)

_Recorded below._

## Residue

_Recorded below._
