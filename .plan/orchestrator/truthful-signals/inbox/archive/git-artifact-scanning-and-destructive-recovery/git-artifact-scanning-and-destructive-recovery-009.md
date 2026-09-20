envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=landing
created=2026-08-31T08:32:23Z

# Landing — PLAN-TRUTH-090 git-artifact-scanning-and-destructive-recovery

**PR:** #1371 · **merge commit:** `8bc4a68f6` · **state:** merged (squash, via merge queue)
**Base:** `main` · **Head at merge:** `b9506f81a` · **Deliverables:** 9 · **Tasks:** 19

## Shipped

- **D1/D2** — `scan_artifacts` never offers a plan's live state. The exclusion is keyed on the
  **first path segment** being `.plan` and is unconditional: not defeatable by `--no-gitignore`, by a
  `.gitignore` lacking a `.plan` rule, or by a failed ignore oracle. Each ignore mechanism is pinned
  by its own test.
- **D3/D4** — the named-recovery contract is inspection-first, the guard detects a restatement, and
  the layer-D `worktree-handling.md` § "Recovery Loop" no longer routes a dirty path to
  `git checkout --` under a "(typical case)" qualifier.
- **D5** — `get_gitignored_files` distinguishes "nothing ignored" from "could not determine", and an
  indeterminate ignore set is an error rather than a silently-empty safe list.
- **D6** — `_capture_config_hash`'s prose states what the code does; the refuted
  "exit 2 → silent None" clause is gone and the non-dict guard is tested.
- **D7** — `main_dirty_exempted` publishes the population the layer-D filter drops, registered
  `informational_only` and deliberately outside `_CORE_INVARIANTS`. Dispatch sites pass `--workflow`.
- **D8** — the `baseline-reconcile` row names the merge-base anchor; the dead `SHIM(B)` marker is gone.
- **D9** — `switch-and-pull --plan-id` resolves the **main checkout root** as its contract states,
  via `main_checkout_root()`, with `RuntimeError` routed onto `project_dir_not_a_git_repo`.

## Not closed — read before assuming coverage

- **No executed red-first evidence for TASK-015, TASK-016, TASK-019.** The only test surface is
  orchestrator-tier (`module-tests` ~1717s, no per-file target), so the RED-before half was reasoned
  and hand-traced; the whole-tree `verify` confirms the GREEN half only. **Deliverables 4 and 9 and
  the D1 test retirement are PARTIAL on that axis.**
- **D7 shipped 7 of 15 declared paths** by the run's own count, and **11 of 19** by the
  retrospective's structured derivation — `unreconciled`. Six of the eight misses are files this
  plan's own Out-of-scope boundary forbade, so **D7 was born partial at outline time**.
- **D7(c) dropped as MOOT** (`doc/plans/` absent from this tree). **D5(b) and half of D7(a)** were
  already closed at HEAD.
- **`.plan/temp` widening is an ACCEPTED deliberate behaviour change**: D1(a)'s first-segment rule is
  broader than the stated goal (which named the plan's *live* state), so scratch files are no longer
  offered for cleanup either. Cleanup there is owned by `system.retention.temp_on_maintenance`.
- **`scope_creep_check` returned `could_not_look`** (`no_baseline_sha`) — unmeasurable, not a clean zero.

## Review coverage — the merge did NOT clear it

**No CodeRabbit review object covers the merge candidate `b9506f81a`.** Its newest is `21:07:11Z`
over `399b9f9b..df27ad2`; the head landed 28 minutes later. Every later trigger was refused as an
*already-reviewed commit* — incremental bookkeeping, not a rate window (two triggers 21 minutes apart
refused byte-identically). The merge proceeded under an explicit HEAD-bound `barrier-ask-override`.

CodeRabbit did review the substance twice and caught two real defects the whole in-house gate suite
passed. `pr-agent` reviewed `b9506f81a` directly and reported nothing. `sourcery` never reviewed
(budget refusal), yet was credited `participated` off that refusal body.

## Owed to this epic

1. **Move-back, worktree removal and `archive-plan` are NOT done.** A stale merge-lock waiter holds
   the FIFO head with no lock holder; `release --require-stale` evicts stale *holders* only, so no
   verb covers it. The worktree is deliberately retained — it holds the only copy of plan state.
2. **Seven instrument defects filed, all `taken_into_account`**, all in `automatic-review/` or
   `phase-6-finalize/`, which sibling plans own: `cbd010`, `a7d7af`, `ec87de`, `ecbbef`, plus the
   `sourcery.md` / `coderabbit.md` registry-pattern gaps and the `refusal_class` mislabel.
   **This same merge landed a sibling's work across `automatic-review/` — check HEAD before treating
   any of them as open.**
3. **Two architecture hints named as owed** (post-merge, so named not written) for modules
   `plan-marshall:automatic-review` and `plan-marshall:phase-6-finalize`.
4. **Amendment to candidate-lesson `-001`**: both surfacer classes it proposes are directional and
   point the same way. Neither catches a predicate that **excludes more than its prose asked for** —
   which is exactly finding `498b7f`, and it shipped. Widen class 1 to be bidirectional.

## Cost

6.2M tokens · **143M billing-weighted** · 4h34m worked / 35h5m wall / **30h30m idle (87%)**.
Idle is rate-window waits, merge-queue polls and orchestrator-tier builds. `6-finalize` alone is
3.2M tokens and 73M billing-weighted — half the run.
