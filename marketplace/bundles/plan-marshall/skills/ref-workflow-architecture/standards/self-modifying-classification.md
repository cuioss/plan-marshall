# Self-Modifying Classification

Defines when a deliverable touches the runtime infrastructure that the plan itself depends on for verification, and what the plan must do about it.

A plan is **self-modifying** when one or more of its deliverables edits the script/skill set that `phase-5-execute` and `execute-task` need to dispatch tasks, run verification gates, and resolve build commands. Without an explicit phasing strategy, self-modifying plans tend to ship "keep both surfaces alongside" outcomes that silently descope hard breaking-change requirements.

This standard is the single source of truth for the path heuristic, the classification rule, the phasing-rationale contract, and the split-vs-single-plan decision. Three callers reference it: `phase-3-outline` (outline-time deliverable classification), `phase-4-plan` (task-split enforcement), and the q-gate-validation workflow (q-gate validator §2.16, dispatched under `--phase phase-N` from each caller).

## Path Heuristic

A deliverable is **self-modifying** when its `Affected files` list contains any path matching the patterns below.

| Pattern | Rationale |
|---------|-----------|
| `marketplace/bundles/plan-marshall/skills/phase-[1-6]-*/` | Phase skills orchestrate the plan loop; mid-flight edits change dispatch behavior |
| `marketplace/bundles/plan-marshall/skills/execute-task/` | Per-task executor; mid-flight edits change verification flow |
| `marketplace/bundles/plan-marshall/skills/manage-status/` | Plan/phase state; mid-flight edits change transition behavior |
| `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_cli.py` | Build wrappers that dispatch every Bucket B verification |
| `marketplace/bundles/plan-marshall/skills/tools-script-executor/` | Notation-to-path resolver and executor entry point |
| `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` | CI/Git provider abstraction |
| `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` | Shared CI/Git base used by every PR/finalize action |
| `marketplace/targets/**` | Multi-target generator and adapter framework. The phase-6-finalize `deploy-target` step invokes the generator at run time; mid-flight edits change deployment behavior for the running plan and any downstream plans that share the cache. |
| `marketplace/bundles/plan-marshall/skills/sync-plugin-cache/**` | Plugin cache sync engine. The phase-6-finalize `sync-plugin-cache` step invokes this skill at run time; mid-flight edits change cache layout and consumption ordering for the running plan and every subsequent plan that loads from the cache. |

The list is intentionally narrow: only files that the running plan actually invokes during its own execution count. Edits to documentation, non-runtime skills, or test scaffolding under these directories do not by themselves trigger the classification — but if a deliverable mixes runtime and non-runtime files under one of the patterns above, the deliverable is self-modifying as a whole.

## Classification Rule

A deliverable is **self-modifying + breaking** when ALL three hold:

1. The deliverable matches the path heuristic above, AND
2. The plan declares `compatibility: breaking` (clean-slate, no transition window), AND
3. The deliverable narrative or its parent solution describes a deletion, rename, or hard-cutover (zero-hit grep gate, "remove flag entirely", "no escape hatch", etc.).

When ALL three hold, the plan MUST carry a documented **phasing rationale** OR be split into two plans (see Split-vs-Single-Plan below). A deliverable that hits (1) but not (2) and (3) is additive and does not require the phasing-rationale contract.

## Phasing-Rationale Contract

When a self-modifying + breaking plan is shipped as a single plan (no split), the deliverable narrative MUST contain a "Phasing Rationale" block that explicitly addresses all three points:

1. **Cache-sync ordering is safe.** The Claude plugin cache (`~/.claude/plugins/cache/plan-marshall/`) re-syncs at finalize. Worktree edits to runtime infrastructure are invisible to the running plan until that sync. Confirm that no in-flight task between the breaking edit and finalize depends on the new behavior.
2. **The verification gate runs against the worktree source post-final-edit.** The deliverable's verification command (e.g., a zero-hit grep) MUST execute against the worktree source AFTER the deletion edit lands, NOT against the cached state. Identify which task carries the gate and confirm it runs after every breaking edit in the plan.
3. **The central narrative carries no transition hedges.** Solution outline, decision log, and any standards prose authored by the plan must not contain phrases like "until X has fully landed", "callers may still see Y", or "legacy code paths may still reference" — these contradict the "no transition window" framing and signal that the plan secretly kept both surfaces.

A deliverable that fails any one of these three points has no valid phasing rationale and MUST be split (see below).

## Split-vs-Single-Plan

The recommended pattern for self-modifying + breaking changes is **two plans**:

```
PLAN A — additive: introduce the new surface (new flags, new helpers, new verbs, new
         standards). Old surface remains. Both work. No deletions. Lands on main; the
         plugin cache syncs at finalize so the new surface is now part of the running
         platform.

PLAN B — deletion: remove the old surface. Runs on clean post-merge infrastructure;
         no longer self-modifying because PLAN A has already landed and is what
         PLAN B's tasks invoke for verification.
```

The split is preferred because:

- It removes the chicken-and-egg coupling: PLAN B's verification gates run against PLAN A's already-landed surface, not against in-flight worktree edits.
- It makes the breaking-change moment explicit and reviewable in isolation.
- It eliminates the "keep both surfaces" failure mode by construction — there is no breaking-edit task in PLAN A to defer.

A **single-plan alternative** is permissible only when the Phasing-Rationale Contract above is fully satisfied AND documented inline in the deliverable. The single-plan path trades reviewability for shipping cadence; choose it only when the cache-sync timing has been verified to be safe and the implementor accepts the responsibility of keeping the central narrative free of transition hedges.

## Caller References

Three callers reference this standard. When the standard's path heuristic, classification rule, or phasing-rationale contract changes, all three callers should be reviewed for drift.

| Caller | Reference | Purpose |
|--------|-----------|---------|
| `plan-marshall:phase-3-outline` (Outline-Workflow Detail § Self-Modifying Classification) | Path heuristic + classification rule | Classify each deliverable at outline time; prompt the author for phasing strategy when the rule fires |
| `plan-marshall:phase-4-plan` (SKILL § Self-Modifying Phasing Enforcement) | Phasing-rationale contract + split rule | Refuse to create tasks for self-modifying + breaking deliverables that lack phasing rationale OR a peer plan |
| `plan-marshall:plan-marshall/workflow/q-gate-validation.md` § 2.16 (Self-Modifying Phased-Rollout Validator) | All three sections | Q-Gate validator that emits a finding when a deliverable matches the rule and has no phasing rationale |

## Related

- `plan-marshall:phase-4-plan/standards/breaking-refactor-task-split.md` — task-allocation pattern for breaking refactors that need a separate test-rewrite task; complementary to (not a replacement for) the split-into-two-plans pattern documented here.
- `plan-marshall:ref-workflow-architecture/standards/scope-deviation-escalation.md` — execute-time escalation rule for any decision that softens a request-level hard requirement; covers the procedural half of the failure mode that motivates this classification.
- Rationale: Self-modifying plans that lack an explicit phasing strategy have shipped with breaking-flag deletions silently descoped, leaving both the old and new surfaces active simultaneously — this classification makes the phasing contract explicit.
