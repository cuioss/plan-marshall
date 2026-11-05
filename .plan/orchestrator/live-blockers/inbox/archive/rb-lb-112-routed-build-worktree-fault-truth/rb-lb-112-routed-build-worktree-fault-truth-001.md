envelope_version=1
sender_type=plan
sender_id=rb-lb-112-routed-build-worktree-fault-truth
epic=live-blockers
kind=landing
created=2026-11-05T11:48:58Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-112-routed-build-worktree-fault-truth
epic=live-blockers
pr=#1910
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
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## 1. Deliverables

Per Done-when, with the `order` the evidence carries. `test-first` means the failing
output came from a run against the unfixed code, before the fix existed.

**D1 — "the failure is reproduced, or the premise is refuted, before any code changes."**
- met — "the PR records the routed and in-process results of one reproduction with
  the copy that ran, and states reproduced or refuted": recorded in PR #1910 §
  Reproduction; verdict **reproduced**; copy = this repository's source tree (the
  executor maps `marketplace/bundles/...`; `executor-skew` answered
  `not_applicable` for exactly that reason and was recorded at setup). The
  reproduction is fixture-level and says so: `build_server` was `down`
  (unreachable) for the whole run, so no live daemon-routed run was possible.
- met — "a fixture test … is red at HEAD when the verdict is reproduced":
  `order: test-first`. Failing run at commit `5555baf33` (pre-fix HEAD) with the
  test uncommitted; output identifier
  `.plan/local/plans/NO_PLAN/build-results/plan-marshall/python-2026-11-04-214901.log`
  — `TestMovedBackPlanRoutedBuild::test_the_routed_result_reaches_the_caller_as_the_child_reported_it`,
  `assert 'build_failed' == 'worktree_resolution_failed'`. The test landed in
  `17191b4fa` with `xfail(strict=True)` on its two forward assertions (each marker
  naming the deliverable that removes it), so the intermediate head stayed green
  without the red-at-HEAD evidence being lost. The in-process leg is pinned by
  `test_the_direct_build_reports_the_same_fault_as_itself` (green at HEAD —
  the contrast that makes the defect routing-specific).

**D2 — "the daemon child resolves the same tree as the routing process."**
- met — the routing process appends `--resolved-project-dir <exec_root>` for a
  real plan id; `build_main` consumes it before any resolution; `--plan-id` stays
  for the ledger row and slot accounting; a carry beside an explicit
  `--project-dir` is refused; the carry is honoured only under `MARSHALLD_JOB`.
- met — "the D1 fixture is green for a routed build with `--plan-id` after
  move-back, and the result is the build's own result, with the plan id on the
  ledger row": `test_the_routed_child_carries_the_tree_the_routing_process_resolved`
  (submitted argv carries the tree; `extract_plan_id` still returns the plan),
  `test_build_main_uses_the_carried_tree_without_resolving_the_plan` (a tripwire
  proves no `--plan-id` resolution happens). `order: test-first` — failing run at
  `5555baf33`, output `…-215045.log`; passed at `a1fac8ee9`
  (`…-220403.log`, `…-220444.log`).
- met — "a direct, non-routed build behaves as before" and "PLAN-LB-104's
  `--project-dir` routed cases stay green unchanged": those routes append no carry
  (`_carry_resolved_tree` returns the argv untouched) and their tests are
  unmodified.
- met — "the strict gate of `get-worktree-path` stays strict": `_status_query.py`
  is not in the diff at all.

**D3 — "a structured fault the child emits before the tool runs reaches the caller as itself."**
- met — "a routed fixture whose child prints the `worktree_resolution_failed` body
  and exits 2 returns that error name and reason with exit 2 and no synthetic row":
  `test_the_routed_result_reaches_the_caller_as_the_child_reported_it` asserts the
  name, the child's reason TEXT, `exit_code: 2`, and the absence of the synthetic
  row; `TestPreToolFaultPassThrough` adds the reader-level discriminator, the slot
  refusal with its corrective, the JSON-formatted refusal, the trailing-object
  guard, and the JSON applied bound. `order: test-first` — failing run at
  `5555baf33`, output `…-214901.log`; passed at `392291ad8`
  (`…-223114.log`, `…-223244.log`).
