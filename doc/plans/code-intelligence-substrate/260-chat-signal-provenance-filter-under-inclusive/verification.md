# Verification — 260-chat-signal-provenance-filter-under-inclusive

**Audited:** `plan.md`, `report-01.md` (no other sibling files present)
**Tree state:** `e678dcb` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The plan's four deliverables are implemented, in the shape the plan specified, and the shipped tests
are non-vacuous on every load-bearing line probed (10 of 10 mutants killed). One fail-toward-operator
hole survives in the positive predicate — an envelope whose body quotes its **own outermost tag name**
without balancing it escapes stripping, is classified operator-authored, and carries `no_signal: false`
on its own — and the aspect contract publishes a guarantee that this counterexample falsifies. The hole
has **two** variants (a quoted unmatched open, and a quoted close that terminates the envelope early);
only the second fires on the one envelope class observed reaching the reducer as inline text. Neither
is present in the reachable transcript corpus, so the hole is latent rather than active. One
run-report record (the build gate) is stale against the PR's own history.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | GATE: enumerate survivors by provenance; publish the marker inventory; record the allow-list decision | "Done" — inventory published in the aspect contract; reproduction re-measured first-party | Inventory published at `chat-history-analysis.md:54-73`, with the "cannot be completed by enumeration" finding and the allow-list rationale at `_chat_provenance.py:55-64`. Reproduction independently re-derived on a live transcript and on the shipped fixtures | CONFIRMED |
| D2 | Provenance filter matches the positive-predicate shape; "by construction" corrected in lock-step | "Done" — `is_operator_authored` replaces the two-class negation list; all three "by construction" sites gone | `_chat_provenance.py:180-206` implements the positive predicate; zero `by construction` occurrences remain in the three chat files or their tests; the contract states why it must never be said (`chat-history-analysis.md:81`). **But** an envelope whose body carries an unbalanced token of its own outermost tag name — an unmatched open, or a close that terminates it early — leaves residue and reads as operator, falsifying the published failure-direction guarantee | PARTIAL |
| D3 | Verdict stops being volume-derived; two counters; gate channel visible | "Done" — `operator_turn_count` + `gate_decision_count`, `no_signal` reads only those | `extract-chat-signal.py:302` (`no_signal = not reduction.has_operator_signal`), `:125-127`, `:239-247`; gate recovery in `_chat_gate_decisions.py:85-107` under role `operator-decision`; `reduced + dropped == raw` preserved | CONFIRMED |
| D4 | Tests (a)–(c) plus the discriminating regression | "160 tests across six modules (34+14+22+17+20+53), 303 assertions"; discriminating regression fails pre-fix | Re-derived: 160 collected, per-module counts match exactly, 303 `assert` statements. All named tests exist. Pre-fix/post-fix fixture measurements reproduce exactly | CONFIRMED |

## Per-deliverable detail

### D1 — GATE: enumerate what actually survives, by provenance

- **Required (plan):** "the marker inventory is derived from real transcripts and published, with the
  allow-list decision recorded rather than re-argued."
- **Claimed (report):** inventory published in `references/chat-history-analysis.md` § "The
  harness-injection marker inventory"; decisive finding recorded that the inventory cannot be
  completed by enumeration; threshold call recorded (re-key `no_signal`, leave
  `DEFAULT_READ_BUDGET_BYTES` untouched).
