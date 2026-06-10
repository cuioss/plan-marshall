# Build Map Setup Reference

Extracted build-map seed logic for the wizard's Project Architecture step and the maintenance Project Structure submenu. Referenced by `wizard-flow.md` Step 8 and `menu-configuration.md` (Project Structure).

The `skill_domains.build_map` block in `marshal.json` is the file-to-build contract: a domain-keyed inventory of `{glob, role, build_class}` entries that maps every changed path to the build action it requires. The seed re-derives that block from every *applicable* registered domain extension's `classify_globs()` + `classify_build_class()` predicates. A domain is *applicable* only when its owning extension's `applies_to_module()` reports `applicable: True` for at least one discovered project module, so a Python-only project never receives `java` / `oci` / `javascript` routes. The schema, the applicability-scoping rule, and the closed canonical-named `build_class` set are owned by `manage-config` — see [`../../manage-config/SKILL.md`](../../manage-config/SKILL.md) § "Workflow: Build Map" for the authoritative contract; this reference covers only the wizard/menu wiring.

## When the Build Map Is Seeded

The build map is **not** seeded at `init` or by `sync-defaults` — `get_default_config()` carries no `build_map` block. The wizard's Step 8b (`build-map seed`) is the **sole authoritative seed point**: it runs after the project architecture is discovered, because applicability scoping needs the discovered modules to decide which domains apply. Re-seeding after a domain extension is added or updated runs the same command. Because the default seed is write-once (an existing `build_map` block is never clobbered), an extension whose `classify_globs()` vocabulary changed after the project was first seeded will not have its new routes picked up by a plain re-seed — use `build-map seed --force` (below) to discard the existing block and re-derive a clean one.

The seed command is quoted verbatim from the `manage-config` canonical surface ([`../../manage-config/SKILL.md`](../../manage-config/SKILL.md) § "Seed the Build Map"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed
```

**Output (TOON)**:

```toon
status: success
action: seeded
domain_count: 2
build_map:
  python: [...]
  documentation: [...]
```

| `action` | Meaning |
|----------|---------|
| `seeded` | A missing `build_map` block was written from the applicable extensions' routes. |
| `preserved` | An existing `build_map` block was left untouched (write-once semantics). |
| `re-derived` | `--force` cleared an existing block and re-derived a clean one from current project state. |

`domain_count` is the number of applicable domains in the resulting block.

### Force a clean re-derivation

`build-map seed --force` bypasses the write-once guard — it clears any existing `build_map` and re-derives a clean one from the current project state (current extensions, current applicability against the discovered modules). Use it to discard stale or hand-edited entries, or to pick up changed `classify_globs()` routes that a plain re-seed would preserve over.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed --force
```

## Wizard Step: Seed the Build Map

Run after the project architecture is discovered (so both the extension set AND the module set are known) and after `marshal.json` is initialised. On a clean first run the block does not yet exist, so the seed reports `action: seeded` — surface the `domain_count` to the user.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed
```

Inspect `action` in the returned TOON:

- `action: seeded` → the block was newly written. Surface the `domain_count` to the user (the common first-run outcome, since this step is the first seed).
- `action: preserved` → an existing block was kept (a wizard re-run where the block was already seeded). No further action — run `build-map seed --force` if a clean re-derivation is needed.

## Inspect the Effective Build Map

To show the operator the map that `architecture derive-verification` reads when it stamps a task's verification commands, read the effective merged map:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map read
```

**Output (TOON)**:

```toon
status: success
build_map:
  python: [...]
  documentation: [...]
domain_count: 2
```

The read **fails closed**: when `skill_domains.build_map` is absent it returns a structured error rather than an empty map. A structural completeness validator (`git ls-files` scan) flags any tracked source file no declared route covers, so a forgotten production module surfaces rather than silently classifying to no build.

## Menu Mode: Re-Seed After an Extension Change

For re-seeding the build map after a domain extension is added or updated, the maintenance Project Structure submenu exposes a "Re-seed Build Map" operation. Because the default seed is write-once, a plain re-seed does NOT pick up changed routes for a block already present — the operator either corrects the seeded entries directly in `marshal.json`, or runs `build-map seed --force` to clear the existing block and re-derive a clean one from current project state (current extensions and applicability). A plain re-seed still picks up newly-added applicable domains the block did not yet have. The menu operation:

1. Runs `build-map seed` (or `build-map seed --force` for a clean re-derivation) and reports `action` (`seeded` / `preserved` / `re-derived`) plus `domain_count`.
2. Runs `build-map read` to display the effective map to the operator.
