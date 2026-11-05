envelope_version=1
sender_type=orchestrator
sender_id=quality-report
epic=live-blockers
kind=finding
created=2026-11-05T15:31:00Z

# Upstream report for plan-marshall: friction seen in the quality-report epic

epic: quality-report
written: 2026-10-31
plugin version in use: 0.1.2027 (landing messages)
status: filed 2026-11-05 into the `live-blockers` inbox of the plan-marshall repository, at the operator's instruction. Bundle: `plan-marshall`. Kind: finding (a collected report; seven themes plus six dated addenda).

Twenty-four `candidate-lesson` messages from PLAN-01 to PLAN-07 name `plan-marshall:*` components, which
this repository cannot fix. They are grouped into six themes. Each theme was also filed as one lesson in
this repo's lesson store with the foreign-store override (`2026-10-31-13-001` to `-006`) so agents running
plans here see the rule. Every statement below comes from the senders' messages and is NOT independently
verified by the orchestrator.

## 1. CodeRabbit's one-review-per-hour quota (5 messages)

Senders: PLAN-01-003, PLAN-02-003, PLAN-03-005, PLAN-04-004, PLAN-06-001. Component: `automatic-review`,
`workflow-integration-github`, `manage-locks`.

- Every plan hit it. A fix push or a late docs commit moves HEAD and the required bot is
  `refused_awaitable (quota)` for the new head; the pre-merge barrier reports `participation_complete=false`
  and the plan merges only under `barrier-ask-override` (PLAN-01, 03, 04, 06, 07).
- Concurrent plans share one account quota: PLAN-06 waited about two hours behind PLAN-07's rate window
  (refusal recovery deferred, then armed, then completed after about two hours).
- After a content-identical rebase the incremental reviewer answered "No files to review", leaving the PR
  without a current review; only the registry `--escalated` full-review command produced one (PLAN-02).
- Suggested upstream work: batch review-driven fixes into one push; treat a docs-only delta after full bot
  coverage as lower risk at the barrier; account for the shared window when pairing plans.

## 2. Merge gate bound to the exact HEAD (4 messages)

Senders: PLAN-01-001, PLAN-01-002, PLAN-02-002, PLAN-06-002. Component: `phase-6-finalize` (pre-merge
barrier), `manage-status` (merge-authorization grant).

- PLAN-01: a formatting commit and a docs-only ADR commit after the gates ran gave `merge_candidate_not_gated`;
  six gates re-ran.
- PLAN-01: the grant verb refused the paraphrased answer "Accept gap and merge"; it accepts only the
  barrier's own label "Merge anyway (record reason)".
- PLAN-02: `finalize-step-sync-baseline` stamped an old `head_at_completion` and was skipped on re-entry as not
  head-dependent, but the gate derives head-dependence from that stamp; main advanced, a rebase was the only
  fix, and every verdict was voided.
- PLAN-06: a test-only commit after the gated head; the step records accepted the operator's re-run waivers
  but the merge gate refused them (`merge_candidate_not_gated`, security audit and functional review), and
  both re-ran about three hours later.
- Suggested upstream work: one source for the skip rule and the gate's head-dependence; a cheap
  re-attestation path for docs-only deltas; a prompt envelope that carries the barrier's own labels; make the
  step records and the gate agree on whether a waiver counts.

## 3. Installed scripts lag the skill docs (7 messages)

Senders: PLAN-01-004, -005, -006, PLAN-04-008, PLAN-06-003, PLAN-07-003, PLAN-07-005. Component: various
(`tools-integration-ci`, `manage-findings`, `manage-architecture`, `tools-script-executor`, `phase-6-finalize`,
`automatic-review`, `build-maven`).

- Documented but not registered: `pre_merge_gate record-merge` and `consequence-text`;
  `review_completeness roster` (rejected 6 times in one plan; registered: check, deficit, size-caps,
  trigger-bot).
- Invented or misplaced: `ci pr list --state merged` (valid: open, closed, all), `manage-findings query`,
  `manage-findings pr-comment`, `manage-config effort resolve-target --step`, `architecture --plan-id P search
  --content`, missing required flags on `ci_complete_precondition resolve` and `ci_verify run`.
- A recovery action returned `close_and_reopen` where the doc says `generate_trigger`; the executor drift
  probe returned `drift=unknown`, so drift was never detected.