- **Found:**
  - Inventory table: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/chat-history-analysis.md:54-67`,
    six classes with "reaches the reducer as" / "recognised by" columns, followed by the
    cannot-be-enumerated finding at `:67` and the residual gap at `:69-73`.
  - Allow-list decision recorded, not re-argued: `_chat_provenance.py:54-64` (the rationale comment
    plus the `OPERATOR_BEARING_TAGS` binding at `:64`) and `chat-history-analysis.md:44`.
  - Threshold untouched: `DEFAULT_READ_BUDGET_BYTES = 2 * 1024 * 1024` at `extract-chat-signal.py:94`
    is byte-identical to the pre-fix value (`git show 8a11858^:…:96`).
- **Checks run:**
  - The report's own session figures (457 raw / 8 kept / 1 operator) are **not re-derivable** — that
    session is machine-local. I reproduced the *shape* independently on this session's live transcript
    (`/root/.claude/projects/-home-user-plan-marshall/a758250e-….jsonl`): pre-fix reducer (extracted
    from `8a11858^`) kept **18 of 266** turns with `no_signal: false`; the shipped reducer kept **1**,
    `operator_turn_count: 1`, `gate_decision_count: 0`. The one survivor is the operator's actual
    prompt; the pre-fix survivors are `<task-notification>` blocks and stop-hook notices.
  - Corpus sweep, **re-measured independently**: **81** reachable transcripts / **16,163** parseable
    turns / **6,190** `user` turns → **82** kept operator turns, **zero** containing any markup token
    and **zero** with a notice-like head. No harness turn is admitted anywhere in the reachable corpus.
    (The corpus is machine-local and grows with every session on this box — an earlier pass over the
    same directory read 42 / 8,382 / 42. The counts are therefore a snapshot, not a stable figure; the
    qualitative result — zero admitted harness turns — reproduces at both sizes.)
- **Verdict:** CONFIRMED — published, derived from real transcripts, decision recorded.

### D2 — the provenance filter matches the positive-predicate shape

- **Required (plan):** "the filter identifies provenance positively and the comment matches the code";
  the "by construction" claim corrected in lock-step.
- **Claimed (report):** `is_operator_authored` strips every harness envelope, matched generically over
  the tag name; three residue rules; all three "by construction" sites removed; the only published
  limit is the envelope-*less* notice class.
- **Found:**
  - Positive predicate: `_chat_provenance.py:180-206`; envelope pairing `:110-159`; generic tag regex
    `:37`; notice backstop `:48-52`, `:170-177`; skill-load recogniser `:67-78`.
  - "By construction": `grep` over the skill tree and the test tree returns **zero** occurrences in
    the three chat modules or their tests. The pre-fix file carried two (module docstring at
    `8a11858^:…:38`, verdict comment at `:262-263`); the aspect contract now carries the corrective
    statement instead (`chat-history-analysis.md:81`).
  - Mutation probes (see Test adequacy) confirm the predicate's rules are pinned, including the
    residue-vs-raw notice check, the operator-bearing allow-list, the trailing-prose tail, and the
    non-whitespace rule.
- **Defect found:** an envelope whose body carries an **unbalanced token of its own outermost tag
  name** escapes stripping and reads as operator. Two distinct mechanisms, both in
  `partition_turn` (`_chat_provenance.py:123-137`), both fail-toward-*operator*:

  - **(a) quoted unmatched open.** The close-tag branch pairs with `positions[-1]` — the *innermost*
    open of that name (`:125-132`). A quoted `<tag>` in the body takes the pairing, the real outer
    open is never matched, and everything from the outer `<tag>` up to the quoted one is returned as
    residue. Verified: `is_operator_authored('<system-reminder>a<system-reminder>b</system-reminder>')`
    → `True`.
  - **(b) quoted close.** A quoted `</tag>` in the body pairs with the outer open and terminates the
    envelope early (`:126-132`); `_drop_above(0)` clears the whole stack, so the real trailing close
    is then an unmatched close and is kept as ordinary text. Everything after the quoted close is
    residue. Verified: `is_operator_authored('<sr>a</sr>b</sr>')` → `True`, residue `'b</sr>'`.

  Both were reproduced end-to-end. 30 identical turns, each wholly one envelope whose body carries the
  unbalanced token, reduce to:

  ```
  raw 30  kept 30  operator 30  no_signal False
  ```

  — the plan's headline failure, a clean verdict over pure instruction text, reachable through the
  mechanism the plan shipped. It falsifies the guarantee published at `chat-history-analysis.md:52`
  ("Residue-based classification fails toward *"synthetic"* instead, **for any injection that carries
  an envelope**"). The balanced cases are tested (`test_chat_provenance.py:63`, `:73`); neither
  unbalanced case is.

  **Which variant is reachable is not symmetric, and this is the load-bearing detail.** Variant (a)
  needs the quoted open to sit **outside every nested pair** in the envelope: if it sits inside one,
  the `_drop_above` unwind at that pair's close restores the outer tag's stack entry and the envelope
  strips cleanly. Measured on the *real* block shape — a `<task-notification>` whose agent prose lives
  inside `<result>…</result>` — a quoted `<task-notification>` inside the `<result>` body classifies
  **synthetic** (`no_signal: true`, operator 0 over 30 turns); the same turn with a quoted
  `</task-notification>` classifies **operator** (`raw 30 kept 30 operator 30 no_signal False`).
  Variant (a) fires on a flat single-level envelope such as `<system-reminder>`; variant (b) fires
  from anywhere in the body regardless of nesting.
- **Verdict:** PARTIAL — implemented as specified and the over-claiming comment is genuinely gone, but
  the structural guarantee has an untested, undisclosed hole in the plan's own failure direction.

### D3 — the verdict stops being purely volume-derived

- **Required (plan):** an operator-authored count distinct from the raw survivor count; gate-style
  operator decisions retained as a distinct signal class; two counters; the two states distinguishable
  in the output.
- **Claimed (report):** payload gains `operator_turn_count` and `gate_decision_count`;
  `no_signal = operator_turn_count == 0 and gate_decision_count == 0`; gate decisions recovered by two
  narrow tests and rendered under `operator-decision`; `reduced + dropped == raw` still holds.
- **Found:** `Reduction` fields at `extract-chat-signal.py:113-117`; `has_operator_signal` at `:125-127`;
  verdict at `:302`; payload keys at `:309-317`; the skipped branch carries both counters at `:289-290`.
  Gate recovery: `_chat_gate_decisions.py:51-66` (tool-use id correlation, structural) and `:85-107`
  (refusal notices anchored at payload start, `head.startswith`), role label at `:41`.
  Real block shapes match the fixtures exactly — a live transcript's `tool_use` carries
  `{type,id,name,input,caller}` and its `tool_result` carries `{type,tool_use_id,content}`.
- **Checks run:** `test_survivor_count_alone_cannot_separate_the_two` asserts equal
  `reduced_turn_count` with unequal `operator_turn_count`; I re-ran it and mutated the verdict back to
  `kept_raw_count == 0` (pre-fix semantics) — killed.
- **Verdict:** CONFIRMED.

### D4 — tests

- **Required (plan):** (a) a fixture of harness-injected turns **in real block shapes** classified
  healthy by the old code and correctly by the new; (b) the mirror false-positive guard; (c) counters
  separating high-volume-low-signal from high-volume-high-signal; plus the cheap discriminating
  regression.
- **Claimed (report):** 160 tests / 303 assertions across six modules; the pre-fix table (4 of 5 kept,
  51 of 51 kept, both `no_signal: false`).
- **Found / re-derived at audit time:**
  - `uv run python -m pytest <six modules> -o addopts="" -q` → **160 passed**; per module
    22 / 34 / 14 / 53 / 20 / 17 — the same multiset the report states.
  - `assert` statements across the six modules: **303**.
  - All eight named tests plus `test_unrecognised_wrapper_fails_toward_synthetic` collect.
  - Pre-fix vs post-fix on the **shipped** fixtures, re-measured by loading the pre-fix reducer from
    `8a11858^`:

    | Fixture | Pre-fix | Post-fix |
    |---|---|---|
    | 5 harness injections (real block shapes) | `reduced_turn_count: 4`, `no_signal: false` | `0`, `no_signal: true` |
    | 50 injections + 1 marker-bearing assistant turn | `51`, `no_signal: false` | `1`, `no_signal: true`, operator 0, gate 0 |

    Exactly the report's table.
  - Fixture realism: `TASK_NOTIFICATION` (`_plan_retrospective_fixtures.py:324-339`) is the nested,
    attribute-less shape with prose inside `<result>`, annotated as observed verbatim; I confirmed the
    same nested shape appears in the live transcript.
  - Validation-trap discipline: no assertion in the six modules validates by a retention ratio — every
    one asserts the classification of a known turn population.
- **Verdict:** CONFIRMED (with the test-gap noted under D2).

## Correctness review

Read in full: `extract-chat-signal.py` (359 lines), `_chat_provenance.py` (207), `_chat_gate_decisions.py`
(108), and the aspect contract. Probed the predicate with 16 adversarial-but-realistic inputs.

**Defect 1 — an envelope whose body carries an unbalanced token of its own outermost tag name is
classified operator-authored.** `_chat_provenance.py:123-137`. Failing inputs, both verified:

```text
(a) <system-reminder>
    As you answer the user's questions, you can use the following context:
    # claudeMd
    Tag-wrapped instruction blocks (`<system-reminder>`, `<task-notification>`) are recognised …
    </system-reminder>

