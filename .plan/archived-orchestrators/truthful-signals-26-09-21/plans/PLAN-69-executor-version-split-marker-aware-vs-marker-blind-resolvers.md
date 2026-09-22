# PLAN-69: Two Version-Selection Legs Disagree — Marker-Aware vs Marker-Blind — Emitting a Silently Version-Split Executor

epic: truthful-signals
workstream: WS-01

> Staged from a **cross-repo finding**: `TokenSheriff` (a plan-marshall consumer) filed
> `.plan/temp/orchestrator-request-executor-version-skew.md` after a `/marshall-steward upgrade`
> emitted an executor stamped `0.1.1212` whose script mappings resolved 121→`0.1.1194` and
> 63→`0.1.1212`. **The consumer silently ran 18-version-old scripts against current skill docs with
> every freshness signal green.**
>
> The filer explicitly flagged their causal account as inferred-from-the-fix and asked for
> confirmation before design. **The orchestrator confirmed the mechanism at HEAD and CORRECTED it —
> see below.** ⭐ **LIVE consumer-impacting defect; highest-priority staged plan.**

## Objective

Two version-selection legs run over the same cache directories with **different predicates**: one
consults the `.orphaned_at` marker, the other is blind to it. Whenever the newest version dir carries
a marker, the legs select different versions and the generated executor is internally split — while
the generator reports `status: success`. Make version selection single-sourced, and make an
inconsistent executor structurally impossible to emit.

## ⚠ Mechanism — OBSERVED, verified at HEAD by the orchestrator (2026-07-26)

**The filer's hypothesis was "script discovery skips marked dirs and falls back to the newest
unmarked one, while the stamp leg reads `dist-manifest.json`." Substantially right, one correction:**
it is not one leg honoring the marker and one reading the manifest. It is **two resolvers over the
same directory set, one marker-aware and one marker-blind.**

- OBSERVED — **marker-AWARE leg**: `script-shared/scripts/marketplace_bundles.py:67`
  `find_bundles` computes `live = [d for d in version_dirs if not (d / '.orphaned_at').exists()]`
  and selects `max(live)` (`:70`). With `0.1.1212` marked and `0.1.1194` unmarked, this returns
  **1194**.
- OBSERVED — **marker-BLIND legs**: `resolve_bundle_path` (`:124-133`) filters only on
  `(version_dir / subpath).exists()`, and `collect_script_dirs` (`:170-174`) filters only on
  `(d / 'skills').is_dir()`. Neither consults `.orphaned_at`; both take `max()` by version tuple, so
  both return **1212**.
- OBSERVED — the two legs feed the SAME executor composition, which is exactly why the split is
  *internal to one bundle* (121 vs 63) rather than a clean whole-file version mismatch.
- OBSERVED — **the saturation fallback is a red herring for this symptom.** `find_bundles:71-91`
  tier 3 (every dir marked) falls back to newest-on-disk, which would return 1212 and *agree* with
  the blind leg. The split therefore proves the state at generation time was **1212 marked, ≥1 older
  dir unmarked** — not full saturation. Full saturation produces a *different* (degraded but
  self-consistent) outcome.
- OBSERVED — **answer to the filer's open question #5: the writer is OURS.**
  `tools-script-executor/scripts/generate_executor.py:1708` — `_mark_superseded_version_dirs` does
  `(version_dir / '.orphaned_at').write_text(marker_ts)`, called from `cmd_preflight`'s pollution
  path (`:1805-1824`). Not the host plugin manager.
- OBSERVED — **the retention pin is WRITE-SIDE ONLY, and nothing ever clears a marker.**
  `_retention_pinned_versions` (`:1575-1609`) pins newest-on-disk + `system.provisioned_version` +
  the `dist-manifest.json` version, and its docstring asserts this makes saturation "structurally
  impossible". But an exhaustive search finds **no code path anywhere in the bundles that removes an
  `.orphaned_at` file** — the sweep explicitly treats it as advisory
  (`cache_retention.py:31`, `:222`). So the pin prevents NEW marks on a pinned dir; it never
  reconciles a mark already present. A marker written before that dir became pinned — e.g. by a
  pre-pin version, or by a run where a newer dir existed and was later pruned — is **permanent**.
  That is why the filer's fix (deleting the markers by hand) worked and why nothing self-heals.
- OBSERVED — this falsifies a shipped justification.
  `manage-config/standards/provisioning-fail-closed-audit.md:96` re-justifies
  `_detect_multi_version_pollution`'s fail-closed status on the premise that "the newest-on-disk dir
  is never marked, so every bundle contributes at least one live dir." True only for marks written
  *after* the pin landed; the field data contradicts it. **The audit entry must be re-opened as part
  of this plan**, not left standing on a refuted premise.
- OBSERVED — the local (meta-repo) cache is currently consistent but carries the precondition:
  `plan-marshall/0.1.1194` and `0.1.1212` are both unmarked while `1202`–`1208` are marked. 1194
  survives unmarked because it is pinned as `system.provisioned_version`. If `1212` is ever marked,
  this machine reproduces the consumer's split immediately.