- For the `architecture` rejections the failure marker keeps only the argv, not the argparse error, so the
  cause cannot be read from the record (PLAN-01-006).
- PLAN-04-008: a cluster of failed full verifies and a bare `test-compile` was transmitted unclassified; the
  underlying work-log lines were not re-analysed.
- Suggested upstream work: keep installed scripts and docs in step (a version-parity check); make every
  failure marker record the raw argv and the argparse error text.

## 4. Bookkeeping slips (3 messages)

Senders: PLAN-03-004, PLAN-07-002, PLAN-07-004. Component: `manage-status`, `manage-change-ledger`,
`phase-3-outline`, `phase-4-plan`, `manage-metrics`.

- PLAN-03: an inline review-fix commit had no `kind=change` ledger row; the 5-execute to 6-finalize
  transition was refused (`execute_commits_unrecorded`).
- PLAN-07: six per-deliverable commits carried `Co-Authored-By: Claude Opus 5.5` where the operator required
  `Claude Sonnet 5.5`; rewriting them left ledger rows on the old SHAs and the same transition was refused.
- PLAN-07: `phase-3-outline` and `phase-4-plan` transitioned the phase themselves, so the metrics boundary
  was stamped retroactively with the repair time (06:01:59Z and 07:58:31Z), skewing per-phase figures.

## 5. Outline and plan quality (4 messages)

Senders: PLAN-02-005, PLAN-03-003, PLAN-04-003, PLAN-04-007. Component: `phase-3-outline`, `execute-task`.

- A criterion about the PR body can never be evidenced by the pre-PR functional review (PLAN-04).
- The outline missed the docs that list a closed set the deliverable extended (PLAN-04).
- A fix-task agent edited files outside its declared set and left an outline "no LogMessages change" note
  stale (PLAN-02).
- A "fails before the fix" criterion was evidenced only at review by overlaying tests on the base commit; for
  a signature change the proof is a compile failure (PLAN-03).

## 6. Stale PR body after loop-back (1 message)

Sender: PLAN-01-008. Component: `phase-6-finalize` (create-pr, loop-back re-entry).

- The PR body went stale after fix tasks TASK-004 to TASK-009; the functional review flagged two false
  self-reports, and the squash merge used the stale body as the commit message.
- Suggested upstream work: regenerate the body on loop-back re-entry.

## Also noted in landing messages (not lessons)

- `branch-cleanup` was recorded through `mark-step-done` in PLAN-06 and PLAN-07 (PLAN-05 reports the same missing verb) because `pre_merge_gate
  record-merge` is not registered.
- `effort` was not stamped in the PLAN-01, 02, 04 and 05 landings (`unknown`); the runtime stamp could not be
  refreshed (`model_unknown`) in several.
- PLAN-07's `branch-cleanup` was recorded with the clean merge wording although a `barrier-ask-override` was
  granted, so that step alone hides the grant.

## Addendum 2026-11-01: PLAN-12 and PLAN-20 (9 more messages)

Recurrences of the themes above (not filed as new lessons):

- Theme 3, scripts lag the docs: PLAN-12-001 and PLAN-20-003. The generated executor was 0.1.2027 while the
  workflow docs read were 0.1.2040 (PLAN-12) and 0.1.2046 (PLAN-20). `pre_merge_gate consequence-text` and
  `record-merge`, `review_completeness roster`, `manage-solution-outline get-deliverable --number`,
  `manage-findings qgate query` and the `generate_trigger` selector result are missing or differ. Both senders
  name regenerating the executor (marshall-steward executor staleness) as the likely fix. A third and fourth
  plan hit the same drift, so a doc-version versus executor-version check before a plan run would prevent it.
- Theme 1, CodeRabbit quota: PLAN-12-005. The required bot was quota-limited for the last two fix commits and
  the automatic-review step could not reach completion; the merge went through under "Accept the coverage gap".
  PLAN-20 also had two quota refusals, switched `review_rate_window_await` on after the first, and waited about
  25 hours of wall time in all.
- Theme 2, head binding: PLAN-20-004. A docs-only follow-up commit after the pre-push gate re-ran every
  head-dependent finalize step, about an hour including the quota wait. PLAN-12-004 is the sibling case: the
  pre-commit profile reformats tracked files after the last commit, so a green build is bound to a HEAD that no
  longer matches the tree to be pushed. Suggested: run the reformatting profile before the final commit, make
  verify fail on a dirty tree after the build, or bind verification records to the tree hash.
