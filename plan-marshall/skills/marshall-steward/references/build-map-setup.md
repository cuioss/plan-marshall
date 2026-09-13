# Build Map Setup Reference

Extracted build-map seed logic for the wizard's Project Architecture step and the maintenance Project Structure submenu. Referenced by `wizard-flow.md` Step 8 and `menu-configuration.md` (Project Structure).

The `build.map` block in `marshal.json` is the file-to-build contract: a domain-keyed inventory of `{glob, role, build_class}` entries that maps every changed path to the build action it requires. The seed re-derives that block from every *applicable* registered domain extension's `classify_globs()` + `classify_build_class()` predicates. A domain is *applicable* only when its owning extension's `applies_to_module()` reports `applicable: True` for at least one discovered project module, so a Python-only project never receives `java` / `oci` / `javascript` routes. The schema, the applicability-scoping rule, and the closed canonical-named `build_class` set are owned by `manage-config` — see [`../../manage-config/SKILL.md`](../../manage-config/SKILL.md) § "Workflow: Build Map" for the authoritative contract; this reference covers only the wizard/menu wiring.

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

### Detect drift without re-seeding

`build-map seed --force` is the *write* path; `build-map drift` is the read-only *detection* path that tells the operator whether a re-seed is even warranted. The verb diffs the persisted `build.map` against the live derivation and returns `in_sync` plus per-domain `added_globs` / `removed_globs`, never mutating `marshal.json`. The steward's re-run remediation pass (below) consumes it to gate an interactive re-seed, so `--force` is no longer the only way a stale persisted map gets surfaced — a deliberate hand-edit is preserved unless the operator explicitly accepts the re-seed.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map drift
```

**Output (TOON)**:

```toon
status: success
in_sync: false
drift:
  python:
    added_globs: [...]
    removed_globs: [...]
```

`in_sync: true` means the persisted map matches the derivation (no prompt warranted); `in_sync: false` carries the added/removed-glob diff the steward displays before prompting.

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

The read **fails closed**: when `build.map` is absent it returns a structured error rather than an empty map. A structural completeness validator (`git ls-files` scan) flags any tracked source file no declared route covers, so a forgotten production module surfaces rather than silently classifying to no build.

## Worktree Executor-Gen: `.plan/local` Refuse-or-Scaffold Requirement

When the wizard runs inside a git worktree (a checkout under `.plan/local/worktrees/`), the executor it generates anchors its script mappings to the worktree via `generate_executor --marketplace-root <REPO_ROOT>`. That generation MUST NOT proceed until the worktree owns its own `.plan/local` directory: without it, `generate_executor` climbs to the **main** checkout's `.plan/local` (the nearest ancestor that has one) and overwrites main's `.plan/execute-script.py`, contaminating the main checkout.

The steward enforces this with a refuse-or-scaffold guard (`determine_mode.py check-worktree-plan-local --repo-root <REPO_ROOT> [--scaffold]`, wired into `wizard-flow.md` Step 4):

- `--scaffold` (the wizard default) creates the missing `<REPO_ROOT>/.plan/local` and proceeds (`status: scaffolded`).
- Without `--scaffold`, a worktree lacking `.plan/local` returns `status: refuse` and generation is aborted.

The working manual workaround when the guard refuses is to create the directory before re-running:

```bash
mkdir -p <REPO_ROOT>/.plan/local
```

For the main checkout (`REPO_ROOT` not under `.plan/local/worktrees/`), the guard is a no-op (`status: ok`) — it governs worktree generation only.

## Menu Mode: Re-Seed After an Extension Change

For re-seeding the build map after a domain extension is added or updated, the maintenance Project Structure submenu exposes a "Re-seed Build Map" operation. Because the default seed is write-once, a plain re-seed does NOT pick up changed routes for a block already present — the operator either corrects the seeded entries directly in `marshal.json`, or runs `build-map seed --force` to clear the existing block and re-derive a clean one from current project state (current extensions and applicability). A plain re-seed still picks up newly-added applicable domains the block did not yet have. The menu operation:

1. Runs `build-map seed` (or `build-map seed --force` for a clean re-derivation) and reports `action` (`seeded` / `preserved` / `re-derived`) plus `domain_count`.
2. Runs `build-map read` to display the effective map to the operator.

### Interactive Drift Gate at Menu-Mode Entry

Beyond the explicit menu operation above, the steward runs an automatic `build.map` drift gate at **menu-mode entry**, before the Main Menu, as part of its re-run remediation pass (see [`../SKILL.md`](../SKILL.md) § "Re-Run Remediation Pass"). The gate is the operator-friendly counterpart to `--force`:

1. Run `build-map drift` (read-only). If `in_sync: true`, continue silently — no prompt.
2. If `in_sync: false`, display the added/removed-glob diff and raise a Y/N `AskUserQuestion`:
   - **Yes** → run `build-map seed --force` to re-seed from the live derivation.
   - **No** → leave the persisted `build.map` untouched, preserving deliberate hand-edits.

This gate means a stale persisted map is surfaced for re-seed without the operator having to remember to run `--force` manually, while still never clobbering a hand-edited block without explicit consent.
