envelope_version=1
sender_type=plan
sender_id=rb-lb-133-criteria-gate-reach
epic=live-blockers
kind=landing
created=2026-11-11T05:56:19Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-133-criteria-gate-reach
epic=live-blockers
pr=#1953
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=3
review_body_findings_handled=3
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (`.plan/temp/guard.log`; refusals listed in § 7).

## 1. Deliverables

All four deliverables are fully met; every Done-when is `order: test-first` except where noted.

**D1 — `criteria_gate` is recorded, and the drop reason has a writer or is removed** (`9eb830015`, extended by `8e833c494`, `80d1a0b86`)
- *after a dropped-review completion, `criteria_gate` is readable from the status record* — **met**, `test-first`.
  Test `test_dropped_review_completion_persists_the_criteria_gate_note` (plus controls
  `test_a_reviewed_plan_records_no_criteria_gate_note`, `test_a_graded_completion_clears_a_stale_criteria_gate_note`
  and `test_a_completion_archive_records_the_criteria_gate_note`). Failing run: HEAD `e7033b83a` with the new tests
  uncommitted, job log `bb8e355ce96a4bdbbdd3d54eb8d99b0e.log` → `KeyError: 'criteria_gate'`.
- *the read is gone and a test asserts no other consumer reads the key* — **met** (the removal branch), `test-first`.
  Test `test_the_retired_drop_reason_key_has_no_reader`. Same failing run and log; the red output named
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` as the offender.
- Decision recorded: the read was REMOVED rather than given a writer. No producer existed anywhere in the tree, and
  the only two production drop paths already state a reason (settled scope, not scheduled in the manifest). A writer
  would have had to live in the manifest composer, i.e. outside this plan's surface, and would have recorded the
  decision a second time.

**D2 — a re-freeze decision in the light lane has a documented path, and the decision is recorded** (`634a7b846`, extended by `e8696c6bb`, `8e833c494`, `80d1a0b86`)
- *a doc test asserts `light-lane.md` names `refreeze_requires_decision`, the verb and the operator question* —
  **met**, `test-first`. Tests `test_the_light_lane_routes_a_refreeze_decision_to_the_operator`,
  `test_the_refreeze_result_is_not_read_as_an_unreadable_outline`, and the consumer test
  `test_the_light_lane_dispatcher_consumes_the_refreeze_envelope` (added after self-review round 1 found the
  envelope had no consumer). Failing run: job log `7597a0fcc0824bb5b3d09e3704581eb3.log`.
- *a doc test asserts `functional-review.md` records the D3e decision* — **met**, `test-first`. Test
  `test_the_functional_review_workflow_records_the_d3e_decision` (asserts `PLAN-LB-70 D3e`, both authorization
  verbs, `verify-first`, and that the D4c record survived). Failing run: job log
  `9a96af4efe48418680bdfb1cefa967c6.log`.

**D3 — `superseded_by` must name an existing deliverable** (`9eb830015` for the snapshot half, `9ef4976cd` for the validator half, `0b2cafc0f` for head-anchoring)
- *a deliverable with `superseded_by: "x"` does not close its criteria and the validator names it* — **met**,
  `test-first`. Tests `test_the_validator_names_a_superseded_by_that_is_no_deliverable`,
  `test_open_criteria_keeps_the_rows_of_an_unnamed_superseded_by`, with the positive controls
  `test_the_validator_accepts_a_superseded_by_that_names_a_deliverable` and
  `test_open_criteria_closes_the_rows_of_a_named_superseded_by`. Failing run: job log
  `a17faf3f75994d6797766ad965a738d9.log`.
- *holds at `9cd644892` and must keep holding: a `superseded_by` naming an existing deliverable closes them; an
  override with a sealed verdict on the same head closes the criteria* — **holds**, by the unchanged
  `test_superseded_deliverable_criteria_do_not_block` and `test_closed_review_closes_criteria_even_with_a_sealed_verdict`
  (green in every run).
- Round-1 review (CodeRabbit inline 1) found the matcher accepted a reference token inside prose; fixed in
  `0b2cafc0f` with `test-first` evidence of its own: `test_a_reference_token_inside_prose_does_not_close_the_criteria`
  failed against the previous matcher (job log `03abedf3ab90477c804757e19243e807`, `open_count == 0`), green in
  `86af67de675e4196a80cb428d7da11f9`.

**D4 — the documents state what the gate does** (`9bfb88c91`)
- *a doc test asserts `triage.md` states the closing states and the exemptions and no longer states the old rule* —
  **met**, `test-first`. Tests `test_triage_states_the_closing_states_and_the_exemptions`,
  `test_triage_no_longer_states_the_old_rule`. Failing run: job log `630098dc8aa3415298747df34a1a15a6.log`.
- *a doc test asserts the `review_support` row lists every verb and names the three private modules* — **met**,
  `test-first`. Test `test_the_review_support_row_lists_every_verb_and_the_private_modules`. Same failing run.

**Per-head test runs (every pushed head).** `module-tests plan-marshall --no-parallel` at `9bfb88c91` — 28237 tests
(`00d5f0634987481c88720c8a177c7e04.log`); `verify` at `0b2cafc0f` — 33227 tests (`e52e1122a94a41d8979b9d8f65d84aa2.log`);
`verify` at `96de7f247` — 33350 tests (`80c4f39ef07943e6a4bd328fe552fa25.log`). CI green on every head
(`verify / verify`, SonarCloud, `verify / gate`, dependency-review, generate-check).

## 2. Personas and skills

- `persona-implementer` — the D1/D3 production changes. `persona-module-tester` — the test modules.
  `persona-documenter` — the D2/D4 documents. `persona-code-reviewer` — the three self-review rounds and the
  triage of every PR comment.
- `skills: none named` for all four deliverables (the spec declares no `Skills:`/`Persona:` lines, and resolve
  reported `skills_note: none named`). No skill was added for surface drift: the modules touched are the ones the
  spec's Expected Surface names, plus `phase-6-finalize/standards/review-rubric.md`,
  `plan-marshall/workflow/planning.md` and two test files — each forced by D3's rule consistency or D2's
  reachability, recorded under § 4 below.

## 3. Hypotheses

- *Persisting `criteria_gate` needs a metadata key, not a new status field* — **confirmed**:
  `_status_core.py:143` (`write_status` commits the whole document) and `:306` (`normalize_metadata` hands back the
  free-form metadata dict); no schema gate stands between the two.
- *No consumer other than the reader at `_criteria_snapshot.py:1821` reads `functional_review_drop_reason`* —
  **confirmed**: a content search over the worktree found only the reader and its delegating caller
  (`_cmd_lifecycle.py:17`, `:1255-1268`), and the new test pins the negative over every `*.py` under the bundles.

## 4. Findings

Self-review (3 rounds, read-only sub-agent, one finding set per round):
- round 1 — 3 blocking: the D3e record named `criteria-authorize` for a re-freeze (fixed, `e8696c6bb`); the review
  rubric still defined `superseded` as a free-text citation (fixed, same commit); the light-lane envelope had no
  consumer in `planning.md` (fixed, same commit: print → question → authorize → one re-dispatch → stop). 7 advisory:
  the shared helper's docstring overclaimed identical populations (fixed); the `open_criteria` docstring's
  closing-state count (fixed); the stale-note clearing branch was untested (fixed); two answered (commit split,
  regex leniency — the latter refuted: `\b` cannot precede a `d` inside a word), one spec-literal (self-reference).
- round 2 — nothing blocking; 7 advisory, fixed in `8e833c494`: `cmd_archive` — the production finalize completion —
  never recorded the note (fixed + tested); the reused `outline_prompt` violated the envelope's declared shape
  (fixed: `questions[]` with `id: refreeze-authorize`); the validator's empty-field message (fixed); `_grade_row`'s
  defaulting population argument (made required); the narrow-report sink sentence; `planning.md`'s missing
  `criteria-refreeze-authorize` command (inlined); `triage.md`/`SKILL.md` wording. Three answered with reasons
  (read path via `manage-status read`; free-text-after-reference by design; population divergence documented).
- round 3 — 4 open at the round limit. Operator asked; selected "fix F1/F2/F4, record F3 as answered". Fixed in
  `80d1a0b86`: the re-freeze branch's narrow-report print, the `verify-first` clause, and a comment typo. F3
  (self-reference) recorded as spec-literal. `self-review: budget-exhausted`.

PR review (CodeRabbit, `96de7f247` and `80d1a0b86`):
- `coderabbit inline inline-1` — reference regex accepted a `D<n>` token inside free text → **fixed** in `0b2cafc0f`.
- `coderabbit inline inline-2` — self-reference accepted → **answered** with the operator's recorded decision.
- `coderabbit nitpick nitpick-1` — add a `D2`-with-prose control → **answered**: both regex alternatives end at the
  same word boundary and take the same number check, so the variant re-runs the identical path.
- `sourcery-ai` — refused on quota (250k diff chars / 7 days); optional reviewer, no action owed.
- CI: no failing check on any head.

## 5. Reviewers

| Reviewer | Required | Outcome | Head reviewed | Trigger / wait history |
|---|---|---|---|---|
| `coderabbit` | yes (`quota_limited: true`) | **reviewed** the merge head `96de7f247` (COMMENTED; `final_review_risk_coverage` `kind=reviewed`, `sourceCommitId` = `coveredCommitId` = `96de7f247`; Merge Risk Minimal); earlier review on `80d1a0b86` | `96de7f247` | 9 triggers: 07:14Z, 16:46Z, 18:22Z (normal and `@coderabbitai full review`), 20:58Z, 22:33Z, 00:07Z, 01:57Z, 03:46Z, 04:02Z, 04:56Z. Seven quota refusals at ≥90-minute intervals per §6 step 7; the ninth trigger secured the review. The two inline findings and the nitpick are disposed above. |
| `sourcery` | no (`quota_limited: true`) | refused (hard quota, "1 day and 10 hours") | — | 1 trigger at 15:14Z; the notice's own ETA is outside this run's scope and the reviewer is optional, so no re-trigger. |

Standing review authorization was never needed for the final head: CodeRabbit reviewed `96de7f247` itself. It was
prepared for (qualifying review on `80d1a0b86`, every finding handled, re-trigger after the `0b2cafc0f` push
refused and recorded) and the alternative path became moot when the 04:56Z trigger succeeded.

## 6. Operator questions

1. "Self-review round 3 hit the 3-round limit with 4 findings open (F1 medium, F2 low, F3 low, F4 trivial) … How do
   you want the run to proceed?" — options: {fix F1/F2/F4 and record F3 as answered (recommended); fix all four
   including F3; land now and report all four as open} → **selected "Fix F1/F2/F4, record F3 as answered"**.
2. "CodeRabbit (required reviewer, quota_limited) has refused 4 trigger attempts over 3.5 hours … How should the run
   proceed?" — options: {keep retrying at the 90-minute cadence; close and reopen the PR then trigger; stop the
   session and resume later; close the PR and stop} → **selected "Keep retrying at the 90-minute cadence"**.

No free-text operator messages were received.

## 7. Rule check

Guard: `present`. One guard refusal belongs to this run: `ls -la .plan/orchestrator/ 2>&1` (R1, shell chaining,
07:01Z). The other five lines in `.plan/temp/guard.log` belong to other sessions (`review_completeness.py` work, the
`lb-134` worktree, a `plan-marshall:tools-integration-ci` call from another run) and are not attributed here.

Rule breaks by this run (not guard-recorded, reported as the rule requires):
- shell `ls` on `.plan/orchestrator/live-blockers/plans/` (a file-listing command where the file tools were required);
- shell `grep` over one build-server job log (the log itself is a sanctioned read, the shell `grep` is not);
- shell `wc -l` over the guard log.
None changed a conclusion: each was re-established with the file tools where it mattered.

No restart inside the session other than one harness restart, after which the lane text was re-read and the run
resumed at the pre-PR `verify` without repeating any completed step. No killed sub-agent; three self-review
sub-agent dispatches (rounds 1–3) plus two operator questions. One model, no switch
(`deepseek-v4.1-flash/high`).

Spec read: `resolve` reported `spec_source: ledger_worktree` and carried no `spec_differ` marker, so the shared
ledger worktree's copy is the one this run implemented and the main checkout's copy agreed.
`executor-skew: not_applicable` (source checkout; executor `0.1.2076`) — answered, recorded, never asked about.

## 8. Build server

Setup preflight `ready` (registered, project root the worktree). Every build was submitted with the default routing
and ran `daemon_longpoll`: **25 routed builds, 0 in-process fallbacks, 0 degradations, 0 launch-fault retries,
0 killed jobs.** Nine submits returned a live `queued` status and were re-attached by job id (the queue was
saturated for long stretches — one wait reported `queued_seconds: 1876`); each re-attach is counted in the 25.
One `verify` ran with the resolved `--timeout 1532` bound and finished in 1023s, so the daemon's supervisory bound
was never reached. No `runtime_stamp_reason` was reported by any resolve.

## 9. Residue

- **Self-supersede is permitted** (F3 / `coderabbit inline inline-2`): the rule accepts a citation naming the citing
  deliverable itself, which the spec's literal wording ("names an existing deliverable") allows. Recorded, not
  changed. If a successor should be required, that is a spec change.
- **`coderabbit nitpick nitpick-1`** was answered rather than fixed; the `D<n>`-with-prose variant remains untested.
- **Commit/Done-when split:** D3's `open_criteria` half and its helper landed in the D1 commit (`9eb830015`) and its
  hand-off wording in the D2 commit (`634a7b846`), because the shared module and workflow document cannot be split by
  path without a rebase (forbidden). The plan's own `test-first` evidence is unaffected: every D3 test was red before
  its fix.
- **An environment-dependent collection error** in the first full `module-tests` run (28236 passed, 0 failed, 1 error:
  `test_target_tree_foundational_skill_freshness.py` — the target-tree generator racing under xdist with
  `Directory not empty`). It did not recur in the `--no-parallel` run or in either `verify`, and the module is
  untouched by this diff.
