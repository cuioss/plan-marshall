# Gaps — 260-chat-signal-provenance-filter-under-inclusive

The plan's four deliverables shipped and its tests are non-vacuous on every load-bearing line probed
(10 of 10 mutants killed, snapshot-restored, re-run independently). What remains is one hole in the
positive predicate — an envelope whose body carries an unbalanced token of its **own outermost tag
name** escapes stripping and scores as operator signal, the plan's headline failure direction —
together with the shipped contract sentence that guarantee falsifies and the missing regression for it;
one classification blur between the two counters D3 created; one payload-size opportunity the new
residue makes free; and two stale records in the run report, one of them the build gate. The predicate
hole is **latent**: it does not occur anywhere in the reachable 81-transcript corpus.

## G1 — Close the same-name unbalanced-token hole in envelope pairing

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_chat_provenance.py:123-137`
  (the tokenizer loop of `partition_turn`; the close-tag branch at `:125-132`, `depth = positions[-1]`
  and `_drop_above(depth)`)
- **Evidence:** two variants, both verified end-to-end at 30 turns → `raw 30  kept 30  operator 30
  no_signal False`:
  - **(a) quoted unmatched open.** The close tag pairs with the *innermost* open of its name, so a
    quoted `<tag>` in the body takes the pairing and the real outer open is never matched.
    `is_operator_authored('<system-reminder>a<system-reminder>b</system-reminder>')` → `True`.
  - **(b) quoted close.** A quoted `</tag>` pairs with the outer open and ends the envelope early;
    `_drop_above(0)` clears the stack, so the real trailing close becomes ordinary text and the whole
    tail is residue. `is_operator_authored('<sr>a</sr>b</sr>')` → `True`, residue `'b</sr>'`.

  No test covers either shape: `test_chat_provenance.py:63` and `:73` cover balanced same-name nesting,
  and `:159` (`test_unmatched_close_tag_is_ordinary_text`) covers a close with no open of that name —
  the opposite configuration.
- **Why it matters:** a transcript of pure harness instruction text renders as a clean verdict, and the
  escaping text is additionally rendered into `reduced_transcript` under the `user:` label and fed to
  the Tier-1 LLM prompt as operator signal — the exact compounding failure this plan exists to remove,
  reachable through the mechanism the plan shipped.
- **Reachability (measured, and asymmetric between the variants):** the trigger is content — an
  injected body quoting its **own outermost** wrapper name. Quoting a *nested* name is harmless
  (verified). Variant (a) additionally requires the quoted open to sit outside every nested pair,
  because the `_drop_above` unwind at a nested close restores the outer tag's stack entry; it therefore
  fires on a flat `<system-reminder>` but **not** inside a `<task-notification>`'s `<result>` body
  (verified: that case still reports `no_signal: true`). Variant (b) fires from anywhere in the body.
  On the harness surface represented by the reachable corpus, `<system-reminder>` never arrives as an
  inline `user` text block (0 of 6,190 `user` turns); the only enveloped inline turns are 36
  `<task-notification>` blocks. **So (b) is the variant reachable on the real block shape**, and its
  plausible source is agent-authored prose inside `<result>` discussing harness block shapes. Neither
  variant occurs in the corpus today (0 same-name quotes, 0 operator-classified turns carrying markup),
  so this is latent rather than active — but it is content-reachable, not fixture-only.
- **Action:** make the classification fail toward *synthetic* when **any** pairing interpretation
  leaves no prose residue, covering both variants. A greedy re-pair (each close against the outermost
  still-open same-name tag, taking the emptier residue) closes (a) but **not** (b) — under greedy
  pairing the quoted close still pairs with the outer open and yields the same tail. Cover (b) as well:
  e.g. when the turn's first token is an open `<T>` and its last token is a close `</T>`, treat the
  whole span as one envelope and take that residue if it is emptier. Do not change the innermost-first
  primary pass, which `test_nested_same_name_envelope_is_fully_stripped` pins for the balanced case,
  and note the constraint that rules out the naive form of that fallback: any whole-span
  reinterpretation must still run the `OPERATOR_BEARING_TAGS` recovery, or a bare
  `<command-args>do it</command-args>` — first token an open, last token its close — would strip to an
  empty residue and the operator's typed instruction would be dropped, which
  `test_a_command_with_arguments_routes_normally` pins.
- **Done when:** all three of `is_operator_authored('<system-reminder>a<system-reminder>b</system-reminder>')`,
  `is_operator_authored('<sr>a</sr>b</sr>')` and the `<task-notification>`-with-quoted-`</task-notification>`
  shape are `False`; a 30-turn transcript of each shape reports `no_signal: true` with
  `operator_turn_count: 0`; and the **four prose-preserving tests** —
  `test_unmatched_open_tag_does_not_swallow_operator_prose`,
  `test_unmatched_close_tag_is_ordinary_text`, `test_prose_after_a_trailing_envelope_survives` and
  `test_a_command_with_arguments_routes_normally` (the `OPERATOR_BEARING_TAGS` recovery named in the
  Action) — plus the two same-name nesting tests still pass unchanged.
- **Effort:** M
- **Risk if fixed:** a fallback that is too eager could swallow genuine operator prose that merely
  opens with markup, or prose that both begins and ends with the same tag — the mirror false-positive
  this plan warns about. The four prose-preserving tests named above are the guard, and any new
  fallback must be mutation-probed in both directions.

## G2 — Correct the published failure-direction guarantee, which G1 falsifies

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/chat-history-analysis.md:52`
  (and the scope of the residual gap at `:69-73`)
