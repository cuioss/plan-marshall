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

**Done.** 95 tests across three modules (26 + 16 + 53 collected), carrying 209 assertions.

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
re-confirmed across every assertion in the three modules by three verification rounds.

## Build gate

`git diff --name-only origin/main...HEAD` includes seven `*.py` files — three scripts, three test
modules and the shared fixture helper (which pytest does not collect) ⇒ **Python changed, full
`./pw verify` required and run.**

Final gate at `8a91744`, read in full (`cmd_verify` returns early on any failed sub-step, so the
printed summary proves all three ran):

| Sub-step | Result |
|---|---|
| quality-gate | mypy clean (410 source files), `ruff … All checks passed!`, `SPDX-header check passed` |
| test-compile | mypy clean (760 files) — the sub-step neither `quality-gate` nor `module-tests` performs |
| module-tests | **20313 passed, 14 skipped**, zero `FAILED`/`ERROR` lines |
| Overall | `=== verify: SUCCESS ===` |

Per-commit gate: every commit touching `*.py` was preceded by a clean `./pw quality-gate`.

## Findings

Five verification rounds plus two defects caught by the run itself — 36 findings, 34 fixed and 2 rejected with reason. Each round targeted the
**previous round's fixes** as a first-class surface, which is what caught most of these — three of the
five rounds found that the prior round's fix had introduced or exposed a new defect. Recorded per
instance.

### Self-caught during implementation (2 findings — both fixed)

Not surfaced by any verification round; found by testing the run's own work before dispatching.
Recorded because a finding is a finding regardless of who found it.

| # | Finding | Disposition |
|---|---|---|
| S1 | The first envelope matcher — a single `<tag>.*?</tag>` regex — was **quadratic on unmatched `<` markup**: every unmatched open tag rescanned to end-of-text before failing. Measured 0.515 s at 0.06 MB, extrapolating to minutes at the 2 MiB read budget — a hang in a pre-pass whose whole purpose is to be cheap | **Fixed** — single linear tokenize-and-pair pass; the same 2.24 MB input strips in 0.072 s |
| S2 | The skip-reason discriminator explained the missing-file path's `no_signal: true` as "it kept zero turns" — the survivor-count semantics the verdict no longer uses. In a section the diff never touched | **Fixed** |

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

### Round 4 (6 findings — all fixed)

| # | Finding | Disposition |
|---|---|---|
| R4-1 | `test_partition_separates_residue_from_recovered_text` asserted the partition on an input where both halves are equal after stripping, so it **passed under an implementation returning the residue twice** — and that mutant admits any turn whose residue is a harness notice but which carries an envelope pair, the exact fail-toward-operator direction this plan closes | **Fixed** — the test now separates prose, envelope and command block three ways; verified by mutation to kill that mutant and two neighbours |
| R4-2 | The aspect contract did not state the precedence rule round 3 introduced, and still said that being listed in `HARNESS_NOTICE_PREFIXES` was sufficient for a turn to be dropped. Both script docstrings defer to that document as normative, so it **is** the spec and it was behind the code | **Fixed** — precedence stated, with its bound and the check ordering |
| R4-3 | Report said six `*.py` files; there are seven | **Fixed** |
| R4-4 | Report conflated 91 tests with 91 assertions | **Fixed** — 94 tests, 207 assertions |
| R4-5 | The coupling registry claimed `AskUserQuestion` lives only in the `_chat_*` modules; it is also in the reducer's `DECISION_MARKERS`, and that registry cites coupling by path | **Fixed** |
| R4-6 | `test_extract_chat_signal_provenance.py` no longer tested provenance, which had moved to `test_chat_provenance.py` | **Fixed** — renamed to `test_extract_chat_signal_verdict.py` |

### Round 5 (6 findings — 5 fixed, 1 rejected)

| # | Finding | Disposition |
|---|---|---|
| R5-1 | The round-4 rename left the sibling module's back-pointer dangling: `test_extract_chat_signal.py`'s docstring named a file that no longer exists, and merged two modules' concerns into one sentence | **Fixed** |
| R5-2 | Mutating `if operator_bearing.strip():` to `if operator_bearing:` survived all 94 tests, and is **not** an equivalent mutant — 3,868 divergences over 26,174 inputs, every one `False → True`. A whitespace-only `<command-args>` (what `/compact ` produces) would be admitted as operator signal | **Fixed** — assertion added pinning that recovered text must be non-whitespace; mutant verified killed |
| R5-3 | "Listing a notice is necessary but **not sufficient**" was scoped to the envelope-less class, and within *that* class listing **is** sufficient — the counterexample requires an envelope. The rule was right, the scope word wrong | **Fixed** |
| R5-4 | The report called the four changed test-tree files "test modules"; one is the shared fixture helper, which pytest does not collect | **Fixed** |
| R5-5 | "797 collected test modules" was the on-disk count; 793 collect (`collect_ignore` excludes 4) | **Fixed** — denominator dropped rather than restated |
| R5-6 | Claimed the report must record that a local `/sync-plugin-cache` is owed, per `CLAUDE.md` | **Rejected** — see below |

**R5-6 rejected, with reason.** `CLAUDE.md` § Standalone Plan Lane does say a lane plan editing
`marketplace/bundles/` "records in its run report that a local sync is owed", but the `cloud-plan-lane`
skill overrides it explicitly: *"A cloud run **neither performs nor owes** a sync"*, and its Step 9
table repeats that a cloud run "**never owes**" one. `CLAUDE.md` itself designates the skill as the
complete working contract, and the plan's first-instruction block states the contract wins on
disagreement. So the report's silence is correct.

