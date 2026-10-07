# PLAN-01: The Files Inventory Cannot See 130 Markdown Files, and Reports Success Over Them

epic: code-intelligence-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Two independent inventories in this repository — `manage-architecture`'s files inventory and
`tools-marketplace-inventory`'s dependency scan — are both blind to the same set of markdown files:
everything under `workflow/`, `references/`, and `examples/`. Worse than the omission is the
reporting: `architecture find` returns `status: success, count: 0` for a file that exists, which is a
confident false negative rather than a failure.

Make both inventories see the whole corpus, and make a zero-result answer distinguish *genuinely
absent* from *not indexed*. This plan is the epic's pinch point: everything built on either inventory
inherits this blind spot until it is fixed.

## Deliverables

1. Extend the `manage-architecture` files-inventory category set so `workflow/`, `references/`, and
   `examples/` markdown is inventoried and reachable via `find` / `files` / `which-module`.
2. Extend `tools-marketplace-inventory`'s dependency scan to read `workflow/` (and the other
   newly-inventoried doc directories) as edge sources, so references that exist only in verb docs are
   detected.
3. Make the zero-result answer honest for the inventory verbs: a caller MUST be able to distinguish
   "no such file" from "that category is not indexed". (The graph-family equivalent is PLAN-02's,
   not this plan's.)
4. Regression tests that are **population-derived**, not sample-based: assert the inventory covers
   every markdown file git tracks under `marketplace/bundles/`, so a future directory convention
   cannot silently reintroduce the blind spot.
5. **Documentation.** Update the `manage-architecture` SKILL.md contract for `find` / `files` (the
   category set and the honest zero-result), and the developer-facing page that describes which
   directories the inventory covers — candidate `doc/developer/repository-layout.adoc`
   (**HYPOTHESIS**: that this is the owning page; confirm at outline and correct the real owner if
   it is a different file). ⛔ Ship docs **in this plan** — doc-contract divergence is a recorded
   recurring defect here.

## Claim Labels

- **OBSERVED**: `architecture files --module plan-marshall` returns exactly eight categories —
  `agent 2, command 2, doc 1, script 269, skill 77, standard 197, template 13, test 679` — with no
  category for `workflow`, `references`, or `examples`. Read live from the verb's own output.
- **OBSERVED**: `architecture find --pattern "*workflow/analyze*"` returns `status: success,
  count: 0` while
  `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/analyze.md` exists
  (confirmed via `git ls-files`). Reproduced a second time with
  `--pattern "*architecture-setup*"` against
  `marketplace/bundles/pm-plugin-development/.../marshall-steward/references/architecture-setup.md`.
- **OBSERVED (derived count)**: **130 markdown files** are absent — **33** under
  `*/skills/*/workflow/*.md` and **97** under `*/skills/*/references/*.md` plus
  `*/skills/*/examples/*.md`, both measured by `git ls-files` across all bundles. The two figures are
  counts this orchestrator derived, not figures read from any tool's own report.
- **OBSERVED**: the SAME blind spot exists in `tools-marketplace-inventory` via an independent code
  path — `resolve-dependencies rdeps --component plan-marshall:platform-runtime:platform_runtime`
  returns 11 dependents and `plan-marshall:marshall-orchestrator` is NOT among them, although all
  nine of its verb docs invoke `platform_runtime session push-title-token` and that reference exists
  ONLY in `workflow/*.md`, never in its `SKILL.md`.
- **HYPOTHESIS**: the category set is produced by the `marshall-plugin` build-system extension's
  discovery rather than by `manage-architecture` itself — confirm/refute at
  `marketplace/bundles/*/skills/plan-marshall-plugin/extension.py` § the file-categorisation function,
  and at `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py`
  § the files-inventory reader (verify-at-outline). **The fix location depends on this** — do not
  scope until it is settled.
- **HYPOTHESIS**: `tools-marketplace-inventory`'s scan-set is defined by an explicit directory or
  glob list — confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py`
  § the component-enumeration function (verify-at-outline).
- **Verify-first clause**: both HYPOTHESIS entries name a *fix location*, and the two inventories may
  turn out to share or not share a single enumeration seam. Settle both against the implementing
  source before scoping. If they DO share a seam, deliverables 1 and 2 collapse into one and the
  plan should be re-scoped smaller rather than executed as written.

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — files-inventory reader and `find` (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/*/skills/plan-marshall-plugin/extension.py` — file categorisation during discovery (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py` — component enumeration (verify-at-outline)
- **OBSERVED**: `test/plan-marshall/` and `test/pm-plugin-development/` — regression tests
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md` — the `find` verb's documented contract, which currently describes a glob search only

## Dependencies and Sequencing

- **Depends on**: none. This is the epic's first plan.
- **Overlaps with**: PLAN-CIS-001 and PLAN-02 on `manage-architecture`; PLAN-CIS-003 and PLAN-CIS-006 on
  `tools-marketplace-inventory`. ⛔ **This plan collides with more of the epic than any other — run
  it ALONE and FIRST, before any parallel wave opens.**
- **Adjacent to**: the dependency-edge derivation in `_cmd_client_query.py` (PLAN-02's surface) sits
  in the same file as the files-inventory reader but is a different concern — do NOT fix edge
  derivation here, even though the file is open.
- **Prerequisite for**: PLAN-CIS-006 and PLAN-CIS-007 (WS-03) — an index blind to 33 `workflow/` docs
  produces false "no references" answers in an editor.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-01-inventory-blind-spot.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
