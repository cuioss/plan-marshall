# PLAN-LB-125: The review gate does not accept a second disabled test in an accepted class, and triage honours a dropped functional review

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-125-review-gate-jvm-acceptance-and-triage-exemption.md` and is queued as one row file, `queue/PLAN-LB-125.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's rulings of 2026-11-07: decision 19 (the review-gate fix for PLAN-LB-119 stays a separate plan) and ruling 23
> (the triage exemption of parked PLAN-LB-75 D1 folds into it, with verify-first clauses). It is the fix plan for PLAN-LB-119 (PR 1925,
> merge `f84eb0e36`; report `landings/PLAN-LB-119.md`); every finding id (L1-n, L3-n, C-n) is that report's. Every cited line was
> re-read at HEAD `5cd8ccd92`; no commit after `f84eb0e36` touches the cited source files. Points re-read at their lines are OBSERVED;
> claims about reach are HYPOTHESIS and are settled first.
>
> Ruling check. D1 is a fail-open on the test-integrity gate (a second test stops running unseen) for the JVM languages this
> repository's consumers use: blocking. D2 makes triage file blocking findings for criteria the completion gate already exempts, which
> then block completion through the findings half: blocking in normal use if its first verify-first clause holds. D3 to D5 are minor.
> Stop rule: a fix plan is staged only for a major that fails open or falsely blocks a gate in normal use; minors ride along on files
> being touched. No token or measurement work. No Sonar.

## Objective

PLAN-LB-119 made a filter acceptance name the identity of each marked test, so a later skip of a further test is a new row. That holds
for Python and JS. A Java or Kotlin test file has no method identity: its markers are collected per CLASS as a set, so after an
operator accepts `@Disabled` on one method of `FooTest`, a second `@Disabled` in the same class produces the same row and is accepted,
or raises no row at all when the class already carried the marker at the merge base. Separately, the finalize triage source reads
every frozen criterion of a plan whose functional review was dropped as open and files it as a blocking finding, while the completion
gate exempts exactly that case.

After this plan a JVM test method is its own unit, an acceptance pairs each marker with its test, triage applies the completion gate's
drop exemption through one reader, and the minors the landing left are closed or stated.

## Deliverables

1. **A disabled JVM test is decided per method, and an acceptance pairs each marker with its test.** *(L3-1, L1-3, L3-9; blocking)*
   - Settle first by reading: no header arm parses a Java or Kotlin method (`_TEST_DEF_RE` is a Python `def`, `_JS_TEST_RE` a JS/TS call,
     `_review_support_integrity.py:87,102`), so a JVM file falls back to `_class_spans` in `_function_assertion_counts` (`:336-338`),
     `_identity_bodies` (`:357`) and `_identity_markers` (`:968`); `SKIP_MARKERS` (`:71-82`) holds `@Disabled` and `@Ignore` and is
     matched as a substring.
   - Decide at outline, and record once in the module docstring and in the identity sentence of `review-rubric.md:41`: (a) a JVM method
     header arm giving `Class::method`, the Python scheme, so all three readers see the method; or (b) the filter row counts marked
     methods per class. (a) also closes the base-marker mask; (b) must count occurrences, not a set, to close it. Under either, an
     annotation above the class header belongs to the class, not to its first method.
   - The acceptance key pairs a marker with its test: `{test, marker}` pairs replace the two separate supersets of
     `review_support.py:319-328`, the writer key `_criteria_snapshot.py:406-423` carries the pairs, and the close and the check read
     one key. An entry recorded under the previous key re-raises its row; it never accepts more.

   *Done when:* a Java fixture whose branch adds `@Disabled` to `a()` of `FooTest` (accepted by a close) and then to `b()` raises a row
   not covered by the acceptance (red at HEAD); the same class with only `a()` disabled raises nothing beyond the accepted row
   (control); a Java fixture whose base already disables `a()` and whose branch disables `b()` raises a row (red); an accepted
   `{skip on a, xfail on b}` with `b` changed from xfail to skip raises a row (red); the existing Python and JS fixtures keep their
   results.

