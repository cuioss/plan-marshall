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

There is no sideways resolution that maps every worktree back to the shared main checkout. Phases 1-4 resolve to the main checkout because cwd **is** the main checkout; phase-5+ resolve to the pinned worktree because the orchestrator pins cwd there after the move-in (`prepare_execute.py`). The plan directory MOVES into the worktree at phase-5 start, so a cwd walk-up from the pinned worktree finds the worktree-resident copy; at finalize the move-back (`integrate_into_main.py`) runs with cwd = main, so the same rule resolves to main. The executor is NOT moved — it is per-tree derived state, generated into the worktree at move-in (see _Which `.plan/` state moves_ below) while main keeps its own copy present throughout.

**Mechanism**: `file_ops.get_base_dir()` in `plan-marshall:tools-file-ops` is the single canonical base resolver. Absent the `set_base_dir()` / `PLAN_BASE_DIR` overrides, it walks up from `Path.cwd()` to the nearest ancestor containing a `.plan/local` directory and anchors `.plan/local` there (`file_ops.get_plan_dir(plan_id)` derives a specific plan directory from that base). `marketplace_paths._find_plan_root_from_cwd()` implements the walk-up. New scripts inherit the behaviour by calling `get_base_dir()` rather than constructing paths from `__file__` or a sideways git resolver.

**Rule**: never construct `.plan/` paths from `__file__` or a sideways main-anchored resolver. Always derive from `get_base_dir()`, which walks up from cwd. The sole execution-time invariant is that the working directory is **never changed away from the pinned worktree** during phase-5+ — enforced as a caller-side guard the lifecycle scripts assert plus the phase-5/finalize wiring.

**There is ONE sanctioned main-anchored resolver utility, used by exactly three cross-session consumers.** `resolve_main_anchored_path` in `script-shared/marketplace_paths.py` is the single deliberate exception to cwd-relative resolution: it resolves a subpath under the MAIN checkout's `.plan/local` regardless of caller cwd (test override first, then `git rev-parse --git-common-dir`). It is consumed by exactly three genuinely-shared cross-session corpora, each reached through that one utility:

- `merge.lock` — the cooperative advisory lock acquired by `integrate_into_main.py` before move-back/merge (`merge_lock.py`);
- `run-configuration.json` — the adaptive-timeout corpus (`manage-run-config/run_config.py`);
- `lessons-learned` — the global lessons corpus, including the id-allocation `plans` scan (`manage-lessons/manage-lessons.py`).

The utility is the ONE mechanism; the three scripts CALL it rather than each carrying its own git-common-dir copy. Every other resolution is cwd-relative. New cross-session shared state MUST route through this utility, not re-implement git-common-dir resolution. The worktree's `.plan/local` is a fully REAL directory with NO symlinks — cross-session visibility comes from the utility, not from a filesystem symlink.

`PLAN_BASE_DIR` and `set_base_dir()` retain top precedence as the legitimate test-isolation hooks (not a hack): tests pin both `PLAN_BASE_DIR` and cwd to a fixture directory so they never contend for the real `.plan/` under `-n auto`.

## Which `.plan/` state moves into the worktree vs stays main-shared

The cwd-unchanged invariant only works because the plan's mutable state physically lives where the pinned cwd resolves. The split is:

- **Moves into the worktree (phase-5 start, via `prepare_execute.py`)**: the plan directory under `.plan/local/plans/{plan_id}/` (request, outline, tasks, references, status, work logs, findings). This is the per-plan, single-authoritative-copy artifact — a cwd walk-up from the pinned worktree finds the moved-in copy, and finalize (`integrate_into_main.py`, cwd = main) moves it back so the same rule resolves to main.
- **Per-tree DERIVED state (generated, not moved)**: the executor `.plan/execute-script.py`. Main keeps its copy present and untouched throughout phase-5+ (so main-anchored hooks that shell out to it never find it missing mid-phase-5), and the worktree generates its OWN at move-in — `prepare_execute.py` invokes `generate_executor generate --marketplace-root {worktree}` with the subprocess cwd pinned to the worktree so the output lands inside the worktree. The on-main copy is regenerated only when a plan changes the marketplace script SET, by the project-level meta-project-only `finalize-step-sync-plugin-cache` step after the cache sync — NOT by `integrate_into_main.py`. The executor is neither a moved slot nor a main-anchored shared resource.
- **Stays main-shared (never moves)**: the three genuinely-shared cross-session corpora — `.plan/local/merge.lock`, `.plan/local/run-configuration.json`, and `.plan/local/lessons-learned` — each resolved to the main checkout via the single `resolve_main_anchored_path` utility regardless of any worktree's pinned cwd. Serialising concurrent finalizes, accumulating adaptive timeouts, and recording lessons are all inherently cross-session concerns. `archived-plans/` is also main-resident but is touched only at finalize after cwd returns to main, so the uniform cwd rule suffices — it needs no resolver.

