---
lane:
  class: core
  cost_size: S
implements: plan-marshall:extension-api/standards/ext-point-build-verify-step
name: default:verify
description: Parameterized canonical-verify step — resolves a canonical command and runs it
order: 10
canonicals:
  - quality-gate
  - module-tests
  - coverage
---

# Canonical Verify

Single **parameterized** built-in verification step that backs every canonical command. The step ID encodes the canonical as its trailing segment — `default:verify:{canonical}` — e.g. `default:verify:quality-gate`, `default:verify:module-tests`, `default:verify:coverage`. The step reads the canonical from the ID, resolves it via `architecture resolve --command {canonical}`, honours the returned `execution_tier` / `bash_timeout_seconds`, runs the resolved executable, and reports pass/fail.

The `canonicals:` frontmatter (`quality-gate`, `module-tests`, `coverage`) is the machine-readable source for discovery-backed seeding — `find_implementors()` expands this list into the built-in `default:verify:{canonical}` step IDs that `verification_steps` seeds. The canonical is a **parameter**, never a hardcoded branch — there is no per-canonical doc and no per-canonical `role:` frontmatter file. The step has **no `role:` frontmatter line**: the matrix role is derived from the trailing canonical segment by the composer (`manage-execution-manifest._role_of` — see [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md)), keyed on this table:

| canonical segment | derived `role:` |
|-------------------|-----------------|
| `quality-gate` | `quality-gate` |
| `verify` / `module-tests` | `module-tests` |
| `coverage` | `coverage` |
| `integration-tests` | `integration` |
| `e2e` | `e2e` |

Ordering among canonical-verify entries comes from the persisted list order (the `verification_steps` / `per_deliverable_build` list as written by `manage-config`); this doc's `order` field positions the parameterized step within the built-in dispatch table, not the canonicals relative to one another.

## Dispatch

Resolved from the `default:verify:` prefix by `phase-5-execute` via the Built-in Step Dispatch Table. Execution is inlined — no external skill is loaded. The SKILL's existing `default:`-prefix detection plus dispatch-table lookup is reused, keyed on the generic `default:verify:` prefix; the trailing `{canonical}` segment is the parameter the step body feeds to `architecture resolve`.

**Whether this step fires is decided exclusively by the per-plan execution manifest** (`manage-execution-manifest read`). This document carries **no embedded skip logic** — a given `default:verify:{canonical}` step runs iff `manage-execution-manifest`'s decision matrix included it in the composed list. Any skip rule (docs-only plans, recipe paths, early-terminate analysis, unresolved-canonical footprint-gating) is encoded in the matrix and the `_apply_canonical_verify_inactive` pre-filter, not here.

## Module-scoped vs whole-tree invocation

The same step body serves **both** consuming contexts; the only difference is an explicit **scope** input.

| Scope | Supplied by | Resolution | Runs over |
|-------|-------------|------------|-----------|
| `module` | Per-deliverable chain-tail (phase-5-execute Step 10b), one entry per `per_deliverable_build` step ID | `architecture resolve --command {canonical} --module {changed_module}` | The changed module(s) only |
| `whole-tree` | End-of-phase-5 sweep (phase-5-execute Step 11b/11c), one entry per `verification_steps` step ID | `architecture resolve --command {canonical}` (no `--module`) | The complete tree |

Scope is the ONLY difference between the two consuming lists — the resolution + execution-tier + report logic is identical. The `per_deliverable_build` list feeds the changed module; the `verification_steps` list feeds whole-tree. Whole-tree gates (e.g. `integration-tests`, `e2e`) live only in `verification_steps`, never in `per_deliverable_build`.

**Division of verification labor (per-task vs per-deliverable).** The module-scoped per-deliverable build is the layer that catches cross-module and sibling regressions — the per-task `execute-task` gate stays deliberately lean (`quality-gate`: mypy + ruff on the touched production sources only; see [`../../execute-task/SKILL.md`](../../execute-task/SKILL.md) implementation-profile Step 5). Because that catch is delegated to this chain-tail build, correct `changed_module` resolution is load-bearing: the module-scoped resolution depends on `architecture which-module --path {changed_path}` returning the owning module for every changed path — including `paths.tests` and project-local `.claude/skills/**` paths. When `which-module` mis-resolves (returns the wrong module or `null`), this build targets the wrong module or none, and the sibling regression it was meant to catch is missed. See [`../../manage-architecture/SKILL.md`](../../manage-architecture/SKILL.md) `which-module` for the containment-resolution contract this build relies on.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Footprint gate (whole-tree scope only)

