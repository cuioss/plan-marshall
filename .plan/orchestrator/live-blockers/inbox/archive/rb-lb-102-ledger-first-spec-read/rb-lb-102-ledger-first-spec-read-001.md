envelope_version=1
sender_type=plan
sender_id=rb-lb-102-ledger-first-spec-read
epic=live-blockers
kind=landing
created=2026-10-28T20:20:05Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-102-ledger-first-spec-read
epic=live-blockers
pr=#1882
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2025
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=unknown
step.sonar-roundtrip.open_issue_rules=unknown
```

guard: present (`.plan/temp/guard.log`; no line for this run's session tree)

PR #1882, merge commit `6d155457052b34b26dceccb170c74d2a67e636e9`.

## 1. Deliverables

**D1 — the default read order is the ledger worktree, then the main checkout. Met.**
- `test_default_reads_the_ledger_worktree_copy` — order `test-first`; failing run at HEAD `c4089e29e`,
  job log `21d1fb6dffd149fd8f13462f6392da95` (`assert ['Main checkout deliverable'] == ['Ledger
  worktree deliverable']`); asserts the worktree body and that `spec` is the worktree path.
- `test_a_spec_only_in_the_ledger_is_read_by_default` — order `test-first`; failing run at HEAD
  `c4089e29e`, job log `0fccbb07ef8749da8fdf523c66d68adb` (`status: error`, `error: invalid_spec`);
  asserts success and the worktree body.
- `test_a_spec_only_in_the_main_checkout_is_read_by_default`, `test_use_worktree_off_reads_the_one_copy`,
  `test_the_ledger_copy_is_readable_by_its_own_absolute_path`, `test_the_knob_gate_ignores_a_ledger_copy_left_on_disk`,
  `test_a_spec_in_neither_copy_is_refused`, `test_the_ledger_spelling_is_knob_gated` — order `none`.
- Commit `4920e7d46` (with the fix-only follow-ups `a1275b796`, `9caa2dfe9`, `cafb6ca84`).

**D2 — `--spec-from-ledger` stays accepted and means what the default now means. Met.**
- `test_the_flag_means_what_the_default_means` — order `none`; same `spec_source` and body with and
  without the flag.
- `test_the_flag_is_still_accepted_with_use_worktree_off`, `test_lane_text_names_the_flag_status` —
  order `none`.
- Decision recorded with its reason: the flag is kept as a documented no-op. Removing it would turn
  every command line that carries it into `unrecognized arguments`, and a deprecation cycle would add
  a surface whose only content is the default. Commit `4920e7d46`.

**D3 — the result and the landing still say which copy was read, and the lane text states the new
order. Met.**
- `test_resolve_reports_the_copy_it_read`, `test_two_differing_copies_carry_the_differ_marker`,
  `test_a_worktree_only_copy_reports_the_worktree_and_no_marker`,
  `test_a_main_only_copy_reports_the_main_checkout_and_no_marker`,
  `test_identical_copies_carry_no_differ_marker`, `test_the_no_op_mode_reports_one_copy_and_no_marker`
  — order `none`.
- `test_lane_text_states_the_worktree_first_order` (new order present, old default sentence absent),
  `test_lane_text_names_the_ledger_read_and_what_it_reports` (landing rule-check keeps
  `spec_source`, `spec_differ`, and now names the worktree-first default rather than the flag) —
  order `none`.
- Commits `4920e7d46`, `9caa2dfe9`.

**D4 — the lane's write rule is unchanged by the changed read. Met.**
- `test_reading_the_ledger_copy_writes_nothing` — order `none`; a full mtime+bytes snapshot of the
  fixture tree is byte-identical after the default worktree read.
- `test_lane_text_keeps_the_write_rule_verbatim` — order `none`.
- Commit `4920e7d46`.

**Per-head test runs against pushed heads**
- `4920e7d46`: scoped runbook-lane suite (229 tests) green.
- `a1275b796`: full `module-tests` 27366 green, but the worktree was edited while that job ran, so
  the run was discarded and superseded rather than credited.
- `9caa2dfe9`: full `module-tests` 27369 green (job `37bef992f0304a12928e50f058dbe873`).
- `cafb6ca84`: full `module-tests` 27370 green (job `05cc7d649d274c0fae035da9bb8833f8`) and
  `test-compile` green.

## 2. Personas and skills

- Setup and D1/D2 (production code): `persona-implementer`.
- Tests, every deliverable (unit/module tests): `persona-module-tester`.
- D3 (lane text): `persona-documenter`.
- Every self-review round: `persona-code-reviewer` (the `general` sub-agent loaded it as a standard).
- Domain skills: `skills: none named` — the spec carries no `Skills:` or `Persona:` lines.
- No surface drift: the change stayed inside the three files the spec's Expected Surface names.

## 3. Hypotheses

- **"The `/plan-marshall` lifecycle lane reads its pointed-at spec by cwd-relative path at
  `phase-1-init` and therefore also reads the main checkout's copy" — REFUTED.**
  `phase-1-init/SKILL.md` L311: the pointer's ingestion goes through
  `request create --body-file`, which resolves via `file_ops.resolve_orchestrator_store_file`; with
  `orchestrator.use_worktree` on a spec staged in the worktree is ingested from there, "never from a
  stale copy on the main checkout". The lifecycle lane already reads worktree-first; only the
  runbook lane did not. Not widened.
- **"Other docs describe the old default or the land-before-emit workaround" — REFUTED.**
  No `spec-from-ledger` occurrence in `marketplace/bundles/plan-marshall/skills/plan-orchestrator/`,
  and none in `doc/` (`doc/developer/opencode.adoc` L360-372 describes the lane without a read
  order). The old default sentence lived only in `runbook-lane/SKILL.md`; the land-before-emit
  workaround survives only in the epic ledger, which is outside this plan's write boundary.

## 4. Findings

**Self-review round 1 (sub-agent, `persona-code-reviewer`)** — 4 confirmed, 5 refuted:
- E1 `invalid_spec` had lost its only test after the rewrite — fixed: added
  `test_a_spec_in_neither_copy_is_refused` (`9caa2dfe9`).
- E2 the landing's rule-check item still credited "the ledger flag" with removing a silent older
  read — fixed: now names the worktree-first default, pinned by the D3 text test (`9caa2dfe9`).
- E4 no test reached the containment check for a *derived* main copy — fixed: added
  `test_a_link_at_the_derived_main_copy_is_not_read` (`9caa2dfe9`).
- E9 the ledger-store spelling was not proven knob-gated — fixed: added
  `test_the_ledger_spelling_is_knob_gated` (`9caa2dfe9`).
- Refuted as non-defects: E3 (silent fallback when the ledger copy fails containment — the standing
  constraint asks for exactly that, and it is tested), E5 (flag omitted from the two surface
  listings — D2 permits a documented no-op, and it is documented in prose), E6 (an explicit
  main-checkout path is overridden by the worktree copy — D1 mandates it), E7 (duplicated fixture /
  `str()` wrapper — load-bearing for mypy), E8 (two `_ledger_store_dir()` calls — deterministic,
  side-effect-free).

**Self-review round 2** — verdict `clear`: every round-1 fix landed and is reachable for the reason
it names, all four Done-whens met with in-tree evidence, no false doc statement, no unexplained file.

**CI review — CodeRabbit (required, quota-limited), review on head `9caa2dfe9`:**
- One Major inline finding: `_resolve_spec` read a same-shaped spec that is in neither store and
  labelled it `main_checkout` — a real defect against the spec's standing constraint. Fixed in
  `cafb6ca84` by `_named_copy_is_contained`, which requires the named file to resolve under one of
  the two store roots, with the plan-worktree-tier regression test the finding asked for. CodeRabbit
  marked the thread resolved and "Addressed in commit cafb6ca".
- A later rate-limit notice is not a finding.

**Sourcery (optional):** refused on its own budget for the first head, then APPROVED `cafb6ca84`.

No other PR comment, review comment or thread was open at the merge head.

## 5. Reviewers

| Reviewer | Required | Head reviewed | History |
|---|---|---|---|
| coderabbit | yes (`quota_limited`) | `9caa2dfe9` (previous head — NOT the merge head) | triggered 18:57:51Z on `9caa2dfe9`, reviewed 19:02:29Z (COMMENTED, marker `sourceCommitId=coveredCommitId=9caa2dfe9`, `kind=reviewed`); one Major finding fixed in `cafb6ca84`; re-triggered once at 19:21:48Z after the last push, refused on quota at 19:24:20Z ("Review rate limited", next included review in 33 minutes) |
| sourcery | no | `cafb6ca84` (merge head) | triggered 18:58:07Z, refused on its own budget 18:58:11Z; ran again on the new head and APPROVED 19:22:46Z |

**Standing review authorization** (CodeRabbit is `quota_limited`): (1) a qualifying review exists —
a formal COMMENTED review on `9caa2dfe9`, one of this PR's heads, with the `kind=reviewed` marker;
(2) its one finding is fixed in a pushed commit and its thread is resolved; (3) it was re-triggered
once after the last push and the refusal is recorded; (4) every other gate condition holds on
`cafb6ca84` — Sourcery approved the merge head, no comment is unhandled, the build gate is green and
CI is green. The merge head differs from the reviewed head only by that fix and its regression test.

## 6. Operator questions

**Asked once** (the question tool): "The Sonar merge condition cannot be met (undecidable read at
`cafb6ca84`); how should I proceed?" — options "Do not merge now" / "Merge despite undecidable
Sonar" / "Close #1882 unmerged". **Selected: "Merge despite undecidable Sonar."** The Sonar condition
was the only unmet merge condition, and the selection names that exact gap.

