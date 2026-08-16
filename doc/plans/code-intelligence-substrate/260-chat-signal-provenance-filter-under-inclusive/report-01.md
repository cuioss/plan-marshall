# Run report — 260-chat-signal-provenance-filter-under-inclusive (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/chat-signal-provenance-filter-agmptk` (harness-assigned, kept as-is)    **PR:** see **Merge gate** below    **Outcome:** completed

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

**Done.** 114 tests across four modules (26 + 19 + 16 + 53 collected), carrying 232 assertions.

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

`git diff --name-only origin/main...HEAD` includes eight `*.py` files — three scripts, four test
modules and the shared fixture helper (which pytest does not collect) ⇒ **Python changed, full
`./pw verify` required and run.**

Final gate at `ce46c30`, read in full (`cmd_verify` returns early on any failed sub-step, so the
printed summary proves all three ran):

| Sub-step | Result |
|---|---|
| quality-gate | mypy clean (410 source files), `ruff … All checks passed!`, `SPDX-header check passed` |
| test-compile | mypy clean (760 files) — the sub-step neither `quality-gate` nor `module-tests` performs |
| module-tests | **20333 passed, 14 skipped**, zero `FAILED`/`ERROR` lines |
| Overall | `=== verify: SUCCESS ===` |

Eight full `./pw verify` runs were performed across the run; this row is the last, at the commit named
above. Any commit landing after it is Markdown-only unless this line says otherwise.

Per-commit gate: every commit touching `*.py` was preceded by a clean `./pw quality-gate`.

## Findings

Seven verification rounds plus two defects caught by the run itself — 68 findings, 66 fixed and 2 rejected with reason. Each round targeted the
**previous round's fixes** as a first-class surface, which is what caught most of these — **six of the
seven** rounds found that the prior round's fix had introduced or exposed a new defect: rounds 2, 3, 4,
5, 6 and 7. Only round 1 had no prior round to check. Recorded per instance.

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
| F10 | `parse_turn` has no production callers | **Rejected** — a documented public parsing-seam helper whose ten boundary tests assert real behaviour; removing it is undeclared collateral the plan did not request. Recorded so the next reviewer does not re-open it blind |

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

### Round 6 (11 findings — 9 fixed at the time, 2 recorded fixed before they were)

Scoped to the previous commit and asked to classify its own findings as behavioural vs. records-only.
It classified **(a) behavioural**, so the loop continued rather than terminating here.

| # | Finding | Disposition |
|---|---|---|
| R6-1 | `head = text.lstrip()` in `extract_gate_decisions` was unpinned and **not** an equivalent mutant. `flatten_tool_result` joins multi-block payloads with `\n`, so a leading empty block shifts a refusal notice off position zero; without the tolerance the decision is lost — under-counting operator signal, driving the verdict toward a false `no_signal: true`. The identical `lstrip()` on the provenance side *was* pinned; this run pinned one half of a pair | **Fixed** — mutant verified killed |
| R6-2 | `if not text.strip():` in the same function was likewise unpinned and non-equivalent: a whitespace-only `AskUserQuestion` payload would count as a gate decision — the same defect class R5-2 had just closed on the provenance side | **Fixed** — mutant verified killed |
| R6-3 | `flatten_tool_result`'s block-list branch had **zero** coverage (module at 76%); no test referenced the function, and the only fixture passed a bare string. That gap is what made R6-1 and R6-2 reachable rather than exotic | **Fixed** — new `test_chat_gate_decisions.py`, 16 tests |
| R6-4 | The newly pinned non-whitespace rule was stated nowhere normative: the contract still said recovered text settles the question, unqualified. **The same defect as R4-2, reintroduced by the commit that fixed its neighbour** | **Fixed** — contract and docstring both qualified |
| R6-5 | The report's aggregate finding count contradicted its own section sub-totals | **Fixed** |
| R6-6 | `test_extract_chat_signal.py` line figure invalidated by the same commit that wrote it (566/+11 → 567/+12) | **Fixed** |
| R6-7 | "twelve boundary tests" for `parse_turn`; there are ten, and there always were | **Fixed** |
| R6-8 | The "what have we learned" evidence list attributed the quadratic hang and the self-poisoning counter to "the previous round's fix", though one was self-caught and the other was round 1. The same section then cited two round-5 rows as "rounds 4 and 5", and contradicted itself about round 4 across consecutive paragraphs | **Fixed** |
| R6-9 | "three of the five rounds" understated — at least four rounds found a defect in the prior round's fix | **Fixed** |
| R6-10 | `**PR:** _see Residue_` and the merge-gate contract row pointed at a Residue section containing neither | **Fixed** |
| R6-11 | The build-gate record named a gate that pre-dated HEAD | **Fixed** — re-gated at HEAD |

