# marketplace/targets/

Build-time target framework. Reads source bundles from
`marketplace/bundles/` (Claude Code format, the source of truth) and emits
platform-specific artifacts.

## Architecture

```
marketplace/targets/
├── __init__.py           # TARGET_REGISTRY + register_target()
├── base.py               # TargetBase ABC
├── generate.py           # CLI entry point
├── claude/               # Verbatim mirror + always-generate plugin.json
│   └── target.py         # ClaudeTarget(TargetBase)
└── opencode/             # OpenCode singular-layout emitter
    ├── target.py         # OpenCodeTarget(TargetBase)
    ├── mapping.json      # Tool/model maps
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