2. **Triage honours a dropped functional review.** *(PLAN-LB-75 D1, triage half; blocking if clause (1) holds)*
   - Verify-first (1), before any edit, recorded in the PR: does a plan whose functional review the manifest dropped (surgical scope,
     `functional_review: off`) enter finalize triage and file its frozen criteria? Read the finalize dispatcher's `finalize-feedback`
     and `ci-verify` dispatch (`verification-feedback.md:24-25`), the manifest rows that drop the review (`decision-rules.md`), and
     `triage.md:40-64`, which reads `open-criteria` before Step 1 and files each open row with `--severity error`. If no such plan
     reaches triage, D2 is closed with the reason and only the `triage.md` text bullet ships.
   - Verify-first (2): is the re-freeze route of PLAN-LB-75 D2 reachable in a normal run, i.e. can an outline re-entry halt on
     `refreeze_requires_decision`? `phase-3-outline/SKILL.md:677` reads every non-success `snapshot-criteria` as "the outline could not
     be read", and no workflow document names `criteria-refreeze-authorize`. If reachable, the outline routes that result to the
     operator question and the verb; if not, the bullet is dropped and the PR says so.
   - If (1) holds: the triage source applies the exemption the completion gate applies (`_cmd_lifecycle.py:1384-1385`), including its
     rule that a deleted or tampered snapshot still reports open. One reader decides the drop: `_criteria_snapshot` may not import
     `manage-status` (`_criteria_snapshot.py:32-39`), so the reader moves to a layer both import, or `open-criteria` returns a named
     `review_dropped` source the triage text reads; decided at outline.
   - `triage.md:62` and `:64` state the exemptions, and the duplicated sentence appears once.
   - Not carried (stays with parked PLAN-LB-75): persisting `criteria_gate` and a producer for the `functional_review_drop_reason`
     field (read at `_cmd_lifecycle.py:1288`).

   *Done when:* `review_support open-criteria` for a fixture with a dropped review and frozen criteria reports no open row to file
   (red at HEAD); a fixture with a scheduled review and an ungraded criterion still reports it (control); a dropped-review fixture
   with a tampered snapshot still reports open (control); a doc test pins the corrected `triage.md` sentence once.

3. **The placement and the coverage marker fail closed.** *(separable; L3-3, L3-2, C9, L3-8)*
   - The placement falls back to the mutable `commit` when `originalCommit` and the review commit are both null
     (`github_ops.py:727-733`). Decide at outline: refuse the placement (no credit) when no stable field exists, or state why the
     fallback is safe.
   - A quoted coverage marker, or one after an unterminated fence, reads as no marker (`_github_pr.py:475-489`), and
     `named_commit_currency` then falls to the token arm (`:590-597`); the re-review gate admits by substring (`github_re_review.py:1720`)
     and asks the parser only whether a marker is present (`:1726`). Route the gates through the parser, and decide whether an
     unterminated fence before a marker is a gate state.
   - The payload is read only on the opener's line (`_github_pr.py:449-460`) while the comment shows a two-line marker (`:387-388`):
     read a multi-line payload, or state the single-line limit.

   *Done when:* a node with both stable fields null is not credited (red); an in-progress summary with an unclosed fence before its
   marker and the head SHA in its body is neither credited nor admitted as an answer (red); a finished single-line marker is still
   credited (control).

4. **The close and the move proof state their reach.** *(separable; L3-4, L3-5)*
   - The validated-head refusal applies to every step's close (`_cmd_loop_back.py:633-643`): pin it with a test for a non-review
     step, or narrow it to the review steps; decided at outline.
   - With no head on the prior record, accepted removals are read at the closing head (`:727-729`), a head nobody validated: refuse
     the accept in that case, or state why the re-derivation is sound.
   - The move proof keys on identity name plus assertion-line text (`_review_support_integrity.py:370-372,691-696`), so a deleted JS
     `it('renders')` with a snapshot assertion is credited by an unrelated new `it('renders')` carrying the same line: qualify a JS
     identity by its enclosing `describe`, or state the limit in the docstring.

   *Done when:* each choice is pinned by a fixture; the JS case raises a row (red) or the docstring states the limit.