## Worktree-path passing is unnecessary under cwd-pinning

Because cwd IS the worktree in phase-5+, passing the worktree path so a command operates on the right tree is redundant: plain `git` and plain commands act on the worktree. The dispatch-header threading, `get-worktree-path` call-site forwarding, and routine `git -C {worktree_path}` rewriting that the old shared/worktree split required are not needed.

A small set of survivors is **explicitly justified and kept**:

- **`--project-dir` escape hatch** — build / CI / Sonar / analysis scripts retain `--project-dir` as the documented explicit override for callers invoked **outside** a pinned-cwd context (test fixtures, ad-hoc invocations from outside any plan). `script_shared/scripts/resolve_project_dir.py` (`resolve_project_dir`, `add_plan_id_arg`, `extract_plan_id`) implements the three-state contract: `--project-dir` only → use it verbatim; `--plan-id` only → resolve via `manage-status get-worktree-path`, falling back to the cwd-relative plan root when `use_worktree=false`; both → `mutually_exclusive_args` error; neither → cwd-relative plan root.
- **Main-session `get-worktree-path`** — retained only where a main-session caller legitimately needs the path: the orchestrator's initial pin (it reads the path `prepare_execute.py` returns, then pins its own cwd) and the shared utility's main resolution.
- **Cross-tree `git -C {path}`** — retained for genuinely cross-tree or main-checkout-from-worktree contexts per the `dev-agent-behavior-rules` git rule. Inside a phase-5+ pinned-cwd context, prefer plain `git`.

## Cross-session re-entry re-anchors cwd to the worktree

The cwd-as-anchor policy covers fresh sessions, not only the session that performed the move-in. A new shell entering `/plan-marshall action=execute|finalize plan={plan_id}` against a phase-5+ plan starts on the main checkout, where the plan directory no longer lives (it was moved into the worktree at move-in). Such a session re-anchors cwd to the worktree before any phase-5/6 work, which is consistent with — not an exception to — the single uniform cwd-relative rule: once cwd is pinned to the worktree, every `.plan/` lookup resolves to the worktree-resident copy exactly as it does for the move-in session.

The re-entry preflight resolves the plan's checkout location via the read-only `locate-plan-checkout` verb (`plan-marshall:workflow-integration-git:git-workflow locate-plan-checkout --plan-id {plan_id}`), then `cd`s into the reported `worktree_path` on the `worktree` result. The verb reuses the same shared resolution channel (`_resolve_worktree_path_for_plan` over `manage-status get-worktree-path`) as the other worktree verbs — it does NOT raw-parse `git worktree list --porcelain`, so it adds no new sideways resolver. The preflight is idempotent: a session already cwd-pinned inside the worktree resolves `current`, so there is no double-`cd`. It runs from main using main's present executor, which stays present and untouched throughout phase-5+ (the executor is per-tree derived state — see ADR-002 § "The executor is per-tree derived state").

## Rationale

- **Worktree isolation**: a plan running in a pinned worktree edits, builds, and tests against its own moved-in state without touching the main checkout or any sibling worktree — because every `.plan/` lookup resolves cwd-relatively to the worktree-resident copy.
- **Single authoritative copy**: the plan directory is MOVED (not copied) into the worktree at phase-5 start, so there is exactly one authoritative copy during execution and no reconcile/merge problem. (The executor is per-tree derived state — generated, not moved — so it has no single-copy constraint.)
- **Agent cwd is the anchor, made reliable by pinning**: the harness resets cwd between tool invocations, so the orchestrator pins cwd to the worktree after move-in and the lifecycle scripts assert their invocation cwd. Making cwd the single resolution anchor — and never changing it away from the worktree during phase-5+ — eliminates the silent-wrong-tree bug class.
- **Cross-session coordination is main-scoped**: the three shared corpora (merge lock, run-config, lessons) are the deliberate exception, reached through the ONE `resolve_main_anchored_path` utility; they always resolve to main because cross-session coordination is inherently a main-checkout concern. Keeping it to one small, explicitly-enumerated utility prevents the codebase from regrowing pervasive ad-hoc git-common-dir resolution.

## Assertion

`file_ops.get_base_dir()` MUST resolve via the single uniform cwd walk-up (`set_base_dir()` → `PLAN_BASE_DIR` → nearest ancestor containing `.plan/local`) and MUST NOT reintroduce a sideways main-anchored resolver for PLAN-SCOPED state. The ONE sanctioned main-anchored resolver is `resolve_main_anchored_path`, used by exactly three cross-session consumers (`merge.lock`, `run-configuration.json`, `lessons-learned`); it is the explicitly-enumerated exception, not a general escape hatch. New cross-session shared state MUST route through that utility rather than copying git-common-dir resolution. Any change that regresses the uniform cwd rule for plan-scoped state, or regrows a pervasive main-anchored resolver outside the one utility, breaks the boundary invariant for every plan-scoped script and must be rejected in review.