⛔ **Two of these dispositions were recorded as fixed when they were not.** R6-10's pointers were
re-aimed at a section that does not exist, and R6-11's build-gate record was never re-pointed at HEAD
at all. Round 7 caught both. This is the failure the contract warns about specifically — *"a findings
table recording a disposition the artifacts contradict … is the one a re-dispatch is least likely to
catch, because the verifier reads the code rather than the record"* — and it happened here twice in
one table. Both are genuinely fixed in the round-7 commit.

### Round 7 (15 findings — all fixed)

Scoped to round 6's commit; classified **(a) behavioural** again, so the loop continued.

| # | Finding | Disposition |
|---|---|---|
| R7-1 | `test_non_tool_result_blocks_are_ignored` was **vacuous for the guard it names**: its fixture carried no `content` key, so the block was dropped by the emptiness check one line later. Removing the type guard left the suite green. Direction: over-counting — a non-`tool_result` block raising `gate_decision_count` | **Fixed** — witness now carries a payload |
| R7-2 | `decision_tool_use_ids`' `tool_use` type guard unpinned; both blocks in the test set `type='tool_use'`, so only `name` discriminated. A differently-typed block bearing the same name would contribute a spurious id | **Fixed** |
| R7-3 | `test_every_refusal_marker_is_recognised` **iterated the constant under test**, so it shrank with the tuple: deleting or mistyping markers 2 and 3 left the suite green while real refusals stopped being recognised. Direction: under-counting, toward a false `no_signal: true`. ⭐ **This plan's own thesis — "a named list is a sample" — turned on the plan's own tests** | **Fixed** — markers named as literals, with the constant asserted against them |
| R7-4 | `OPERATOR_DECISION_TOOL` was referenced only symbolically, so renaming it left the suite green while the entire gated-decision correlation silently died | **Fixed** — pinned to the literal and cross-checked against the reducer's copy |
| R7-5 | `test_non_list_content_yields_no_ids` killed no mutant: a bare string is iterable, so the per-block dict filter carried it, not the list guard | **Fixed** — non-iterable and dict witnesses |
| R7-6 | `isinstance(use_id, str)` unpinned; an unhashable id would raise and abort the whole reduction. The sibling guard was pinned — one half of a pair again | **Fixed** |
| R7-7 | The build-gate record still named a gate three commits behind HEAD. **R6-11 recorded this "Fixed" when the commit never touched the section** | **Fixed** — re-gated at HEAD |
| R7-8 | "seven `*.py` files" was eight | **Fixed** |
| R7-9 | The PR and merge-gate pointers resolved to a section that does not exist. **R6-10 recorded this "Fixed"; the fix made it worse** — previously it pointed at a real section lacking the content | **Fixed** — a Merge gate section now exists and carries both |
| R7-10 | "four of the six rounds" undercounted; the report's own rows show six of seven | **Fixed** |
| R7-11 | The what-have-we-learned evidence cited instances spanning three rounds to support a "four rounds" claim, and named a different round set than the Findings header | **Fixed** — one instance per round, both statements reconciled |
| R7-12 | The round count contradicted itself three ways across the document (six / five / four) | **Fixed** |
| R7-13 | Round 6 was placed before round 5 in a per-round record | **Fixed** |
| R7-14 | Round 6's header claimed all 11 fixed; two were not | **Fixed** |
| R7-15 | The round-6 docstring edit left a 134-character line in a docstring wrapping at ~78; `E501` is in ruff's ignore list, so nothing caught it | **Fixed** |

### Accepted, not fixed

| Item | Reason |
|---|---|
| `test_extract_chat_signal.py` is 567 lines, over the 400-line `test-module-line-budget` | **Pre-existing** (555 at merge-base). This run added 12 lines to it while splitting the *new* tests into modules that are within budget. The rule is warning-severity and does not gate the build, and 316 test modules in this tree already exceed it. Splitting a pre-existing over-budget module is unrelated maintenance the plan did not request — carried to Residue |

## Merge gate

**PR:** _filled in when the PR is opened; this section is the single place the run records it._

Conditions per the lane contract:

1. **Required contexts green on the head SHA** — read from GitHub's own computation over the ruleset
   (`mergeable_state`), never from a ruleset-config call, which is unreachable on the cloud MCP path.
2. **Every PR comment handled** — fixed, or answered on the thread.
3. **This report finalized and pushed** as the last pre-merge commit, before auto-merge is armed:
   arming locks the branch, and a report finalized afterwards can never reach this PR.
