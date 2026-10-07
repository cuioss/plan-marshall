envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=finding
created=2026-07-28T13:13:30Z

# Migration/back-compat shims accumulate with no expiry mechanism

**Raised during**: PLAN-92 phase-3-outline operator review (2026-07-28).

**Trigger**: PLAN-92's D3 landed a one-shot `marshall-steward` auto-map
(`enabled_bots` → `required_bots`) at operator direction. That is a legitimate
migration, but it would become the **12th** back-compat/migration site in the
tree, and the operator asked how many already exist and how they get removed.

## Verified inventory — 11 live sites, first-party at HEAD

### Category A — one-shot migrations that self-disarm (5)

| Site | What it migrates |
|---|---|
| `manage-config/scripts/_cmd_sync_defaults.py:74` `_migrate_retired_step_keys` | retired finalize step-key renames |
| `manage-config/scripts/_cmd_sync_defaults.py:160` `_migrate_run_at_all_to_lane` | `run_at_all` → lane model |
| `manage-providers/scripts/_providers_core.py:363` `_migrate_credentials_home_if_needed` | credentials home relocation (3 call sites) |
| `manage-providers/scripts/_providers_core.py:114` `_migrate_credentials_config_keys_if_needed` | credential config-key rename (2 call sites) |
| `tools-permission-fix/scripts/permission_fix.py:1084` `cmd_migrate_executor` | an entire CLI verb |

### Category B — permanent "tolerate the old shape" read paths (6)

These never disarm. They are the half that actually accumulates.

| Site | What it tolerates forever |
|---|---|
| `manage-status/scripts/_cmd_mark_step.py:128` | canonicalized scan for stale pre-migration step keys |
| `manage-status/scripts/_cmd_mark_step.py:146` | `legacy_string_entry` bare-string storage |
| `manage-status/scripts/_cmd_mark_step.py:261` | callers omitting `--head-at-completion` |
| `manage-status/scripts/_cmd_assert_step_recorded.py:120` | pre-migration key insertion order |
| `manage-metrics/scripts/manage-metrics.py:1057` `_read_status_created` | "safety net for plans materialised under older orchestrator versions" |
| `marshall-steward/scripts/determine_mode.py:601,655` + `gitignore_setup.py:84` | legacy list-of-id-strings; legacy gitignore rules no longer emitted |

## The defect

**None of the 11 carries an expiry condition or an owner.** There is no registry,
no marker convention, no plugin-doctor rule, and nothing that ever fires to say
"this is now dead." `_read_status_created`'s docstring cites "older orchestrator
versions" without recording a **version floor**, so nobody can ever prove it is
safe to delete — the shim is unfalsifiable in exactly the way this epic's theme
describes (a confident signal hiding a caveat: the code reads as defensive
correctness while actually being undeletable-by-construction).

Category B is strictly worse than category A: A expires by construction, B
expires never and silently widens the accepted input surface of every reader.

## Proposed scope (operator chose: SEPARATE PLAN, not a PLAN-92 deliverable)

1. **A shim-marker convention** — every migration / back-compat shim declares an
   owner, a version floor, and a removal trigger at its definition site.
2. **A plugin-doctor rule** that flags an unmarked shim (edit-time guard, so the
   12th one cannot land unmarked).
3. **A retirement sweep** over the 6 category-B sites: for each, either record a
   concrete version floor + removal trigger, or delete it outright where the
   tolerated shape can be shown extinct.

## Coordination notes

- PLAN-92's own D3 auto-map is **category A** (self-disarming: step 1 deletes the
  legacy key, so a second run is indistinguishable from never having had one).
  It should be marked by whatever convention this plan lands, but it is not a
  defect and does NOT block PLAN-92.
- Surface overlap with PLAN-92 is limited to `marshall-steward`; sequence this
  plan AFTER PLAN-92 lands so the 12th shim is in the inventory being marked.
- ⚠ Do NOT let the sweep degrade into deleting category-B readers without
  evidence the old shape is extinct. Absence of a marker is not evidence the
  shim is dead — that inversion would be the same archetype one level up.
