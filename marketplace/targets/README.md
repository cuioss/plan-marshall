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
├── opencode/                     # OpenCode singular-layout emitter
│   ├── target.py                 # OpenCodeTarget(TargetBase)
│   ├── mapping.json              # Tool/model maps
│   └── frontmatter-rules.json
└── pr_agent/                     # PR-Agent per-domain instruction packs
    └── target.py                 # PrAgentTarget(TargetBase) + composition rules
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

    @property
    def emits_bundle_tree(self) -> bool: ...   # default True
```

`generate()` reads source bundles and writes the target's output. The
return value is the list of paths the target produced (or would produce —
validation-only modes may return an empty list).

Configuration is data-driven. Per-target rules live as JSON files inside
the target's own `config_dir/` so a mapping change is a JSON edit, not a
code edit. The `pr-agent` target is the one exception and states its reason
in its module docstring: a new `marketplace/targets/**/*.json` path is
claimed by no build extension and by no owner-less classifier rule, so it
would resolve to the `unknown` role bucket. Its composition rules are
module-level constants instead.

`emits_bundle_tree` declares whether the target's output directory is a
published bundle tree. The CLI applies two generic post-emit steps to every
output tree — the deterministic `0.1.N` version stamp over each bundle
`plugin.json`, and the `dist-manifest.json` at the output root — and both
are bundle-tree semantics. A target whose output is something else
overrides the property to `False` so those steps are skipped rather than
writing a wrong artifact; `--target all` reaches that path for every
registered target, so the gate is not optional.

## CLI Usage

```bash
# Verbatim Claude mirror + plugin.json regeneration
python3 marketplace/targets/generate.py --target claude --output target/claude

# Equality check only (no emit) — exits 2 if committed plugin.json drifts
python3 marketplace/targets/generate.py --target claude

# OpenCode emit
python3 marketplace/targets/generate.py --target opencode --output target/opencode

# PR-Agent reviewer pack → ./.pr_agent.toml at the repository root
python3 marketplace/targets/generate.py --target pr-agent --output .

# Every target at once (claude → target/claude/, opencode → target/opencode/,
# pr-agent → target/pr-agent/.pr_agent.toml)
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

The `pr-agent` target is the exception: its output is a **committed
configuration file**, not a build artifact. `.pr_agent.toml` is read by the
PR-Agent reviewer from the repository's default branch, so it must be
tracked in git. It is generated rather than hand-maintained — regenerate it
instead of editing it, and a regeneration must reproduce the committed file
byte-for-byte.

## PR-Agent target — per-domain instruction packs

The `pr-agent` target emits a reviewer configuration instead of an
assistant bundle tree: a `.pr_agent.toml` carrying exactly one composed
instruction pack under `[pr_reviewer].extra_instructions`. Every other key
— model, token budgets, output suppression — is inherited from the
organisation-wide `cuioss/pr-agent-settings` configuration, which is merged
beneath the repository-local file.

Two properties are load-bearing:

* **The domain set is derived, never hand-transcribed.** The target scans
  `marketplace/bundles/` for the per-domain standards skills —
  `*-security`, `arch-gate-*` and `ext-triage-*` — so a bundle added to the
  marketplace appears in the derived domain set with no code edit. Each
  pack carries the cross-cutting `plan-marshall:persona-security-expert`
  spine plus that domain's own rules, harvested from the domain security
  skill's `## Enforcement` block.
* **A repository carries exactly one pack, and swaps rather than
  accumulates.** Pack selection is an argument to the target; a run writes
  one `.pr_agent.toml`, replacing whatever pack was there before.

The composition is bounded and guarded. The category bullet list is capped
at ten entries (past roughly ten, the answer is a second focused pass, not
an eleventh bullet); the substantiation bar and the anti-fabrication clause
are carried verbatim into every pack; and withholding language — the
measured cause of five consecutive empty reviews — is dropped from any
harvested rule that carries it. `test/marketplace/targets/pr_agent/`
enforces those invariants across the whole derived pack population.

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