## Deliverables

### D1 — GATE: single-source the version selection (mutates nothing)

Settle which selector is authoritative and collapse the others onto it. The filer's requirement is
the right north star: **the version dir named by the installed `dist-manifest.json` must be the one
script discovery uses**, and `.orphaned_at` must never steer discovery away from it. Decide (a) the
one selection function all three call sites route through; (b) what `.orphaned_at` is *for* once it
can no longer influence selection — the audit doc already calls it "advisory only", so the honest
options are keep-as-diagnostic or retire it; (c) whether the marker's meaning should be reconciled on
read (treat a mark on a pinned dir as stale and ignore it) or on write (clear it when a dir becomes
pinned) — **read-side reconciliation is the safer default**, since a write-side-only rule is exactly
what produced this defect.

### D2 — one selector, used by every leg

Route `find_bundles`, `resolve_bundle_path`, and `collect_script_dirs` through the D1-chosen
single-source selection. No caller may re-derive "which version dir is live" with its own predicate.

### D3 — post-generation fail-closed self-check (the filer's item 3 — highest value)

After composing the executor and before writing it, assert every emitted script path resolves under
the `MARSHALL_VERSION` dir (allowing explicitly-sanctioned alternates such as genuine project-local
scripts). On violation: refuse with `status: error` and leave the prior executor **byte-identical** —
the same fail-safe contract the placeholder-residue and `py_compile` guards already honour. This is
the deliverable that makes the whole class unshippable regardless of how selection later evolves.

### D4 — marker lifecycle is reconciled, not write-only

Implement the D1 verdict so a marker on a currently-pinned dir can never suppress that dir. Re-open
and correct `provisioning-fail-closed-audit.md:96`, whose `_detect_multi_version_pollution`
justification rests on the refuted "newest is never marked" premise.

### D5 — tests

(a) With the newest dir marked and an older dir unmarked, generation emits a single-version executor
or refuses — never a split one (the filer's stated acceptance criterion). (b) The three legs return
the same version dir for the same cache state, across: newest-marked, all-marked (saturation), and
none-marked. (c) The D3 guard refuses and preserves the prior executor byte-for-byte. (d) A marker on
a pinned dir does not suppress it.

## Expected surface

- OBSERVED: `script-shared/scripts/marketplace_bundles.py` — `find_bundles` (`:52-92`),
  `resolve_bundle_path` (`:107-135`), `collect_script_dirs` (`:148-...`)
- OBSERVED: `tools-script-executor/scripts/generate_executor.py` — `_live_version_dirs` (`:1540`),
  `_retention_pinned_versions` (`:1575`), `_mark_superseded_version_dirs` (`~:1664-1710`), the
  composition path (`:761-762`) and its existing self-checks
- OBSERVED: `manage-config/standards/provisioning-fail-closed-audit.md:96` — the refuted
  justification
- HYPOTHESIS: `marshall-steward/scripts/cache_retention.py` — touched only if D1 retires or
  redefines the marker (verify-at-outline)
- OBSERVED: tests under `test/plan-marshall/tools-script-executor/**` and the `script-shared` module

**Disjointness:** `script-shared` + `tools-script-executor`. Disjoint from PLAN-66 (`manage-locks`),
PLAN-53 (`marshall-orchestrator`), PLAN-51 (`plan-retrospective`), PLAN-57 (`manage-status`).
⚠ **OVERLAPS PLAN-68** — both touch `generate_executor.py`, and the filer's item 4 (teach preflight
to see per-mapping divergence) **IS PLAN-68's D2**. See sequencing.

## Dependencies and Sequencing

- **PLAN-69 and PLAN-68 must not run concurrently** — same file, same function family.
- **Preferred order: PLAN-69 first, then PLAN-68.** 69 establishes what "the right version" means;
  68's preflight check then verifies against a single-sourced answer rather than inventing its own.
  Running 68 first would build a resolution check on top of the very ambiguity 69 removes.
- **Reconsider a merge at D1.** If 69's D1 lands the single selector, PLAN-68 may shrink to "preflight
  calls the D2 selector and reports divergence" — small enough to fold in. The split-guard favours
  keeping them separate (69 is already 5 deliverables); revisit once D1 is settled.
- Not gated on PR #1003 (different surface from PLAN-67's key-order work).

## Notes

- Flagship archetype, and the most consequential instance yet: **every** freshness signal reported
  green — generator `success` + 140 scripts discovered, `preflight` `fresh`, `cache_freshness check`
  `fresh` — while the consumer ran 18-version-old code. The filer's point 3 is exactly right: there
  is currently **no** surface in the upgrade flow that reports this class.
- Vacuous-guard family too: the generator's three existing self-checks (TEMPLATE_FORMAT_VERSION
  handshake, placeholder residue, `py_compile`) all pass on a split executor — none asserts the
  emitted paths agree with the stamp. D3 closes that.
- Cross-repo credit: the finding, the reproduction handles, and the acceptance criterion come from
  the TokenSheriff session. The mechanism correction and the writer identification are the
  orchestrator's verification pass.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