- met — "a fixture whose child ran the tool and failed still returns `build_failed`
  with the row": `test_a_build_that_ran_and_failed_keeps_build_failed_and_its_rows`,
  green at HEAD and after (a true matched control: the discriminator is the child's
  error NAME, never its exit code).
- met — "the result formatter's field whitelist carries any new field on both the
  TOON and the JSON path": no new field was needed — `reason` and `message` are
  already in `_build_format.EXTRA_FIELDS`, so TOON and JSON agree.
- met — "a direct, non-routed build already reports `worktree_resolution_failed` as
  itself with exit 2; the routed path matches it": both answer name + reason +
  exit 2.

**D4 — "the factory docstring states the invariant that holds."**
- met — the claim that `--plan-id` "resolves identically in both processes" is gone
  (the only remaining hit is the inbox finding that quotes it as the defect), the
  replacement states when the two resolutions agree and names the carry, and
  `TestResolvedTreeDocContract` pins the removal, the mechanism and the seam's
  behaviour. `order: mutation-after` — re-inserting the committed old sentence made
  `test_the_old_identical_resolution_claim_is_gone` fail at `85a1588ac`'s follow-up
  state, output `…-224023.log`; the restored text is byte-identical to `85a1588ac`
  (`git status` showed only `uv.lock`).

Per-head test runs against pushed heads: `module-tests plan-marshall` at
`a1fac8ee9` (27501 passed, 0 failed; one environment flake in
`test_target_tree_foundational_skill_freshness`, green in isolation at
`…-222459.log`); whole-tree `module-tests` at `85a1588ac` (learned bound expired at
1643 s, `…-224412.log`; raised-bound re-run green, `…-231215.log`); at `eada532bf`
(32590 tests, `…-065629.log`); at `403cbc1d0` (32593 tests, `…-075952.log`); at the
merged head `1cb7b8bb1` (32648 tests, `…-092814.log`); at `d014fd73c` (32649 passed,
0 failed, one fixture-setup flake in `test_marshalld_supervisor.py` —
"the build never published its pid before the timeout" — green in isolation at
`…-110656.log`; the project's own `verify / verify` CI job was green on that head).

## 2. Personas and skills

- production code (D2, D3, D4): `persona-implementer`, loaded before the first
  deliverable and applied throughout.
- tests: `persona-module-tester` methodology (AAA, matched positive/negative
  controls, purpose-stating docstrings, non-vacuity tripwires) applied to every
  new test without loading the binding (the lane accepts the standard).
- self-review rounds 1–5 and every PR comment: `persona-code-reviewer`.
- Domain skills: **skills: none named** — the spec declares no `Skills:`/`Persona:`
  lines for any deliverable.
- Surface drift: none beyond the spec's own Expected Surface list, and that
  drift is declared in PR #1910 § "Surface drift" (`_build_cli.py`,
  `resolve_project_dir.py`, `test_build_cli.py`, one bullet in
  `extension-api/standards/build-api-reference.md`). No domain skill applies to
  those modules, so none was added.

## 3. Hypotheses

- "The inner process fails after move-back (cwd in the worktree, plan directory
  absent, strict gate fails)." — **confirmed**, by fixture:
  `test_the_child_cannot_resolve_the_plan_from_its_own_tree` raises
  `WorktreeResolutionError` from the child's tree while
  `test_the_routing_process_resolves_the_still_existing_worktree` resolves the
  same flag from main. `resolve_project_dir.py:124-130` (plan-id branch) →
  `file_ops._query_worktree_path` (strict, `_status_query.py:683-691`).
- "The daemon child's structured error body is discarded or not parsed on the
  routed result path." — **confirmed**: the routed failure leg built
  `build_failed` from the daemon job outcome and the reader attached a fault only
  for `LAUNCH_FAULT_ERRORS` (`_build_result.py:267` at HEAD). Fixed by
  `PRE_TOOL_FAULT_ERRORS` + `ChildFault`.
- "The field whitelist the formatter needs is `_build_format.EXTRA_FIELDS`." —
  **confirmed and not needed**: `reason`/`message` were already whitelisted
  (`_build_format.py:41-58`), so no formatter change was required.