(b) <task-notification>
    <result>Verification complete. The reducer strips a
    </task-notification> envelope generically over the tag name.
    </result>
    </task-notification>
```

`is_operator_authored` → `True` in both. (a) leaves residue `"<system-reminder>\nAs you answer the
user's questions…"`; (b) leaves residue `" envelope generically over the tag name.\n</result>\n</task-notification>"`.
Consequence: a wholly harness-authored turn raises `operator_turn_count` and can flip `no_signal` to
`false` alone — measured for each shape at 30 turns → `operator 30`, `no_signal False`.

**Reachability, stated precisely** (this is a prompt-injection-adjacent surface, so the distinction
between "reachable from real content" and "reachable from a hand-built fixture" matters):

- The trigger is content-dependent, not structural: an injected body must quote its **own outermost**
  wrapper name. Quoting a *nested* tag name is harmless — verified,
  `<task-notification><result>…<result>…</result></task-notification>` still strips to empty.
- Of the two shapes, **(b) is the one that fires on the block shape actually observed reaching the
  reducer**. Across the 81-transcript corpus the only wholly-enveloped inline `user` text turns are
  36 `<task-notification>` blocks; `<system-reminder>` reaches the reducer as an inline text block in
  **0 of 6,190** `user` turns on this harness surface (it arrives as an `attachment` with no
  `message`, exactly as the inventory row at `chat-history-analysis.md:64` predicts). Shape (a) — the
  flat `<system-reminder>` demonstration — is therefore a fixture-shaped input on this surface,
  though the contract itself notes at `:62` that other harness surfaces do persist such blocks inline.
