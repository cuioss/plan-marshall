# Worktree Handling

Single canonical reference for the worktree mechanism used by plan-marshall: why it exists, where worktrees live, how they propagate through agent dispatch, the git invocation rule that applies inside them, the never-edit-main-checkout invariant, the cleanup ordering, and the `--plan-id` three-state contract that replaces per-call path forwarding.

This document is the source of truth. Sibling skills and standards reference it rather than duplicating the narrative. The per-call-site rule (e.g., "use `git -C` here", "pass `--plan-id` to the build wrapper there") stays at the call site; the worktree-specific application of that rule lives here.

## Why Worktrees

Plans run in **isolated git worktrees** for three independent reasons:

1. **Isolation** — uncommitted edits, generated files, and partial test runs stay confined to the plan's own working tree. A failed or aborted plan never pollutes the main checkout's index, working tree, or branch state.
2. **Parallelism** — multiple plans can execute simultaneously without contending for the main checkout's HEAD. Each worktree has its own branch and index, and under the move-based model (ADR-002) each holds its own authoritative copy of the plan's non-git state moved in at phase-5 start; the only shared state is the `.git/` repository (commits, refs, objects).
3. **No main-checkout pollution** — the main checkout remains the user's primary working environment. The agent never edits, builds, or tests inside the main checkout while a plan is in flight.

A plan opts into worktree mode at `phase-1-init` via `branch_strategy: feature` (the default for new plans). Plans that target the main checkout directly (e.g., docs-only patches with `branch_strategy: main`) skip worktree allocation and run against the main checkout — every rule below that mentions `{worktree_path}` substitutes `{main_checkout}` for those plans.

## Path Convention (Platform-Neutral)

Worktrees live at the platform-neutral location:

```text
<project_root>/.plan/local/worktrees/{plan-id}/
```

Rationale:

- `.plan/` is the canonical plan-state root that is already excluded from version control by every plan-marshall project's `.gitignore`. Placing worktrees under `.plan/local/worktrees/` inherits the same gitignore coverage without a separate carve-out.
- `local/` signals "host-local, do not transport" — the directory is a per-host scratch space, never published, never archived.
- `{plan-id}/` is the plan identifier (e.g., `my-feature-plan`), one directory per active plan.

The path is computed by the worktree-handling layer; callers never construct it from string concatenation. Resolve it via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

The script returns the absolute path when `metadata.use_worktree == true` and an empty string when the plan runs against the main checkout.

## Worktree Lifecycle

A worktree-enabled plan transitions through three distinct lifecycle states between `phase-1-init` and `phase-6-finalize`. The same plan record is read at every state; what changes is whether the worktree directory exists on disk and whether `worktree_path` is populated. Every other rule in this document — Dispatch Protocol, the `git -C` rule, the never-edit-main-checkout invariant, the cleanup ordering — applies **post-materialization only** (state 3 below). The pre-materialization phases run against the main checkout and DO NOT trigger worktree-binding requirements.

`phase-1-init` records only `use_worktree` — it does not seed the feature branch, the worktree path, or any worktree directory. The feature branch (`feature/{plan-id}`) and the worktree directory are created together at the first phase that mutates source code (phase-5-execute Step 2.5). Phases 2-4 are read-only analysis that produce only `.plan/` artifacts — they have no reason to allocate a working tree, and allocating one early would mean carrying an empty worktree through clarification, outline, and planning iterations that may be aborted before any code is touched.

### Lifecycle States

| State | When | `metadata.use_worktree` | `metadata.worktree_branch` / `worktree_path` | Worktree dir on disk | Path-binding rules apply |
|-------|------|-------------------------|----------------------------------------------|----------------------|--------------------------|
| 1. Pre-materialization | `phase-1-init` through `phase-4-plan` | `true` | unset | no | no — main checkout |
| 2. Materialization | `phase-5-execute` Step 2.5 | `true` | populated atomically (references.json + status.metadata) | yes — created | becomes yes during this step |
| 3. Post-materialization | rest of `phase-5-execute` and all of `phase-6-finalize` | `true` | populated | yes | yes — all rules below apply |

The post-materialization state ends when the cleanup ordering below removes the worktree directory; from that point the plan is back to the main checkout for the remaining branch / PR operations.

### Concurrent-Session Visibility

Per ADR-002, the move-based model means a plan's non-git-controlled runtime state — its plan directory (`.plan/local/plans/{plan_id}`) and the executor — MOVES into the worktree at phase-5 materialization (state 1 → state 3) and moves back to main at finalize. While the plan is post-materialization (state 3), there is exactly one authoritative copy of that state and it lives in the worktree; main does not hold it during execution.

