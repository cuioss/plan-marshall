envelope_version=1
sender_type=plan
sender_id=rb-lb-172-consolidated-leftover-fixes
epic=live-blockers
kind=landing
created=2026-11-20T14:04:29Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-172-consolidated-leftover-fixes
epic=live-blockers
pr=#2036
merge_state=open
cleanup_owed=false
deliverables_total=10
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2173
steps=setup:done,implement:D1-D5:done,D6-D10:not_shipped,build-gate:done,self-review:budget-exhausted,pr:done,reviews:open,merge:open
unresolved_review_threads=6
review_body_findings_total=23
review_body_findings_handled=0
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

## Deliverables

| # | Verdict | Evidence |
|---|---------|----------|
| 1 | **met** | Parser: 12 construct-tests red at `c22d103fb`, green at `a39aa80d6`; `order: test-first`; failing run base worktree, log `9b1cf2ad3c39474eaf1eaab990e78de8.log`; `_body_findings` 287 → 105 lines. |
| 2 | **met** | Carry-forward binding and decision-verb edges: 13 tests red at `a39aa80d6` (sonar sources identical to `c22d103fb`), green at `54fe92366`; `order: test-first`. |
| 3 | **met** | Delegating-consumer classifier change (code, not text: the CI rule is not in this checkout); one retry-class list cited by §7; whole-document doc pins; `order: test-first` for the classifier, `mutation-after` for the text pins; green at `93d55c4b3`. |
| 4 | **met** | Slot anchor, `invalid_slot` ordering, derived valid slot, one doc owner; `order: test-first`; green at `28e051041`. |
| 5 | **met** | Time-classified false claim, `deliverables_retired`, six closing states, Watch rule, whole-document reopen detector (three planted shapes) and the provider-fetch property with rename/shell-out controls; `order: test-first` for the detectors; green at `6ebc69cf4`. |
| 6-10 | **not shipped** | Not started. The run reached its working limit with five deliverables complete and `verify` green at `a8bd2ffac`. Each is recorded by number in the PR body so the orchestrator can re-stage it. |

`verify` (mypy + ruff + pytest, whole tree) green at `a8bd2ffac` (daemon job `45b60d30254c49b0a6c0db257f3b236f`, 1071 s).

## Personas and skills

Per deliverable, as declared in the spec: `persona-implementer` for every one; skills
`plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`,
`plan-marshall:runbook-lane` (D1-D3), `plan-marshall:workflow-integration-sonar` (D2),
`pm-documents:ref-documentation` (D3, D5), `pm-plugin-development:plugin-architecture` and
`plan-marshall:tools-integration-ci` (D4), `plan-marshall:plan-orchestrator` (D5).
`skills added: none` (no surface drift; every touched file is inside the Expected Surface).

## Hypotheses

- **D1 (a)-(d) under-count** — CONFIRMED by running each constructed input at base (12 red).
- **D2 carry-forward / decision-verb minors** — CONFIRMED (13 red at base).
- **D3(a) the delegating consumer is decided by a rule the CI never applied** — CONFIRMED by reading
  `.github/workflows/python-verify.yml` (opts in, no `paths-ignore`, delegates via `uses:`), so the
  CODE changed and the text stands.
- **D5(b) `triage.md` says "five closing states"** — CONFIRMED; six, the retirement decision being the
  sixth.
- **D3(e) "the §7 reach rule is empty for its own example"** — REFUTED: §7 states the reach rule and
  covers "merge without reviewer X"; nothing changed there.
- **D4 live executor bound 64** — CONFIRMED by the spec's own statement; the derivation is capped at 64.
- **D2(e) head revision from local refs** — the read already resolves local AND remote refs and requires
  agreement, which is the "two independent observations" the spec asks for; no code change.

## Findings

Self-review: the dispatched `persona-code-reviewer` sub-agent round was NOT run — the run reached its
working limit first. `self-review: budget-exhausted`, with no findings raised and no verdict claimed.
PR review surfaces (CodeRabbit, on the head): 6 unresolved threads and 23 review-body findings, none
handled — the PR is left OPEN for them, and the merge gate correctly refuses.

## Reviewers

| Reviewer | State | Head | Trigger |
|---|---|---|---|
| coderabbit (required, `quota_limited`, `review_complete_after_handling`) | reviewed | `a8bd2ffac` | `@coderabbitai review` posted; review completed (check SUCCESS) |
| sourcery (optional) | skipped | — | `Sourcery review` reported SKIPPED by the provider |

## Operator questions

None asked.

## Rule check

- Guard: present on this harness; no guard refusal was recorded for this run.
- One shell file operation was issued early (`ls` of the progress directory) and refused/used before the
  rule was applied — recorded here rather than hidden.
- `spec_source: ledger_worktree`, no `spec_differ` marker.
- `executor-skew: not_applicable` (source checkout) — answered, recorded, never asked about.
- Base evidence: one detached base worktree at `c22d103fb` (D1), removed with `git worktree remove`
  after a clean `status --porcelain`; `cleanup_owed=false`.
- Builds: all `daemon_longpoll`; no fallback, no retry, no `killed` job. One `verify` run was
  re-attached twice through the daemon's bounded wait before it reported success.

## Build server

`build_server: ready` (registered), `mechanism=daemon_longpoll` for every build; 0 in-process
fallbacks. `verify` green at `a8bd2ffac`; `quality-gate` green at every commit point.

## Residue

- PR #2036 is OPEN: 6 unresolved CodeRabbit threads and 23 review-body findings need triage before the
  merge gate can pass.
- D6-D10 are not started (recorded above and in the PR body).
- The runbook-lane worktree remains for that follow-up; the base worktree is removed.