- **Neither shape occurs in the corpus**: 0 same-name quotes inside the 36 enveloped turns, and 0
  operator-classified turns containing any markup token. The defect is **latent, not active**.
- The plausible real trigger is agent-authored prose inside a `<task-notification>`'s `<result>` —
  a sub-agent reporting on harness block shapes, which is precisely what work on this reducer
  produces. A secondary concern follows from that: text which escapes stripping is not merely
  miscounted, it is rendered into `reduced_transcript` under the `user:` label and fed to the Tier-1
  LLM prompt as operator signal. Third-party text (a quoted review comment, quoted file content) that
  reaches a sub-agent's final message could therefore both inflate the verdict and reach that prompt
  labelled as the operator. That path is multi-step and unwitnessed; it is recorded as a reason the
  fix direction matters, not as an observed exploit.

**Defect 2 — the contract publishes a guarantee this falsifies.** `chat-history-analysis.md:52` states
the residue rule fails toward *synthetic* "for any injection that carries an envelope", and `:69-73`
scopes the published residual gap to envelope-*less* notices only. Defect 1 is an envelope-bearing
injection failing toward *operator*, so the published limit is incomplete.

**Observation 3 — kept turns carry their envelopes into the Tier-1 payload.**
`extract-chat-signal.py:251-253` renders `turn['text']`, the raw text, not the residue
`partition_turn` already computed. Reproducible measurement, using the shipped `SYSTEM_REMINDER`
fixture so a later reader can re-take it: a `user` turn of 26 bytes of operator prose plus the 166-byte
fixture reminder renders **199 bytes** into `reduced_transcript` where the residue is **27**; ~86 % of
the payload is envelope the reducer had already identified. The ratio scales with the reminder, so a
multi-kilobyte one dominates the turn entirely. Behaviour is unchanged from pre-fix, so it is not a
regression — but the epic's theme is token reduction and the residue is now available for free.
⚠ Scope caveat, measured: across the 81-transcript corpus the 82 kept operator turns carry **0 bytes**
of envelope (residue == raw for every one), because the reminder class does not reach the reducer as
inline text on this surface. The waste is real where the shape occurs, but no reachable transcript
exhibits it today, and the "can push a real transcript over budget" argument is therefore prospective.