The consequence for concurrent sessions: a plan-discovery operation (`manage-status list`) resolves plan directories via the single uniform cwd/worktree-relative rule, so a session operating from the main checkout will NOT see an in-flight plan whose state currently lives in another session's worktree — the plan reappears in the main-checkout listing only after its finalize move-back returns the plan directory to main. A session operating from inside that worktree (the orchestrator running the plan, with cwd pinned to the worktree root) resolves and sees the in-flight plan normally. This is expected behaviour, not a discovery defect: it is the direct corollary of moving (rather than copying) the plan state, which is what removes the reconcile-or-merge problem between a worktree copy and a main copy. The shared corpora (`lessons-learned/`, `archived-plans/`) and the cooperative `merge.lock` stay main-anchored by design and remain visible to every session throughout. The `manage-status list` operation documents the user-facing form of this property — see `manage-status/SKILL.md` § "list" → "Concurrent-session visibility".

### Worktree-Resolution Contract

Every script and skill that consumes `worktree_path` reads it as a boolean disk-presence signal — there is no empty-path sentinel state to carry. The applicability decision is governed by a single materialization predicate (`_worktree_materialized` in the handshake's `_invariants.py`): the worktree is in play when **either** `worktree_path` is present and non-empty **or** the active phase is a materialization phase (`5-execute`, `6-finalize`). The phase term is what lets the predicate treat the transient phase-5 window — after phase entry but before Step 2.5 backfills the path — as materialized even while `worktree_path` is still empty. The three disk-presence observations below are the path-binding consequence of that predicate:

| Observation | Meaning | Required behaviour |
|-------------|---------|--------------------|
| `use_worktree == false` | plan opted out of worktree mode entirely | bind to main checkout; never expect `worktree_path` to populate later |
| `use_worktree == true` AND `worktree_path` unset | pre-materialization (phases 1-4) — the worktree does not yet exist | bind to main checkout for this call; do NOT auto-create the worktree from outside Step 2.5 |
| `use_worktree == true` AND `worktree_path` non-empty | post-materialization — worktree exists on disk | bind to `worktree_path`; all rules below apply |

The phase-handshake worktree assertion (`_resolve_worktree_assertion`, exercised by both `phase_handshake capture` and `phase_handshake verify --strict`) is the fail-loud guard, and it consults the **same** `_worktree_materialized` predicate — so the assertion and the invariant-applicability gate can never disagree on whether the worktree is in play. Every phase boundary captures and verifies handshake invariants (including the `1-init` capture and the `verify` before `2-refine`), so the assertion *is* invoked during phases 1-4 — but for the on-main planning phases (`1-init` / `2-refine` / `3-outline` / `4-plan`) the predicate reports "not yet materialized" for an empty path, so the assertion treats the empty `worktree_path` as the legitimate pre-materialization state and passes. From phase-5 onward — and whenever the boundary phase is unknown (the fail-closed default) — the predicate reports "materialized", so an empty path while `use_worktree == true` is `worktree_unresolved`. A *set-but-broken* path (missing directory, non-worktree, or stale toplevel) is `worktree_unresolved` at every phase, planning phases included, independent of the predicate. Under cwd-pinning the common path never needs to consult this signal — the inherited cwd binds the caller to the correct tree. The `--plan-id` two-state contract documented below covers the residual escape-hatch callers that still resolve explicitly: invoked with `--plan-id`, they resolve internally and fall back to the cwd-relative plan root when the worktree is not yet materialized.

### Pre-Materialization Bypass

During phases 1-4 there is no worktree on disk and the orchestrator's cwd is the main checkout. Subagents inherit that cwd, so `.plan/` and project content resolve to main cwd-relatively (the uniform walk-up; ADR-002). Bucket A `manage-*` scripts are cwd-agnostic regardless of state, and Bucket B scripts resolve against the inherited cwd without any routing flag.

The practical consequence: phase-2 / phase-3 / phase-4 agents follow the same dispatch shape they would use for a `use_worktree == false` plan. They never construct a worktree path, never forward `--plan-id`/`--project-dir` for path resolution (the inherited main-checkout cwd binds them), and never embed a Worktree Header into subagent prompts (the header is a phase-5+ reminder and would be misleading before materialization).

### Materialization in Phase-5 Step 2.5

The transition from state 1 to state 3 is a single atomic step inside `phase-5-execute` (Step 2.5, after task planning is loaded but before the first task dispatch). The step:

1. Reads `metadata.use_worktree` from status and derives the feature branch `feature/{plan-id}` (phase-1-init persisted neither the branch nor a path).
2. Creates the worktree directory at `<project_root>/.plan/local/worktrees/{plan-id}/` and checks out the feature branch (creating it from the base ref if it does not already exist).
3. Persists `worktree_branch` and `worktree_path` into `references.json` AND `status.metadata` in a single write batch so that no reader can observe one populated and the other empty.
4. From this point forward, every Edit/Write/Read tool call and every Bucket B subprocess MUST resolve against `worktree_path` (the rules below take effect).

If Step 2.5 fails (e.g., branch already checked out elsewhere, base ref missing, worktree directory already occupied with conflicting content), the plan halts before any task dispatch and `worktree_path` remains unset — the plan is still pre-materialization and the operator must either resolve the materialization failure or downgrade the plan to `use_worktree: false`.

## Dispatch Protocol (cwd-Pinned Inheritance)

**Applies in state 3 (post-materialization) only.** During the pre-materialization phases there is no worktree on disk; the orchestrator's cwd is the main checkout and subagents inherit that cwd, so `.plan/` and project content resolve to main automatically via the uniform cwd walk-up. No header and no path forwarding are required pre-materialization.

Under the move-based, cwd-pinned model (ADR-002), the worktree binding is carried by the **pinned current working directory**, not by per-call parameter forwarding. At phase-5 materialization the orchestrator pins its cwd to the worktree root after `prepare_execute.py` moves the plan directory and the executor in; every subprocess it spawns — and every subagent it dispatches — inherits that cwd. Because `.plan/` resolution is cwd-relative (`file_ops.get_base_dir()` walks up from cwd to the nearest ancestor containing `.plan/local`), a dispatched subagent resolves the worktree-resident state without being told a path. See [`tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) for the single cwd-unchanged invariant — it is not restated here.

The consequence for dispatch: subagents do NOT forward `--plan-id` or `--project-dir` to working-tree-touching scripts for path resolution. The pinned cwd already binds them to the worktree. The only structured input a dispatched workflow takes is `plan_id` as the *plan-identifier* prompt-body field (selecting which plan's metadata to operate on — unrelated to cwd binding), per the workflow's own input contract (`execute-task`, the per-phase workflow doc loaded by `execution-context-{level}`).

A short header MAY be embedded as a reinforcement reminder so the never-edit-main-checkout invariant stays salient through free-form delegation:

```text
WORKTREE: cwd is pinned to this plan's worktree (ADR-002 cwd-pinned model).
Resolution is cwd-relative — do NOT forward a worktree path; do NOT pass --project-dir.
All Edit/Write/Read tool calls and raw git/mvn/npm commands operate against the pinned cwd.
NEVER edit the main checkout. See tools-script-executor/standards/cwd-policy.md.
```

The header is a reminder, not a path-routing mechanism — the binding holds whether or not the header is present, because cwd-pinning carries it. Child agents inherit the same pinned cwd and MUST NOT re-derive or forward a worktree path into any further dispatch.

`--project-dir <abs>` survives **only as the escape hatch** for callers invoked outside a pinned-cwd context — post-worktree-removal cleanup, fixture-driven test invocations, or ad-hoc invocations from outside any plan. It binds subprocesses verbatim to the supplied path. Inside a phase-5+ pinned-cwd dispatch it is never needed and MUST NOT be forwarded. `--plan-id` and `--project-dir` remain mutually exclusive at every call site; passing both is a hard error.

## The `git -C {path}` Rule (Worktree Application)

**Applies in state 3 (post-materialization) only.** Pre-materialization, `{worktree_path}` is unset and the universal rule already governs main-checkout invocations (`git -C {main_checkout} ...`); the worktree-specific application below activates the moment Step 2.5 materializes the worktree directory.

The universal "no `cd <path> && <tool>`" prohibition is established in [`persona-plan-marshall-agent/standards/tool-usage-patterns.md`](../../persona-plan-marshall-agent/standards/tool-usage-patterns.md) — that document defines the rule for every tool with a native cwd flag.

**Worktree-specific application**: when a plan runs in an isolated worktree, every git command that targets the plan's working tree MUST use the form:

```bash
git -C {worktree_path} <subcommand>
```

`{worktree_path}` is the value returned by `manage-status get-worktree-path --plan-id {plan_id}`. Never derive it from `pwd`, never substitute `cd {worktree_path} && git ...`, never rely on the agent's process cwd.

When a plan runs against the main checkout (no worktree allocated), substitute the main checkout absolute path for `{worktree_path}` — the structural rule is unchanged, only the target tree differs.

The same `<tool> -C / -f / --prefix / --directory / --rootdir` discipline applies to every tool that operates on a working tree (mvn, npm, uv, pytest, ruff). See the native-cwd-flag table in `tool-usage-patterns.md` for the complete mapping.

## Never-Edit-Main-Checkout Invariant

**Applies in state 3 (post-materialization) only.** Pre-materialization the plan legitimately operates against the main checkout (no worktree exists yet); the invariant takes effect at Step 2.5 materialization and remains in effect until the worktree is removed during cleanup.

While a plan is in flight in an isolated worktree, the agent MUST NOT:

- Edit any file under the main checkout via Edit/Write/Read tool calls.
- Run raw build, test, or lint commands against the main checkout.
- Stage or commit changes from the main checkout's working tree.

Every Edit/Write/Read tool call MUST resolve its target against `{worktree_path}`. Editing the main checkout while a plan runs in a worktree:

- Pollutes the main checkout's uncommitted state with content the plan never committed.
- Bypasses worktree isolation, defeating the whole point of running in a worktree.
- Lets tests silently load stale source via PYTHONPATH — the test runner sees the main checkout's PYTHONPATH entries and reports green while the worktree's edits go entirely unexercised.

This invariant is enforced at four layers:

- **Layer A — `manage-*` scripts** resolve `.plan/` via the uniform cwd walk-up (ADR-002): they find the nearest ancestor of cwd containing `.plan/local`. During phase-5+ the orchestrator's cwd is pinned to the worktree, so these scripts resolve the worktree-resident `.plan/` copy moved in at phase-5 start. They are path-stable for a given pinned cwd by construction.
- **Layer B — Bucket B `--plan-id` auto-routing** binds build / CI / Sonar wrappers to the worktree path internally; the main checkout is not reachable from those subprocess trees.
- **Layer C — Raw tool flags** (`git -C`, `mvn -f`, `pytest --rootdir`, etc.) target the worktree explicitly when the agent invokes external CLIs directly. This is the call-site rule documented in `persona-plan-marshall-agent/standards/tool-usage-patterns.md`.
- **Layer D — Phase-handshake strict-verify drift detection** catches free-form filesystem leaks that escape layers A/B/C. See the next section.

## Layer D: Phase-Handshake Drift Detection

Layers A/B/C cover structured tooling (manage-* scripts, build wrappers, raw tool flags), but they cannot constrain free-form filesystem operations: `Edit` / `Write` / `Read` against an absolute path, `Bash` invocations that ignore `git -C`, external CLIs that accept no cwd flag, or scripts that `chdir` mid-execution. Layer D closes that gap **structurally** by detecting filesystem-state drift at every phase boundary instead of relying on prompt discipline.

### Why Not a `PreToolUse` Hook

A `PreToolUse` hook approach for intercepting `Edit` / `Write` / `Read` tool calls and rejecting any call whose path resolves outside `{worktree_path}` is not viable for two structural reasons:

1. **Host-platform-specific.** Hooks live in `.claude/settings.json` and only fire under the Claude Code CLI host. The same plan running under OpenCode (or any future adapter target) silently loses the enforcement — the hook config is not portable across hosts. This violates the bundle's multi-host design contract.
2. **Brittle in practice.** Hook configurations require absolute-path matching, settings.json mutation by `marshall-steward` (with version drift between bundle releases), and case-by-case allow-list tuning for legitimate `.plan/` writes. Operators routinely disable misbehaving hooks, training muscle memory that masks legitimate violations later.

The chosen approach is host-agnostic and lives on the same code surface as the existing handshake invariants: at every phase boundary, the handshake captures the main checkout's dirty-file set; on the next boundary's `verify --strict`, a proper-superset comparison detects new dirty paths and refuses to advance.

### What Layer D Detects

The **`main_dirty_files`** invariant captures the set of paths reported by `git status --porcelain` against the main checkout, filtered to exclude `.plan/` artifacts (which legitimately live in the main checkout). The set is persisted on every phase boundary inside `handshakes.toon`.

The **`main_dirty_drift`** check (invoked at verify time, not via the registry) compares the live capture against the captured baseline using **proper-superset semantics**: drift fires when

1. The boundary phase is one of the on-main planning phases (`_PLANNING_PHASES_ON_MAIN` = `1-init` / `2-refine` / `3-outline` / `4-plan`) — gate, see the separation note below — AND
2. `metadata.use_worktree == true` (gate — main-checkout plans dirty freely without enforcement), AND
3. The live dirty-file set is a *proper superset* of the captured baseline (contains every baseline path AND at least one new path).

**Separation from the applicability predicate**: the planning-phase set that gates layer D (`_PLANNING_PHASES_ON_MAIN`, phases 1-4) is the **inverse** of the materialization-phase set that drives the `_worktree_materialized` applicability predicate (`5-execute` / `6-finalize`). They are two distinct phase partitions consulted for two unrelated purposes and MUST NOT be conflated: the applicability predicate answers "is the worktree in play, so do the `worktree_sha` / `worktree_dirty` invariants and the phase-entry assertion apply?", whereas the layer-D gate answers "could a free-form write still leak into the main checkout at this boundary?". Layer D fires only on the planning boundaries because after phase-5 materialization the move model structurally closes the leak-into-main surface — there is no main checkout to dirty once the plan's working state lives in the worktree.

On detection, `phase_handshake verify --phase {N} --strict` exits non-zero with the structured payload:

```text
status: error
error: main_checkout_dirtied_during_plan
plan_id: ...
phase: ...
baseline[]: [...]    # paths dirty at the previous boundary capture
observed[]: [...]    # paths dirty at the current verify
newly_dirty[]: [...] # the set difference — exactly the leaked paths
```

Because detection is **filesystem-state-based** at every phase boundary (not tool-call-based), layer D catches every leak channel uniformly:

- `Bash`-driven writes (`echo > /path/in/main`, `cat ... > path`, `sed -i`, etc.).
- External CLI writes (`prettier --write`, `gofmt -w`, IDE formatters, etc.).
- `Edit` / `Write` / `Read` against absolute paths in the main checkout.
- Subprocess invocations that `chdir` mid-execution.

It catches leaks regardless of which tool produced them — the only question layer D asks is "did the main checkout's dirty set grow between boundaries?".

### Granularity Trade-Off

Layer D operates at **per-phase-boundary** granularity rather than per-tool-call. A leak introduced mid-phase is not detected until the next boundary capture, so the agent may complete additional work on top of the polluted main checkout before the verify fires. This is an explicit trade-off:

- **Recovery is identical either way** — the operator must revert the leaked main-checkout changes (or move them into the worktree branch) before the boundary advances. Per-tool-call detection would surface the leak earlier but would not change the recovery steps.
- **Filesystem-based detection works across hosts**, while a tool-call hook would not. Granularity is the cost; portability is the benefit.

Plans that need finer-grained enforcement can run `phase_handshake capture` / `verify --strict` at intra-phase checkpoints (the `phase-6-finalize` orchestrator already does this for the `automated-review → branch-cleanup` and `sonar-roundtrip → next` boundaries), but the core contract remains per-phase.

### Recovery Loop

When `phase_handshake verify --phase {N} --strict` fails with `error: main_checkout_dirtied_during_plan`, the operator's recovery path is:

1. **Inspect `newly_dirty[]`.** The payload lists the exact paths that leaked into the main checkout between captures.
2. **Decide per-path: revert or relocate.**
   - *Revert* — when the change was unintended (typical case): `git -C {main_checkout} checkout -- {path}` to drop the dirty state. The plan's worktree edits remain unaffected.
   - *Relocate* — when the change is intentional but landed in the wrong tree: stage the file in the main checkout (`git -C {main_checkout} add {path}`), copy the staged blob into the worktree branch, and revert the main-checkout staging. The most reliable mechanical form is `git -C {main_checkout} stash push -- {path}` followed by `git -C {worktree_path} stash pop` from the corresponding stash entry.
3. **Re-run the boundary verify.** Once `git status --porcelain` against the main checkout is back to (or below) the baseline, `phase_handshake verify --phase {N} --strict` returns `status: ok` and the boundary advances.

The proper-superset rule means the operator does not need to *clean* pre-existing dirty paths — only the **newly-dirty** paths must be addressed before the boundary will advance. This keeps the recovery loop scoped to the actual leak rather than demanding a fully-clean main checkout that may carry unrelated dirty state from before the plan started.

### Filter Rule: `.plan/` Paths Are Excluded

The invariant filters paths beginning with `.plan/` out of both the capture and the comparison. The plan-marshall `.plan/` directory holds plan metadata, status files, lessons aggregate state, etc. During phases 1-4 these resolve to the main checkout's `.plan/local/` via the uniform cwd walk-up (cwd is main); the lessons corpus stays main-only throughout. Dirtying `.plan/` is part of normal phase-boundary bookkeeping.

A user-side hook (the original lesson's proposal) would need a complex allow-list of `.plan/`, `.plan/local/`, `.plan/temp/` etc. patterns to avoid false positives. The handshake-driven approach uses a single canonical filter applied identically at capture and verify time, eliminating the allow-list-drift class of bug entirely.

### Baseline-Equal Paths Are Not Drift

The proper-superset rule explicitly tolerates **baseline-equal main-dirty state**: a file that was dirty at boundary N and remains dirty (with the same path) at boundary N+1 is not a leak — it predates the current phase boundary and either pre-dated the plan or was already surfaced at a prior boundary. Only **newly-dirty** paths count.

This matches the operator's mental model ("only flag what changed") and keeps the failure payload focused on the paths that actually need attention.

## Cleanup Ordering: Worktree First, Then Branch

**Applies only when the plan reached state 3 (post-materialization).** A plan that aborts pre-materialization has no worktree to remove; cleanup degenerates to a branch deletion against the main checkout. The ordering below assumes the worktree directory exists on disk.

When a plan completes and the feature branch is ready for deletion, the operations MUST happen in this order:

1. **Remove the worktree.** `git worktree remove` refuses to operate on a worktree that is the cwd of any shell, and the local branch cannot be deleted while still checked out in a worktree. Any uncommitted state in the worktree at this point is a fail-loud condition — never pass `--force` to salvage; the user may still want to recover the work.
2. **Switch the main checkout to the base branch.** `git -C {main_checkout} checkout {base_branch}`.
3. **Pull the merge commit on the base branch.** `git -C {main_checkout} pull`.
4. **Delete the local feature branch.** `git -C {main_checkout} branch -d {head_branch}`.

After step 1, every git call MUST switch from `git -C {worktree_path}` to `git -C {main_checkout}` because `{worktree_path}` no longer exists on disk. Build / CI / Sonar invocations that previously took `--plan-id` MUST omit it after step 1 (the plan still has metadata, but no worktree to bind to).

On any plan abort or failure path, do NOT auto-remove the worktree — leave it in place so the user can inspect, salvage, or replay. Worktree removal happens only on successful cleanup.

## The `--plan-id` Three-State Contract

Build wrappers (`build-maven`, `build-pyproject`, `build-npm`, `build-gradle`), CI scripts (`tools-integration-ci`), the Sonar wrapper (`workflow-integration-sonar`), and any other Bucket B script that touches a working tree accept `--plan-id` as their working-tree binding flag, with `--project-dir` retained as an explicit override.

The contract has three states:

| Invocation | Resolution | Effective working tree |
|------------|-----------|------------------------|
| `--plan-id X` (preferred) | Script calls `manage-status get-worktree-path --plan-id X` internally, binds subprocesses to the resolved path. | The worktree at `<project_root>/.plan/local/worktrees/X/`. |
| `--project-dir <abs>` (override) | Script binds subprocesses verbatim to `<abs>`. Used when a caller already holds an absolute path — e.g., post-worktree-removal cleanup, fixture-driven test invocations. | The supplied absolute path. |
| Neither flag | Script binds subprocesses to the plan root resolved cwd-relatively (the nearest ancestor of cwd containing `.plan/local`; ADR-002). | The cwd-resolved tree — main in phases 1-4, the pinned worktree in phase-5+. |

`--plan-id` and `--project-dir` are **mutually exclusive at every call site**; passing both is a hard error.

When a script invoked with `--plan-id X` resolves an empty path (i.e., the plan exists but `metadata.use_worktree == false`), the script falls back to the cwd-relative plan root — the plan opted out of worktree mode at init time, and the caller's `--plan-id` becomes a no-op for path resolution.

Bucket A `manage-*` scripts MUST NOT accept `--plan-id` for cwd binding — they resolve `.plan/` via the uniform cwd walk-up regardless of how the script was invoked. (Many `manage-*` scripts already accept `--plan-id` as a *plan-identifier* argument that selects which plan's metadata to read or write — that usage is unrelated to the cwd contract here.) See [`tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) for the authoritative single uniform cwd-relative rule and the merge-lock exception.

## The Consolidated Branch-Cleanup Verbs

Three verbs — `force-push-with-lease`, `switch-and-pull`, and `prune-local-and-remote-ref` — wrap the branch-cleanup git calls that `branch-cleanup.md` sequences. They share a common resolution pattern and are documented here together because they cross the worktree/main-checkout boundary in a structured way.

### Resolution Pattern

All three verbs accept `--plan-id` as the primary resolution path and `--project-dir` as the escape hatch. They are mutually exclusive; passing both is a hard error.

**Primary path (`--plan-id`)**: The verb calls `manage-status get-worktree-path --plan-id {plan_id}` internally to resolve the working tree. For `force-push-with-lease`, the resolved path is the **worktree** (the branch lives there until `worktree-remove` runs). For `switch-and-pull` and `prune-local-and-remote-ref`, the verb derives the **main checkout** root via the uniform cwd-relative resolution (`file_ops.get_base_dir()` / `marketplace_paths._find_plan_root_from_cwd()`) because those operations run after worktree removal, when cwd is back on main.

**Escape hatch (`--project-dir [--branch|--head]`)**: Useful in post-worktree-removal cleanup, non-plan contexts, or fixture-driven test invocations where the caller already holds the path. All git calls use `git -C {project_dir}`.

### `force-push-with-lease`

Pushes the feature branch to `origin` with `--force-with-lease` — a lease violation indicates the remote moved since the last fetch and is surfaced as `status: rejected` / `error_type: push_rejected_non_fast_forward` rather than silently overwriting remote state.

Resolution: `--plan-id` → `worktree_path` and `worktree_branch` from `manage-status get-worktree-path`.

**Output** (success):
```toon
status: success
operation: force-push-with-lease
plan_id: PLAN_ID
branch: feature/PLAN_ID
remote: origin
remote_sha: {sha after push}
```

**Typed errors**: `plan_not_found`, `worktree_not_materialized`, `missing_required_arg`, `project_dir_not_a_git_repo`, `branch_not_found`, `push_rejected_non_fast_forward`, `lease_check_failed`, `push_failed`.

### `switch-and-pull`

Checks out `--base` on the main checkout and pulls from `origin` using `git pull origin {base_branch}` (the explicit form; never plain `git pull`). Captures `pre_sha` and `post_sha` and computes `commits_pulled` via `git rev-list --count`.

Resolution: `--plan-id` → main checkout root via the uniform cwd-relative resolution (`file_ops.get_base_dir()`).

**Output** (success):
```toon
status: success
operation: switch-and-pull
plan_id: PLAN_ID
base_branch: main
pre_sha: {sha before checkout}
post_sha: {sha after pull}
commits_pulled: N
```

**Typed errors**: `plan_not_found`, `missing_required_arg`, `project_dir_not_a_git_repo`, `branch_not_found`, `merge_conflict`, `pull_failed`.

### `prune-local-and-remote-ref`

Deletes the local feature branch (`git branch -D {head_branch}`) and, in `local_and_remote` mode, prunes the remote-tracking ref `refs/remotes/origin/{head_branch}` via `git update-ref -d`. An internal `show-ref` guard is issued before `update-ref -d` — if the ref is already absent, the verb returns `status: partial` with `remote_ref_deleted: false` and a `remote_ref_warning`, avoiding a non-zero exit for a ref that `git fetch --prune` (or the PR host) may have already cleaned up.

Safety invariants:
1. Never deletes the currently checked-out branch.
2. Uses force-delete (`git branch -D`) — post-merge squash merges make safe-delete (`-d`) refuse.
3. `show-ref` guard before `update-ref -d` — targeted ref deletion only; no `git fetch --prune`.
4. `local_only` mode skips all remote-tracking ref operations.

Resolution: `--plan-id` → `worktree_branch` from `manage-status get-worktree-path`, and main checkout root via the uniform cwd-relative resolution (`file_ops.get_base_dir()`).

**Output** (success — full deletion):
```toon
status: success
operation: prune-local-and-remote-ref
plan_id: PLAN_ID
head_branch: feature/PLAN_ID
mode: local_and_remote
local_deleted: true
remote_ref_deleted: true
```

**Output** (partial — remote-tracking ref already absent):
```toon
status: partial
operation: prune-local-and-remote-ref
plan_id: PLAN_ID
head_branch: feature/PLAN_ID
mode: local_and_remote
local_deleted: true
remote_ref_deleted: false
remote_ref_warning: "remote-tracking ref refs/remotes/origin/feature/PLAN_ID was already absent — no-op"
```

**Typed errors**: `plan_not_found`, `worktree_not_materialized`, `missing_required_arg`, `project_dir_not_a_git_repo`, `branch_delete_failed`, `unexpected_ref_error`.

### Sequencing with `worktree-remove`

The three consolidated verbs are designed to be invoked **after** `worktree-remove` because they target the main checkout; `worktree-remove` is `worktree-first` (it removes the worktree directory before deleting the branch ref). The sequence in `branch-cleanup.md` enforces:

1. `worktree-remove --plan-id {plan_id}` — removes the worktree directory and its local branch ref.
2. `switch-and-pull --plan-id {plan_id} --base {base_branch}` — checks out base and pulls on the main checkout.
3. `prune-local-and-remote-ref --plan-id {plan_id} [--mode ...]` — deletes the local branch (post-removal cleanup) and the remote-tracking ref.

`force-push-with-lease` runs **before** `worktree-remove` (the branch must still be checked out in the worktree when pushing). After `worktree-remove`, the worktree path is gone; callers that need to reference the branch path must switch to `--project-dir {main_checkout}` + `--branch {head_branch}` (the `--plan-id` path for `force-push-with-lease` resolves the worktree path — if the worktree no longer exists, the verb will fail with `project_dir_not_a_git_repo`).

See `phase-6-finalize/standards/branch-cleanup.md` for the canonical sequencing and the Conflict-Severity Classifier that gates interactive confirmation.

## The `worktree-rebase-to` Verb

`git_workflow worktree-rebase-to --plan-id X --base BRANCH` rebases the worktree's branch onto `--base` after detecting which of eight documented worktree states applies. The verb is intentionally narrow — it does not stash, force, or salvage; the caller is responsible for setting the worktree to a rebaseable state before invoking it.

### Resolution

`--plan-id X` resolves the worktree path via `manage-status get-worktree-path`. Every git invocation issued by the verb uses `git -C {worktree_path} <subcommand>` per the rule above; the main checkout is never modified.

### The 8-State Matrix

| State | Detection | Status | Action |
|-------|-----------|--------|--------|
| `clean` | branch and base point at same commit (ahead/behind both 0) | `success` | no-op, returns `action: noop` |
| `dirty` | `git status --porcelain` reports any modified, staged, or untracked entries | `error` | rejects with `dirty_worktree`; caller MUST stash, commit, or discard |
| `ahead` | branch has commits not on base; base has none branch lacks (or both diverge) | `success` | rebases commits onto base via `git rebase {base}`; returns `action: rebased` |
| `behind` | base has commits branch lacks; branch has none base lacks | `success` | rebases to incorporate base commits via `git rebase {base}`; returns `action: rebased` |
| `conflict` | rebase produces conflicts (`.git/rebase-merge` or `.git/rebase-apply` exists after non-zero exit) | `conflict` | leaves rebase in progress with conflict markers; caller resolves and runs `git rebase --continue` or `git rebase --abort` |
| `detached` | `git symbolic-ref --short HEAD` returns non-zero (no checked-out branch) | `error` | rejects with `detached_head`; caller MUST check out a branch first |
| `missing-base` | `git rev-parse --verify {base}^{commit}` returns non-zero | `error` | rejects with `missing_base`; caller MUST fetch or correct the base ref |
| `missing-target` | resolved worktree path is not a directory on disk | `error` | rejects with `missing_target`; caller MUST recreate the worktree (e.g., `worktree-create`) |

The first six states are detected by inspection before any rebase runs; `conflict` is determined by the rebase attempt itself. `clean` is a no-op; `ahead` and `behind` both attempt the rebase (the detected state is preserved in the response so callers can distinguish what was relocated).

### Output Contract

```text
status: success | error | conflict
plan_id: {echo}
worktree_path: {resolved}
base: {echo}
state: clean | dirty | ahead | behind | conflict | detached | missing-base | missing-target
head_branch: {when detected}
ahead: {commits ahead of base, when detected}
behind: {commits behind base, when detected}
action: noop | rebased   # success only
conflicts[N]: [paths]    # conflict only
error: {error_code}      # error or conflict only
message: {human-readable summary}
```

### Conflict Handling

The default behavior on conflict is **leave-in-place**: the rebase remains in progress and the working tree carries conflict markers. This lets the caller inspect the conflicts (the paths are enumerated in `conflicts[]` via `git diff --name-only --diff-filter=U`) and choose between manual resolution (`git rebase --continue`) and abandonment (`git rebase --abort`). The verb never auto-aborts because the caller — typically a higher-level workflow — owns the decision.

Per the never-edit-main-checkout invariant above, `worktree-rebase-to` operates exclusively against `{worktree_path}`; the main checkout's HEAD, index, and working tree are untouched even when the rebase fails.

## Related

- [`persona-plan-marshall-agent/standards/tool-usage-patterns.md`](../../persona-plan-marshall-agent/standards/tool-usage-patterns.md) — universal "no `cd && <tool>`" rule, native cwd flags for every tool.
- [`tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) — the single uniform cwd-relative resolution rule and the merge-lock exception for marketplace scripts.
- [`phase-5-execute/SKILL.md`](../../phase-5-execute/SKILL.md) — Dispatch Protocol section anchors the Worktree Header at the orchestration layer.
- [`execute-task/SKILL.md`](../../execute-task/SKILL.md) — execute-task input contract surfaces `plan_id` so the skill can resolve the worktree internally.
- [`tools-integration-ci/SKILL.md`](../../tools-integration-ci/SKILL.md) — CI leaf subcommands accept `--plan-id` for worktree-aware invocation.
- [`phase-6-finalize/standards/branch-cleanup.md`](../../phase-6-finalize/standards/branch-cleanup.md) — applies the cleanup ordering during finalize.
