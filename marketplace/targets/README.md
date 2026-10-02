# marketplace/targets/

Build-time target framework. Reads source bundles from
`marketplace/bundles/` (Claude Code format, the source of truth) and emits
platform-specific artifacts.

## Architecture

The tree below is **exhaustive over the Python modules** in this package — a
module absent from it is a defect in the tree, not a module judged
unimportant. A tree that silently lists a subset reads as a map of the
package while being a map of whatever its last editor happened to touch, and
the modules it omitted were the shared ones a newcomer most needs to find.

```text
marketplace/targets/
├── __init__.py                   # TARGET_REGISTRY + register_target()
├── base.py                       # TargetBase ABC
├── generate.py                   # CLI entry point
├── sync.py                       # Single sync engine (claude/opencode/antigravity)
├── body_transform_engine.py      # Target-shared data-driven body rewrites
├── component_targets.py          # `targets:` frontmatter scope filter
├── fs_safety.py                  # Containment primitives for destructive emits
├── skill_identity.py             # Flat-target SKILL.md bundle/skill identity metadata
├── cuioss_review_bot/            # Reviewer per-domain instruction packs
│   ├── __init__.py               # Registers CuiossReviewBotTarget
│   └── target.py                 # CuiossReviewBotTarget(TargetBase) + derivation rules
├── claude/                       # Verbatim mirror + plugin.json + marketplace.json
│   ├── __init__.py               # Registers ClaudeTarget
│   ├── target.py                 # ClaudeTarget(TargetBase) + removed-bundle prune
│   ├── emitter.py                # Verbatim bundle copy
│   ├── plugin_json_gen.py        # Per-bundle plugin.json regen
│   ├── marketplace_json_gen.py   # Top-level marketplace.json regen
│   ├── variant_emitter.py        # Per-level agent variant emission
│   ├── equality_check.py         # Source ↔ target drift detection
│   ├── source_fingerprint.py     # Worktree fingerprint for the staleness guard
│   ├── cache_sync.py             # Plugin-cache sync + staleness guard (sync.py's claude path)
│   ├── reconcile_daemon.py       # marshalld reconcile after a cache version bump
│   ├── list_bundles_and_versions.py  # Bundle/version table of target/claude/
│   ├── content_drift.py          # Live content-drift check engine
│   └── content_drift_cli.py      # CLI wrapper for the content-drift check
├── antigravity/                  # Google Antigravity build target
│   ├── __init__.py               # Registers AntigravityTarget
│   ├── target.py                 # AntigravityTarget(TargetBase)
│   ├── emitter.py                # Plural-layout emit + plugin.json
│   ├── frontmatter.py            # Frontmatter transform + fail-closed validation
│   ├── variant_emitter.py        # Per-level agent variant emission
│   ├── mapping.json              # Tool/model maps
│   ├── frontmatter-rules.json
│   └── templates/
│       └── user-invocable-command.md
└── opencode/                     # OpenCode singular-layout emitter
    ├── __init__.py               # Registers OpenCodeTarget
    ├── target.py                 # OpenCodeTarget(TargetBase)
    ├── emitter.py                # Singular-layout emit + stale-output prune
    ├── frontmatter.py            # Frontmatter transform + fail-closed validation
    ├── variant_emitter.py        # Per-level agent variant emission
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

    @property
    def emits_bundle_tree(self) -> bool: ...  # default True
```

`generate()` reads source bundles and writes the target's output. The
return value is the list of paths the target produced (or would produce —
validation-only modes may return an empty list).

Configuration is data-driven. Per-target rules live as JSON files inside
the target's own `config_dir/` so a mapping change is a JSON edit, not a
code edit. The `cuioss-review-bot` target is the one exception and states its reason
in its module docstring: a new `marketplace/targets/**/*.json` path is
claimed by no build extension and by no owner-less classifier rule, so it
would resolve to the `unknown` role bucket. Its derivation rules are
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