4. **Review-coverage shortfall disclosed** — a disclosure, not a gate; see Reviewer participation.

## Reviewer participation

Population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc, not a
list transcribed here: **`sourcery-ai`, `coderabbitai`, `cuioss-review-bot`** (M = 3).

_Verdicts recorded below once the PR review cycle has run._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** one interactive cloud session; see the PR's commit timestamps. Seven full `./pw verify`
  runs at ~6–8 minutes each, and seven verification sub-agents.
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
| 6 Verification sub-agent | **Done** | Seven rounds, each targeting the prior round's fixes; all findings and dispositions recorded above |
| 7 PR cycle | See Reviewer participation |
| 8 Merge gate | See **Merge gate** below |
| 8 Bridge | **Done** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory |
| 9 This check | **Done** | This table |
| 9 What have we learned | **Done** | Below |

**GitHub access path:** the GitHub MCP server (no `gh` CLI in this cloud session).
**Branch form:** harness-assigned `claude/*`, kept per the contract's resumability rule.
**Plugin cache sync:** **not owed.** A cloud run neither performs nor owes one — it is a machine-local
build step (§ Scope and precedence). Stated explicitly because two verification rounds disagreed
about it.

One deviation from the contract, recorded rather than narrated as compliance: the contract's Step 6
describes dispatching *a* verification sub-agent, and this run dispatched **seven**. Each round was
triggered by the previous round's fixes being a new, unreviewed surface — which the contract itself
requires ("A verification pass that found a defect has not finished"). It is more than the minimum,
not less.

## What have we learned (Step 9)

**One contract change is proposed, on evidence this run produced.**

**The evidence.** Six of seven verification rounds found that the *previous round's fix* had introduced
or exposed a new defect, one per round: round 2 on round 1's `command-name` addition (R2-3); round 3 on
round 2's `__all__`, which disowned its module's API (N1); round 4 on round 3's vacuous test, masking a
live fail-toward-operator path (R4-1); round 5 on round 4's dangling rename reference (R5-1); round 6
on round 5's rule pinned in a test but never written into the spec (R6-4); and round 7 on round 6's
two dispositions recorded as fixed before they were (R7-7, R7-9). The contract's § Step 6 already says
to sweep the previous round's fixes, and that instruction is what caught every one of them.

But the contract offers no way to tell when the loop should **stop**. This run ran seven rounds. Rounds 6 and 7
were each dispatched with an explicit instruction to classify their findings as behavioural or
records-only; both returned **behavioural** — round 6 found three unpinned non-equivalent mutants in a
module sitting at 76% coverage, round 7 found five more in the test module round 6 had just written —
so the loop continued both times. That classification was improvised for this run; nothing in the
contract asks for it.

**The proposed change.** Add to § Step 6 a stated stopping rule — for example: *the loop may stop when
a round's findings are confined to the run's own records and prose (report figures, docstrings,
cross-references) with no finding touching production behaviour, and the run states that verdict
explicitly in the report.* A round that finds a behavioural defect, however small, always earns
another.

**Why it is worth adding.** Without it, each run improvises the termination decision, and the two
failure modes are opposite and both bad. Stopping too early ships defects: round 4 found a vacuous
test masking a live fail-toward-operator path, so stopping at round 3 would have shipped it; round 6
found three unpinned non-equivalent mutants, so stopping at round 5 would have shipped those; and
round 7 found that two round-6 dispositions were recorded as fixed before they were, so stopping at
round 6 would have shipped a report that misdescribed its own artifacts.
Looping too long burns budget re-checking prose. A stated rule makes the decision reviewable instead
of a matter of the run's judgement — and this run's own experience is that the rule has to be applied
by the *verifier*, not the author, since the author is the party motivated to stop.

**Not self-approved.** Per § Step 9 this is presented to the operator and NOT applied here; it would
ship as its own `chore/` branch touching only the skill, without `skip-bot-review`. It is deliberately
kept out of this PR: two changes with different review audiences in one diff means neither is read
properly.

## Residue

- **`test_extract_chat_signal.py` is 567 lines**, over the warning-level 400-line
  `test-module-line-budget` (555 at merge-base; this branch added 12). Pre-existing and unrelated to
  the plan's brief — a follow-up should split it by behaviour cluster, as this run did for the modules
  it created.
- **`parse_turn` has no production caller** (round-1 F10, rejected). Retained as a documented parsing
  seam with ten boundary tests. A future run may decide to fold it into `parse_message` +
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
