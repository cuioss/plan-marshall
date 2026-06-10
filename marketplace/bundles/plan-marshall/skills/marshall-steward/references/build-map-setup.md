# Build Map Setup Reference

Extracted build-map seed logic for the wizard's Project Architecture step and the maintenance Project Structure submenu. Referenced by `wizard-flow.md` Step 8 and `menu-configuration.md` (Project Structure).

The `skill_domains.build_map` block in `marshal.json` is the file-to-build contract: a domain-keyed inventory of `{glob, role, build_class}` entries that maps every changed path to the build action it requires. The seed re-derives that block from every registered domain extension's `classify_globs()` + `classify_build_class()` predicates. The schema and the closed canonical-named `build_class` set are owned by `manage-config` — see [`../../manage-config/SKILL.md`](../../manage-config/SKILL.md) § "Workflow: Build Map" for the authoritative contract; this reference covers only the wizard/menu wiring.

## When the Build Map Is Seeded

The build map is **always** seeded automatically at `init` and `sync-defaults` — the wizard does not need to seed it manually on a clean first run. The explicit seed step exists for one reason: **re-seeding after a domain extension is added or updated**. Because the seed is write-once (an existing `build_map` block is never clobbered), an extension whose `classify_globs()` vocabulary changed after the project was first initialised will not have its new routes picked up until a re-seed runs.

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
| `seeded` | The `build_map` block was written from the registered extensions' routes. |
| `preserved` | An existing `build_map` block was left untouched (write-once semantics). |

`domain_count` is the number of domains in the resulting block.

## Wizard Step: Seed the Build Map

Run after the project architecture is discovered (so the extension set is known) and after `marshal.json` is initialised. On a clean first run `init` has already seeded the block, so the explicit seed reports `action: preserved` — that is the expected, non-error outcome.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed
```

Inspect `action` in the returned TOON:

- `action: seeded` → the block was newly written. Surface the `domain_count` to the user.
- `action: preserved` → an existing block was kept (the common first-run outcome, since `init` already seeded it). No further action.

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

For re-seeding the build map after a domain extension is added or updated, the maintenance Project Structure submenu exposes a "Re-seed Build Map" operation. Because the seed is write-once, re-seeding alone does NOT pick up changed routes for globs already present — the operator corrects the seeded entries directly in `marshal.json` when a route must change, and runs the seed to pick up newly-added domains. The menu operation:

1. Runs `build-map seed` and reports `action` (`seeded` / `preserved`) plus `domain_count`.
2. Runs `build-map read` to display the effective map to the operator.
