# 04 — OpenCode developer inner loop (`sync-opencode`)

## Objective

Give a developer working on plan-marshall a fast edit → deploy → test loop on OpenCode,
analogous to the Claude `/sync-plugin-cache` loop. This requires a deploy skill that does
not exist yet.

## Current state

- **Claude inner loop: done.** Edit `marketplace/bundles/` → `/sync-plugin-cache` rsyncs
  `target/claude/` into `~/.claude/plugins/cache/plan-marshall/`. Documented in
  `doc/developer/marketplace-build.adoc`.
- **OpenCode inner loop: missing.** No `sync-opencode` skill and no `sync_opencode.py`
  exist anywhere under `marketplace/bundles/`.

The gap: OpenCode cannot read Claude source format, so the loop is two-phase — generate
`target/opencode/` (singular `skill/`/`agent/`/`command/` layout), then deploy it into a
location OpenCode discovers (plural `skills/`/`agents/`/`commands/`).

## Tasks

1. **`sync-opencode` skill + `sync_opencode.py`.** Create the skill under
   `marketplace/bundles/plan-marshall/skills/sync-opencode/` and register it. The script
   rsyncs (with `--delete`) `target/opencode/skill/` → `{target}/skills/`,
   `agent/` → `{target}/agents/`, `command/` → `{target}/commands/` — performing the
   singular→plural rename. Default `--target` is `~/.config/opencode/`; honour `--source`,
   `--target`, `--bundles`, `--dry-run`. Namespacing is `{bundle}-{skill}` (no consecutive
   `--`). Mirror the `sync-plugin-cache` engine shape.

2. **Decide whether this is meta-project-only.** `/sync-plugin-cache` is project-local
   under `.claude/skills/` because only this repo owns marketplace sources. `sync-opencode`
   has the same property — a consumer project never generates OpenCode output. Place it
   the same way (project-local), not in the shipped bundle, unless [02](02-validate-opencode-runtime.md)
   surfaces a reason to ship it.

3. **Document the three inner-loop options** (in the OpenCode developer doc from
   [05](05-opencode-documentation.md)):
   - **A — deploy to global** (`sync-opencode` into `~/.config/opencode/`): recommended
     for daily work; auto-discovered, ~3s/cycle.
   - **B — `OPENCODE_CONFIG_DIR`** pointed at a plural-renamed staging copy of
     `target/opencode/`: no global-config pollution. Spell out the precedence caveat —
     a committed project-local `.opencode/` shadows the env-var directory, and the env
     var cannot point directly at the singular `target/opencode/`.
   - **C — `opencode-marketplace install <local path>`**: validates the end-user path;
     slower; for distribution testing, not rapid iteration.

## Acceptance

- `sync-opencode` deploys a generated `target/opencode/` into a live OpenCode config with
  the singular→plural rename, tested by at least one developer.
- All three options are documented with the precedence caveat called out.
- Unit tests cover the path-rename mapping, `--dry-run`, and `--bundles` subset.

## Dependencies

- [02 — Validate the OpenCode runtime](02-validate-opencode-runtime.md) — the deploy loop
  is only useful once skills actually run on OpenCode. (02 may consume an early version of
  this deploy script for its own setup; that is fine — they can land together.)
