# Landing Analysis: PLAN-LB-119 — the review gate stops failing open

epic: live-blockers
workstream: WS-03
pr: #1925

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-119.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `f84eb0e36bc5787ffca65c8d392d46ffb83a9126`, a squash commit with ONE parent, `b4430a0a6718b6341913b5b413fa2e9931ccf2a3` (the merge of PLAN-LB-120, read with git and named in the leaf prompt); it is the checkout HEAD. Landing message `rb-lb-119-review-gate-truth-fixes-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; out of scope); its surface delta is `unmeasured`, so the surface was read from the diff: 33 files, +1905/−261 (`git show --stat f84eb0e36`). The lane reports 6 of 7 deliverables done (D7 not fully met), `self-review: clear` after two rounds, a spec read from the ledger copy. No verb or flag was added (`git diff b4430a0a6 f84eb0e36 -G'add_parser|add_argument' --stat` is empty, leaf), so no executor regeneration is owed; a harness sync is.

Surface against the spec's Expected Surface: unplanned but justified are `bot-participation-contract.md`, `findings-pipeline.md`, `_config_defaults.py` and `manage-config/standards/data-model.md` (comment and document text for the new head-plus-tail cut and footer rule), `_findings_ingest.py` (the true `original_length`), `_review_support_validate.py` (the `criterion_unparsed` gate), `manage-status/SKILL.md` (the new error row), the `_records` and `_resolution` participation-site test copies, `test_manage_findings.py` and `test_loop_back_close.py`. In the surface and untouched: `runbook-lane/SKILL.md`, `review_completeness.py`, `validate_struct.py`, `bot_registry.py`; `sourcery.md` was touched.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — merge-gate evidence read from the head | shipped | Placement reads `originalCommit`, then `pullRequestReview.commit`, then `commit` (`github_ops.py:727-733`, re-read); a reply is never evidence (`github_pr.py:2131-2138`); a marker beside a limit block is decided by the settled lead (`github_pr.py:2108`, `:2148`) (leaf). The `commit` fallback is the residue L3-3. |
| D2 — a loss decided per identity, a move proven by content | shipped-modified | The "content" is the stripped assertion lines per identity, not the whole body; whole-file credit is whole-text equality; partial credit when an after-body's excess lines fall wholly inside the before-lines (`_review_support_integrity.py:370-372,670-700,816-845`; leaf). |
| D3 — an acceptance covers exactly what was accepted | shipped for Python and JS, **not for JVM test files** (L3-1) | `review_support.py:319-328` (re-read): a filter row is accepted when its markers and its marked tests are each supersets of an accepted entry's. |
| D4 — a close at an unvalidated head is refused | shipped | `close_head_not_validated` (`_cmd_loop_back.py:626-643`); the Branch-B escape sentence pinned (`functional-review.md:559`). |
| D5 — the evidence root and the git calls fail closed | shipped | Branch check, three-state `--is-ancestor`, the narrowed absent patterns, NUL-delimited paths (`_review_support_integrity.py:184-217,256-259,444-465,525-529`; leaf). |
| D6 — the parser reports what it dropped | shipped; one document line stale (L1-6) | Fences kept, an unterminated fence a gate state, the count-less rule pinned (`test_lb118_criteria_parser_d5.py:323-338`, leaf). |
| D7 — the review-bot evidence minors | **not met, 6 of 7 as the lane says** | The two weak-test tightenings were not done; no gate path depends on them (L1-7). |
| executor regeneration | not owed | The argparse diff is empty. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit, which equals the checkout HEAD. It reported its tool deviations (a skill load, no logging calls, `git log -S` and `git show <rev>:<dir>/` in place of a denied Grep, one `git -C` against the ledger worktree) and no write. The orchestrator re-read the points marked `re-read`. It was a reading only: no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — the read crosses 33 files, with 12 narrative claims passed one by one.
- **Verdict:** layer 1 findings (one major shared with layer 3, minor, info); layer 2 findings (minor, info); layer 3 findings (**one major**, minor, info). No blocker.
- **Orchestrator re-read:** L3-1 (the acceptance test and the identity fallback), L3-3 (the placement chain), L1-6 (the rubric line). Every other row is a lead the leaf checked and I did not re-read.
- **Prompt check.** The 12 claims went into the prompt as separate items.
- **Not read by the leaf:** the phase-6 re-fire dispatcher (so C4's "not re-graded" is consistent with `pre_merge_gate.py:11-63`, which has no integrity re-grade, but not shown there); `_evidence_named_verdict`, `_is_participation_evidence`, `_reported_commit_matches_candidate`; the `_plan_parsing.py` splitter body; the `branch` writer; the diffs of two test files; the live CodeRabbit marker shape; the PLAN-LB-116 and PLAN-LB-46 Expected Surface sections.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line at f84eb0e36) |
|---------|-------|---------|-----------------------------------|
| L1-3 (major, shared with L3-1; re-read) | D3: "a later skip of a further test in the same file is a new row" | met for the Python and JS fixtures the Done-when names; **not met for a file whose identity falls back to the class** (Java and other JVM test files). The Done-when's fixtures pass; the stated behaviour does not hold for the language this repository's consumers use. | `review_support.py:319-328`; `_review_support_integrity.py:968` |
| L1-2 (minor, leaf) | D2 "a move is proven by content" | met with deviation: the proof is assertion lines per identity (L3-5) | `_review_support_integrity.py:370-372,670-700` |
| L1-6 (minor, re-read) | D6 / constraint: documentation states current behaviour | the frozen-record bullet in `review-rubric.md:42` still describes `parser_extended` by the old prefix rule and does not name `criterion_unparsed`, the state this PR's parser bump added. It does state the `parser` marker admission, so the omission is the new state, not the old rule | `review-rubric.md:42`; `_criteria_snapshot.py:169,1443-1475,1491-1505` |
| L1-7 (minor, leaf) | D7 weak-test bullet | not met, as the lane says: the PLAN-LB-106 D4 fetch-layer test and the currency test asserting the classifier, not `pre_merge_gate merge`, are unchanged. Also: the "clean Sourcery body" test covers only a body that is nothing but footer (a "looks great" body plus footer is still filed), and `runbook-lane/SKILL.md` was not edited — its "one of this PR's heads" wording (`:705-712`) stays; only the guard now reads the production parser | `test_comments_stage_fetch.py:953,1032-1054`; `test_runbook_lane.py:340-402` |
| L1-8 (minor, leaf) | Constraint: a test that inverts or resets an existing control says why | violated: `test_a_close_of_another_step_records_no_override_head` had its setup changed (`completed_at` to `head`) with no docstring saying why | `test_loop_back_close.py:449-453` |
| L1-1, L1-4, L1-5 (info, leaf) | D1, D4, D5 Done-whens | met | see the fidelity table |

**Layer 1 verdict:** findings — one major shared with layer 3, three minor, the rest met.

### Layer 2 — Implemented

- **Confirmed (leaf):** C1 (reply never evidence; a marker beside a limit block decided by the settled lead), C3 (the key includes `acceptance_kind`, sorted `markers` and `marked_tests`; the writer fails on an entry that normalizes to nothing, `_criteria_snapshot.py:406-423,457-498`), C4 (the refusal; consistent with `pre_merge_gate.py:11-63`, dispatcher not read), C5 (`branch` is in the references schema, `_references_core.py:29`; the writer not read), C6, C7 (the footer test is synthetic), C9 (`github_re_review.py:1720-1727`, graded minor: it affects the re-review await, not the merge barrier).
- **C2 corroborated with qualifications:** "whole-body equality" holds only for the whole-file move; per identity the proof is assertion lines with partial credit, and the docstring's "even one that shares a line — survives nothing" is not exact (a one-shared-line unrelated test gets partial credit; the row still raises) (L2-2, minor).
- **C6 residue is real (leaf):** the section splitter is not fence-aware (`DELIVERABLE_HEADING_PATTERN` has no fence handling, `_plan_parsing.py:64`). It fails closed (L3-7).
- **C8 closed for permissiveness:** no generation-2 snapshot is graded more permissively than the generation-2 parser would grade it (`_criteria_snapshot.py:1443-1475`); fence edits on parser-2 snapshots stay advisory (L3-6).
- **C10:** see Surface above. **C11:** the argparse diff is empty. **C12** unverifiable (CI, review and merge-queue facts).

**Layer 2 verdict:** findings — two minor, the rest confirmed.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `_review_support_integrity.py:95-97,357,957-987`; `review_support.py:319-328` | A Java test class `FooTest` with no py or js header: the operator accepts `@Disabled` on one method; a later head adds `@Disabled` to a second method of the class | `_identity_markers` uses `_identity_spans(text) or _class_spans(text)`, so the identity is the class and its markers are a SET. The class's markers are unchanged by the second annotation, so no row is raised at all; even if one were, the acceptance test compares the same marker set and the same single identity, and accepts it. A second test stops running unseen. This is the shape D3 was written to close, left open for the JVM. | major |
| L3-2 (leaf) | `_github_pr.py:475-489,590-597`; `github_re_review.py:1720-1727`; `coderabbit.md:52-55` | A CodeRabbit summary with an unclosed fence before an in-progress marker, whose body names the head SHA | The parser reads a quoted marker or one after an unterminated fence as "no marker" (not a gate state). The producer's admission and re-review gates still use substring matching, so the decision falls to the token arm: credited by `named_commit_currency`, or an end to a re-review wait as `head_sha_verified: true`. The root is shared with C9. | minor |
| L3-3 (re-read) | `github_ops.py:732-733` | A node whose `originalCommit` and review commit are both null (a lead: a force-pushed-away commit) | The placement falls to the mutable `commit`, the field D1 exists to distrust, and credits the comment at the newest head. | minor |
| L3-4 (leaf) | `_cmd_loop_back.py:633-643, 723-728` | (a) A close of any step; (b) a prior record with no head | (a) The validated-head refusal now applies to every step's close, not only functional review: a scope widening. (b) With no head on the prior record, the close recomputes the integrity rows at the closing head, so a later removal in an accepted path is recorded accepted without anyone having seen it. | minor |
| L3-5 (leaf) | `_review_support_integrity.py:370-372,691-696` | `it('renders')` with `expect(wrapper).toMatchSnapshot()` is deleted and an unrelated new `it('renders')` carries the same line | The move proof keys on identity name plus assertion-line text, and JS identities are bare quoted names. The new test is credited as the move; the set total is unchanged, so no row. | minor |
| L3-6 (leaf) | `_criteria_snapshot.py:1407-1408,1453-1455` | A parser-2 snapshot with a fenced block added or edited under a criterion | Still advisory `parser_extended`. D6 protects only snapshots frozen at generation 3; the docstring says an author's append "is never admitted". Not more permissive than generation 2. | minor |
| L3-7 (leaf) | `_plan_parsing.py:64`; `_criteria_snapshot.py:1491-1505` | A column-zero `### N.` inside a fenced criterion | The splitter is not fence-aware; a phantom deliverable N can appear. Not a fail-open: the cut leaves an unterminated fence, so `criterion_unparsed` blocks when a snapshot exists. | minor |
| L3-8 (leaf) | `_github_pr.py:387-388,449-460` | If the live marker is multi-line | The payload is read only on the opener's line while the module comment shows a two-line marker; every finished review would read as unreadable. Fails closed (blocks). | info |
| L3-9 (leaf) | `review_support.py:322-327` | An accepted `{skip on a, xfail on b}` and `b` changing from xfail to skip | Markers and marked tests are checked as two separate supersets, not paired per test; identity-less files keep the markers-only key. | info |
| L3-10 (leaf) | `github_pr.py:443-449` | A footer literal in the middle of a body | The footer strip is terminal and drops all later signal. Sourcery is optional. | info |
| L3-11 (leaf) | `_github_pr.py:492-506`; `_criteria_snapshot.py:103-128` | — | Two copies of the CommonMark fence rule: drift risk. | info |
| L3-12, L3-13 (leaf) | `_review_support_integrity.py:199-217,454-459`; `review_support.py:315,334` | — | The `--is-ancestor` handling and the NUL parse are correct (including rename and copy order and a truncated tail); the writer and the re-seed are correct, and legacy entries without `acceptance_kind` fail closed. | info |

