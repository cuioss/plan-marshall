# Plan — finalize-step-integrity

**GROUP: FINALIZE** (surface: phase-6-finalize step scripts + their SKILL bodies) — shares the phase-6 surface with `docs-contract-consistency` (P7), which is doc-prose-only; the two are the same GROUP, so run them serially OR accept one rebase (second finisher re-validates). Disjoint from MANIFEST and EXEC-CONTEXT surfaces.

**Error class:** finalize-step correctness — a finalize step reports green (or mis-scopes its scan, or mis-guards re-entry) in a way that diverges from what CI / a fresh worktree actually sees.

> **Frozen-source caveat:** re-ground every file:line below against current source at outline. These
> are 2026-07-17 citations and will have drifted.

## Deliverables

### D1 — finalize `plugin-doctor` / `pre-push-quality-gate` runs SCOPED, CI runs it WHOLE-TREE ⇒ false-green in finalize

**Evidence (orchestrator #915, 2026-07-17):** a lint rule passed the finalize `plugin-doctor` (scoped to touched skills) then went CI-RED because CI runs it whole-tree. Same "finalize acts as if it shipped, CI disagrees" class as the P1 commit-integrity family — a tool-layer gap, not a manual-reminder lesson (`2026-07-17-09-002` currently just says "run whole-tree `quality-gate` with no module arg locally").

**Fix (fix-at-tool-layer):** make the finalize `plugin-doctor`/`pre-push-quality-gate` step run whole-tree to match CI, OR warn loudly when the scoped result could diverge from a whole-tree run. **Acceptance:** a change that is scoped-green but whole-tree-red is caught (or explicitly warned) at finalize, not first at CI.

### D2 — pre-submission self-review surfacer scans the WHOLE worktree, not the diff

**Evidence (API-Sheriff #426/#455, 2026-07-17):** the surfacer walked 77 unrelated `node_modules` schema files instead of the changed set (harmless there, but wasted scan + false-scope; in a big vendored tree it is noise + cost).

**Fix (fix-at-tool-layer):** scope the self-review surfacer's file set to the diff/changed-paths, or exclude `node_modules`/vendored trees. **Acceptance:** the surfacer's file set equals the plan's changed paths (or the changed paths minus vendored trees), verified on a fixture with a vendored subtree.

> **⚠ Direction trap — D1 and D2 pull OPPOSITE ways.** D1 wants a finalize step to run WHOLE-TREE
> (to match CI); D2 wants a finalize step to run DIFF-SCOPED (to match the change). They are different
> steps with different correct scopes. Do NOT unify them into a single "always scoped" or "always
> whole-tree" rule. The invariant is "match the authority": `plugin-doctor` matches CI (whole-tree);
> the self-review surfacer matches the change (diff).

### D3 — freshness-gate behavior-transparent reconciliation (P1 arm-6 split-out)

Deliberately carved out of P1 #914 rather than rushed in. The freshness gate should reconcile in a behavior-transparent way (surface WHY it re-stales / what it re-stamped), not silently. **Re-ground against P1's shipped freshness-gate code** (`branch-sync-state` / the `worktree_dirty_at_boundary` post-condition landed in #914) and the recurring "freshness-gate re-stale after a finalize-internal commit" family (push `--force` override observed on TokenSheriff #565 and others). **Acceptance:** a finalize-internal commit (e.g. simplify/lessons-capture) that re-stales the gate produces a legible reconciliation record instead of a silent `--force`.

### D4 — `prepare_execute` re-entry-guard idempotency bug (false negative)

**Evidence (nifi-extensions, 2026-07-16):** surfaced during a `code-review-followup` loop-back re-entry; worktree state was healthy and non-blocking, so the operator continued (re-homed lesson `2026-07-16-16-002`). The re-entry guard returns a false negative on a healthy re-entry. **Fix:** correct the idempotency check so a healthy re-entry is recognized as such. **Acceptance:** a loop-back re-entry with a healthy worktree passes the guard without a false-negative block; a genuinely dirty/blocking re-entry still blocks.

## Out of scope / do NOT expand
- P7's doc-contract items (`*_without_asking` family, `auto_merge_after_ci` docs) — that is the sibling `docs-contract-consistency` plan.
- Any change to the harness-kill / build-server surface (plan-server epic).

## Absorbs
- HANDOVER §5 plugin-doctor scoped-vs-whole-tree datapoint (lesson `2026-07-17-09-002`).
- HANDOVER §5 self-review surfacer whole-tree-scan bug (API-Sheriff).
- HANDOVER §4 P1-arm6 freshness-gate split-out.
- HANDOVER §5 `prepare_execute` re-entry idempotency (lesson `2026-07-16-16-002`).

## Size
4 deliverables, all phase-6 finalize-step correctness. At the scope-bloat guard's edge — if the outline finds D3 (freshness) materially larger than the other three, split it back out as its own micro-plan.