**Observation 4 — counter-class blur.** A harness interrupt notice arriving as plain user *text*
(`[Request interrupted by user]`) is not in `HARNESS_NOTICE_PREFIXES`, so it scores in
`operator_turn_count` (defined at `chat-history-analysis.md:28` as *free-form operator corrections*)
rather than in `gate_decision_count`, where the same wording is listed
(`_chat_gate_decisions.py:33-37`). Re-verified: `is_operator_authored('[Request interrupted by user]')`
→ `True`; end-to-end that single turn yields `operator 1, gate 0, no_signal False`. The verdict is
still right — an interrupt *is* an operator action — and the misattribution is confined to which
counter moves; the split D3 exists to create is what fails. Corpus occurrences of the shape on the
text channel: **0 of 6,190** `user` turns, so this too is latent.

**Observation 5 — the gate-decision channel has never run on real data.** `decision_tool_use_ids`
found **0** `AskUserQuestion` `tool_use` blocks across all 81 transcripts (27 files contain the
literal string, none as a tool call), so `gate_decision_count` is 0 corpus-wide and every test of the
D3 channel drives a hand-built fixture. The block shapes the code keys on were confirmed against real
data; the exchange it keys on was not. Tracked as G8.

**Checked and found sound:** the linear tokenizer terminates on unmatched markup; unmatched close tags
are ordinary text; the outermost-pair cursor skips nested pairs; `OPERATOR_BEARING_TAGS` recovery is
top-level only; self-closing operator-bearing tags recover nothing; skill-load detection requires both
marker and heading and survives CRLF; the notice check is anchored and case-sensitive; UTF-8 byte
measurement, `errors='replace'`, the `is_file` guard and the `FileNotFoundError`-only except clause are
all as the docstrings state; the missing-file branch emits both counters; `reduced + dropped == raw`
holds; and `DECISION_MARKERS`-bearing assistant turns move no operator counter.

## Test adequacy

| Deliverable | Covering tests |
|---|---|
| D2 predicate | `test_chat_provenance.py` (34), `test_chat_provenance_recognisers.py` (14) |
| D3 counters + gate channel | `test_extract_chat_signal_verdict.py` (17), `test_chat_gate_decisions.py` (22) |
| D4(a) / discriminating regression | `test_extract_chat_signal_verdict.py:217`, `:241` |
| D4(b) mirror guard | `:258`, `:283`, `:308` |
| D4(c) counters | `:136`, `:146`, `:155` |
| I/O and scalar edges | `test_extract_chat_signal_io.py` (20), `test_extract_chat_signal.py` (53) |