5. **The documents and tests state what they pin.** *(separable; L1-6, L1-8, L1-7, L3-7, L3-11)*
   - `review-rubric.md:42` names `criterion_unparsed` and states the parser-2 admission as the code does (generation-2 replay,
     `_criteria_snapshot.py:1450-1455`), not only the prefix rule.
   - `test_loop_back_close.py:449-453` says in its docstring why the control's setup changed.
   - The PLAN-LB-119 D7 weak tests: the PLAN-LB-106 D4 ingestion test exercises the fetch layer; the currency test asserts
     `pre_merge_gate merge`, not the classifier; a Sourcery body with signal plus footer is tested beside the footer-only case
     (`test_comments_stage_fetch.py:1032-1054`).
   - The splitter's limit (`_plan_parsing.py:64`, not fence-aware, fails closed through `criterion_unparsed`) is stated in its docstring.
   - One owner for the CommonMark fence rule (`_github_pr.py:492-506`, `_criteria_snapshot.py:103-128`).

   *Done when:* a read of each cited line shows the change; each test change fails against a stub of what it pins.

Split guard: five deliverables on the finalize review gate and the review-bot reader. D1 and D2 are the core and are independent (D1:
the integrity module and the acceptance key; D2: the criteria source and the triage text). Split order if the PR grows: D5, then D4,
then D3. A split runs in sequence, since D1, D2, D4 and D5 share `_criteria_snapshot.py` or `review-rubric.md`.

## Standing Constraints

- **Settle each HYPOTHESIS and verify-first clause first.** A refuted claim is dropped from its deliverable, not worked around, and the
  PR says so.
- **The gate gets more precise, never more permissive.** Every relaxation ships a control showing a genuine loss still blocks: D2 keeps
  the tampered-snapshot refusal and the scheduled-review refusal; D1 keeps the Python and JS results.
- **One identity scheme, one acceptance key, one drop reader.** The close and the check read the same key; triage and the completion
  gate read the same drop decision.
- **Fail closed.** An entry under a retired key, an unreadable marker or a placement with no stable field is a stop, never a credit.
- **Required reviewers keep their text.** No change to the standing review authorization, the required-reviewer rule or the quota
  policy.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so. A test that changes
  a control says why in its docstring; counts come from an enumeration.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: a JVM file has no method identity; `_identity_markers` uses `_identity_spans(text) or _class_spans(text)` and collects a
  marker SET per identity — `phase-6-finalize/scripts/_review_support_integrity.py:87,102,957-987`; `_added_marker_units` reports
  `markers - before_markers[identity]` against the merge-base pre-image (`:1000-1012`, `:864-871`), so a second `@Disabled` in a class
  that already carries one at base adds nothing, and one added in the branch reproduces the accepted row.
- OBSERVED: `SKIP_MARKERS` matches by substring (`:71-82`, `:314-315`, `:975`), so `@DisabledOnOs` reads as `@Disabled`.
- OBSERVED: a filter row is accepted when markers and marked tests are each a superset of one entry's, unpaired —
  `review_support.py:319-328`; the writer key holds sorted markers and sorted marked tests separately — `_criteria_snapshot.py:406-423`.
- OBSERVED: `open_criteria` exempts authorized, superseded and operator-closed criteria and a broken snapshot, not a dropped review —
  `manage-solution-outline/scripts/_criteria_snapshot.py:1773-1839`; `run_open_criteria` calls it unchanged —
  `review_support.py:581-584`; the completion gate alone applies `_functional_review_drop_reason` —
  `manage-status/scripts/_cmd_lifecycle.py:1276-1294,1379-1385`.
- OBSERVED: triage reads `open-criteria` before Step 1, files each open row `--severity error`, and twice says the completion gate
  "refuses that exit independently" — `plan-marshall/skills/plan-marshall/workflow/triage.md:40-64`.
- OBSERVED: the outline reads any non-success `snapshot-criteria` as unreadable — `phase-3-outline/SKILL.md:677`; `git log -S` over
  `marketplace/bundles` finds `refreeze_requires_decision` only in `a297ea762` and `criteria-refreeze-authorize` only in `a297ea762`
  and `931d5847b`, neither touching `phase-3-outline`.
- OBSERVED: the placement chain and its last-resort `commit` — `workflow-integration-github/scripts/github_ops.py:727-733`; the
  parser, the token-arm fall-through and the single-line payload read — `_github_pr.py:387-388,449-460,475-489,590-597`; the
  re-review admission — `github_re_review.py:1720-1727`.
- OBSERVED: the close refusal and the head the accepted removals are read at — `manage-status/scripts/_cmd_loop_back.py:633-643,727-729`.
- HYPOTHESIS: a surgical or `functional_review: off` plan still composes `automatic-review` or `ci-verify` and so reaches the
  `finalize-feedback` or `ci-verify` triage — confirm/refute at `manage-execution-manifest/standards/decision-rules.md` and the phase-6
  dispatcher (verify-at-outline). It decides D2.
