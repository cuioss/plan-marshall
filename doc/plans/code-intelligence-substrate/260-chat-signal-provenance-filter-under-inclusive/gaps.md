# Gaps — 260-chat-signal-provenance-filter-under-inclusive

The plan's four deliverables shipped and its tests are non-vacuous on every load-bearing line probed
(10 of 10 mutants killed, snapshot-restored). What remains is one reachable hole in the positive
predicate — an envelope whose body quotes its own tag name escapes stripping and scores as operator
signal, the plan's headline failure direction — together with the shipped contract sentence that
guarantee falsifies and the missing regression for it; one classification blur between the two
counters D3 created; one payload-size opportunity the new residue makes free; and two stale records in
the run report, one of them the build gate.

## G1 — Close the same-name unmatched-open hole in envelope pairing

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_chat_provenance.py:125-132`
  (the close-tag branch of `partition_turn`, `depth = positions[-1]`)
- **Evidence:** the close tag pairs with the *innermost* open of its name, so an envelope whose body
  contains an unmatched same-name open token leaves the real outer open unpaired and its text in the
  residue. Measured on a realistic claudeMd-style reminder whose body quotes `<system-reminder>`:
  `is_operator_authored` → `True`, residue `"<system-reminder>\nAs you answer the user's questions…"`.
  End-to-end over 30 identical such turns the reducer reports `raw 30  kept 30  operator 30
  no_signal False`. No test covers the shape: `test_chat_provenance.py:63` and `:73` cover balanced
  same-name nesting only.
- **Why it matters:** a transcript of pure harness instruction text renders as a clean verdict and is
  fed to the Tier-1 LLM prompt as operator signal — the exact compounding failure this plan exists to
  remove, reachable through the mechanism the plan shipped. The trigger is any injected body that
  quotes its own wrapper name, which in this repository includes CLAUDE.md excerpts and sub-agent
  result text that discuss harness block shapes.
- **Action:** make the classification fail toward *synthetic* when **any** pairing interpretation
  leaves no prose residue — e.g. after the linear walk, if unmatched opens remain and at least one
  pair was found, re-pair greedily (each close against the outermost still-open same-name tag) and
  take the emptier residue. Do not change the innermost-first primary pass, which
  `test_nested_same_name_envelope_is_fully_stripped` pins for the balanced case.
- **Done when:** `is_operator_authored('<system-reminder>a<system-reminder>b</system-reminder>')` is
  `False`, a 30-turn transcript of that shape reports `no_signal: true` with `operator_turn_count: 0`,
  and `test_unmatched_open_tag_does_not_swallow_operator_prose`,
  `test_unmatched_close_tag_is_ordinary_text` and the two same-name nesting tests still pass unchanged.
- **Effort:** M
- **Risk if fixed:** a greedy fallback that is too eager could swallow genuine operator prose that
  merely opens with markup — the mirror false-positive this plan warns about. The three
  prose-preserving tests above are the guard, and any new fallback must be mutation-probed in both
  directions.

## G2 — Correct the published failure-direction guarantee, which G1 falsifies

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/chat-history-analysis.md:52`
  (and the scope of the residual gap at `:69-73`)
- **Evidence:** the contract states residue-based classification "fails toward *'synthetic'* instead,
  **for any injection that carries an envelope**", and scopes the published residual gap to
  envelope-*less* notices only. G1 is an envelope-bearing injection that fails toward *operator*.
- **Why it matters:** both script docstrings defer to this document as normative, so it is the spec. A
  guarantee stated more broadly than the code delivers is precisely the over-claim this plan removed
  from the code, reintroduced one file over — and a reader trusting it will not look for G1's class.
- **Action:** if G1 is fixed, restate the guarantee with the pairing rule that now backs it; if G1 is
  deferred, scope the sentence to *well-formed* envelopes and add the same-name unmatched-open case to
  the residual-gap section with its error direction (fail toward operator).