Free-text operator messages: none.

## 7. Rule check

- Guard: `guard: present`; `.plan/temp/guard.log` holds no line for this run's session tree, so no
  guard refusal is attributed to it.
- **Disclosed deviation — reads outside the repository root.** Two build job logs were read at
  `/home/oliver/.plan-marshall/marshalld/job-logs/…`, which the "stay inside the repository" rule
  forbids. The lane's § 4 "open the `log_file` it names" is what pointed there, because the daemon
  writes job logs outside the checkout. Logs under the repo's own `.plan/…/build-results/…` were
  never read directly — they were only passed to `pyproject_build parse`.
- **Disclosed deviation — absolute `--project-dir`.** Builds were run with an absolute worktree path
  rather than the resolve-supplied relative one. The relative form is re-run by the daemon from a cwd
  where it does not resolve, so the wrapper falls back to the absent `pwx` and the job fails
  `execution_failed` (jobs `9ee31ce3695d441cba98b390f5c8b97c`, `91ec1f43db5b4bc69e3ad03488bab293`).
  Same worktree, different spelling of the path.
- **Disclosed deviation — extra pw tasks through the build wrapper.** Beyond the resolved canonicals,
  `lint`, `compile` and `test-compile` were run through the same `pyproject_build` wrapper to locate
  a red quality gate and to pre-empt a red `verify`; no binary was invoked directly.