- Theme 5, outline quality: PLAN-20-001. The solution outline gave two different fallbacks for the same
  re-injection case; the phase-3 quality gate caught the contradiction. State each case's fallback in one place.

New items:

- PLAN-12-002 (with its correction PLAN-12-003): a code-review finding with `fix_kind correction` has no
  applier when the review step declares `mutates_source: false`, so it loops back for an in-place correction
  that nothing can perform, and was closed as accepted. The sender later corrected itself: on main the
  `CoreJfrBenchmark` defect IS fixed (the token is selected once and that same token is validated), so the
  statement in 002 that it was not fixed is wrong. What still holds is the routing gap. The related functional
  review findings (no failing pre-fix run for `BenchmarkStateScopeTest`) were closed the same way.
- PLAN-20-002: an advisory code-review finding about documentation claims that outrun their sources was not
  acted on before the PR went up, and CodeRabbit then raised the same defect as an actionable comment, costing
  an extra review round. The operator's fix-immediately policy covers it; whether the review step should
  surface advisories of this class before push is a plan-marshall question.

## Addendum 2026-11-02: PLAN-21 (6 plan-marshall messages)

PLAN-21-004 (a lock/publish race plus under-pinned tests) is project-owned and was filed as the local lesson
`2026-11-02-10-001`; it is not part of this report. The other six name `plan-marshall:*` components.

Recurrences of the themes above (not filed as new lessons):

- Theme 2, head binding: PLAN-21-002 and PLAN-21-003. The first sync-baseline record forwarded
  `--head-at-completion`, which that step's workflow doc does not record. The pre-merge barrier later compared
  the extra binding with the merge candidate and refused with `merge_candidate_not_gated`, so the record had to
  be redone without the flag. Suggested: the recording verb rejects a head binding the step does not own. And
  PLAN-21-003 is the third plan (after PLAN-20-004 and PLAN-12-004) where a fix commit made by triage after the
  pre-push gate could not be pushed until the gate and the whole build re-ran: either route the re-gate
  automatically in the triage fix loop or batch review-bot follow-ups and gate findings before the gate runs.
- Theme 3, scripts lag the docs: no new case. PLAN-21 ran on `executor_version` 0.1.2046, equal to the plugin
  version, so the drift reported in the first addendum is gone once marshall-steward regenerated the executor.
- Theme 5, outline and plan quality: PLAN-21-005 and PLAN-21-006. The phase-4 description-drift Q-Gate flagged
  ADR numbers (`17`, `18`, `16`) that the phase-4 ADR scan itself had injected into task descriptions as
  lifecycle-contract pointers; the outline never mentions them. Both findings were accepted by hand. Suggested:
  exempt references that originate from the ADR scan, or have the scan record its pointers so the validator can
  read them.

New items:

- PLAN-21-001: the pre-push gate's `test-compile` arm cannot succeed for a module that consumes the
  `token-sheriff-validation` generators test-jar. The test-jar is attached at `package`, so a reactor
  `test-compile` that stops earlier cannot resolve it, yet `architecture resolve test-compile` still emits that
  command for the consumer modules. The failed attempt filed 120 `build-error` findings with one root cause,
  which had to be resolved by hand, and the landing recorded `test-compile` and `module-tests` as UN-GATED. The
  same degradation was recorded for PLAN-05 and PLAN-12. Suggested: detect test-jar producer/consumer pairs and
  either resolve `test-compile` to a goal that reaches `package` for the producer or mark it unsupported for
  such modules; and collapse build failures that share one unresolvable artifact into one finding.
- PLAN-21-007: `module_mapping_validator` flagged a `module_testing` task whose files were mechanical
  caller updates after a signature change (client lifecycle code, Quarkus integration tests), because no
  implementation task lived in the test module and `doc/developer/test-impl-mapping.adoc` does not exist.
  Accepted. Suggested: route compile-compat caller updates into the implementation task, not into
  `module_testing`.

## Addendum 2026-11-02 (second): PLAN-08 (10 plan-marshall messages)

PLAN-08-002, -004, -005, -006 and -007 are project-owned (config docs and Javadoc promising more than the code,
`@DefaultBean` wording, a security fixture without a negative control). They were filed as the local lessons
`2026-11-02-14-001` and `-002` and are not part of this report.