- **Done when:** the sentence at `:52` is true of the shipped code, and the residual-gap section names
  every known escape with its direction.
- **Effort:** S
- **Risk if fixed:** none beyond ordinary doc drift; the section is referenced by both script
  docstrings, so the wording must stay consistent with them.

## G3 — Add the regression for an envelope containing an unmatched same-name open tag

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-retrospective/test_chat_provenance.py:63-83` (`TestSyntheticClasses`)
- **Evidence:** the suite pins `<a><a>x</a></a>`, `<a><a><a></a></a></a>` and `<a><b><a></a></b></a>`
  — every one balanced. The unbalanced `<a>x<a>y</a>` shape is unexercised, which is why G1 survived
  twelve verification rounds and a 240-probe mutation campaign.
- **Why it matters:** without a witness at both the predicate and the verdict level, a later refactor
  of the pairing walk can reintroduce G1 silently; the class already demonstrates that balanced-only
  coverage does not imply the guarantee.
- **Action:** add a predicate-level case and a verdict-level case (a transcript of such turns must
  report `no_signal: true`), naming the tag literally rather than iterating any constant.
- **Done when:** both new tests exist and fail against the current implementation, then pass after G1.
- **Effort:** S
- **Risk if fixed:** none.

## G4 — Re-point the run report's build-gate record at the last Python-changing commit

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/260-chat-signal-provenance-filter-under-inclusive/report-01.md`
  § "Build gate" ("Final gate at `809022d`", "**20371 passed, 14 skipped**", "Any commit landing after
  it is Markdown-only unless this line says otherwise")
- **Evidence:** PR #1271's commit list places `3224ea1` **after** `809022d`, and its file stats show
  three modified Python test modules (`test_chat_gate_decisions.py`, `test_chat_provenance_recognisers.py`,
  `test_extract_chat_signal_io.py`, +75 lines). The PR description records "`./pw verify`: … **20379
  passed**, 14 skipped" — eight more than the report's row. This is the fifth recurrence of the
  stale-build-gate defect the same report catalogues at R6-11, R7-7, R8-13 and R11-10.
- **Why it matters:** the report's build-gate evidence does not cover the Python state that shipped, so
  a reader auditing the lane's Step 5 cannot tell whether the final code was gated. The verify almost
  certainly ran (the 20379 figure); only the record is stale.
- **Action:** correct the section to name `3224ea1` and the figures from the gate that ran there, or
  state plainly that the last gate predates the final Python commit.
- **Done when:** the build-gate section names a commit at or after `3224ea1`, and the pass count it
  quotes matches the one in the PR description.
- **Effort:** S
- **Risk if fixed:** none — a record-only edit to a landed run report.

## G5 — Correct the run report's PR head SHA

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `report-01.md` § "Merge gate" ("head `3224ea1`")
- **Evidence:** PR #1271's merged head is `07c8c00e73596a8d3880f9874d19fa37c2e408d4` — the
  report-finalization commit itself; `3224ea1` is its predecessor.
- **Why it matters:** the merge-gate record names a SHA that was not the head at merge, so the
  "required contexts green on the head SHA" condition cannot be re-checked from the report alone.
- **Action:** state the head as "the report-finalization commit (the report cannot name its own SHA)",
  or record the SHA post-merge.
- **Done when:** the merge-gate row either names `07c8c00` or explains why the head cannot be named.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Stop rendering harness envelopes into the Tier-1 payload

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py:251-253`
  (`render_reduced`) and `:244` (the kept turn stores raw `text`)
- **Evidence:** a kept operator turn is rendered with its attached envelopes intact. Measured: an
  operator turn of 20 characters carrying an 11 KB `<system-reminder>` renders **11,563 bytes** into
  `reduced_transcript`, every byte counted against `read_budget_bytes` and `over_budget`.
  `partition_turn` already computed the residue and it is discarded.
- **Why it matters:** this epic's theme is token reduction; the reducer now knows exactly which bytes
  are harness boilerplate and still ships them to the LLM prompt, and they can push a real transcript
  over the budget into a false Tier-2 refusal. Behaviour is unchanged from pre-fix, so this is an
  unclaimed opportunity rather than a regression.
- **Action:** render the residue (plus recovered operator-bearing text) for kept `user` turns instead
  of the raw text, leaving `assistant` context turns as they are; measure the payload reduction on a
  real transcript before and after.
- **Done when:** a turn of operator prose with an attached reminder yields a `reduced_transcript`
  containing the prose and not the reminder body, `operator_turn_count` is unchanged, and the six chat
  test modules still pass.
- **Effort:** M
- **Risk if fixed:** the Tier-1 prompt loses context that a human reader might have used to interpret a
  turn; and any consumer asserting on the exact `reduced_transcript` text would need updating.

## G7 — Classify text-channel interrupt notices as gate decisions, not free-form corrections

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `_chat_provenance.py:48-52` (`HARNESS_NOTICE_PREFIXES`) vs
  `_chat_gate_decisions.py:33-37` (`OPERATOR_REFUSAL_MARKERS`)
- **Evidence:** `is_operator_authored('[Request interrupted by user]')` → `True`, so the turn scores in
  `operator_turn_count`. The identical wording is listed as a **gate decision** marker on the
  tool-result side. `chat-history-analysis.md:28` defines `operator_turn_count` as *free-form operator
  corrections*.
- **Why it matters:** the two counters exist precisely to keep free-form corrections and gate decisions
  apart; a harness-authored interrupt notice arriving on the text channel lands in the wrong one, so a
  run instrumented only by interrupts reads as having free-form operator prose it never had.
- **Action:** recognise the refusal/interrupt wordings on the text channel too and count them as gate
  decisions (rendered under `OPERATOR_DECISION_ROLE`), sharing one constant between the two modules
  rather than duplicating the literals.
- **Done when:** a user turn whose text is exactly an interrupt notice yields `operator_turn_count: 0`,
  `gate_decision_count: 1`, `no_signal: false`, with the shared constant pinned to its literals in
  both modules' published-constant tests.
- **Effort:** M
- **Risk if fixed:** widening a text-channel prefix list is the direction that can discard a genuine
  operator turn quoting the wording — the anchoring and case-sensitivity guards
  (`test_notice_matching_is_anchored_at_the_start`, `test_notice_matching_is_case_sensitive`) must be
  extended to the new list, not bypassed.

## G8 — Witness the gate-decision channel against a real gated transcript

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-retrospective/test_chat_gate_decisions.py` and the fixture
  builders `_plan_retrospective_fixtures.py:378-385`
- **Evidence:** across 42 reachable transcripts (8,382 parseable turns) there is not one
  `AskUserQuestion` `tool_use` block, so `gate_decision_count` is 0 corpus-wide and the D3 channel has
  never been exercised on real data. The fixtures are hand-built; the run report's residue lists other
  unwitnessed shapes but not this one. (The block *shapes* the code keys on were confirmed against
  real data: `tool_use` carries `{type,id,name,input,caller}`, `tool_result` carries
  `{type,tool_use_id,content}`.)
- **Why it matters:** if a real `AskUserQuestion` answer differs from the fixture in any way the code
  keys on, the whole recovered channel is inert in production and nothing in the suite would notice —
  and the channel exists precisely because it is the one an operator uses on a gated run.
- **Action:** capture one real `AskUserQuestion` prompt/answer pair from a live session into the shared
  fixture module (redacted), and assert the reducer recovers it; record in the aspect contract that the
  fixture is captured rather than constructed.
- **Done when:** at least one gate-decision test drives a transcript fragment captured verbatim from a
  real session, and the captured shape is named as such in the fixture module.
- **Effort:** M
- **Risk if fixed:** a captured fixture can carry session-specific content; it must be redacted, and it
  pins one harness version's shape, so it should complement rather than replace the constructed cases.