- **Re-dispatch.** One routed `module-tests` job (`306453e0…`) ran while the worktree was being
  edited; its green result was discarded and a fresh per-head run (`05cc7d64…`) is the evidence.
- Shell file operations issued by the run: none — files were read with Read/Grep/Glob; every shell
  call was one git plumbing command or one executor call. One command per call; no `&&`, `;`, pipes,
  command substitution, loops or heredocs.
- Spec read: `spec_source: main_checkout` at setup (the ledger worktree held no copy then), and
  `spec_source: ledger_worktree` with no `spec_differ` marker on the landing-time re-run — i.e. the
  new default reading the landed ledger copy, identical to the main checkout's.
- `executor-skew` verdict: `not_applicable` — the lane text lives in the source checkout, whose
  executor maps that checkout's own scripts, so the lane text cannot name a verb they lack. Answered
  and recorded, never asked about.

## 8. Build server

- Setup preflight on the worktree: `ready` (registered, version 1). Routing `auto`, worktree
  executor `present`.
- Every build routed (`mechanism=daemon_longpoll`); no `degraded` fallback and no
  `executor_absent_from_worktree` degradation.
- Routed `verify` hit the daemon's supervisory bound once (`timeout_used_seconds: 1498`,
  `timeout_source: explicit`, job `3d1aaa2c…`); the project's split form (`quality-gate` +
  `module-tests`) is the gate that ran from then on.
- No `killed` job.
- Runtime stamp: complete at landing time — no `runtime_stamp_reason`.

## 9. Residue

- **Routing defect (for the orchestrator):** a daemon-routed build with a *relative* `--project-dir`
  fails with `execution_failed`, because the daemon re-runs the executor from a cwd where the
  relative path does not resolve and the wrapper falls back to `pwx`. The lane's own § 4 spells the
  flag that way, so every runbook-lane run on this project pays the failure before discovering it.
- **Sonar:** the merge proceeded with an `undecidable` Sonar read (`analysis_revision_unavailable`) on
  the operator's explicit selection. The project has no Sonar job in `.github/workflows`, and its
  non-PR read is undecidable too (issue list truncated: 500 of 1242 returned), so no future lane can
  satisfy the Sonar merge condition on this project until one of the two is addressed.
- **Epic ledger:** `.plan/orchestrator/live-blockers/epic.md` still records the open item this change
  closes ("the lane accepts `resolve --spec-from-ledger`, but the emitted command carries no argument
  that sets it"). Reconciling it is the orchestrator's write, not this plan's.