- HYPOTHESIS: the `triage.md` open-criteria read also runs under the phase-5 `build-runner` producer, before any verdict exists —
  confirm/refute at `triage.md:40-47` and `verification-feedback.md:19` (verify-at-outline). If it does, the PR records it as a finding
  for the orchestrator; it is not widened here.
- HYPOTHESIS: `snapshot-criteria` on an outline re-entry with an existing snapshot returns `refreeze_requires_decision` — confirm/refute
  at `manage-solution-outline.py` § `snapshot-criteria` (verify-at-outline). It decides D2's second clause.
- HYPOTHESIS: a review-comment node can carry neither `originalCommit` nor a review commit (a force-pushed-away commit) — confirm/refute
  against the GraphQL fragment in `github_ops.py` (verify-at-outline).
- HYPOTHESIS: the live CodeRabbit marker is single-line — confirm/refute against `automatic-review/standards/coderabbit.md`
  (verify-at-outline).
- Verify-first clause (D1): reproduce both JVM shapes and the L3-9 pairing as fixtures at HEAD before editing.
- Verify-first clauses (D2): clauses (1) and (2) above, settled before any D2 edit and recorded in the PR.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_integrity.py` — identity arms, marker units, move proof, docstring (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py` — the filter acceptance, `run_open_criteria` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — the acceptance key, `open_criteria`, the fence rule (D1, D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — the drop reader, only if it moves (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — the close (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` — L40-64 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` — L41, L42 (D1, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — the placement (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — the coverage parser, the fence copy (D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — the answer admission (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — the splitter docstring (D5)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_lb118_test_integrity_d1.py` — the JVM and move fixtures (D1, D4)
- OBSERVED: `test/plan-marshall/manage-status/test_lb118_accepted_removals_d2.py` — the acceptance and close fixtures (D1, D4)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_criteria_gate_completion_d1.py` — the drop-exemption fixtures (D2)
- OBSERVED: `test/plan-marshall/manage-status/test_loop_back_close.py` — the docstring, the close-scope fixture (D4, D5)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_pr_comments.py` — the placement fixture (D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_fetch.py` — the fetch-layer and footer tests (D5)
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_lb118_criteria_parser_d5.py` — the fence-rule owner (D5)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-github/test_github_pr_currency.py` — the marker and currency fixtures (D3, D5; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` — L677, only if clause (2) holds (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — § 3e, only if the identity scheme is restated there (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md` — read for clause (1), not edited (D2)

## Dependencies and Sequencing

- **Depends on:** the merge of PLAN-LB-119 (`f84eb0e36`), on the base branch.
- **Absorbs parked PLAN-LB-75 D1** (the triage exemption) and, only if clause (2) holds, its D2 outline bullet. PLAN-LB-75 keeps D1's
  `criteria_gate` and drop-reason-producer bullets and its D4; re-ground it against this plan's line moves before it is un-parked.
- **Overlaps with parked PLAN-LB-46** on `github_ops.py` and `github_re_review.py` (its D7) and on `_github_pr.py` (its D2, D5,
  HYPOTHESIS), the bot participation rules D3 edits: if PLAN-LB-46 is un-parked first, run D3 after it, or split D3 off.
- **Overlaps with staged PLAN-LB-116** on `_github_pr.py` only (its D1 HYPOTHESIS, "only if a thread or body read is missing"); no
  other shared file. If both run, D3 runs in sequence with it. **Overlaps with staged PLAN-LB-127** (CodeRabbit registry) on
  `_github_pr.py` and `github_pr.py` as a possible collision; the disjointness gate decides at emit from both specs' explicit files.
- **Independent of running PLAN-LB-115 and PLAN-LB-123** by their Expected Surface: no shared file (PLAN-LB-123 edits
  `phase-6-finalize/SKILL.md`, which this plan reads only).
- **Adjacent to** (left untouched): `runbook-lane/SKILL.md` (PLAN-LB-116), the merge gate `pre_merge_gate.py`, the bot registry.
- **Owed outside this plan, operator-run:** a harness sync after merge. No verb or flag is added unless D2's outline adds one; then an
  executor regeneration is owed and the landing says so.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-125-review-gate-jvm-acceptance-and-triage-exemption.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
