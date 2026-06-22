# Coverage Contract: Scope × Thoroughness

Coverage is a two-dial contract — **scope** (where the boundary is drawn) and **thoroughness** (how completely in-radius items are covered and how deeply their relationships are traced). This standard defines both ladders, the rule for grading a unit's thoroughness, the load-bearing coupling constraint that binds the two dials, and the self-report every coverage-class task owes.

## Effort vs Thoroughness

**Effort** and **thoroughness** are orthogonal dials. Conflating them is the failure this standard exists to prevent.

- **Effort** is *compute-per-item*: the model tier the harness selects for a dispatch (`level-1` … `level-7`). It is deterministic and harness-selected — the agent does not choose it. A higher effort tier reasons harder about each item it looks at.
- **Thoroughness** is *coverage breadth + relationship-tracing depth*: how many in-scope items are actually examined, and how far the relationships radiating from each change are traced. It is behavioral and agent-self-policed — the agent decides, on each item, whether to read it in full, sample it, or skip it, and whether to trace its neighbors.

Raising effort does **NOT** raise thoroughness. A maximum-effort agent that reads one file in three and traces no relationships is doing shallow work with a strong model. The two dials must be set independently: effort governs the quality of reasoning applied to each examined item; thoroughness governs which items are examined and how their relations are followed.

## Thoroughness Ladder (T1–T5)

Thoroughness is a **single scalar** ladder. Relation-depth is the upper rungs of this one ladder, not a separate axis.

- **T1 — Sampled**: tools (grep/glob/structured queries) run across all in-scope items, a representative subset is read, and the remainder is assumed fine. The fastest rung; appropriate when items are homogeneous and the risk of a localized surprise is low.
- **T2 — Full-read**: every in-scope item is read in full, in isolation. No cross-item analysis — each item is judged on its own contents, with no attention to how items relate to one another.
- **T3 — Full-read + local relations**: T2 plus each change's immediate neighborhood — its direct callers, its tests, and its direct references — is verified. Relationships are traced one hop out from each change.
- **T4 — Full-read + global relations**: T2 plus a scope-wide relationship model — the call graph, the cross-reference graph, and cross-item duplicate-contract detection — is built and consulted before any change is made. Relationships are traced across the entire scope, not just one hop.
- **T5 — Exhaustive / adversarial**: T4 plus an independent completeness pass — a what-did-I-miss critic, a loop-until-dry sweep, and a declared-vs-achieved reconciliation. The agent adversarially attacks its own coverage until no further gap surfaces.

## Scope Ladder

Scope is the boundary radius, a nested ladder from narrowest to widest:

```
change-set ⊂ artifact ⊂ component ⊂ module ⊂ overall
```

- **change-set** — only the files modified by the current change.
- **artifact** — the single file/document/class the change lives in, in full.
- **component** — the cohesive unit (a skill, a package, a feature) the artifact belongs to, including its untouched siblings.
- **module** — the build/deploy unit (a bundle) the component belongs to.
- **overall** — the entire codebase.

`finalize-step-simplify` ships the embryo of this ladder via `--scope {changeset|artifact}`, capped to the plan's live footprint (derived on demand from the worktree). The full ladder names the rungs above `artifact` that a deliberate wide-scope campaign needs.

## Grade to the Floor

A unit's thoroughness is the **floor** across its items, not the average. The thoroughness of a unit is the lowest thoroughness any in-scope item received.

A sweep where the changed files got T3 but the unchanged majority got T1 is a **T1 sweep**, not "≈4." Averaging hides the items that were skipped or sampled, which are exactly the items where an undetected defect survives. The floor is the honest number because coverage is only as strong as its weakest-covered item.

## Coupling Constraint

Relation-tracing thoroughness lower-bounds scope. You cannot trace a relationship whose other end lies outside scope — so `T4 over change-set` is incoherent: the global relationship model T4 demands cannot be built when the scope excludes the very siblings the relations point at. Honoring T4+ therefore forces scope ≥ `component`.

The constraint, stated precisely so config validation can cite it verbatim:

```
reject thoroughness ≥ T4 ∧ scope < component
```

**Proof.** The `_output_error` sibling-consistency miss is the canonical witness: a component-level invariant lived partly in untouched sibling files. At change-set or artifact scope those siblings are out of radius, so the invariant violation was structurally uncatchable — at *any* thoroughness, because no amount of depth on the in-radius items can reach an item the scope excludes. The only fix is to widen scope to `component` so the siblings enter the radius. This is why T4/T5 (which exist precisely to trace such cross-item relationships) are incoherent below `component` scope: the depth has nothing to bite on.

## Floor-Graded Self-Report

Coverage-class work — sweeps, audits, refactors, refines, and any task whose value comes from how completely it covered a surface — MUST state the scope × thoroughness it was **asked for** and the scope × thoroughness it **achieved**, graded to the floor, with evidence:

- **What was read** — the items examined in full, distinguished from items sampled or assumed.
- **What relations were traced** — the callers, tests, cross-references, and graphs actually consulted (the T3/T4/T5 evidence).
- **What was assumed-not-read** — the items deliberately left unexamined, named so the gap is visible rather than hidden behind an average.

The self-report is the mechanism that makes the declared-vs-achieved comparison auditable. Without it, "thorough" is an unfalsifiable claim.

The self-report is the quality signal for coverage-class work — there is no blocking gate and no mechanical thoroughness measurement. A component honors the contract by stating its floor-graded asked-for-vs-achieved cell, not by passing an enforcement check.

## See Also

This standard defines the **levels** — the two ladders, grade-to-the-floor, the coupling constraint, and the self-report. It deliberately does NOT define what each `(thoroughness, scope)` cell *operationally means* for a broad-pass component (which files to cover, which relations to trace, how many lenses, sampling-vs-exhaustive, how many loop-until-dry rounds). That **operational instruction per cell** is owned by the [coverage-gathering contract](coverage-gathering-contract.md), whose static expansion table maps each cell to its instruction text. The division is explicit and non-duplicating:

- **`thoroughness.md` (this standard) defines the LEVELS** — T1–T5, the scope ladder, grade-to-the-floor, the coupling constraint, the self-report.
- **`coverage-gathering-contract.md` defines the OPERATIONAL INSTRUCTION per cell** — what a level *means* for a component's breadth and depth, gathered from the user via `AskUserQuestion`, expanded via `manage-config coverage expand`, and consumed by the components that implement the contract.

Coverage is gathered, expanded, and consumed per the coverage-gathering contract; the ladders here are cross-referenced by it, never restated there.
