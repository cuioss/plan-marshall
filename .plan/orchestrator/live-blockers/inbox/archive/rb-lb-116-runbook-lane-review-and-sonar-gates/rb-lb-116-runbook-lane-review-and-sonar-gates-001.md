envelope_version=1
sender_type=plan
sender_id=rb-lb-116-runbook-lane-review-and-sonar-gates
epic=live-blockers
kind=landing
created=2026-11-08T20:39:32Z
revision=1
amended=2026-11-08T20:39:53Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-116-runbook-lane-review-and-sonar-gates
epic=live-blockers
pr=#1940
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=5
review_body_findings_handled=5
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

Guard: present (OpenCode guard installed; `.plan/temp/guard.log` read for this run's sessions — no refusal for this run's session tree).

## Deliverables

| # | Done-when | Verdict | Order | Test | Failing run | Commit |
|---|---|---|---|---|---|---|
| D1 | one fixture per case: open thread, undisposed body finding, Follow-ups/Nitpicks only, resolved thread restating the defect, undecidable read, clean PR | met | mutation-after | `test_runbook_lane_review_gate.py` | `e9405db93`, job `48a5b55aa9db42b1b120c8b9a5c8d8c4` — every refusing case read `merge_allowed: true` under the unresolved-threads-only mutation | `e9405db93` |
| D1 | each false case is red against a stub that checks only unresolved threads | met | mutation-after | `test_each_refusing_case_is_red_against_the_unresolved_threads_only_stub` | same run | `e9405db93` |
| D1 | § 7 names the verb as a condition | met | none | `test_the_merge_gate_names_the_review_gate_as_a_condition` | — | `e9405db93` |
| D2 | `landing-check` fails for each of the four missing fields, passes with all four | met | mutation-after | `test_landing_completeness.py::TestReviewAndSonarNumbers` (pure + real `inbox landing-check`) | `60db2e7a3`, job `04bf6cdb205d49f8855cd9049a4996f8` — 11 failures, `complete: true` over the missing keys | `60db2e7a3` |
| D2 | the lane text's facts block lists them | met | none | `test_a_landing_from_the_section_8_template_is_complete_except_total_tokens` | — | `60db2e7a3` |
| D2 | the analyze workflow carries the re-read step | met | none | `analyze.md` § Step 4 + the landing-template contract suite | — | `60db2e7a3`, `38c8ced67` |
| D3 | the gate refuses a lane dismissal, still admits a confirmed 0, still stops on undecidable/unconfigured, admits a key only on the operator's selection | met | mutation-after | `test_runbook_lane_sonar.py` | `b03f86eeb`, job `c67e3fd79e8042fb9cc6c4f825f45f5f` — the dismissal test read `success` where it must read `error` | `b03f86eeb`, `6475408f1`, `e8fb39841` |
| D3 | a hotspot-only head is not a confirmed 0; a page shorter than its total is undecidable; `not_configured` reads nothing | met | mutation-after | `test_read_open_issues.py` (incl. the real hotspot request) | `c6c3d59a1`, job `f2ea9fba45c544ef9812a36f2423049b` — `open_issue_count == 0` for one unreviewed hotspot | `c6c3d59a1` |
| D3 | the existing Sonar tests are updated, not deleted | met | none | `test_runbook_lane_sonar.py`, `test_runbook_lane_sonar_landing.py`, `test_read_open_issues.py` | — | `b03f86eeb`, `38c8ced67` |
| D4 | `resolve` returns the command; the lane text names the three points and the progress line; the command is the orchestrator's documented read | met | mutation-after | `test_runbook_lane.py` (5 fixtures, one parsing the emitted flags through the orchestrator's own argparse) | `e219b11d6`, job `dbf5088df9434a58ae9ca37b292d9b07` — `KeyError: 'inbox_read_command'` | `e219b11d6` |
| D5 | the rule once in § 1, § 8 refers to it, a text test pins `not evidenced` in both | met | mutation-after | `test_the_grading_rule_requires_an_artifact_for_every_claim`, `test_the_landing_report_grades_a_claim_by_the_artifact_rule` | `abfb5fce8`, job `d33e95327b4a4443a41c10aa090792a8` — `'not evidenced'` absent from § 1 | `abfb5fce8` |

