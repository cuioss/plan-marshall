# Landing Analysis: PLAN-21 — the worktree executor-regeneration trap

epic: multiplattform
workstream: WS-03
pr: #1444 (https://github.com/cuioss/plan-marshall/pull/1444)

> Landing record for one shipped plan. Lives at `landings/PLAN-21.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Drained from `inbox/worktree-executor-root-resolution-001.md`, corroborated against the merged
diff (`64733323a`), the CI abstraction, and the change ledger.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| **D1** — make the worktree escape detectable | **shipped-as-specified, at the alternative placement the spec authorised** | `file_ops.py` +123: new `WorktreeEscapeWarning(RuntimeWarning)` issued by `_warn_on_worktree_escape(root)`, invoked from `get_executor_path()`. `test_file_ops.py` +95, six tests. |
| **D2** — document the trap and the override | **shipped-as-specified** | `doc/developer/repository-layout.adoc` — the doc that already describes the `.plan/` layout and the `worktrees/{plan-id}/` tree. |

## ⭐ The declared surface matched the realized footprint EXACTLY — the first time in this epic

Realized: **3 paths**. Declared: **3 paths**. Intersection: **3**. Undeclared: **0**.
Over-declared: **0**.

```
doc/developer/repository-layout.adoc
marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py
test/plan-marshall/tools-file-ops/test_file_ops.py
```

Set against the measured series — PLAN-04: 1 undeclared, PLAN-15: 6, PLAN-11: 15 — this is the
first exact match the epic has recorded. ⚠️ **Do not over-read it as proof the pattern is
broken.** PLAN-21 was a three-file plan whose surface was swept against HEAD at staging time
*because* the PLAN-11 landing had just made under-declaration the live concern; it is the easiest
possible case, deliberately staged that way. What it does establish is that the sweep-then-stage
discipline works when applied — which is a claim about the discipline, not about the corpus. The
harder test is a spec with a split or a prose consumer-set, which is exactly what the standing
under-declaration watch names as the unfixed class.

## ⭐ The verify-first clause was genuinely settled, not stamped

The spec left D1's failure mode open on purpose — raise, warn, or flagged return — and required
the plan to *enumerate the caller set first* and state the choice. It did:

- The escape is surfaced at **`get_executor_path()`**, not inside `_resolve_plan_root()`. That is
  the alternative placement the spec's HYPOTHESIS explicitly authorised ("if the escape is better
  surfaced at one of these callers … take that placement and record why").
- The recorded reason is a real constraint, not a preference: `get_base_dir()` is **read-reach**
  — `_config_core` calls it at import time, and under pytest's `filterwarnings=["error"]` regime a
  warning there **would abort the whole suite**. `_resolve_plan_root` and `get_base_dir` therefore
  stay silent by design.
- A **warning rather than a raised error** is the deliberate flag: the docstring states the
  presence of the warning *is* the marker, and resolution still returns the escaped root.

This is what a settled verify-first clause looks like — the enumeration drove the choice, and the
choice is defensible from the enumeration alone.

## ⭐ The matched negatives are stronger than the spec asked for

The spec required "the escape case **and** a matched negative". Six tests landed:

| Test | What it pins |
|---|---|
| `..._worktree_subtree_escape_warns` | the escape itself |
| `..._unaffected_from_cwd_under_plan_local_plans` | **matched negative** — cwd under `.plan/local/` but OUTSIDE `worktrees/` stays unaffected |
| `..._unaffected_from_cwd_at_worktrees_container` | **boundary negative** — cwd exactly AT the `worktrees` container, no named worktree |
| `get_base_dir_..._read_reach_stays_silent` | the read-reach carve-out is PINNED, not merely asserted in prose |
| `..._tracked_config_override_from_raw_worktree` | the advertised remedy actually works |
| `..._tracked_config_override_wins_over_plan_base_dir` | override precedence |

⭐ The fourth row matters most: the carve-out that makes D1 safe is itself under test, so a future
change that starts warning from `get_base_dir` fails loudly instead of silently aborting suites.
The fifth exists because CodeRabbit found the remedy did not in fact pin the executor — the
finding was fixed at `35a3b8532` and turned into a regression test rather than a one-off patch.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown`; `landing-check` → `complete: false`,
  `missing_keys: [total_tokens]`. **7-for-7 on the OpenCode lane** — folds into the standing lane
  entry as a recurrence, not a new defect. `unknown` over `n/a` is again the correct anti-`n/a`
  choice.