- **Evidence:** the contract states residue-based classification "fails toward *'synthetic'* instead,
  **for any injection that carries an envelope**", and scopes the published residual gap to
  envelope-*less* notices only. G1 is an envelope-bearing injection that fails toward *operator*.
  A neighbouring claim needs the same scoping treatment though it is not itself false: `:43` and the
  matching docstring at `_chat_provenance.py:93-96` say an unmatched tag "cannot suppress the
  stripping of a well-formed envelope that follows it". That is literally true — verified,
  `partition_turn('<sr>x<sr>body</sr>')` does strip the inner pair — but the surviving unmatched token
  *is itself* the residue that makes the turn read as operator, which is the outcome the sentence is
  cited to rule out.
- **Why it matters:** both script docstrings defer to this document as normative, so it is the spec. A
  guarantee stated more broadly than the code delivers is precisely the over-claim this plan removed
  from the code, reintroduced one file over — and a reader trusting it will not look for G1's class.
- **Action:** if G1 is fixed, restate the guarantee with the pairing rule that now backs it; if G1 is
  deferred, scope the sentence to envelopes whose body carries no unbalanced token of the envelope's
  own tag name, and add **both** G1 variants (quoted unmatched open, quoted close) to the residual-gap
  section with their error direction (fail toward operator) and the note that only the second fires
  inside a nested envelope such as `<task-notification>`.
- **Done when:** the sentence at `:52` is true of the shipped code, and the residual-gap section names
  every known escape with its direction — including both G1 variants while G1 is open.
- **Effort:** S
- **Risk if fixed:** none beyond ordinary doc drift; the section is referenced by both script
  docstrings, so the wording must stay consistent with them.