Recurrences of the themes above (not filed as new lessons):

- Theme 5, outline quality: PLAN-08-001. A success criterion said "any `.properties` file found is fixed here",
  which implies writes to files the architecture inventory does not index, so the outline could not list them
  under Affected files; phase 4 listed candidate directories as conditional changes instead. Suggested:
  enumerate the candidate files by a direct read, or narrow the criterion to "verified none exist".
- Theme 5 and the finalize loop: PLAN-08-003. A code-review loop-back fix touched rows of a file whose
  per-deliverable scope had been narrowed by an overlap carve-out with another plan, so the functional review
  flagged it as out of scope and the operator had to accept a scope exception. Suggested: attribute the fix to the
  deliverable that owns the feature, or let the carve-out name the rows that stay open to this plan.
- Theme 3, verbs paraphrased: PLAN-08-008 and PLAN-08-011. `manage-solution-outline get-deliverable --number`
  (the flag is `--deliverable-number`; also seen in PLAN-12-001 and PLAN-20-003) and
  `review_completeness check --pr-number` (the verb is plan-scoped and takes no PR number). Check whether a doc
  quotes the short form; if not, this is one more recurrence of the argparse-rejection lesson.

New items:

- PLAN-08-009: `manage-tasks list --status pending,in_progress` is rejected because `--status` takes one value,
  yet "open tasks" (pending plus in_progress) is the natural query after verification feedback adds fix tasks.
  Suggested: accept a repeatable or comma-separated `--status`.
- PLAN-08-010: the 5 → 6 phase transition was refused twice because commits made outside the per-deliverable
  commit (a finalize code-review loop-back fix, triage inline fixes) carry no `kind=change` ledger row. The guard
  is right; the inline-commit paths should append their own row. The log records only the first missing SHA.
- Landing residue of PLAN-08: the pre-merge gate refused on 120 stale pending `build-error` findings that the
  build tooling's dedupe had re-opened when the (pre-existing) red `test-compile` re-observed them, after a later
  green build had resolved them. Same root cause as PLAN-21-001. Dedupe should not re-open a finding that a later
  green build resolved.

## Addendum 2026-11-04: PLAN-09 (4 plan-marshall messages)

PLAN-09-002 (a COVERED register row needs a wired test on every path) and PLAN-09-005 (the DPoP proof path must
enforce the same key checks as the token path) are project-owned and were filed as the local lessons
`2026-11-04-13-001` and `-002`; they are not part of this report. The other four name marketplace components.

Recurrences of the themes above (not filed as new lessons):

- Theme 3, verbs paraphrased: PLAN-09-006. Two more argparse rejections, and this time both were issued by the
  orchestrating main-context session, not by a dispatched leaf: `manage-execution-manifest record-step` with a
  flag it does not declare (the real flags are `--plan-id --step-id --phase --outcome`, with `--phase` one of
  `5-execute` / `6-finalize`), and `manage-findings` with `query` and `qgate query` (the real read verbs are
  `list` / `get` and `qgate list --phase P`; `qgate query` was already named in the first addendum). The rule in
  `agent-behavior-rules.md` § Never invent script subcommands already covers dispatched leaves. This run shows it
  also has to bind the main-context session, which drives `manage-*` scripts ad hoc between dispatches with no
  loaded workflow quoting the canonical invocation. Suggested: run `{script} {verb} --help` before an ad-hoc call
  no loaded workflow spells out.

New items:

- PLAN-09-001: a deliverable that changes a documented semantic (here the expiry boundary `exp + skew < now`)
  left three prose restatements of the old rule (a Javadoc in `IssuerConfig`, a config-key doc in
  `JwtPropertyKeys`, and a specification page). Only the finalize code review found them. Fixing them added files
  outside the declared footprint, which with two review-driven test files and one threat-model row pushed the plan
  to six out-of-scope files (threshold five) and a hand-accepted scope-creep warning at the pre-merge gate.
  Suggested: at outline, search the repository for the literal old expression and its key names, and list every
  restating file in the deliverable's affected files; or have the scope-creep check treat a documentation-only
  correction of the changed semantic as in scope.
