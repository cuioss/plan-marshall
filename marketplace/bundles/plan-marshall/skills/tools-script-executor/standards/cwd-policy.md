# cwd Policy for the Script Executor

## Purpose

`.plan/execute-script.py` is a **pass-through proxy**: it forwards `argv` to the target script and never alters the caller's current working directory. All cwd control is therefore **explicit at the call site**. This document defines the single resolution rule every marketplace script obeys so that operations behave correctly whether they run from the main checkout (phases 1-4) or from a pinned worktree (phase-5+).

The underlying problem is well-known in agent tooling: LLM harnesses (aider, claude-code, SWE-agent, etc.) share a process-wide cwd, which changes silently between tool calls. A script that relies on implicit cwd will appear to work when run from the repo root and silently target the wrong tree when run from a worktree — corrupting state or testing stale code. The move-based, cwd-pinned model (ADR-002) eliminates that class of bug by making the working directory the single authoritative resolution anchor.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule.

## The Single Uniform cwd-Relative Rule (ADR-002)

Every script resolves `.plan/` and project content by **one rule, not a per-phase branch**:

```
set_base_dir() override  →  PLAN_BASE_DIR env override  →  walk up from cwd to the nearest ancestor containing .plan/local
```

There is no sideways resolution that maps every worktree back to the shared main checkout. Phases 1-4 resolve to the main checkout because cwd **is** the main checkout; phase-5+ resolve to the pinned worktree because the orchestrator pins cwd there after the move-in (`prepare_execute.py`). The plan directory and the executor MOVE into the worktree at phase-5 start, so a cwd walk-up from the pinned worktree finds the worktree-resident copy; at finalize the move-back (`integrate_into_main.py`) runs with cwd = main, so the same rule resolves to main.

**Mechanism**: `file_ops.get_base_dir()` in `plan-marshall:tools-file-ops` is the single canonical base resolver. Absent the `set_base_dir()` / `PLAN_BASE_DIR` overrides, it walks up from `Path.cwd()` to the nearest ancestor containing a `.plan/local` directory and anchors `.plan/local` there (`file_ops.get_plan_dir(plan_id)` derives a specific plan directory from that base). `marketplace_paths._find_plan_root_from_cwd()` implements the walk-up. New scripts inherit the behaviour by calling `get_base_dir()` rather than constructing paths from `__file__` or a sideways git resolver.

**Rule**: never construct `.plan/` paths from `__file__` or a sideways main-anchored resolver. Always derive from `get_base_dir()`, which walks up from cwd. The sole execution-time invariant is that the working directory is **never changed away from the pinned worktree** during phase-5+ — enforced as a caller-side guard the lifecycle scripts assert plus the phase-5/finalize wiring.

**The merge lock is the single, deliberate exception to cwd-relative resolution.** `merge_lock.py` (the cooperative advisory lock under the main checkout's `.plan/local/merge.lock`, acquired by `integrate_into_main.py` before move-back/regenerate/merge) always resolves to the MAIN checkout, because cross-session coordination is inherently main-scoped. It is the ONLY surviving main-anchored resolver; every other resolution is cwd-relative.

`PLAN_BASE_DIR` and `set_base_dir()` retain top precedence as the legitimate test-isolation hooks (not a hack): tests pin both `PLAN_BASE_DIR` and cwd to a fixture directory so they never contend for the real `.plan/` under `-n auto`.

## Which `.plan/` state moves into the worktree vs stays main-shared

The cwd-unchanged invariant only works because the plan's mutable state physically lives where the pinned cwd resolves. The split is:

- **Moves into the worktree (phase-5 start, via `prepare_execute.py`)**: the plan directory under `.plan/local/plans/{plan_id}/` (request, outline, tasks, references, status, work logs, findings) and the generated executor `.plan/execute-script.py`. These are the per-plan, single-authoritative-copy artifacts — a cwd walk-up from the pinned worktree finds the moved-in copy, and finalize (`integrate_into_main.py`, cwd = main) moves them back so the same rule resolves to main.
- **Stays main-shared (never moves)**: the cross-session merge lock at `.plan/local/merge.lock`. Serialising concurrent finalizes is inherently a main-checkout concern, so it always resolves to the main checkout regardless of any worktree's pinned cwd.

## Worktree-path passing is unnecessary under cwd-pinning

Because cwd IS the worktree in phase-5+, passing the worktree path so a command operates on the right tree is redundant: plain `git` and plain commands act on the worktree. The dispatch-header threading, `get-worktree-path` call-site forwarding, and routine `git -C {worktree_path}` rewriting that the old shared/worktree split required are not needed.

A small set of survivors is **explicitly justified and kept**:

- **`--project-dir` escape hatch** — build / CI / Sonar / analysis scripts retain `--project-dir` as the documented explicit override for callers invoked **outside** a pinned-cwd context (test fixtures, ad-hoc invocations from outside any plan). `script_shared/scripts/resolve_project_dir.py` (`resolve_project_dir`, `add_plan_id_arg`, `extract_plan_id`) implements the three-state contract: `--project-dir` only → use it verbatim; `--plan-id` only → resolve via `manage-status get-worktree-path`, falling back to the cwd-relative plan root when `use_worktree=false`; both → `mutually_exclusive_args` error; neither → cwd-relative plan root.
- **Main-session `get-worktree-path`** — retained only where a main-session caller legitimately needs the path: the orchestrator's initial pin (it reads the path `prepare_execute.py` returns, then pins its own cwd) and the merge-lock's main resolution.
- **Cross-tree `git -C {path}`** — retained for genuinely cross-tree or main-checkout-from-worktree contexts per the `dev-agent-behavior-rules` git rule. Inside a phase-5+ pinned-cwd context, prefer plain `git`.

## Rationale

- **Worktree isolation**: a plan running in a pinned worktree edits, builds, and tests against its own moved-in state without touching the main checkout or any sibling worktree — because every `.plan/` lookup resolves cwd-relatively to the worktree-resident copy.
- **Single authoritative copy**: the plan's non-git state is MOVED (not copied) into the worktree at phase-5 start, so there is exactly one authoritative copy during execution and no reconcile/merge problem.
- **Agent cwd is the anchor, made reliable by pinning**: the harness resets cwd between tool invocations, so the orchestrator pins cwd to the worktree after move-in and the lifecycle scripts assert their invocation cwd. Making cwd the single resolution anchor — and never changing it away from the worktree during phase-5+ — eliminates the silent-wrong-tree bug class.
- **Cross-session coordination is main-scoped**: the merge lock is the one deliberate exception; it always resolves to main because serialising concurrent finalizes is inherently a main-checkout concern.

## Assertion

`file_ops.get_base_dir()` MUST resolve via the single uniform cwd walk-up (`set_base_dir()` → `PLAN_BASE_DIR` → nearest ancestor containing `.plan/local`) and MUST NOT reintroduce a sideways main-anchored resolver. The merge lock is the only main-anchored resolver. Any change that regresses the uniform cwd rule or regrows a pervasive main-anchored resolver breaks the boundary invariant for every plan-scoped script and must be rejected in review.