**Layer 3 verdict:** findings — one major (L3-1), minor L3-2 to L3-7, the rest info.

**Collisions with other plans (leaf, partly re-read by the orchestrator against the specs):**
- **PLAN-LB-75 (parked):** D1 cites `review_support.py:358-361` (shifted by about 14 lines); D4 cites `_criteria_snapshot.py:287-311` (shifted by about 40); both also touch `functional-review.md` and `review-rubric.md`. Re-ground before un-parking.
- **PLAN-LB-46 (parked):** D1 and D6 (summary credit, edited-comment credit) sit on the refusal bypass at `github_pr.py:2107` and on `_strip_footer_markers`. D7 must also remove the new `cuioss-review-bot` comment at `github_pr.py:2127-2130` or its "search returns nothing" Done-when fails, and the `github_ops.py` site records this PR added to all three participation-site test files.
- **PLAN-LB-116 (staged):** this PR edited `test_runbook_lane.py` (it now imports `_github_pr`); `runbook-lane/SKILL.md` was not touched, so the spec's D7-versus-116 sequencing concern is moot for the SKILL.md side. LB-116's review-body parser would sit beside the coverage parser in `_github_pr`.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `6b1aa69a6`, `545d113ad`, `f33b03988` and the merge head `c6dd8e650` (marker `kind=reviewed`, risk Low, one performance nitpick), with quota refusals at four points handled under the 90-minute policy; Sourcery (optional) refusing on size at every trigger. I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue run are the lane's claim and are `not_shown_by_reading`. Git confirms the squash commit `f84eb0e36` and its subject.

## Residue and Watches

- One major layer-3 finding (L3-1) wants a fix plan; it is staged on the operator's word only. It sits on `_review_support_integrity.py` and `review_support.py`, the same files as parked PLAN-LB-75 D1; the two should be reconciled in one plan, not run apart.
- Settle first at that plan's outline: whether the JVM identity can be the method (a Java test header arm) rather than the class, and whether the acceptance key should pair a marker with its test (L3-9 is the same shape).
- The minor set (L3-2 and C9 share one root in the substring marker check; L3-3 the placement fallback; L3-4 the close scope; L3-5 the move proof; L3-6, L3-7 the parser; L1-6 the rubric line; L1-8 a docstring) is one coherent follow-up on the review gate. It is NOT staged; it is offered to the operator.
- The D7 weak-test items (two) are test-strength gaps only; they ride any plan touching the same test files.
- Owed outside this plan, operator-run: the harness sync. No executor regeneration.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (an early run of builds with `--execution-mode in_process`, build job logs read outside the repository, two guard refusals) is its own account and is not re-read.
