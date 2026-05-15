# marketplace/targets/

Build-time target framework. Reads source bundles from
`marketplace/bundles/` (Claude Code format, the source of truth) and emits
platform-specific artifacts.

## Architecture

```
marketplace/targets/
├── __init__.py                   # TARGET_REGISTRY + register_target()
├── base.py                       # TargetBase ABC
├── generate.py                   # CLI entry point
├── claude/                       # Verbatim mirror + plugin.json + marketplace.json
│   ├── target.py                 # ClaudeTarget(TargetBase)
│   ├── emitter.py                # Verbatim bundle copy
│   ├── plugin_json_gen.py        # Per-bundle plugin.json regen
│   ├── marketplace_json_gen.py   # Top-level marketplace.json regen
│   ├── variant_emitter.py        # Per-level agent variant emission
│   └── equality_check.py         # Source ↔ target drift detection
└── opencode/                     # OpenCode singular-layout emitter
    ├── target.py                 # OpenCodeTarget(TargetBase)
    ├── mapping.json              # Tool/model maps
    └── frontmatter-rules.json
```

Each target lives in its own sub-package. The sub-package's `__init__.py`
calls `register_target('{name}', TargetClass)` to register itself in
`TARGET_REGISTRY`. The top-level `marketplace.targets` package imports the
sub-packages so registrations fire on first use.

## TargetBase Contract

Every target implements:

```python
class TargetBase(ABC):
    @property
    def name(self) -> str: ...

    def generate(
        self,
        marketplace_dir: Path,
        output_dir: Path,
        bundles: list[str] | None = None,
    ) -> list[Path]: ...

    def supports_agents(self) -> bool: ...
    def supports_commands(self) -> bool: ...

    @property
    def config_dir(self) -> Path: ...
```

`generate()` reads source bundles and writes the target's output. The
return value is the list of paths the target produced (or would produce —
validation-only modes may return an empty list).

Configuration is data-driven. Per-target rules live as JSON files inside
the target's own `config_dir/` so a mapping change is a JSON edit, not a
code edit.

## CLI Usage

```bash
# Verbatim Claude mirror + plugin.json regeneration
python3 marketplace/targets/generate.py --target claude --output target/claude

# Equality check only (no emit) — exits 2 if committed plugin.json drifts
python3 marketplace/targets/generate.py --target claude

# OpenCode emit
python3 marketplace/targets/generate.py --target opencode --output target/opencode

# Both targets at once (claude → target/claude/, opencode → target/opencode/)
python3 marketplace/targets/generate.py --target all --output target

# Scope to specific bundles
python3 marketplace/targets/generate.py --target opencode --output target/opencode \
    --bundles plan-marshall,pm-dev-java
```

The CLI exits `0` on success and `2` on any failure (unknown target,
missing flag, generator error, plugin.json drift, unmapped tool, etc.).

## Adding a New Target

1. Create a sub-package: `marketplace/targets/{name}/`.
2. Implement a `TargetBase` subclass in `{name}/target.py`.
3. In `{name}/__init__.py`, import the subclass and call:

   ```python
   from marketplace.targets import register_target
   from marketplace.targets.{name}.target import {Name}Target

   register_target('{name}', {Name}Target)
   ```

4. Add `from marketplace.targets import {name}` to
   `marketplace/targets/__init__.py` so the registration side-effect
   fires.
5. Add config files under `marketplace/targets/{name}/` and tests under
   `test/marketplace/targets/{name}/`.

## Output directories

`target/claude/` and `target/opencode/` are gitignored — they are build
artifacts, not committed sources. The `project:finalize-step-deploy-target` finalize
step emits `target/claude/` during the finalize phase; the
`/sync-plugin-cache` skill consumes that directory when syncing the
Claude plugin cache.

## Claude target — emitted artifacts

In addition to the per-bundle verbatim mirror, the Claude target emits two
regenerated JSON manifests:

* `target/claude/{bundle}/.claude-plugin/plugin.json` — per-bundle manifest
  produced by `plugin_json_gen.py`. The `agents` array expands role-eligible
  agents into per-level variants; the `commands` array reflects the bundle's
  on-disk command files; `skills` is intentionally emitted as `[]` because
  the Claude Code runtime's default `skills/` folder scan owns skill
  discovery, and declaring a `skills:` array ADDS to that scan rather than
  replacing it (declaring would double-load every skill).
* `target/claude/.claude-plugin/marketplace.json` — top-level manifest
  produced by `marketplace_json_gen.py`. Mirrors the source marketplace
  manifest verbatim except that each plugin's `source` is rewritten from
  the source `./bundles/{name}` layout to the flat target `./{name}` layout
  so `target/claude/` can be registered as a Claude Code marketplace.

The registered Claude Code marketplace MUST point at `target/claude/`, not
at the source `marketplace/` directory. The source only declares canonical
agent files; registering it skips the variant expansion and breaks every
dispatch site that resolves to `execution-context-{level}`. See the
"Registered Marketplace Path" section in the top-level `CLAUDE.md` for
the migration steps.