- Verification clause: the window is reachable in a normal plan run — **confirmed**
  by the lane's own ordering (`phase-6-finalize/SKILL.md` § "Return-to-main
  ordering": move-back → resume remaining finalize steps → worktree removal), so a
  build routed with `--plan-id` during the resumed steps hits it.

## 4. Findings

Five self-review rounds (rounds 4 and 5 operator-authorized past the lane's
three-round limit) plus three CodeRabbit review rounds. Every finding was fixed or
answered; the ones that mattered:

- the carry's trust hole (`--resolved-project-dir` consumed before any resolution
  on every build subcommand) → now marker-gated, refused with
  `carried_tree_outside_daemon_job`;
- the refusal message named the wrong flag pair → the raise's own reason wins;
- `invalid_invocation` promised more than the executor checks → the residual is now
  stated precisely, in both skew directions;
- `queue_saturated` was the last child-side pre-tool refusal outside the classifier
  → classified, and the factory imports the constant instead of respelling it;
- an unclassified refusal this branch itself introduced
  (`carried_tree_outside_daemon_job`) → classified;
- the routed `invalid_invocation` dropped the executor's actionable corrective →
  `ChildFault.corrective` publishes it as `message`;
- four stale enumerations of a fault set that kept growing → removed; the set is
  the single statement of membership;
- the JSON-formatted child verdict was not read at all (CodeRabbit) → JSON fallback;
- that fallback kept the last object *decoded* rather than the last with a `status`
  (CodeRabbit) → fixed, so a trailing `{}` cannot discard a verdict;
- the JSON path ignored the applied-bound triple (CodeRabbit) → read with the same
  guards as TOON;
- the carry flag was spelled in two modules (CodeRabbit nitpick) → imported from
  its declaring module.

Answered, not fixed: (a) probing the child executor's surface from the routing seam
or regenerating from it — the executor is per-project derived state regenerated at
finalize, and a silent preflight would turn a stale executor into a green build in
the wrong tree; (b) deriving `PRE_TOOL_FAULT_ERRORS` from its producers — the
producers are a narrower layer (`resolve_project_dir` is imported by ci/extension
code) and generated template text, so no shared source exists; the drift is instead
guarded in both directions by a test.

Residue: an **unstructured** dispatch refusal (no executor surface applies, so an
older script's argparse writes usage to stderr with no TOON body) still reports as
`build_failed` plus the synthetic row. Outside D3's "structured fault" wording,
named in the `ERROR_INVALID_INVOCATION` docstring.

## 5. Reviewers

| reviewer | required | quota-limited | reviewed head | trigger / wait history | verdict |
|---|---|---|---|---|---|
| coderabbit | yes | yes | `eada532bf` (review 1), `1cb7b8bb1` (review 2); **not** `d014fd73c` | `@coderabbitai review` posted 6× (07:20, 07:50, 10:10, 10:32, 11:xx); refusals recorded as "review rate limited" / "already reviewed the last commit" | reviewed twice; every finding fixed or answered; the last push was refused on quota |
| sourcery | no (optional) | yes | none | `@sourcery-ai review` posted; refused with its own review budget ("request another review in 16 hours") | refused (non-gating) |

**Standing review authorization** (required reviewer is quota-limited): the
qualifying review is CodeRabbit's on head `1cb7b8bb1`, whose
`final_review_risk_coverage` marker reads
`{"sourceCommitId":"1cb7b8bb1…","coveredCommitId":"1cb7b8bb1…","kind":"reviewed"}`.
Its findings were the two JSON items, both fixed in `d014fd73c` (the commit pushed
after that review) and both threads resolved; the earlier review's three threads
plus its nitpick were handled the same way. It was re-triggered after the last
push and refused on quota ("Next included review available in 33 minutes"), which
is recorded above. Every other condition held on `d014fd73c`: CI green, the gate
green, every comment handled, Sonar not configured.

## 6. Operator questions

Two `question`-tool calls, both answered; no free-text operator messages.

1. "The third self-review round (the lane's limit) reported six open items. All six
   are now fixed in commit 04aa23304 … How do you want to proceed?" — options
   "Run a 4th self-review round" / "Proceed to the PR as budget-exhausted".
   Selected: **"Run a 4th self-review round"**. (Acted on: rounds 4 and 5 ran.)
2. "The worktree's `uv.lock` is modified by the build toolchain, not by this change
   … It now blocks `git merge origin/main` …" — options "Restore uv.lock from HEAD,
   then merge" / "Commit the lock refresh, then merge" / "Stop here and leave the
   PR open". Selected: **"Restore uv.lock from HEAD, then merge"**. (Acted on: the
   file was restored to HEAD's content with `git checkout-index -f -- uv.lock`,
   then the base merge ran; the file was byte-identical to HEAD afterwards, and the
   merge itself brought main's own lock refresh.)

## 7. Rule check

- **Guard**: `guard: present` (opencode, pre-tool-use hooks installed). Two
  refusals occurred, both by the run's own record: **R1** (a `ls … | grep …`
  listing — shell chaining) and **R7** (an edit aimed at the main checkout's test
  file, reissued in the worktree). Neither was worked around; both were reissued
  with the permitted form. The guard log holds 877 lines across many sessions and
  is not attributed here by time window — this count is from the run's own record,
  not from the log.