- **Build gate: green, and this time the "merged tree" claim holds up.** Ledger's newest build row
  is `2026-09-07T21:36:48Z`, `exit_code: 0`, `tests_run: 20736`, `--project-dir
  .../worktrees/worktree-executor-root-resolution`. The merge commit is `21:38:37Z`. ⚠️ The same
  MECHANICAL gap as PLAN-11 exists — no post-merge run on main is recorded anywhere in the ledger
  — but the SUBSTANCE is different and the two must not be conflated: PLAN-21's merge parent
  `33c8140f3` (#1443) landed at `20:25:17Z`, over an hour BEFORE the verify, and nothing landed in
  the 2-minute window between verify and merge. The verified tree therefore equals the merged
  tree. PLAN-11's did not — PLAN-130 landed inside its 23-minute gap. **The defect is narrowed to
  its mechanical form, not re-raised.**
- ⚠️ **Unexplained: the test count fell 24773 → 20736 (−4037, −16%) between the two landings.**
  Both figures come from the same `--command-args verify` invocation shape, so they are
  comparable. The intervening commits ADDED 6304 net test lines (#1443 alone: +6802/−498 under
  `test/`), so line growth does not explain count shrinkage. Plausibly a parametrisation change —
  #1443's stated purpose is replacing vacuous cases with mutation-verified ones, and that could
  legitimately trade many weak cases for fewer strong ones. **Recorded as an unverified lead, not
  a finding:** both verifies were green, and this landing did not establish the cause.

## Routing and Merge Behavior

- **Review — full participation, and the required arm was obtained this time.** CodeRabbit
  reviewed and raised one Major finding (the `PLAN_TRACKED_CONFIG_DIR` remedy did not actually pin
  the executor), fixed at `35a3b8532` and confirmed resolved. Sourcery approved.
  `cuioss-review-bot` clean.
- **The stall recovery ran, and it worked.** CodeRabbit's per-developer quota stalled **#1439**
  for hours. Per the standing recovery policy the PR was closed unmerged and reopened as **#1444**
  on the same `fix/worktree-executor-root-resolution` head; the quota had cleared and the review
  arrived within minutes. #1439 is confirmed `closed` with `merge_commit_sha: null` — closed, not
  merged. ⭐ **This is the first execution of that policy in this epic, and it converted an
  unobtainable arm into an obtained one** — contrast PLAN-11, which shipped with CodeRabbit
  disclosed-unobtainable because no legitimate new head existed.
- **CI/merge:** merged via the merge queue; squash `64733323a47cda18771661db81f62c1eb3a6aad6`,
  confirmed an ancestor of `origin/main`. Branch prefix `fix/` — canonical.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `pr` stamped `#1444`
- [x] row `landing` stamped `landings/PLAN-21.md`
- [x] row `plan_marshall_plan_id` stamped `n/a` (OpenCode lane)
- [x] epic.md narrative reconciled from status.json
- [x] Open Defect — landing incomplete (`total_tokens`), folded into the standing lane entry
- [x] Open Defect — post-merge-verify gap NARROWED to mechanical, not re-raised
- [x] Watch opened — unexplained −4037 test-count drop
- [x] Watch retired — the CodeRabbit unobtainable-arm exposure (#1433 landed AND the recovery ran)
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **F1** The two contract-change proposals (`--project-dir` absolute form; basetemp geometry)
  shipped as **PR #1445** (`chore/contract-edits-project-dir-basetemp`, docs-only,
  skip-bot-review), **still OPEN** at the time of this landing. Its worktree
  `.plan/local/worktrees/worktree-contract-edits-project-dir-basetemp` is retained until it
  merges. ⛔ This is the one piece of PLAN-21's work not yet on main.
- **F2** The runbook mirror remains unshipped and unshippable by PR — `.plan/local/opencode/RUNBOOK.md`
  is gitignored. It stays folded into the standing one-machine-only gap. ⚠️ **Unresolved
  question the drain cannot settle:** whether a local runbook edit was in fact made during this
  run. It would be invisible to the PR by construction, so only the operator can answer.