For a **whole-tree** end-of-phase-5 run (Step 11b / the `verification_steps` `default:verify:{canonical}` loop), the build is gated on the live footprint BEFORE resolution. Consult the **existing** `manage-config build-decision` verb — a thin wrapper over `extension_base.should_execute_build`, the same `build.map ∩ live-footprint` authority phase-6 uses (NOT a new verb, NOT a parallel when-to-build mechanism):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-decision \
  --command {canonical} --plan-id {plan_id}
```

Parse `decision` and `reason`. When `decision == not_necessary` (the live footprint is empty or intersects no registered `build.map` glob — a docs-only change), SKIP the canonical: do NOT resolve, do NOT run. Emit a decision-log line naming the footprint `reason` and record the step `skipped` via `manage-execution-manifest record-step --outcome skipped` (phase-5-execute Step 8c), then continue to the next canonical. When `decision != not_necessary`, proceed to the Workflow below.

**Module-scoped** per-deliverable invocations (Step 10b) are **NOT** subject to this whole-tree footprint gate — they already carry the documentation-only short-circuit (a changed-path set with no buildable module yields no module-scoped run) and are unchanged. Step 11c (Execute-Exit Verify Gate) is likewise already footprint-aware (it derives the affected-bundle set from the live footprint) and is unchanged.

## Workflow

1. **Resolve the canonical.** Read the canonical from the trailing segment of the step ID, then resolve it:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
     resolve --command {canonical} --module {module} --audit-plan-id {plan_id}
   ```

   Add `--module {module}` only when invoked **module-scoped** (per-deliverable); omit it for the **whole-tree** end-of-phase-5 sweep. Pass `--audit-plan-id {plan_id}` so the resolved build's execution-log entries stay **plan-scoped regardless of which tier ultimately runs the build**. For a whole-tree run, the **Footprint gate** above has already returned `decision != not_necessary` — a `not_necessary` verdict skips before this resolution.

   **Unresolved-canonical skip:** when the canonical does not resolve for the project (no matching Maven profile / no command for the build system), record the step `skipped` and continue — this is **not** a failure. integration-tests / e2e legitimately do not resolve on a project that lacks the profile.

2. **Honour `execution_tier`.** The resolved envelope carries an `execution_tier` field that decides **who runs the build**, not just how long it may take:

   - **`execution_tier=per_task`** — the resolved `executable` runs **inline** in the step body. Pass `timeout: bash_timeout_seconds * 1000` on the Bash call so the synchronous build is not silently moved to the background.
   - **`execution_tier=orchestrator`** — the build is **handed off to the orchestrator** and is **NOT run inline** by this step. Long-running canonicals (full test suites, Docker cold-start integration-tests) are the prime candidates for this tier; the step body returns control to the orchestrator, which runs the build through the [`await-long-running`](../../plan-marshall/workflow/await-long-running.md) detach-and-notify seam — the canonical orchestrator-tier consumer that backgrounds the resolved wrapper (`run_in_background: true`) and wakes on the completion notification to read the compact TOON, with today's synchronous blocking call at `bash_timeout_seconds` as its documented fallback. The **not-run-inline-by-the-step-body invariant holds**: the step body neither backgrounds the command nor polls for its completion — it only hands off; the seam owns the background-and-notify flow in the orchestrator's own envelope.

3. **Run and report.** Run the resolved `executable` (inline at `bash_timeout_seconds`, or via orchestrator hand-off per tier). On failure, surface via the phase-5-execute Step 10/11 triage loop (fix-task creation, suppress, or accept) with `max_iterations` from config. Report pass/fail.

## Return Contract

Follows the standard phase-5-execute verification result shape: a non-zero exit code or findings in the build log surface as failures and are routed through the Step 11/11b triage loop. An unresolved canonical reports `skipped`, not a failure.

## Related Steps

See the phase-5-execute SKILL.md **Built-in Step Dispatch Table** for the single parameterized `default:verify:{canonical}` built-in step — do not inline-copy the step dispatch table in any consumer; xref this doc instead.