## G3 — Add the regressions for an envelope carrying an unbalanced token of its own tag name

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-retrospective/test_chat_provenance.py:63-83` (`TestSyntheticClasses`)
- **Evidence:** the suite pins `<a><a>x</a></a>`, `<a><a><a></a></a></a>` and `<a><b><a></a></b></a>`
  — every one balanced. Both unbalanced shapes, `<a>x<a>y</a>` and `<a>x</a>y</a>`, are unexercised,
  which is why G1 survived twelve verification rounds and a 240-probe mutation campaign. The nearest
  existing case, `test_unmatched_close_tag_is_ordinary_text` (`:159`), pins a close tag with **no**
  open of that name and so cannot see either shape.
- **Why it matters:** without a witness at both the predicate and the verdict level, a later refactor
  of the pairing walk can reintroduce G1 silently; the class already demonstrates that balanced-only
  coverage does not imply the guarantee. Two cases are needed rather than one because the two variants
  fail through different branches and a fix for one does not imply a fix for the other.
- **Action:** add predicate-level cases for **both** shapes and a verdict-level case for each (a
  transcript of such turns must report `no_signal: true`), naming the tag literally rather than
  iterating any constant. Include one case in the real `<task-notification>`/`<result>` nesting, since
  the flat-envelope case does not discriminate it: a quoted open inside `<result>` is already
  classified synthetic today, so a test using only that shape would pass pre-fix and be vacuous.
- **Done when:** the new tests exist, each **fails** against the current implementation (verified by
  running them before the fix), and all pass after G1.
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
- **Evidence:** a kept operator turn is rendered with its attached envelopes intact. Reproducible
  measurement against the shipped `SYSTEM_REMINDER` fixture: a `user` turn of 26 bytes of operator
  prose plus the 166-byte fixture reminder renders **199 bytes** into `reduced_transcript` where the
  residue `partition_turn` already computed is **27** — ~86 % of the payload is envelope, and every
  byte counts against `read_budget_bytes` and `over_budget`. The proportion scales with the reminder.
- **Why it matters:** this epic's theme is token reduction; the reducer now knows exactly which bytes
  are harness boilerplate and still ships them to the LLM prompt, and in principle they can push a
  real transcript over the budget into a false Tier-2 refusal. Behaviour is unchanged from pre-fix, so
  this is an unclaimed opportunity rather than a regression.
- ⚠ **Scope, measured:** across the 81 reachable transcripts the 82 kept operator turns carry **0
  bytes** of envelope — residue equals raw text for every one, because the reminder class does not
  reach the reducer as an inline `user` text block on this harness surface. The saving is real only
  where the attached-envelope shape occurs, which no reachable transcript currently exhibits; the
  false-Tier-2-refusal argument is prospective, not observed. Measure the real saving before spending
  the effort.
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
  `operator_turn_count` (re-verified end-to-end: `operator 1, gate 0, no_signal false`). The identical
  wording is listed as a **gate decision** marker on the tool-result side.
  `chat-history-analysis.md:28` defines `operator_turn_count` as *free-form operator corrections*.
  Corpus occurrences of the shape on the text channel: **0 of 6,190** `user` turns, so the
  misattribution is latent.
- **Why it matters:** the two counters exist precisely to keep free-form corrections and gate decisions
  apart; a harness-authored interrupt notice arriving on the text channel lands in the wrong one, so a
  run instrumented only by interrupts reads as having free-form operator prose it never had. Note the
  bound on the harm, which is why this is `low` and not `high`: an interrupt *is* an operator action,
  so `no_signal: false` remains the correct verdict — only the attribution between the two counters
  is wrong.
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
- **Evidence:** across 81 reachable transcripts (16,163 parseable turns) `decision_tool_use_ids`
  returns not one `AskUserQuestion` `tool_use` block — 27 files contain the literal string, none as a
  tool call — so `gate_decision_count` is 0 corpus-wide and the D3 channel has never been exercised on
  real data. The fixtures are hand-built; the run report's residue lists other unwitnessed shapes but
  not this one. (The block *shapes* the code keys on were confirmed against real data: `tool_use`
  carries `{type,id,name,input,caller}`, `tool_result` carries `{type,tool_use_id,content}`.)
- **Why it matters:** if a real `AskUserQuestion` answer differs from the fixture in any way the code
  keys on, the whole recovered channel is inert in production and nothing in the suite would notice —
  and the channel exists precisely because it is the one an operator uses on a gated run.
- **Action:** capture one real `AskUserQuestion` prompt/answer pair from a live session into the shared
  fixture module (redacted), and assert the reducer recovers it; record in the aspect contract that the
  fixture is captured rather than constructed.
- **Done when:** at least one gate-decision test drives a transcript fragment captured verbatim from a
  real session, and the captured shape is named as such in the fixture module. ⚠ This entry is
  **contingent on an input that does not exist yet**: no reachable transcript contains an
  `AskUserQuestion` exchange, so a fix run must first produce one (drive a gated run) or wait for one.
  A run that cannot obtain a real exchange should record that and close the entry as blocked rather
  than substitute another hand-built fixture, which would add nothing.
- **Effort:** M
- **Risk if fixed:** a captured fixture can carry session-specific content; it must be redacted, and it
  pins one harness version's shape, so it should complement rather than replace the constructed cases.
