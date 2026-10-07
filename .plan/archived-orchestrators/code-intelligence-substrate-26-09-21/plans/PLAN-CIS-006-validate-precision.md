# PLAN-CIS-006: `validate` Reports 120 Broken References and Most Are Not Broken

epic: code-intelligence-substrate
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`resolve-dependencies validate` is the closest thing this repo has to a corpus-wide broken-reference
gate, and it cannot be used as one: it reports 120 unresolved references of 2467, and the visible
sample is dominated by false positives from three distinct detector confusions.

Make `validate` precise enough to gate on. This is the plan that converts a useful query tool into an
enforceable contract — and it is a hard prerequisite for the LSP, which would otherwise surface
false diagnostics directly into an editor.

## Deliverables

1. Stop counting literal documentation placeholders as references (the string `bundle:skill:script`
   appearing in prose that *documents* the notation).
2. Stop misreading `bundle:skill:subcommand` as `bundle:skill:script` — subcommands of a skill's
   entry script are not separate scripts.
3. Stop counting canonical command references (`default:verify:*`) as script notation.
4. Re-baseline the real unresolved set after 1-3 and report it; genuinely-broken references are then
   either fixed or filed.
5. A precision regression test: a corpus fixture containing one instance of each false-positive class
   plus one genuinely-broken reference, asserting exactly one finding.
6. **Documentation.** Update `tools-marketplace-inventory`'s SKILL.md `validate` contract — what it
   detects, what it deliberately does NOT treat as a reference (placeholders, subcommands, canonical
   commands), and whether its output is now gate-grade. `doc/developer/` — if `validate` becomes a
   gate, the page describing repository quality gates must say so. ⛔ Ship docs **in this plan**.

⚠ **At 6 deliverables this spec is AT the split guard.** Deliverables 1-3 (the three false-positive
classes) form one coherent unit and 4-5 (re-baseline + regression fixture) another. **Re-evaluate at
outline**; proceeding unsplit requires a recorded decision.

## Claim Labels

- **OBSERVED**: `resolve-dependencies validate --scope marketplace` returns
  `validation_result: failed`, `total_components: 294`, `total_dependencies: 2467`, `resolved: 2347`,
  `unresolved_count: 120`. Run live.
- **OBSERVED (false-positive class 1 — placeholders)**: `plan-marshall:tools-input-validation` and
  `plan-marshall:phase-6-finalize` report unresolved target **`bundle:skill:script`** — the literal
  placeholder string used when documenting the notation.
- **OBSERVED (false-positive class 2 — subcommands)**: unresolved targets include
  `plan-marshall:manage-execution-manifest:compose`, `plan-marshall:phase-6-finalize:qgate`,
  `plan-marshall:phase-6-finalize:lessons-capture`, `plan-marshall:phase-6-finalize:adr-propose`,
  `plan-marshall:phase-6-finalize:freshness-reconcile`,
  `plan-marshall:manage-execution-manifest:classify`. These are subcommands of their skill's entry
  script, not separate scripts.
- **OBSERVED (false-positive class 3 — canonical commands)**: unresolved targets include
  `default:verify:quality-gate`, `default:verify:module-tests`, `default:verify:coverage`,
  `default:verify:arch-gate`.
- **HYPOTHESIS (derived count)**: the majority of the 120 fall into these three classes, so 2347/2467
  (95.1%) is a **floor** on real health and 120 is an **overcount** of real breakage. ⚠ This
  orchestrator read only the first ~33 rows of the 120 — **this is a sample, not an enumeration**.
  Confirm/refute by classifying the FULL 120 before scoping (verify-at-outline).
  ⛔ **Do not carry the "majority" claim into the fix without enumerating all 120** — a reviewer's or
  orchestrator's list of instances is a sample, and this epic has already recorded that archetype.
- **HYPOTHESIS**: the three classes are separable in `_dep_detection.py`'s regex/AST layer without a
  redesign — confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py`
  § `ComponentId.from_notation` and the `SCRIPT_NOTATION` detector (verify-at-outline). ⚠
  `from_notation` treats ANY three-part notation whose middle segment is not `agents`/`commands` as a
  script — that single branch may be the whole of class 2.
- **Verify-first clause**: deliverable 4 assumes a genuinely-broken residue exists. If enumerating
  all 120 shows the residue is empty, the plan ships 1-3 plus 5 and reports zero real breakage —
  which is a *success*, not an under-delivery.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py` — `ComponentId.from_notation`, the five detectors
- **HYPOTHESIS**: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py` — resolution pass (verify-at-outline)
- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/SKILL.md` — the `validate` contract
- **OBSERVED**: `test/pm-plugin-development/` — precision fixture and tests

## Dependencies and Sequencing

- **Depends on**: PLAN-01 — the index is blind to 130 files including 33 `workflow/` docs, so
  re-baselining before that lands would produce a baseline that shifts underneath the fix.
- ⛔ **MUST land before PLAN-CIS-007.** An LSP over a ~50%-false-positive broken-reference set ships
  confident-wrong diagnostics into an editor — this epic's own archetype at its highest-visibility
  surface yet.
- **Overlaps with**: PLAN-01 and PLAN-CIS-003 on `tools-marketplace-inventory`. ⛔ Never pair those
  three.
- ✅ Disjoint from PLAN-CIS-001, PLAN-02, PLAN-CIS-004.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-006-validate-precision.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
