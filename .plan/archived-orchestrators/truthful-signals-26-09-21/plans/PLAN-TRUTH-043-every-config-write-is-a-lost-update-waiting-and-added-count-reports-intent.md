> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-007`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-043: every config write is an unguarded whole-document overwrite, and `added_count` reports intent rather than state

epic: truthful-signals
workstream: WS-01

## Objective

Reported from an API-Sheriff `marshall-steward upgrade` (bundle 0.1.1286), Stage 2:

> `sync-defaults` reported `status: success`, `added_count: 1` — **and a later config write in the same
> stage silently reverted it.** The key was absent from disk and `provisioned_version` was still
> `0.1.1275`.

⭐⭐ **The revert target is the decisive evidence.** `provisioned_version` did not go missing — it went
**back to its previous value**. A partial delete cannot do that. **Only a whole-document overwrite from
a snapshot taken BEFORE `sync-defaults` ran can**, and that is exactly what the code does.

## OBSERVED — first-party, in our tree, population derived

Every marshal.json mutation is a **whole-document read-modify-write with no staleness control**: no
version check, no fingerprint compare, no re-read, no compare-and-swap.

- `_config_core.py:62` `load_config()` — reads the whole document
- `_config_core.py:117` `save_config()` — writes the whole document back
- **42 write paths total**: 37 `save_config()` call sites across 14 files, plus **5 direct
  `marshal_path.write_text` sites**.

⇒ **Any process that loads the config before another writes, and saves after, silently reverts that
write.** There is no mechanism by which it could notice.

⭐ **The concrete suspect matches the reported sequence exactly**: Stage 2 ran `sync-defaults` and then
re-seeded `build.map`. `_cmd_build_map.py` carries a `save_config()` call. ⛔ **HYPOTHESIS — confirm at
D0 by reading the ordering of loads and saves in that stage.** Do not fix the suspect before confirming
it; the class defect is real regardless of which site did it.

## ⭐ Second defect, found while verifying: the ordering authority's docstring is FALSE

`order_config_keys`'s docstring (`_config_core.py:102-105`) states it is

> *"the single authority for top-level marshal.json key ordering: both `save_config` and the
> `manage-providers` `write_provider_config` write path route through it, **so no write appends a block
> out of canonical order**."*

⛔ **`ext_defaults_set` (`:338`) and `ext_defaults_set_default` (`:361`) write directly** —
`json.dumps(config, indent=2)`, no ordering, and no trailing newline where `save_config` adds one. Plus
`opencode_runtime.py:78` and `_providers_core.py:108`.

⇒ The docstring names **two** routed paths; there are **five** write sites and at least three bypass it.
⭐ **This is our defending-documentation / vacuous-authority archetype** — a claim of completeness that
is false at the moment it is read, in the very file that implements the guarantee. **The differing
trailing-newline shape also makes these writes a silent diff-churn source.**

## ⭐ Third defect: `added_count` is a report about a function call, not about a file

The upgrade flow's own detect/warn rule treats `added_count > 0` as **the normal path**, so a
successful-then-reverted add is **structurally invisible**. Nobody re-reads.

⇒ **`added_count: 1` was true when `sync-defaults` returned and said nothing about the file afterwards.**
This is the `unchecked-persist-loses-the-finding` archetype (PLAN-86, #1038) at the config layer: a
return value about an *intention* consumed as a fact about *state*.

## ⛔⛔ What actually caught it was two oracles disagreeing — that is not a check

Stage 3 preflight reported **`marshal_status: stale` while `executor_action: fresh`**, and the operator
investigated the disagreement. ⚠ **Had both oracles agreed — which is the normal case — the upgrade
would have shipped with the key silently absent.** ⇒ **The detection was accidental redundancy, not
designed verification.** Any remedy that leaves verification to the disagreement of two independent
freshness reports is not a remedy.

## Deliverables

1. **D0 — GATE: confirm the clobber site and derive the full write population.** Confirm or refute the
   `build.map` suspect by reading the Stage-2 load/save ordering. ⛔ **Both directions**: sites that
   read-then-write across another write, AND sites that write without reading. **42 is the count from
   one sweep — re-derive it.**
2. **D1 — make a stale write fail rather than win.** A compare-and-swap on the document (fingerprint or
   mtime read at load, re-checked at save) so a write over a changed document is **rejected, not
   silently applied**. ⛔ **This is the load-bearing deliverable.** ⚠ Confirm no legitimate flow depends
   on last-writer-wins before enforcing it — if one does, it must be made explicit rather than implicit.
3. **D2 — `sync-defaults` verifies its own write.** Re-read after writing and assert the key is present
   and `provisioned_version` is stamped. ⭐ **Report the verified state, not the attempted mutation** —
   rename or supplement `added_count` so the return says which it is.
4. **D3 — fix the detect/warn rule's vacuous success path.** `added_count > 0` must not be self-
   certifying. ⛔ **A control assertion is required**: the rule must be shown to FIRE on a
   write-then-revert fixture, or it is the same vacuous guard in a new place.
5. **D4 — route the bypassing write sites through `order_config_keys`, or correct the docstring.**
   ⚠ **One or the other, never neither** — an authority claim that is false is worse than an absent one.
   Include the trailing-newline difference.
6. **D5 — tests, each verified to FAIL pre-fix.** (a) A write over a document changed since load is
   rejected. (b) `sync-defaults` followed by an independent `save_config` from a stale snapshot does not
   lose the key. (c) The detect/warn rule fires on write-then-revert. (d) Every write site emits
   canonically ordered JSON with identical trailing bytes. (e) The D0 population is asserted non-empty
   and contains all five direct-write sites.

⚠ **Six deliverables, at the scope-bloat threshold.** Split evaluated and **declined**: D1 is
meaningless without D0's population, and D2/D3 are the same verification obligation at two layers.
⭐ **D4 is the split point** — it is a separate defect that merely shares the file.

## Claim Labels

- **OBSERVED (first-party, this orchestrator)**: `load_config`/`save_config` as whole-document
  read-modify-write; the 42-path population (37 `save_config` + 5 direct); the false docstring at
  `:102-105` against the bypassing writes at `:338`, `:361`, `opencode_runtime.py:78`,
  `_providers_core.py:108`; `_cmd_build_map.py` carrying a `save_config`.
- **REPORTED (operator, first-party to them)**: the `added_count: 1` success, the absent key, the
  `provisioned_version` still at `0.1.1275`, the Stage-3 `marshal_status: stale` /
  `executor_action: fresh` split, and that the flow's rule treats `added_count > 0` as normal.
- **INFERENCE, explicitly labelled**: that the revert-to-previous-value proves a whole-document
  overwrite from a pre-`sync-defaults` snapshot. ⚠ **Strong but not proof** — a second `sync-defaults`
  path that restores an older stamp would produce the same observable. **D0 must distinguish them.**
- **HYPOTHESIS**: `build.map` re-seeding is the clobbering write. ⛔ **Suspect, not conclusion.**
- **HYPOTHESIS**: no flow depends on last-writer-wins. **Verify before D1 enforces CAS** — an asserted
  absence, and the higher-risk half.

## Expected Surface

- **OBSERVED**: `manage-config/scripts/_config_core.py` — `load_config`, `save_config`,
  `order_config_keys`, `ext_defaults_set*`
- **OBSERVED**: `manage-config/scripts/_cmd_sync_defaults.py` (D2), `_cmd_build_map.py` (D0 suspect)
- **OBSERVED**: `manage-providers/scripts/_providers_core.py`, `platform-runtime/scripts/opencode_runtime.py` (D4)
- **HYPOTHESIS**: `marshall-steward/scripts/upgrade.py` and the upgrade flow doc — the detect/warn rule (D3)

## Dependencies and Sequencing

- ⚠ **Adjacent to `PLAN-TRUTH-007`** (key-order canonicalization unreachable, `_config_core.py`) and
  **`PLAN-TRUTH-009`** (surface every knob in marshal.json, `manage-config`). ⛔ **Same file as 007 —
  SERIALIZATION PAIR, and 007 may already own part of D4.** Evaluate absorption at outline.
- ✅ Disjoint from both running plans (TRUTH-010 executor/`manage-status`, TRUTH-035 `manage-metrics`).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-043-every-config-write-is-a-lost-update-waiting-and-added-count-reports-intent.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