Per-head test runs: every pushed head ran the affected module-tests, and the final merge head `f7612b086` ran the full `verify` (compile + lint + 33,325 tests) green; CI's `verify / verify` was green on that head.

## Personas and skills

- Production code (`runbook_lane.py`, `sonar.py`, `_orchestrator_inbox.py`): `persona-implementer`.
- Tests: `persona-module-tester`; documentation (`SKILL.md`, the standards, the templates, `analyze.md`): `persona-documenter`.
- Every self-review round and every PR-comment triage: `persona-code-reviewer`.
- Skills: none named in the spec.

## Hypotheses

- *The CI layer already exposes the unresolved threads with path and line, and each review's body* — **confirmed**: `github_ops.fetch_pr_comments_data` returns `inline` records carrying `thread_id`/`isResolved`/`path`/`line` and `review_body` records carrying the body, plus a `complete` coverage flag.
- *A review body's Follow-ups / Nitpick / Outside-diff sections are parseable from that body text* — **confirmed**: the live bodies carry `<details><summary>Label (N)</summary>` blocks; a nested `<summary>path (n)</summary>` is a per-file grouping inside one.
- *No lane step reads security hotspots, so a hotspot-only head passes as a confirmed 0* — **confirmed**: `read_open_issues` consulted the issue search only and `_fetch_hotspots` did not exist.
- *The orchestrator's inbox surface already has a verb that reads one plan's delivered mailbox* — **confirmed**: `orchestrator inbox read --slug … --plan-id …`.
- *The landing check holds the required-field set in `_orchestrator_inbox.py` and versions it by `landing-facts/1`* — **confirmed**. Decision recorded: an older producer is rejected under the SAME schema version and named at the four keys, because a bump would collapse the diagnosis to `['schema']`.
- *The project's new-code quality gate can fail for a reason that is neither an issue nor a hotspot* — **confirmed** (metric conditions such as coverage and duplication). Decision recorded: such a failure is **not** a finding for the open-findings rule; it is reported as the optional `step.sonar-roundtrip.quality_gate_status` fact.

## Findings

