# PLAN-CIS-023: The Path-Attribution Seam — core owns the merge, bundles claim their paths

epic: code-intelligence-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`which-module` resolves a path to its owning module through a four-step ladder whose third step
is a **hardcoded single-entry tuple in core** — `_PROJECT_LOCAL_PREFIX_MAP = (('.claude/skills',
'plan-marshall'),)`. Every path outside a module's declared `paths.sources` / `paths.tests` that
is not that one prefix resolves to `module: null`: `.plan/**` and `.claude/commands/**` both do
today.

This is the same architectural inversion PLAN-02 removed one tier up. There, core owned the Maven
coordinate join and no other build system could contribute an edge; here, core owns the
project-local path claim and no bundle can contribute an attribution. **Core should own the merge,
the provenance, and the resolution order — and own none of the claims.**

Turn the prefix map into a bundle-contributed attribution seam, and register core's own claim
(`.plan/**` → the plan-marshall module) through it rather than beside it.

## Deliverables

1. **A path-attribution extension point** — a bundle declares the path prefixes/globs it owns and
   the module each maps to. Modelled on the shipped `ext-point-derivation-resolver` contract
   (declaration, discovery, dispatch, null-on-absent), because that seam already solved the
   identical shape at Tier 1 and a second, differently-shaped seam for the same problem is the
   duplication this epic exists to remove.
2. **Merge semantics with provenance.** Resolution stays core's: longest-prefix wins, and every
   resolved attribution names the bundle that claimed it. ⛔ **A path claimed by two bundles is an
   ambiguous key, not a tie to break by iteration order** — emit no attribution and report the
   collision, exactly as `ext-point-derivation-resolver` obliges a resolver facing an ambiguous
   identity key. This epic has already recorded that non-deterministic answers presented as
   confident ones are the failure mode.
3. **`_PROJECT_LOCAL_PREFIX_MAP` retired**, its single entry re-homed as a declared claim. ⚠ The
   entry is marked "operator-confirmed owner" in its own comment — **re-home the claim, do not
   silently re-decide the owner.** Whether `.claude/skills/**` should move from `plan-marshall` to
   `pm-plugin-development` is PLAN-CIS-025's call, not this plan's.
4. **Core's own claim registered through the seam**: `.plan/**` → the plan-marshall module,
   closing the `module: null` answer for the executor and every `.plan/` script path.
5. **Fail-closed reporting for the unclaimed residue.** A path no bundle claims must stay
   distinguishable from a path whose claiming bundle is absent — the `resolver_count: 0` vs
   `resolver_count: N, edges: []` distinction ADR-009 and the provenance contract already
   establish at Tier 1, applied to attribution.
6. **Documentation** — the extension-point standard under `extension-api/standards/`, the
   `which-module` resolution-order contract in `manage-architecture`, and the attribution model on
   `doc/concepts/code-intelligence.adoc` (which currently documents the tier ladder but not path
   attribution at all).

⚠ **Six deliverables — the split guard applies.** Proceed-unsplit rationale: D1–D5 are one seam
and its first two claims; splitting them ships a seam with no claim through it, which is
unexercised by construction. D6 is the doc contract for D1–D5 and this epic has recorded
doc-contract-divergence as a standing archetype. **Evaluate the split at outline; if D4 (`.plan`
claim) can ship separately without leaving the seam unexercised, split it out.**

## Claim Labels

- **OBSERVED** — `_PROJECT_LOCAL_PREFIX_MAP: tuple[tuple[str, str], ...] = (('.claude/skills',
  'plan-marshall'),)` at `_architecture_core.py`:742, consumed by
  `project_local_module_for_path()` at `:745`, guarded by module existence at `:765`.
- **OBSERVED** — the four-step resolution ladder at `_cmd_client_handlers.py`:815–828, documented
  at `:751–763`: exact-inventory-more-specific-than-root → longest `sources ∪ tests` containment
  prefix → project-local prefix map → root-inventory match → `None`.
- **OBSERVED (probed against HEAD 2026-08-01)** — `.plan/execute-script.py` → `module: null`;
  `.claude/commands/marshall-steward.md` → `module: null`; `.claude/skills/sync-plugin-cache/SKILL.md`
  and `.claude/skills/build-fix-commit/SKILL.md` → `module: plan-marshall` (both probed).
- **OBSERVED** — `_cmd_client_handlers.py`:754 states project-local dotfile trees "are never
  inventoried at all", so the prefix map is the *only* path by which such a tree resolves.
- **HYPOTHESIS** — the ambiguous-key obligation transfers cleanly from edge derivation to path
  attribution. Confirm/refute at
  `extension-api/standards/ext-point-derivation-resolver.md` § the ambiguous-identity-key
  obligation (verify-at-outline). ⚠ Attribution differs from edge derivation in one respect: an
  edge is an unweighted boolean so union is idempotent, whereas an attribution is a **function**
  (one path → one module) and therefore genuinely conflictable. **If that asymmetry breaks the
  transfer, the merge rule must be designed for a function, not copied from a union.**
- **HYPOTHESIS** — no consumer depends on `which-module` returning `null` for `.plan/**`.
  Confirm/refute by enumerating `which-module` consumers across `marketplace/`, `.claude/`, `doc/`
  (verify-at-outline). ⛔ **Derive the population; an orchestrator-supplied list is a SAMPLE** —
  standing rule 4, and this epic has been bitten by it twice.
- **Verify-first clause**: this plan changes what a currently-`null` answer becomes. Any consumer
  branching on `module is None` changes behaviour. Enumerate before scoping; refutation loops back.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py`:735–766 — the prefix map and its reader
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py`:742–836 — `cmd_which_module` and its ladder
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/` — new ext-point standard, sibling to `ext-point-derivation-resolver.md`
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/` — discovery/dispatch plumbing (verify-at-outline)
- **OBSERVED**: `doc/concepts/code-intelligence.adoc` — attribution model
- **OBSERVED**: `test/plan-marshall/manage-architecture/` — tests

## Dependencies and Sequencing

- **Depends on**: none. PLAN-02's seam is the *model*, not a prerequisite — this is an independent
  extension point at a different tier.
- **Gates**: PLAN-CIS-024 and PLAN-CIS-025 both consume this seam. ⛔ **Neither can ship first** —
  without the seam they would each re-add a hardcoded map, which is the defect.
- **Overlaps with**: PLAN-01, PLAN-02, PLAN-CIS-001, PLAN-CIS-002 on `manage-architecture`.
  ⛔ **Never pair with any of them.**
- **Adjacent to**: the Tier-1 derivation seam (`ext-point-derivation-resolver`) — this plan copies
  its *shape* and touches none of its code. If this plan finds itself editing edge derivation,
  stop: that means the two seams are being conflated, and they are deliberately separate tiers.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-023-path-attribution-seam.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