The generator runs inside the project environment because it reads component
frontmatter with `yaml.safe_load` — `PyYAML` is a declared project dependency,
so a bare `python3 marketplace/targets/generate.py` fails with
`ModuleNotFoundError: No module named 'yaml'`. Always invoke it through the
`./pw` wrapper: `uv` is installed only into the project-local `.pyprojectx/`
tree and is not on `PATH`, so a bare `uv run …` exits 127 outside it. The
`generate`, `generate-claude`, `generate-opencode` and `generate-antigravity` aliases in
`pyproject.toml` are the invocation surface, and `generate` forwards whatever
arguments follow it. See `component_targets.py` for the frontmatter extraction
and the shape rules that module owns on top of the YAML load.


```bash
# Verbatim Claude mirror + plugin.json regeneration
./pw generate-claude

# Equality check only (no emit) — exits 2 if committed plugin.json drifts
./pw generate --target claude

# OpenCode emit
./pw generate-opencode

# Reviewer packs → target/cuioss-review-bot/packs/, one Markdown artifact per
# derived review domain plus spine.md. The run takes no selection argument: it
# emits the whole derived set, and a consumer selects from the published one.
# --bundles below does not narrow this target — it is ignored here.
./pw generate --target cuioss-review-bot --output target/cuioss-review-bot

# Every target at once (claude → target/claude/, opencode → target/opencode/,
# cuioss-review-bot → target/cuioss-review-bot/packs/)
./pw generate --target all --output target

# Scope to specific bundles (bundle-tree targets only — cuioss-review-bot ignores it)
./pw generate --target opencode --output target/opencode \
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
6. **If the target emits a component tree, honour the `targets:` scope.** Call
   `marketplace.targets.component_targets.emits_to(component_path, self.name)`
   (or `excluded_emission_roots(bundle_dir, self.name)` for a
   whole-bundle walk) from the emit path, and skip a component whose
   declaration omits this target — a skill's declaration takes its whole
   directory with it. A single `*.md` file *inside* a skill may carry its own
   file-level declaration that omits this target; the whole-bundle walk
   computes those exclusions too, so use it (or honour the file-level
   exclusions yourself) rather than filtering only via `emits_to`. A target
   whose output is not a component tree declares `emits_bundle_tree = False`
   and has nothing to filter.

   Step 6 is not optional and not self-enforcing: no shared code can apply
   the filter for a target, because only the target knows which paths it
   emits. `test/marketplace/targets/test_target_scoped_emission.py`
   generates through **every** registered component-tree target and asserts
   a scoped-out component is absent from its output (file-level exclusions
   included), so a target that skips this step fails the suite rather than
   shipping components it was told not to.
7. **If the target supports local developer deployment, register it with the sync engine (`sync.py`).**
   `marketplace/targets/sync.py` is the single engine that syncs a generated tree into a harness's local install; the `sync-harnesses` command of every harness runs it. A harness whose generated tree deploys as a component tree (as `opencode` and `antigravity` do) hooks in declaratively. The Claude target is the exception: its install is the versioned plugin cache, so its path is the rsync mirror in `marketplace/targets/claude/cache_sync.py` rather than a `TargetSyncConfig`.
   Add the target's name to `SYNC_TARGETS` and a `TargetSyncConfig` entry to `TARGET_CONFIGS` in `marketplace/targets/sync.py`:

   ```python
   TARGET_CONFIGS['{name}'] = TargetSyncConfig(
       name='{name}',
       default_dest=Path.home() / '.config' / '{name}',
       source_skills_dir='skills',  # or 'skill' if target generator outputs singular layout
       source_agents_dir='agents',  # or 'agent'
       source_commands_dir='commands',  # or 'command'
       root_assets=(
           ('plugin.json', 'config', False),
           ('install.sh', 'asset', True),  # (filename, kind, is_executable)
       ),
       extra_count_key='assets_count',  # or 'config_count'
   )
   ```

   The new harness is then reached by `--target {name}` and by every all-targets run. Add the `sync-harnesses` command file in the harness's own project-local command location, running `python3 marketplace/targets/sync.py $ARGUMENTS` like the existing three, and add unit tests under `test/sync-harnesses/`.

## Target Synchronization Engine (`sync.py`)

`marketplace/targets/sync.py` is the single sync engine. It deploys the generated trees (`target/{name}/`) of every harness — `claude`, `opencode` and `antigravity` — into that harness's local install location, with one shared, safe, and structured implementation.

### Architecture & Pipeline

```text
marketplace/bundles/  ──[ generator ]──>  target/{name}/  ──[ sync.py [--target {name}] ]──>  the harness's install location
```

The generator hop is `./pw generate-claude`, `./pw generate-opencode` or `./pw generate-antigravity`. `--target` is optional. Without it the engine syncs `claude`, `opencode` and `antigravity` in that fixed order, attempting each one even when an earlier one failed, and reports one aggregate result. With `--target {name}` it syncs exactly that harness.

| Target | Source | Destination | Implementation |
|--------|--------|-------------|----------------|
| `claude` | `target/claude/` | `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/`, plus `dist-manifest.json` at the cache root | `claude/cache_sync.py` — per-bundle rsync mirror behind a staleness guard |
| `opencode` | `target/opencode/` (singular layout) | `~/.config/opencode/` (plural layout) | `TargetSyncConfig` deploy |
| `antigravity` | `target/antigravity/` | `~/.gemini/config/plugins/plan-marshall/` | `TargetSyncConfig` deploy |

The engine is stdlib-only and runs under a bare `python3`. It loads `claude/cache_sync.py` by file location, never through the `marketplace.targets` package, whose `__init__` modules import third-party dependencies.

### The Claude path (`claude/`)

The Claude leg lives under `marketplace/targets/claude/`:

* `cache_sync.py` — mirrors each bundle of `target/claude/` into the versioned plugin cache. A staleness guard refuses a tree that is missing, empty, or behind `marketplace/bundles/`. The guard expects exactly the bundles whose `plugin.json` admits `claude` through its `targets` declaration, and it reports `guard_outcome: stale` (regenerate the tree) separately from `guard_outcome: probe_failed` (a probe could not run, so freshness is unknown).
* `reconcile_daemon.py` — reconciles a running `marshalld` after a Claude sync moved the cache version. It is run once the Claude target reports `status: success`.
* `list_bundles_and_versions.py` — prints the bundle/version table of `target/claude/`.

### The `sync-harnesses` command files

Each harness carries the same command in its own project-local location. All three are thin pointers that regenerate the selected targets, run the engine with their arguments passed through, and reconcile the build daemon when the Claude target synced:

| Harness | Command file |
|---------|--------------|
| Claude Code | `.claude/skills/sync-harnesses/SKILL.md` |
| OpenCode | `.opencode/commands/sync-harnesses.md` |
| Antigravity | `.agents/skills/sync-harnesses/SKILL.md` |

### Declarative Configuration (`TargetSyncConfig`)

Each component-tree target (`opencode`, `antigravity`) is registered in `TARGET_CONFIGS` with a `TargetSyncConfig` dataclass defining:
* `name`: The target key passed via `--target` (e.g., `'antigravity'`, `'opencode'`).
* `default_dest`: The target platform's default user/global installation path (e.g., `~/.gemini/config/plugins/plan-marshall` or `~/.config/opencode`). Can be overridden at runtime via `--target-dir`.
* `source_skills_dir`, `source_agents_dir`, `source_commands_dir`: Source directory names under `target/{name}/`. The engine normalizes both singular layouts (`skill/`, `agent/`, `command/`) and plural layouts (`skills/`, `agents/`, `commands/`) into the standard plural structure expected by target runtimes at destination.
* `root_assets`: A tuple of `(filename, kind, is_executable)` records for files copied directly to the destination root (e.g., descriptors like `plugin.json` or `opencode.json`, installers like `install.sh`, and documentation like `README.adoc`). Executable assets automatically preserve `0o755` permissions.
* `extra_count_key`: Output metric key for root assets in the TOON report (e.g., `assets_count` or `config_count`).

### Pruning Safety & Managed Boundaries

The sync engine enforces strict safety boundaries when pruning stale files:
* **Longest-Prefix Matching against Known Bundles**: Rather than naïve hyphen splitting, `_derive_synced_bundles()` reads the canonical bundle list from `marketplace/bundles/` and identifies managed components using longest-prefix matching. Multi-segment bundle names (e.g., `pm-dev-frontend-css` vs `pm-dev-frontend`) resolve strictly to their owning bundle.
* **Preservation of Unmanaged Assets**: User-created skills, third-party skills, and custom commands outside the synced bundles' prefixes are never touched or pruned.
* **Agent Preservation**: Subagent definition files (`agents/*.md`) are deployed into destination, but stale agent pruning is omitted to prevent deleting user-defined or runtime-discovered subagents.
* **Bundle Scoping (`--bundles`)**: When deployment is scoped to specific bundles (e.g., `--bundles pm-dev-java`), only components belonging to those bundles are pruned or updated. Components belonging to other managed bundles already present in destination remain completely untouched.

### Output Contract (TOON)

The sync engine serializes its execution report in compact TOON format using `toon_parser.serialize_toon`. The shape depends on the run.

A single-target `opencode` or `antigravity` run:
```text
status: success
target: antigravity
source: /path/to/target/antigravity
destination: /Users/.../.gemini/config/plugins/plan-marshall
skills_count: 53
agents_count: 10
commands_count: 1
assets_count: 3
deployed_count: 67
removed_count: 0
summary_message: "deployed 67 components, removed 0 stale entries to /Users/.../.gemini/config/plugins/plan-marshall"
```

When stale items are removed, a structured `removed` array is included:
```text
removed_count: 1
removed[1]{kind,name}:
  skills,plan-marshall-stale-skill
```

A single-target `claude` run:
```text
status: success | partial | error
synced_count: N
failed_count: M
summary_message: "<summary>"
guard_outcome: stale | probe_failed   # only on a staleness-guard refusal
synced[N]{bundle,version,status}:
failed[M]{bundle,error}:              # only when failed_count > 0
```

An all-targets run (no `--target`) emits one aggregate document: a `targets` table with one row per harness, followed by each harness's own result block.
```text
status: success | partial | error
targets[3]{target,status,summary_message}:
  claude,success,"..."
  opencode,success,"..."
  antigravity,error,"source not found: ..."
claude:
  <the claude result block>
opencode:
  <the opencode result block>
antigravity:
  <the antigravity result block>
```

The aggregate `status` is `success` only when every harness reported `success`, `partial` when some did, and `error` when none did.

### CLI Interface

The engine is invoked directly with the host interpreter; it has no `./pw` alias.

```bash
# Sync all three harnesses to their default install locations
python3 marketplace/targets/sync.py

# Sync one harness only
python3 marketplace/targets/sync.py --target antigravity

# Sync to a custom or staging directory (opencode / antigravity; requires --target)
python3 marketplace/targets/sync.py --target opencode --target-dir /tmp/opencode-test

# Dry-run preview: report what would be synced, write nothing
python3 marketplace/targets/sync.py --dry-run

# Restrict every selected target to a single bundle
python3 marketplace/targets/sync.py --target opencode --bundles plan-marshall

# Claude path: sync from another worktree's generated tree
python3 marketplace/targets/sync.py --target claude --from-worktree /path/to/worktree
```

`--source` and `--target-dir` are single-target overrides and require `--target`. `--from-worktree`, `--cache-root` and `--skip-staleness-guard` configure the Claude path only. `python3 marketplace/targets/sync.py --help` prints the authoritative flag set.

Exit codes: an all-targets run exits `0` on aggregate `success` and `1` on `partial` or `error`. `--target opencode` and `--target antigravity` exit `0` on `success` and `1` on `error`. `--target claude` exits `0` on `success` or `partial`, `1` on `error`, and `2` on a staleness-guard refusal. Rejected arguments exit `2`.

## Output directories

`target/claude/`, `target/opencode/`, and `target/antigravity/` are gitignored — they are build
artifacts, not committed sources. The `project:finalize-step-deploy-target` finalize
step emits all three during the finalize phase; the
`/sync-harnesses` command consumes those directories when syncing the
harness installs.

`target/cuioss-review-bot/packs/` is the same kind of output: a build artifact,
not a committed source. The repository tracks no generated reviewer
configuration — the artifact set is published to `cuioss/cuioss-review-bot` by
`.github/workflows/cuioss-review-bot-packs-publish.yml` on merge to `main`, and
a consumer repository names a selection from that published set rather than
carrying a copy of it.

## cuioss-review-bot target — per-domain instruction packs

The `cuioss-review-bot` target emits a reviewer artifact set instead of an
assistant bundle tree: one Markdown artifact per derived review domain under
`{output}/packs/`, plus `spine.md` carrying the cross-cutting review charter.
The artifacts are published to the organisation-wide
`cuioss/cuioss-review-bot` settings repository, which is also where every other
reviewer key — model, token budgets, output suppression — lives.

Three properties are load-bearing:

* **The domain set is derived, never hand-transcribed.** The target scans
  `marketplace/bundles/` for the per-domain standards skills —
  `*-security`, `arch-gate-*` and `ext-triage-*` — so a bundle added to the
  marketplace appears in the derived domain set with no code edit. A domain
  artifact carries that domain's own rules, harvested from the domain
  security skill's `## Enforcement` block.
* **The artifact set is orthogonal, and a repository composes by
  selecting.** Composition is not an act of this target: a domain artifact
  carries the domain part alone, and the cross-cutting charter appears
  exactly once, in `spine.md`. A repository that is several languages at
  once — this marketplace is both Python and marketplace-tooling — names
  several published artifacts instead of carrying one file that folds them
  together, so a charter change is published once rather than regenerated
  into every consumer.
* **A run emits the whole set, and the set stays equal to the derivation.**
  One artifact per derived domain plus the spine, and the generated header
  names the argument-free command that reproduces it. `--bundles` is accepted
  and ignored, which is what keeps `--target all --bundles X` working for the
  targets that do scope; and a generated artifact the current run did not
  write is pruned, so a domain that stops deriving does not survive in the
  output. The spine is emitted unconditionally on every run. Whether a consumer
  then applies it is not something this target enforces — no consumer of these
  artifacts exists yet — so each domain artifact's header asks for it and says
  what a lone domain artifact lacks without it.

The emission is bounded and guarded. The substantiation bar and the
anti-fabrication clause are carried verbatim into the **spine artifact** and
appear in no domain artifact; withholding language — the measured cause of
five consecutive empty reviews — is dropped from any harvested rule that
carries it.

**The category ceiling is a two-part budget, not a grouping.** The ten is an
observed organisation rule quoted in the `cuioss/cuioss-review-bot` documentation, not an
internal number this target may raise. The spine reserves one slot: it
carries at most nine category bullets, and each domain artifact contributes
exactly one. A single-domain assembly therefore lands exactly at the
ceiling; grouping the domain bullets of a multi-domain assembly back into
one is the consumer's obligation at assembly time, and no assembled pack
exists in this repository to prove it against. Rules are not categories and
are deliberately not governed by that ceiling — each domain artifact carries
its own per-domain rule cap.

`test/marketplace/targets/cuioss_review_bot/` enforces those invariants over the
emitted artifact set: one guard pins the emitted stems to the derived domain
set plus the spine, and a second pins each charter clause and each spine
category to `spine.md` and to nowhere else.

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
"Registered marketplace path" section in `doc/developer/marketplace-build.adoc`
for the migration steps.