**No vacuity found on any probed line.** Ten mutants applied to load-bearing production lines, each
with a byte snapshot taken and written back by this audit (never `git checkout`), run under
`PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged per run:

| Mutant | Result |
|---|---|
| `no_signal = not has_operator_signal` → `kept_raw_count == 0` (pre-fix semantics) | KILLED |
| `is_harness_notice(residue)` → `is_harness_notice(text)` | KILLED |
| `OPERATOR_BEARING_TAGS` → `frozenset()` | KILLED |
| skill-load early return removed | KILLED |
| refusal marker `head.startswith` → `marker in text` (the F3 defect) | KILLED |
| outermost-pair `if block_start < cursor: continue` removed | KILLED |
| trailing-prose `parts.append(text[cursor:])` removed | KILLED |
| gate-decision `role == 'user'` guard → `True` | KILLED — but **not** by either module this table maps to D3; the killer is `test_extract_chat_signal_io.py::TestRoleGuards::test_a_tool_result_on_an_assistant_turn_is_not_a_gate_decision`. Run against `test_extract_chat_signal_verdict.py` alone the mutant survives (17 passed) |
| operator-count `role == 'user'` guard → `True` | KILLED |
| `operator_bearing.strip()` → `operator_bearing` | KILLED |

The whole sweep was re-run independently for this review: byte snapshots taken to
`$TMPDIR/adv-260-…-mutsweep/` and written back by the reviewer (never `git checkout`/`restore`/`stash`),
`PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged per run. All ten reproduce as KILLED.
`git status --porcelain` shows none of the three production files modified after the sweep.

**Gap:** no test exercises an envelope whose body carries an *unbalanced* token of its own outermost
tag name — either variant behind Defect 1. `test_nested_same_name_envelope_is_fully_stripped` and
`test_three_level_same_name_nesting_is_fully_stripped` cover balanced nesting only, and
`test_unmatched_close_tag_is_ordinary_text` covers a close tag with **no** open of that name, which is
the opposite configuration.

## Report accuracy

Claims re-derived and **held**: the ten changed `*.py` files (three scripts, six test modules, one
fixture helper); 160 tests and their six per-module counts; 303 assertions; the pre-fix/post-fix
fixture table; module sizes 359/207/108; `test_extract_chat_signal.py` 555 at merge-base → 575 now;
the `test-module-line-budget` rule being `severity='warning'`; "316 test modules already exceed it"
(318 today, the tree having moved); the four first-party pre-fix claims (verdict was `len(turns) == 0`;
two enumerated classes; "by construction" twice; `tool_result` blocks yield empty text); the finding
arithmetic (151 = 147 + 2 + 2, and the per-round sub-totals sum to 151); eleven of twelve rounds
(rounds 2–12); and the reviewer table (`cuioss-review-bot` published "PR contains tests / No security
concerns identified / No major issues detected"; `coderabbitai` rate-limited with a countdown;
`sourcery-ai` refused on the 150000-diff-character ceiling; coverage 1 of 3).

**False / stale claims:**

1. **The build-gate record.** The report states *"Final gate at `809022d`, read in full"* with
   *"module-tests **20371 passed, 14 skipped**"*, and *"Any commit landing after it is Markdown-only
   unless this line says otherwise."* That is false: commit `3224ea1` landed **after** `809022d` and
   modified three Python test modules (`test_chat_gate_decisions.py`, `test_chat_provenance_recognisers.py`,
   `test_extract_chat_signal_io.py`; +75 lines). The PR description itself records
   *"`./pw verify`: … 20379 passed, 14 skipped"* — eight more tests, consistent with a verify run at
   `3224ea1` that the report's build-gate row was never re-pointed at. This is the fifth recurrence of
   the exact stale-build-gate defect the report catalogues at R6-11, R7-7, R8-13 and R11-10.
2. **The PR head SHA.** The report states *"head `3224ea1`"*; the merged head is `07c8c00` (the
   report-finalization commit itself). Structurally unavoidable for a report finalized as the last
   commit, but the stated value is not the head that merged.