- PLAN-09-003 (`pm-dev-java:java-security`): inserting a new check ahead of existing steps dropped a precondition
  the downstream step enforced implicitly (a null signature used to be rejected by the format converter; after
  the change the new check threw `NullPointerException`, breaking the declared `SignatureException` contract), and
  placing the check after `initVerify` made its own guard branches unreachable, so the tests passed for the wrong
  reason. Suggested for the skill: list the preconditions a downstream step used to enforce, keep the exception
  type and message, and place a new guard before any provider call that could reject the same input first.
- PLAN-09-004 (`pm-dev-java:junit-core` / `persona-module-tester`): CodeRabbit found three test gaps where a guard
  existed and no test failed when only that guard was removed: an inner-JWS empty signature masked by an earlier
  part-count check, rejection tests run in one decode mode only, and a range check with separate `r == 0` and
  `s == 0` conditions covered only by an all-zero input. The same class as the local lesson `2026-11-02-10-001`
  (tests that pin less than the spec names). Suggested for the skill: one test input per reject condition, built
  to pass every earlier check, run across every mode with the existing cross-product helpers.

Landing residue of PLAN-09: the pre-push gate arms had no standalone `module-tests` and no valid whole-tree
`test-compile` (same root cause as PLAN-21-001; the fifth plan with this degradation after PLAN-05, PLAN-08,
PLAN-12 and PLAN-21); `effort` was not stamped again (`unknown`); two metrics rows carried placeholder figures written before
the agent usage arrived and were followed by corrected rows; the post-merge `Run JMH Benchmarks` workflow was
still running when the post-merge wait hit its deadline; the merge-queue squash message is platform-composed.

## Addendum 2026-11-04: PLAN-11 (2 plan-marshall messages)

Both messages recur items above; nothing here was sent.

- PLAN-11-001 (outline / Q-Gate): a deliverable's change-per-file entry said "if a new log identifier turns out to
  be required, add it to `JWTValidationLogMessages` and `doc/LogMessages.adoc`", and neither file was in "Files
  expected to mutate". The Q-Gate `scope_criterion_validator` flagged it as `under_coverage` (finding 835478, warning)
  and the phase-4 `declared_set_closure` referrer check would have caught the write. Recurrence of the "conditional
  changes instead of declared files" items earlier in this report. Suggested: at outline, resolve a conditional
  "if X is needed also change F" clause (commit to one branch) or require F in the declared set; a new `LogRecord`
  always implies the doc file, so the check could add it automatically.
- PLAN-11-002 (pre-push gate / `build-maven` canonical resolution): same root cause as PLAN-21-001. New here: the
  failed stand-alone `test-compile` was parsed into 120 `build-error` findings that blocked the first merge
  dispatch until each was resolved as `rejected` by hand, which PLAN-04-008 saw in smaller form. Suggested, in
  addition to the test-jar producer/consumer detection already proposed: file one structural build failure as a
  single finding (or a cluster) rather than one per compile error, so it cannot hold a merge behind a rejection batch.

Landing residue of PLAN-11: the sixth plan with the degraded pre-push gate (after PLAN-05, PLAN-08, PLAN-09, PLAN-12
and PLAN-21); the project default `final_merge_without_asking: true` (`.plan/marshal.json`) would have merged without
asking, which conflicts with the repository rule in `CLAUDE.md` that auto-merge is never enabled unless told, so the
operator authorised the merge by hand for this PR; `effort` was stamped this time.

## Addendum 2026-11-05: PLAN-10 (7 plan-marshall messages)

Nothing here was sent. Lessons 002 (negative `max_age` plus skew) and 004 (DSL-JSON unchecked exception) are
project-owned and are handled in the epic ledger, not here. Lesson 005's project half (write the suppression marker
up front) is already the operator's OpenRewrite rule in the epic.

- PLAN-10-001 (review / doc restatement): a best-practice paragraph restated a rule without the scope qualifier the
  owning spec section carries ("for a JWT access token"); two functional and code review rounds over the same files
  missed it and the external bot caught it. Suggested: when a deliverable restates a normative rule in a summary
  document, the review compares the restatement with the owning section, not only with the code.
- PLAN-10-003 (outline / phase 5): three finalize loop-backs (about 90 minutes of re-dispatched reviews), each on a
  defect phase 5 should have caught: a correction deliverable that did not enumerate every file carrying the wrong
  claim (a diagram and an architecture page), and a new fail-closed check whose "cannot decode" branch had no
  malformed-but-present test, so unparseable was treated as absent. Suggested: outline lists every file carrying the
  claim being corrected; phase 5 asks for one test per "cannot decode" branch of a new security check.
