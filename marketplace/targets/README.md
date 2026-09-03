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
├── body_transform_engine.py      # Target-shared data-driven body rewrites
├── component_targets.py          # `targets:` frontmatter scope filter
├── fs_safety.py                  # Containment primitives for destructive emits
├── claude/                       # Verbatim mirror + plugin.json + marketplace.json
│   ├── __init__.py               # Registers ClaudeTarget
│   ├── target.py                 # ClaudeTarget(TargetBase) + removed-bundle prune
│   ├── emitter.py                # Verbatim bundle copy
│   ├── plugin_json_gen.py        # Per-bundle plugin.json regen
│   ├── marketplace_json_gen.py   # Top-level marketplace.json regen
│   ├── variant_emitter.py        # Per-level agent variant emission
│   ├── equality_check.py         # Source ↔ target drift detection
│   ├── source_fingerprint.py     # Worktree fingerprint for the staleness guard
│   ├── content_drift.py          # Live content-drift check engine
│   └── content_drift_cli.py      # CLI wrapper for the content-drift check
├── opencode/                     # OpenCode singular-layout emitter
│   ├── __init__.py               # Registers OpenCodeTarget
│   ├── target.py                 # OpenCodeTarget(TargetBase)
│   ├── emitter.py                # Singular-layout emit + stale-output prune
│   ├── frontmatter.py            # Frontmatter transform + fail-closed validation
│   ├── variant_emitter.py        # Per-level agent variant emission
│   ├── mapping.json              # Tool/model maps
│   └── frontmatter-rules.json
└── pr_agent/                     # PR-Agent per-domain instruction packs
    ├── __init__.py               # Registers PrAgentTarget
    └── target.py                 # PrAgentTarget(TargetBase) + derivation rules
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
`generate`, `generate-claude` and `generate-opencode` aliases in
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

# PR-Agent reviewer packs → target/pr-agent/packs/, one Markdown artifact per
# derived review domain plus spine.md. The run takes no selection argument: it
# emits the whole derived set, and a consumer selects from the published one.
# --bundles below does not narrow this target — it is ignored here.
./pw generate --target pr-agent --output target/pr-agent

# Every target at once (claude → target/claude/, opencode → target/opencode/,
# pr-agent → target/pr-agent/packs/)
./pw generate --target all --output target

# Scope to specific bundles (bundle-tree targets only — pr-agent ignores it)
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
6. **If the target emits a component tree, honour the per-component
   `targets:` scope.** Call
   `marketplace.targets.component_targets.emits_to(component_path, self.name)`
   (or `excluded_emission_roots(bundle_dir, self.name)` for a
   whole-bundle walk) from the emit path, and skip a component whose
   declaration omits this target — a skill's declaration takes its whole
   directory with it. A target whose output is not a component tree
   declares `emits_bundle_tree = False` and has nothing to filter.

   Step 6 is not optional and not self-enforcing: no shared code can apply
   the filter for a target, because only the target knows which paths it
   emits. `test/marketplace/targets/test_target_scoped_emission.py`
   generates through **every** registered component-tree target and asserts
   a scoped-out component is absent from its output, so a target that skips
   this step fails the suite rather than shipping components it was told
   not to.

## Output directories

`target/claude/` and `target/opencode/` are gitignored — they are build
artifacts, not committed sources. The `project:finalize-step-deploy-target` finalize
step emits `target/claude/` during the finalize phase; the
`/sync-plugin-cache` skill consumes that directory when syncing the
Claude plugin cache.

`target/pr-agent/packs/` is the same kind of output: a build artifact, not a
committed source. The repository tracks no generated reviewer configuration —
the artifact set is published to `cuioss/pr-agent-settings` by
`.github/workflows/pr-agent-packs-publish.yml` on merge to `main`, and a
consumer repository names a selection from that published set rather than
carrying a copy of it.

## PR-Agent target — per-domain instruction packs

The `pr-agent` target emits a reviewer artifact set instead of an assistant
bundle tree: one Markdown artifact per derived review domain under
`{output}/packs/`, plus `spine.md` carrying the cross-cutting review charter.
The artifacts are published to the organisation-wide
`cuioss/pr-agent-settings` repository, which is also where every other
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
observed organisation rule quoted in `pr-agent-settings`' README, not an
internal number this target may raise. The spine reserves one slot: it
carries at most nine category bullets, and each domain artifact contributes
exactly one. A single-domain assembly therefore lands exactly at the
ceiling; grouping the domain bullets of a multi-domain assembly back into
one is the consumer's obligation at assembly time, and no assembled pack
exists in this repository to prove it against. Rules are not categories and
are deliberately not governed by that ceiling — each domain artifact carries
its own per-domain rule cap.

`test/marketplace/targets/pr_agent/` enforces those invariants over the
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
"Registered Marketplace Path" section in the top-level `CLAUDE.md` for
the migration steps.