3. **Unverifiable, not counted against the report:** the D1 session figures (457 / 8 / 1.8 % / 1) refer
   to a machine-local transcript; the "Sixteen full `./pw verify` runs"; and the quoted CodeRabbit
   countdown ("51 minutes" vs the comment body's current "49 minutes" — that body is updated in place
   by the bot).

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| `test_extract_chat_signal.py` over the 400-line budget | **Open** | `wc -l` → 575; rule is `severity='warning'` (`_analyze_test_conventions.py:61`) |
| `parse_turn` has no production caller | **Open** | Only definition site in `marketplace/bundles/**` is `extract-chat-signal.py:199`; 15 references, all in `test_extract_chat_signal.py` |
| Envelope-less notice class remains an enumeration | **Open, published** | `_chat_provenance.py:48-52`; gap published at `chat-history-analysis.md:69-73`. Confirmed live: a new tagless notice ("System notice: …") classifies operator |
| "Zero operator turns survived" case not re-witnessed | **Still unwitnessed** | 42-transcript sweep: the genuine operator turn survives in every transcript that has one |
| `<command-args>`-plus-notice co-occurrence unwitnessed | **Still unwitnessed** | No such turn in the reachable corpus |
| Contract-change proposal (stopping rule) awaiting an operator decision | **Closed by a later plan** | `2b5d1aa` — "chore(cloud-plan-lane): fold the two stopping rules into one (#1273)", explicitly "Follow-up to #1271"; later refined by `18b1b5c` (#1292) |

Additionally, the run's N9/R4-5 edit to `doc/refactor/08-claude-coupling-inventory.md` became moot when
`bb85899` (#1275) retired `doc/refactor/`; the coupling entry survives at
`doc/plans/multiplattform/reference/coupling-inventory.md:84`, naming all three chat modules and the
`AskUserQuestion` literal. No loss.

## Out-of-scope and collateral

All four exclusions respected. The footprint/coverage-recall surface (`_footprint_*.py`) is untouched
by `8a11858`; no routing-checker or report-section-partition file appears in the diff; and the routing
threshold is unchanged (`DEFAULT_READ_BUDGET_BYTES` byte-identical pre and post). The one change
outside the plan's Expected surface — four lines in the Claude-coupling inventory — is declared in the
report (N9, R4-5). The three-way module split is not listed in the plan's Expected surface but is
declared in both the report and the PR body and is required by the skill's own 400-line modularization
rule.

## Method and coverage

- Read `plan.md`, `report-01.md`, the three production modules, the aspect contract, the six chat test
  modules' relevant sections, and the shared fixture block shapes.
- Re-derived every count stated above at audit time (`pytest --collect-only`, `grep -c "^\s*assert "`,
  `wc -l`); no number was copied from the report.
- Extracted the pre-fix reducer from `8a11858^` and ran it, and the shipped reducer, over (a) the two
  shipped fixtures and (b) a live 265-turn session transcript.
- Swept 42 reachable transcripts (8,382 parseable turns) for false positives; none.
- Ran 10 targeted mutants with self-taken byte snapshots; all killed; tree verified clean afterwards.
- Read PR #1271 through the GitHub MCP server: commit list, per-commit file stats for `3224ea1`,
  reviews, comments, and the merged head SHA.
- **Could not check:** the report's own session figures (457 raw / 8 kept / 1.8 %) and the "zero
  operator turns survived" incident — the transcripts are machine-local and unreachable, exactly as
  the plan states; the "sixteen `./pw verify` runs" count; and the live behaviour of the gate-decision
  channel against a real `AskUserQuestion` exchange — no such tool call exists anywhere in the 42
  reachable transcripts, though the block shapes the code keys on were confirmed against real data.
- Deliberately did not run `./pw verify` (out of scope for this audit and multi-minute).
