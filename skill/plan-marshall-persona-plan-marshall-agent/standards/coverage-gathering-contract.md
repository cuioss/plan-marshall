# Coverage-Gathering Contract

> **Type**: Reusable Component Contract | **Gather mechanism**: `AskUserQuestion` | **Expander**: `manage-config coverage expand` | **Implementations**: 6 | **Status**: Active

## Overview

Coverage is a reusable two-dial contract — **scope** (where the boundary is drawn) and **thoroughness** (how completely in-radius items are covered and how deeply their relationships are traced). Broad-pass components — wide audits, compliance sweeps, simplification and refactor campaigns, and pre-submission review — *implement* this contract: each gathers a `(thoroughness, scope)` cell from the user at invocation, expands it into a canonical operational instruction, persists both, and consumes the **expanded instruction** to govern its own breadth and depth.

This contract replaces the removed enforcement-gate model (the blocking phase-handshake invariant and the mechanical thoroughness-measurement path) with a **user-gathered, statically-expanded, component-consumed dial**. The quality signal is the floor-graded self-report defined in [`thoroughness.md`](thoroughness.md) — not a blocking gate.

The transport mirrors the `compatibility` → `compatibility_description` pattern exactly. `phase-2-refine` reads a single configured **identifier** (`compatibility`), maps it through a **static table** to a long description (`compatibility_description`), persists BOTH, and passes the **description** downstream for LLM consumption (see `phase-2-refine/standards/refine-workflow-detail.md` § Step 5 / Step 13). Coverage is identical: the small `(thoroughness, scope)` identifier is mapped through a static table — owned by this contract, emitted by the `coverage expand` script — to a multi-line operational **instruction block**; the component persists identifier + instruction and consumes the instruction downstream. The only structural difference is that coverage's identifier is a two-field cell whose expansion is a multi-line operational block rather than a one-line description, so the expansion lives in a script + this contract's table rather than a single inline markdown row.

This contract does NOT restate the `thoroughness.md` ladders, the grade-to-the-floor rule, the coupling constraint, or the self-report. The division is explicit:

- **`thoroughness.md` defines the LEVELS** — the T1–T5 thoroughness ladder, the `change-set ⊂ artifact ⊂ component ⊂ module ⊂ overall` scope ladder, grade-to-the-floor, the coupling constraint `reject thoroughness ≥ T4 ∧ scope < component`, and the floor-graded self-report.
- **This contract's expansion table defines the OPERATIONAL INSTRUCTION per cell** — for each `(thoroughness, scope)` cell, the concrete instruction text the level *means* for a broad-pass component: which files to cover, which relations to trace, how many lenses, sampling-vs-exhaustive, how many loop-until-dry rounds.

No duplication: the ladders are cross-referenced, never copied.

## The Canonical Gather Shape

A component gathers the cell at invocation via `AskUserQuestion`, in two coupled questions, each carrying an explicit `inherit` escape:

- **scope** — one of `change-set`, `artifact`, `component`, `module`, `overall`, plus `inherit (default — behave exactly as today)`.
- **thoroughness** — one of `T1`, `T2`, `T3`, `T4`, `T5`, plus `inherit (default — behave exactly as today)`.

The coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`, owned by `thoroughness.md` and enforced by `_validate_coupling`) constrains the offered options: when the user selects thoroughness ≥ T4, the scope question MUST offer only `component`/`module`/`overall`, OR the gathered pair is validated after the fact and re-asked on violation. The component MUST NOT re-implement the coupling math — validation of the **gathered literal pair** is delegated to `manage-config coverage expand --thoroughness {T} --scope {S}`, which applies `_validate_coupling` to the passed values and returns `error_type: coverage_coupling_violation` on an incoherent pair; the component re-prompts on that error. (`coverage resolve` is NOT a validator for a gathered pair — it resolves the project-default cell from `marshal.json` and has no way to accept a literal pair; see Persistence + Transport below.)

`inherit` on either dial means "behave exactly as today — no breadth or depth change". `inherit/inherit` is the behavior-preserving default; a component invoked with `inherit/inherit` reproduces its pre-contract behavior bit-for-bit.

## The Expansion Table (the load-bearing addition)

This table is the single source of expansion every implementing component consumes. For each cell, it defines the canonical operational instruction text — what the cell *means* in terms of breadth (which items to cover) and depth (which relations to trace, how many lenses, sampling-vs-exhaustive, loop-until-dry rounds). The D2 `coverage expand` script (`manage-config/scripts/coverage_presets.py`) transcribes this table; a lock-step test asserts the script table and this authored table stay identical. This standard is authoritative for the *operational instruction text*; the script is authoritative for *emitting* it.

The thoroughness rung sets the depth dimension of every cell; the scope rung sets the breadth dimension. The table below states the per-rung instruction along each axis — the cell instruction is the composition of its scope-rung breadth instruction and its thoroughness-rung depth instruction.

### Behavior-preserving cell

| Cell | Operational instruction |
|------|-------------------------|
| `inherit / inherit` | Behave exactly as the component does today — no breadth change, no depth change. The expander returns this instruction whenever either dial is `inherit` and no concrete cell is supplied. Default everywhere. |

### Scope rung → breadth instruction

| Scope rung | Breadth instruction (which items to cover) |
|------------|--------------------------------------------|
| `change-set` | Cover only the items the current change touches — the narrowest radius. Untouched siblings are out of scope. |
| `artifact` | Cover the single file/document/class the change lives in, in full, including its untouched in-file content. |
| `component` | Cover the cohesive unit (skill, package, feature) the artifact belongs to, including its untouched siblings. The coupling floor for thoroughness ≥ T4. |
| `module` | Cover the build/deploy unit (bundle) the component belongs to. |
| `overall` | Cover the entire codebase / full corpus — the widest radius. |

### Thoroughness rung → depth instruction

| Thoroughness rung | Depth instruction (how deeply to cover, which relations to trace) |
|-------------------|-------------------------------------------------------------------|
| `T1` | Sampled: run tools across all in-scope items, read a representative subset in full, assume the remainder. No relation tracing. One lens. |
| `T2` | Full-read: read every in-scope item in full, in isolation. No cross-item relation tracing. One lens. |
| `T3` | Full-read + local relations: T2 plus trace each item's immediate neighborhood one hop out — direct callers, tests, direct cross-references. |
| `T4` | Full-read + global relations: T2 plus build and consult a scope-wide relation model (call graph, cross-reference graph, duplicate-contract detection) before acting. Requires scope ≥ `component`. |
| `T5` | Exhaustive / adversarial: T4 plus an independent completeness pass — a what-did-I-miss critic, a loop-until-dry sweep that repeats until no further gap surfaces, and a declared-vs-achieved reconciliation. |

A component "composes" its cell instruction by taking the breadth instruction for its scope rung and the depth instruction for its thoroughness rung. The contract's static expander emits the composed instruction block for the requested cell; an incoherent cell (`thoroughness ≥ T4 ∧ scope < component`) is rejected at expansion time via the shared coupling validator and never appears in the table.

## What "Implements the Coverage Contract" Means

Modeled on the `ext-point-*` extension contracts, this contract declares an **implementor obligation** with three parts. A component implements the coverage-gathering contract when it:

1. **Gathers** the `(thoroughness, scope)` identifier from the user at invocation via the canonical `AskUserQuestion` shape above (coupling-constrained options, `inherit` default).
2. **Expands + persists** — expands the identifier into the canonical operational instruction block via `manage-config coverage expand` (this contract's static table), and persists BOTH the identifier and the expanded instruction via the Decision-D mechanism below. This mirrors `phase-2-refine` storing `compatibility` + `compatibility_description`.
3. **Consumes the expanded instruction** (NOT the raw cell) to govern its runtime breadth (how many files/components/candidates it covers) and depth (how far it traces relations, how many lenses / loop-until-dry rounds it runs, sampling vs exhaustive) — with the `inherit/inherit` instruction reproducing the component's pre-contract behavior bit-for-bit.

Each implementor cross-references this contract and declares only its own component-specific **scope-rung → breadth-dial** and **thoroughness-rung → depth-dial** bindings — which of its existing dials each rung indexes. An implementor MUST NOT re-author the operational instruction text (that lives here) and MUST NOT restate the `thoroughness.md` ladders.

## Persistence + Transport Mechanism

The gathered cell is captured at invocation, persisted, and consumed at runtime as expanded instruction text.

- **Gather** — `AskUserQuestion` per the canonical shape above.
- **Validate + Expand (one call)** — `manage-config coverage expand --thoroughness {T} --scope {S}` validates the gathered literal pair (it applies `_validate_coupling` to the passed values) AND returns the canonical operational instruction block for the cell in a single call. A `coverage_coupling_violation` re-prompts the gather. No re-implemented coupling math. **`coverage resolve` MUST NOT be used to validate a gathered pair** — it resolves and validates only the PROJECT-DEFAULT cell read from `marshal.json` (`plan.coverage`); it has no per-plan tier and no parameter for a literal `(thoroughness, scope)` pair, so it silently ignores the gathered values. The validator for a gathered literal is always `coverage expand`.
- **Persist** — for plan-bound components, persist via `manage-status metadata --set`:
  - `--field coverage_thoroughness` and `--field coverage_scope` — the identifier.
  - `--field coverage_instruction` — the expanded instruction block.

  This is the same `status.json` metadata channel that `recipe_profile`, `recipe_domain`, and `change_type` already use. Single-invocation audit skills that operate outside a plan hold the identifier + expanded instruction **in-context** for the invocation — no cross-phase persistence is needed.
- **Runtime consume** — the executing component reads `coverage_instruction` (the expanded block) from metadata and consumes it directly. When the metadata is absent, it re-expands the identifier via `coverage expand`, then falls back to `coverage resolve` (the project-default tier reading `plan.coverage` in `marshal.json`) → `inherit/inherit` → the expander's behavior-preserving instruction.

Persisting BOTH the identifier and the expansion (rather than the identifier alone) follows the `compatibility` + `compatibility_description` precedent for the same auditability reason: a plan's chosen coverage is human-readable directly from `status.json` without re-running the expander.

`coverage read` / `coverage resolve` are the project-DEFAULT lookup (they read `marshal.json` only, with no per-plan tier and no literal-pair parameter); they CANNOT validate a gathered pair — they resolve and validate only the project-default cell. The per-invocation user-gathered cell lives in `status.json` metadata, and the verb that validates it is `coverage expand`. See `manage-config` § coverage for the resolver walk and the `coverage expand` verb.

## Current Implementations

| Component | Scope rung → breadth dial | Thoroughness rung → depth dial |
|-----------|---------------------------|--------------------------------|
| `audit-archived-plan-retrospectives` | `change-set`/`artifact` → single plan (`--plan-id`); `component`/`module` → a domain/scope-filtered subset; `overall` → the full corpus (default). | T1 → cheap checks + sample; T2 → all checks once; T3 → add cross-check-synthesis coupling; T4/T5 → add the loop-until-dry / what-did-I-miss completeness pass. |
| `recipe-plugin-compliance` | `component` → one bundle/skill; `module` → a bundle set; `overall` → all bundles (default). | T1/T2 → frontmatter + enforcement-block surface; T3 → add standards cross-ref tracing; T4/T5 → add cross-skill relation-graph + loop-until-dry. |
| `recipe-simplify-codebase` | scope rung IS the existing `recipe_scope`. | thoroughness rung IS the existing `recipe_thoroughness`; T4+ triggers the relation-graph pre-deliverable. |
| `recipe-refactor-to-profile-standards` | scope rung selects the package/module radius in the module filter. | T2 full-read each file; T3 trace callers/tests; T4+ scope-wide relation model before refactor. |
| `pre-submission-self-review` | scope rung indexes the candidate-count gate and the surfacer `--contract-radius`. Surface-only rule retained at every rung. | `inherit`/T1/T2 → the surface checks as today; T3+ → also trace each surfaced candidate's siblings/cross-refs. |
| `finalize-step-simplify` | `change-set`/`inherit` → `changeset`; `artifact`+ → `artifact` (each modified file in full). | T1/T2/`inherit` → review anti-patterns at face value; T3+ → trace each deletion candidate's callers/cross-refs before deleting. |

`inherit/inherit` everywhere → the expander's behavior-preserving instruction → today's hardcoded behavior, so default plans are byte-for-byte unchanged.

## See Also

- [`thoroughness.md`](thoroughness.md) — the two ladders, grade-to-the-floor, the coupling constraint, the floor-graded self-report. The contract restates none of these; it adds the operational instruction per cell.
- `manage-config` § coverage — the `coverage read` / `coverage resolve` resolver and the `coverage expand` static expander verb.
- `phase-2-refine/standards/refine-workflow-detail.md` § Step 5 — the `compatibility` → `compatibility_description` identifier-expands-to-instruction precedent this contract mirrors.
