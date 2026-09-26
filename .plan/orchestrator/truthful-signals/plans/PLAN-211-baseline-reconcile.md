# PLAN-08: Localized-git parsing and drift routing

> ⛔ **NARROWED BY PM-MCP (2026-09-26, operator decision; row status `staged`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits. The operator kept this spec emittable **only for D1, D4, D6 and D7**,
> because that defect breaks current delivery (localized merge-tree prose parsed as conflict paths aborts phase-5). Every other deliverable below is superseded: do NOT implement it.
> The invariants of ALL deliverables, including the kept ones, were extracted to `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.

epic: truthful-signals
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-08-baseline-reconcile.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Parse git output by structure instead of prose: localized merge-tree lines never
filed as conflicts, drift recovery routed past uncleanable gates, lesson dedup on
canonical keys, and the YAML-frontmatter corpus split closed. G09 (8 lessons).

## Deliverables

1. Informational merge-tree lines excluded from conflict counts (2026-09-03-19-001).
2. Documented-set contract test for termination-cause block (2026-09-03-19-002).
3. YAML-frontmatter lessons normalized + write-path closed (2026-09-03-22-002).
4. Localized git prose never parsed as file paths (2026-09-04-17-011).
5. Orchestration context forwarded from source_id (2026-09-06-07-002).
6. Localized merge-tree conflict parser fix (2026-09-07-21-001).
7. Drift recovery clearing git-ancestry gates without refine re-dispatch (2026-09-08-01-001).
8. Dedup on canonical component spelling (2026-09-08-01-002).

## Claim Labels

- OBSERVED: baseline-reconcile reported 5 conflicts for a 1-file drift, filing German merge prose as paths — read at `lessons-archive/2026-09-03-19-001.md` § What happened.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_baseline_reconcile.py:411-414 treats every stdout line after the tree SHA as a path; no stop at the blank separator before the informational messages, no --no-messages; git_provider.run_git pins no locale.
- OBSERVED: 10–12 lessons YAML-frontmatter, listable but unaddressable by every id verb, population growing — read at `lessons-archive/2026-09-03-22-002.md` § What happened + Recurrence.
  - verdict: unverifiable | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: lessons-archive/2026-09-03-22-002.md not in the repo inventory; claim belongs to D3, superseded by the PM-MCP narrowing.
- HYPOTHESIS: locale-pinned parsing plus canonical dedup keys plus header normalization closes the class — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/` § baseline-reconcile (verify-at-outline).
  - verdict: unverifiable | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Fix hypothesis; caveat at _cmd_baseline_reconcile.py:411-414: locale pinning alone does not close D1/D4/D6 (English 'Auto-merging'/'CONFLICT' lines still parsed as paths); structural fix = stop at the section separator or --no-messages.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/` — baseline-reconcile parser.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/` — header parsing, dedup keys.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none.
- Adjacent to: WS-06/PLAN-12 consult path reads lesson headers without touching them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-211-baseline-reconcile.md"
```

## ⭐ FOLDED 2026-09-22 — D3's "population growing" claim gets fresh evidence; the specific mechanism a relayed lesson blamed is refuted at HEAD

Inbox lesson `2026-09-21-13-003` (relayed via `lessons-handling-26-09-22-01`) claimed `manage-lessons set-body`
destroys the metadata header `add` wrote. **Refuted at `7d82d5d90`**: `set_body` (`_lessons_crud.py:163–256`)
splits the file, rebuilds it as `frontmatter_block + h1_line + body`, and fails closed with
`error: malformed_lesson` when either is absent — it cannot destroy the header. The lesson's own PR#1560
diff-scoping check was correct but verified the wrong hypothesis (that diff never touched `cmd_set_body`).

**The subject is nevertheless live and this fold is real evidence for D3.** `_lessons_crud.py`'s module
docstring states the canonical path-allocate flow: `add` returns a fresh lesson stub's path, the caller
writes the body to a SEPARATE `work/lesson-body-{id}.md`, and only `set-body` (never a direct `Write` over
the path `add` returned) populates it. A caller that writes directly over that path destroys the header —
exactly the provenance the relayed lesson gives for four other 2026-09-21 lessons with unparseable metadata
headers ("they look hand-authored directly into files rather than filed via `manage-lessons add`"). Those
four are fresh, corroborated population for D3's `2026-09-21-13-003` claim: *"10–12 lessons YAML-frontmatter
… population growing"*. Expected Surface unchanged — `manage-lessons/` already declared.

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