⚠ Worth noting that **two verification rounds reached opposite conclusions on this point** — round 3
read the precedence correctly, round 5 did not. That the record was ambiguous enough to split two
readers is itself the signal, so the Contract check below now states the disposition explicitly
instead of leaving it to inference.

### Accepted, not fixed

| Item | Reason |
|---|---|
| `test_extract_chat_signal.py` is 566 lines, over the 400-line `test-module-line-budget` | **Pre-existing** (555 at merge-base). This run added 11 lines to it while splitting the *new* tests into modules that are within budget. The rule is warning-severity and does not gate the build, and 316 test modules in this tree already exceed it. Splitting a pre-existing over-budget module is unrelated maintenance the plan did not request — carried to Residue |

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

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done** | Named above; loaded by bundle path (plugin absent in this session) |
| 2 Branch | **Done** | `claude/chat-signal-provenance-filter-agmptk` — **harness-assigned, kept as-is**, and on `origin` before the first edit |
| 3 Plan directory | **Done** | `doc/plans/code-intelligence-substrate/260-chat-signal-provenance-filter-under-inclusive/plan.md`, opening with the first-instruction block (present on arrival; no repair needed) |
| 4 Implement | **Done** | Every commit carries the `Co-Authored-By` trailer and no "Generated with" footer; deliverable paths staged explicitly, never `git add -A`; no lockfile churn reached a commit |
| 4 Per-commit gate | **Done** | Every commit touching `*.py` preceded by a clean direct `./pw quality-gate` — `ruff … All checks passed!`, `mypy … Success`, `SPDX-header check passed` |
| 4 Pushed | **Done** | Pushed after every commit; `git status -sb` reports no `ahead` |
| 5 Build gate | **Done** | Git-derived verdict (seven `*.py`) and full `./pw verify`, read in full rather than by exit code |
| 6 Verification sub-agent | **Done** | Five rounds, each targeting the prior round's fixes; all findings and dispositions recorded above |
| 7 PR cycle | See Reviewer participation |
| 8 Merge gate | See Residue |
| 8 Bridge | **Done** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory |
| 9 This check | **Done** | This table |
| 9 What have we learned | **Done** | Below |

**GitHub access path:** the GitHub MCP server (no `gh` CLI in this cloud session).
**Branch form:** harness-assigned `claude/*`, kept per the contract's resumability rule.
**Plugin cache sync:** **not owed.** A cloud run neither performs nor owes one — it is a machine-local
build step (§ Scope and precedence). Stated explicitly because two verification rounds disagreed
about it.

One deviation from the contract, recorded rather than narrated as compliance: the contract's Step 6
describes dispatching *a* verification sub-agent, and this run dispatched **five**. Each round was
triggered by the previous round's fixes being a new, unreviewed surface — which the contract itself
requires ("A verification pass that found a defect has not finished"). It is more than the minimum,
not less.

## What have we learned (Step 9)

**One contract change is proposed, on evidence this run produced.**

**The evidence.** Three of five verification rounds found that the *previous round's fix* had
introduced or exposed a new defect — a quadratic hang, a self-poisoning counter, a vacuous test, an
`__all__` that disowned its module's API, and a spec left behind by the code. The contract's § Step 6
already says to sweep the previous round's fixes, and that instruction is what caught them. But the
contract offers no way to tell when the loop should **stop**. This run ran five rounds; rounds 4 and 5
returned progressively smaller findings (a dangling docstring reference, a denominator off by four),
and nothing in the contract distinguishes "keep going, the surface is still hot" from "this is now
costing more than it returns".

**The proposed change.** Add to § Step 6 a stated stopping rule — for example: *the loop may stop when
a round's findings are confined to the run's own records and prose (report figures, docstrings,
cross-references) with no finding touching production behaviour, and the run states that verdict
explicitly in the report.* A round that finds a behavioural defect, however small, always earns
another.

**Why it is worth adding.** Without it, each run improvises the termination decision, and the two
failure modes are opposite and both bad: stopping while behavioural defects are still surfacing (round
4 found a vacuous test masking a live fail-toward-operator path — stopping at round 3 would have
shipped it), or looping indefinitely on prose. A stated rule makes the decision reviewable instead of
a matter of the run's judgement.

**Not self-approved.** Per § Step 9 this is presented to the operator and NOT applied here; it would
ship as its own `chore/` branch touching only the skill, without `skip-bot-review`. It is deliberately
kept out of this PR: two changes with different review audiences in one diff means neither is read
properly.

## Residue

- **`test_extract_chat_signal.py` is 566 lines**, over the warning-level 400-line
  `test-module-line-budget` (555 at merge-base; this branch added 11). Pre-existing and unrelated to
  the plan's brief — a follow-up should split it by behaviour cluster, as this run did for the modules
  it created.
- **`parse_turn` has no production caller** (round-1 F10, rejected). Retained as a documented parsing
  seam with twelve boundary tests. A future run may decide to fold it into `parse_message` +
  `extract_text`; recorded so the question is not re-opened from scratch.
- **The envelope-less notice class remains an enumeration.** `HARNESS_NOTICE_PREFIXES` is a sample by
  construction, and a new tagless harness notice is a false *operator* until it is added — the
  direction that inflates the verdict. Published as a residual gap in the aspect contract. Closing it
  properly needs a structural signal the transcript does not currently carry.
- **The plan's "zero operator turns survived" case was not re-witnessed.** In the one reachable
  transcript the genuine operator turn did survive. Carried forward from the plan, not confirmed here.
- **The `<command-args>`-plus-notice co-occurrence is unwitnessed.** The precedence rule that handles
  it is correct and tested, but no reachable transcript exhibits the shape; verified across 158 user
  turns, zero occurrences.
- **The contract-change proposal above** awaits an operator decision and its own PR.