- Self-review rounds 1–4 (sub-agent, `persona-code-reviewer`, read-only): round 1 = 8 defects (fail-open on an unread surface, GitLab coverage diagnosis, the flattened-body inline count, an executor-resolution escape, doc drift across five files) — fixed in `e2befb3a8`; round 2 = 3 residuals (the landing template still demanding a provider re-read of the handled count, three-key enumerations, an unreachable guard) — fixed in `38c8ced67`; round 3 = 3 residuals — fixed in `aad97c2bb`; round 4 = 3 residuals (two three-key sentences, an untested guard) — fixed in `9027a8dfe`. `self-review: budget-exhausted`: no fifth round was dispatched, so the round-4 fixes are unverified by a further round.
- PR comments (all handled, threads replied-to and resolved):
  - nested file summary read as an unreadable section — fixed `63083479a`;
  - `--progress-file` optional, so the operator rule was lane prose — fixed `6475408f1` (`progress_file_required` + witness check);
  - the depth rule fail-open for a body wrapped in one block — fixed `6475408f1`;
  - the nearest holder must be a RECOGNISED section — fixed `529a8f680`;
  - a selected hotspot could be admitted — fixed `9935e8089` / `e8fb39841` (`hotspot_not_dismissable`, `hotspot_keys_required`);
  - the generic "concern remains" marker refused a thread whose bot confirmed a fix and named a separate concern — fixed `dfea285ec` (markers narrowed to this thread's defect).
- Body-finding dispositions: `inline-1 — 63083479a`, `inline-2 — 6475408f1`, `inline-3 — 6475408f1`, `inline-4 — 529a8f680`, `inline-5 — e8fb39841`. `review-gate` on the merge head: `merge_allowed: true` (`unresolved_review_threads: 0`, `5/5` handled).

## Reviewers

| Reviewer | Required | Outcome | Head reviewed | History |
|---|---|---|---|---|
| coderabbit | yes (quota-limited) | reviewed | `e8fb39841` via the marker-bearing summary (`coveredCommitId: e8fb39841`, `kind: reviewed`); formal reviews also on `9027a8dfe`, `63083479a`, `6475408f1`, `9935e8089` | seven trigger comments; six reviews with findings, each answered in-thread and resolved; after `e8fb39841` CodeRabbit paused automatic reviews, so `dfea285ec` and `f7612b086` carry no review — **standing review authorization** applied: a qualifying review exists on a PR head, every finding is handled, the reviewer was re-triggered after the merge-head push (silent: reviews paused, check SKIPPED, recorded), and every other gate condition held on `f7612b086`. |
| sourcery | no (optional) | refused | — | triggered twice; both times "your pull request is larger than the review limit of 150,000 diff characters". Optional, so not a merge gate. |

## Operator questions

1. "The self-review reached its 3-round limit… How should I proceed?" — options: "Run a 4th review round" / "Open the PR now". Selected: **Run a 4th review round**. Free-text messages: none.

## Rule check

- Every section 1 rule was kept by this run and by its sub-agent: no `gh`/`glab`/build-wrapper/binary invocation, no `python3 -c`, no shell file operations, one command per shell call, no `git stash`/`restore`/`rebase`/force-push, no `git branch -D`, every repository edit inside the worktree, `.plan/` writes limited to `.plan/temp/` and the `ci` body slots.
- **Two guard refusals, both mine, both corrected at once:**
  - `R7` — an edit attempted on the main checkout's `marketplace/.../runbook_lane.py`. The guard refused it and named the worktree; every later edit went to the worktree.
  - `R1` — a shell command carrying `;` (`cat >> /dev/null; echo ok`). The guard refused it; the command was abandoned, and the file tools were used instead.
  No rule was re-attempted after a refusal.
- One `unknown_verb` rejection was reported by the EXECUTOR (not the guard): `review-gate` through the main checkout's executor, which predates the verb. Recorded, then `worktree-executor-refresh` regenerated the worktree's surface as step 3 prescribes, and the verb ran there.
- Guard state: `guard: present` on this harness; `.plan/temp/guard.log` is the audit log this run read.
- Restarts / killed sub-agents / re-dispatches: none. Four self-review dispatches, each recorded above.
- Spec read: `spec_source: ledger_worktree`, no `spec_differ` marker (the main checkout's copy was identical).
- `executor-skew`: `not_applicable` (source checkout; the executor maps this checkout's own scripts), answered and recorded, never asked about.

## Build server

Setup preflight: `ready` (enrolled, daemon reachable). Every build was routed and reported `mechanism=daemon_longpoll`; no build fell back in-process and none was retried for a launch fault. Several routed calls returned a live `queued` status while another job held the machine's slots; each was re-attached with `build_server wait` on its job id (the same call, never backgrounded), and none of those re-attachments is a fallback. No `killed` job. `runtime_stamp_reason`: none — the landing-time `resolve` returned a complete stamp.

## Residue

- **The lifecycle producer cannot satisfy the four new required landing keys.** No `phase-6-finalize` step publishes `unresolved_review_threads`, `review_body_findings_total` or `review_body_findings_handled`, and `sonar-roundtrip` counts issues without hotspots, so a lifecycle-emitted landing is now INCOMPLETE at those keys. Named as the remedy in `emit-landing.md`, `landing-payload-spec.md` and the inbox constants — **owed outside this plan**, alongside the executor regeneration and the harness sync the spec already lists.
- **GitLab publishes no coverage signal**, so `review-gate` answers `coverage_unavailable` there and the merge gate cannot be satisfied until that provider publishes one. Stated in the lane text; **owed** if this lane is to serve GitLab projects.
- `read_open_issues` without `--pr` has a project-scoped hotspot leg (documented; the lane always passes `--pr`).
- `_count_section_findings` reports one finding for a section that declares no count and nests no counted blocks (documented; over-count only, dischargeable with a stated reason).
- Sonar stays `not_configured` in this repository, so the D2/D3 Sonar paths are exercised by fixtures only, as the spec requires.