- **Shell file operations issued**: none for reading or searching (Read/Grep/Glob
  used throughout). Git commands were the lane-sanctioned ones (`status`,
  `diff --name-only`, `log`, `fetch`, `merge`, `push`, `worktree remove`,
  `rev-list`, `checkout-index` once, per the operator's selection).
- **Routed builds**: zero. Every build reported `mechanism=in_process_fallback`;
  no daemon job was ever submitted (`daemon_longpoll: 0`).
- **Operator messages / model switches**: two operator questions (section 6); no
  model or effort switch during the run — `deepseek-v4.1-flash/high` throughout.
- **Restarts / re-dispatches**: none. Five self-review sub-agents were dispatched
  (rounds 1–5), each read-only, none killed.
- **Spec read**: `spec_source: ledger_worktree`, and no `spec_differ` marker was
  reported — the ledger worktree's copy was the one read, and no diverging second
  copy was flagged.
- **Executor skew**: `verdict: not_applicable`, reason "the lane text lives in a
  source checkout … so the lane text cannot name a verb those scripts lack".
  Answered, recorded, never asked about; the run proceeded.
- **Executor regeneration**: the worktree executor was refreshed
  (`worktree-executor-refresh`, `executor_regenerated: true`) after the new flag
  entered the argparse surface.

## 8. Build server

- Setup preflight on the worktree: **down** (`reason: unreachable`); the resolve
  result agreed for the project root. The daemon never became reachable during the
  run (the client's own streak notices say so).
- Per-mechanism: `daemon_longpoll: 0`; `in_process_fallback`: every build. The
  exact total is not durably recorded here rather than guessed — each build's own
  `[BUILD-SERVER] resolved build` line named `resolved=in_process,
  reason=unreachable`.
- No build fell back mid-run for any other reason, and no launch fault occurred, so
  there is no `degraded` / `launch-fault-retry` entry; no `killed` job.
- One bound expiry: the whole-tree `module-tests` at `85a1588ac` hit the learned
  bound at 1643 s (`timeout_used_seconds: 1643`, `timeout_source: learned`) at 99 %
  and was re-run with `--timeout 3300` (green, 1685 s).
- `runtime_stamp_reason`: absent — every runtime fact resolved.

## 9. Residue

- The unstructured dispatch-refusal residual (section 4).
- **Owed after merge**: regenerate the executor in every project before a *routed*
  plan build can use the carry — an executor generated before this change still
  matches its recorded script digest (only shared modules moved), so it applies its
  stale surface and refuses `--resolved-project-dir` as `unknown_flag`, reported as
  `invalid_invocation` (as itself, not as a red build) until regenerated. Direct
  builds are unaffected. A live routed check in the move-back window is likewise
  owed after that reconcile.
- The `uv.lock` refresh that the toolchain rewrites on every build reappeared at
  the end of the run; the merge brought main's own copy, so the worktree was clean
  at removal.