- PLAN-10-005 / -006 (pre-push gate, push freshness): the `pre-push-quality-gate` step made its own source commit
  (an OpenRewrite-inserted TODO replaced by the suppression marker), which moved HEAD past the last validated build
  and needed a manual `freshness-reconcile` decision; a later inline-fix commit was refused with
  `head_not_validated_by_gate` and re-fired security-audit, functional-review, code-review, the gate, push, CI-verify,
  automatic-review and sonar-roundtrip. Related to the PLAN-12-004 and PLAN-20 head-dependent-chain items above.
  Suggested: the gate should not commit source (or should declare the commit and re-validate itself), and inline
  review-bot fixes should batch into one commit.
- PLAN-10-007 (code-review verifier schema): a verifier dispatch wrote `findings_supported` where the workflow reads
  `grading_supported` and the verdict was read as malformed. Only partly confirmed: the surviving artifact has the
  correct key and no log line records the malformed read. Suggested: validate the verdict JSON by script at write
  time, naming the expected key, with one shared schema for the code-review and functional-review workflows.
- PLAN-10-008 (CodeRabbit quota, recurrence of theme 1): the re-review wait burned its full 600 seconds on a quota
  refusal that stated an ETA of 17 minutes, then escalated; the operator chose merge-anyway under
  `barrier-ask-override`. New detail: the unseen delta was only the bot's own two accepted suggestions. Suggested:
  recognise the quota answer, read the ETA, wait if it fits the budget or escalate at once, and record "unseen delta
  = the bot's own suggestions" with the override.
- PLAN-10-009 (argparse, recurrence of theme 3): `architecture --plan-id P search ...` rejected (exit 2); the leaf
  appended `--plan-id` by rote before the verb. One more data point for the router-scoped-flag class; no new
  suggestion.

Landing residue of PLAN-10: `effort` unknown again (runtime stamp unreadable; the model refresh found
`model_unknown`); `total_tokens` spans mixed populations and a phase figure is over-counted by about 125 thousand;
the post-merge CI wait hit its deadline on the non-gating `Run JMH Benchmarks` job (it finished green afterwards);
one ADR candidate was proposed and not created.

## Addendum 2026-11-05: PLAN-23 (2 plan-marshall messages)

Nothing here was sent. A third message (an owed `architecture enrich` hint about `java:S1612`) is epic-local and is
tracked in the epic's Watches.

- PLAN-23-001 (`review_support test-integrity`): the default `--base-ref` is the `origin/main` tip, so on a branch
  that lags a moved `main` the two-dot comparison attributes upstream's own assertion changes to the branch and
  raises a false `weakened_test` (here on `RefreshFailureClassificationTest`, which PLAN-10 #856 had edited). It
  cleared after the rebase. Two more `weakened_test` flags on this plan were judged false positives by every
  verifier (a parameterised merge of three tests over the same inputs, and an `assert true` replaced by a real
  check), and the functional and code reviews were closed by operator override at each head. I read both in the merged
  diff and agree they are false positives. Suggested: anchor the default on the merge-base (three-dot semantics);
  count a parameterised test's rows, not its methods, when comparing assertion totals; treat `assert true` ->
  real assertion as a strengthening.
- PLAN-23-002 (pre-push gate, Maven): the `module-tests` arm is reported as un-gated on every Maven push even though
  the whole-tree `verify` ran the tests (3680 green). Seventh plan with the degraded arm (after PLAN-05, 08, 09, 11,
  12, 21); the same family as PLAN-21-001 and PLAN-11-002. Suggested, in addition to the earlier items: treat a
  resolved whole-tree `verify` that runs the test phase as satisfying the arm for Maven, or have `build-maven` declare
  a `module-tests` canonical, and stop emitting a per-push warning for a configuration that is normal for the build
  system.

Landing residue of PLAN-23: the first `lessons-capture` run did not receive the orchestration verdict and wrote two
lessons to the global store with `--allow-foreign-store` (both were tombstoned and re-sent to the inbox): one more
instance of the lesson-routing gap at the top of this report; the merge went through under a `barrier-ask-override`
because CodeRabbit's one-review-per-hour quota was spent on the previous push; the plan's wall time was about 21.6
hours, mostly review-quota and review-override waits.
