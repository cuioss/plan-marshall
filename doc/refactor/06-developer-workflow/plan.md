# 06 — Developer Workflow

## Objective

Define the inner development loop: how a developer working on plan-marshall tests their skill/agent/command changes in their local AI assistant before committing.

## Scope

This cluster covers the **local developer iteration cycle**:
- Edit a skill/agent/command in `marketplace/bundles/`
- Deploy the change to the local AI assistant
- Test the change in the AI assistant
- Iterate

This is distinct from:
- **02 — Build System**: The generator framework that produces target output
- **05 — Distribution**: CI/CD pipeline and end-user installation
- **03 — Refactor for Portability**: Structural changes to skills

---

## The Problem

plan-marshall is a source-only repository. The "runtime" is the AI assistant's plugin cache or discovery directory. To test a change, the developer must get their edited source into a form the AI assistant can load, then trigger a reload.

Each platform has different mechanisms:

| Platform | Source Format | Runtime Discovery | Reload Mechanism |
|----------|--------------|--------------------|------------------|
| **Claude Code** | Claude Code native (`marketplace/bundles/`) | `~/.claude/plugins/cache/` | `sync-plugin-cache` skill copies to cache |
| **OpenCode** | Generated OpenCode format (`target/opencode/`) | `~/.config/opencode/skills/` (global) or `OPENCODE_CONFIG_DIR` (custom) | `sync-opencode` script copies to global dir, or env var points to build output |

The challenge: Claude Code developers can edit-and-sync directly. OpenCode developers must generate first, then deploy.

---

## Claude Code Developer Workflow (Existing)

### How It Works

Claude Code's plugin cache is a directory snapshot. The existing `sync-plugin-cache` skill copies `marketplace/bundles/` to `~/.claude/plugins/cache/plan-marshall/`.

### Workflow

```bash
# 1. Edit source
vim marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md

# 2. Sync to Claude Code plugin cache
python3 .plan/execute-script.py plan-marshall:sync-plugin-cache:sync_cache

# 3. Test in Claude Code
#    - New session: skills load from cache automatically
#    - Existing session: restart Claude Code or use /sync-plugin-cache command
```

### What sync-plugin-cache Does

See `marketplace/bundles/plan-marshall/skills/sync-plugin-cache/SKILL.md` for the full contract. In brief:

- Source: `marketplace/bundles/` (in the working tree or a specified `--marketplace-root`)
- Destination: `~/.claude/plugins/cache/plan-marshall/`
- Method: `rsync --delete` for exact mirroring
- Scope: All 10 bundles, or `--bundles` for subset

### Iteration Speed

- **Fast**: Single skill edit → sync takes ~1 second → test immediately
- **No build step**: Source format IS runtime format
- **No restart needed**: New Claude Code sessions load from cache; existing sessions need restart

---

## OpenCode Developer Workflow (To Be Designed)

### The Challenge

OpenCode cannot consume Claude Code source format directly. The developer must:
1. Generate OpenCode output from source (using the 02 build system)
2. Deploy the generated output to a location OpenCode discovers
3. Iterate

### Why `.opencode/skills/` at Project Root Is Wrong

Generating to `.opencode/skills/` at the project root is **not a valid development path** because:
- `.opencode/skills/` may already contain committed project-local skills
- Mixing generated (ephemeral) and committed (source-controlled) skills creates confusion
- The project directory is for source code, not runtime artifacts

**The correct approach is to deploy to OpenCode's global user directory**, analogous to how `sync-plugin-cache` deploys to `~/.claude/plugins/cache/`.

### Research: How OpenCode Discovers Skills

OpenCode discovers skills from multiple locations in priority order:

| Priority | Location | Type | Notes |
|----------|----------|------|-------|
| 1 | `.opencode/skills/` | Project-local | Highest priority; may conflict with committed skills |
| 2 | `.claude/skills/` | Project-local | Claude compatibility |
| 3 | `~/.config/opencode/skills/` | **User-global** | **Recommended for development deployment** |
| 4 | `~/.claude/skills/` | User-global | Claude compatibility |
| 5 | `~/.claude/plugins/cache/` | Claude plugins | Cached Claude Code plugins |
| 6 | `~/.claude/plugins/marketplaces/` | Claude plugins | Installed from marketplace |

**Key insight:** `~/.config/opencode/skills/` is OpenCode's equivalent of Claude Code's `~/.claude/plugins/cache/`. This is the correct target for local development deployment.

### OpenCode Config Directory Override

OpenCode supports `OPENCODE_CONFIG_DIR` environment variable to point to a custom config directory:

```bash
OPENCODE_CONFIG_DIR=/path/to/custom/opencode opencode
```

This custom directory is searched for `skills/`, `agents/`, `commands/`, `plugins/` just like the standard `~/.config/opencode/` directory. It loads **after** global config and `.opencode` directories, so it can override them.

**Use case:** Point `OPENCODE_CONFIG_DIR` to the generated `target/opencode/` output directory. This avoids polluting the user's global `~/.config/opencode/skills/` and provides complete isolation.

### Recommended: Two-Phase Workflow (Generate + Deploy)

#### Phase 1: Generate

```bash
# Generate to a build output directory (NOT .opencode/ at project root)
./pw generate -- --target opencode --output target/opencode/
```

Output structure:
```
target/opencode/
├── skills/
│   └── plan-marshall-plan-marshall/
│       └── SKILL.md
│   └── pm-dev-java-java-core/
│       └── SKILL.md
│   └── ...
├── agents/
│   └── automated-review-agent.md
│   └── ...
├── commands/
│   └── tools-fix-intellij-diagnostics.md
│   └── ...
└── opencode.json
```

**Namespacing:** Skills are prefixed with bundle name to avoid collisions in the global directory (e.g., `plan-marshall-plan-marshall`, `pm-dev-java-java-core`). OpenCode skill names must not contain consecutive `--`.

#### Phase 2: Deploy (Choose One)

**Option A: Deploy to Global User Directory (Recommended for Daily Development)**

Copy generated skills to `~/.config/opencode/skills/` using a deployment script:

```bash
# Deploy script (to be created)
python3 marketplace/bundles/plan-marshall/skills/sync-opencode/scripts/sync_opencode.py \
  --source target/opencode/ \
  --target ~/.config/opencode/
```

**What the deploy script does:**
- Copies `skills/` → `~/.config/opencode/skills/`
- Copies `agents/` → `~/.config/opencode/agents/`
- Copies `commands/` → `~/.config/opencode/commands/`
- Uses `rsync --delete` for exact mirroring (same pattern as `sync-plugin-cache`)
- Namespaces skills to avoid collisions

**Pros:**
- Mirrors the existing `sync-plugin-cache` pattern
- OpenCode discovers automatically (no env var needed)
- Fast iteration: generate → deploy → test

**Cons:**
- Pollutes user's global OpenCode config
- Must be careful with namespacing to avoid overwriting other skills

**Option B: Use OPENCODE_CONFIG_DIR (Recommended for Isolated Development)**

Set the environment variable to point to the build output:

```bash
# Generate
./pw generate -- --target opencode --output target/opencode/

# Launch OpenCode with custom config directory
OPENCODE_CONFIG_DIR=/path/to/plan-marshall/target/opencode opencode
```

**Pros:**
- Complete isolation — no pollution of user-global config
- No copy step — OpenCode reads directly from build output
- Fastest iteration: generate → test (no deploy step)

**Cons:**
- Must remember to set env var every time
- May not discover user's other global skills (unless they are also in the custom dir)
- The custom config dir loads AFTER global config, so it overrides same-key settings from earlier configs

**Option C: opencode-marketplace with File URL (For Testing Distribution)**

```bash
# Generate
./pw generate -- --target opencode --output target/opencode/

# Install via marketplace CLI (tests end-user path)
opencode-marketplace install /path/to/plan-marshall/target/opencode/ --scope user
```

**Pros:**
- Validates the same path end users will take
- Content-hash tracking avoids redundant copies
- Uses official OpenCode tooling

**Cons:**
- Requires `opencode-marketplace` CLI installed
- Slower iteration (~5s per cycle)
- Not suitable for rapid development

### Recommended OpenCode Developer Workflow

**For daily development: Option A (Deploy to Global) or Option B (OPENCODE_CONFIG_DIR)**

```bash
# Setup (once)
git clone https://github.com/{org}/plan-marshall.git
cd plan-marshall

# Inner loop
vim marketplace/bundles/.../SKILL.md        # Edit source
./pw generate -- --target opencode          # Generate to target/opencode/

# Deploy and test (Option A - deploy to global)
python3 .plan/execute-script.py plan-marshall:sync-opencode:sync_opencode \
  --source target/opencode/ \
  --target ~/.config/opencode/
opencode                                      # Test (auto-discovers)

# OR deploy and test (Option B - isolated with env var)
OPENCODE_CONFIG_DIR=/path/to/plan-marshall/target/opencode opencode
```

### Deployment Script Design (`sync-opencode`)

Following the same pattern as `sync-plugin-cache`:

```python
# sync_opencode.py
# Source: target/opencode/
# Destination: ~/.config/opencode/ (or custom path via --target)

# Behavior:
# - rsync skills/ to ~/.config/opencode/skills/ (with namespace prefix)
# - rsync agents/ to ~/.config/opencode/agents/
# - rsync commands/ to ~/.config/opencode/commands/
# - --delete for exact mirroring
# --dry-run for preview
# --bundles for subset
```

**Namespacing convention:**
- Skills: `{bundle}-{skill}` directory name (e.g., `plan-marshall-plan-marshall`)
- This avoids collisions with other skills in the global directory
- OpenCode skill names must not contain consecutive `--`

---

## Comparison

| Aspect | Claude Code | OpenCode (Deploy to Global) | OpenCode (OPENCODE_CONFIG_DIR) |
|--------|-------------|---------------------------|-------------------------------|
| **Edit source** | `marketplace/bundles/` | `marketplace/bundles/` | `marketplace/bundles/` |
| **Build step** | None (source = runtime) | Generate to `target/opencode/` | Generate to `target/opencode/` |
| **Deploy step** | `sync-plugin-cache` to `~/.claude/plugins/cache/` | `sync-opencode` to `~/.config/opencode/` | None (env var points to build output) |
| **Reload** | New session or restart | Restart OpenCode | Restart OpenCode |
| **Iteration time** | ~1s (sync) | ~3s (generate + deploy) | ~2s (generate only) |
| **Isolation** | Shared cache | Shared global dir | Complete isolation |
| **Namespacing** | Bundle directory | `{bundle}-{skill}` prefix | Bundle directory |
| **Best for** | Rapid skill editing | Daily development | Isolated testing, CI |

---

## Verification

This cluster is complete when:
1. Claude Code: `sync-plugin-cache` workflow is documented and works
2. OpenCode: `sync-opencode` deploy script copies generated skills to `~/.config/opencode/skills/`
3. OpenCode: `OPENCODE_CONFIG_DIR` workflow (point to `target/opencode/`) works
4. OpenCode: `opencode-marketplace install file:///` workflow is documented
5. All workflows have been tested by at least one developer
6. README at repo root documents all workflows for contributors

---

## Dependencies

- [02 — Build System](02-build-system) — OpenCode workflow requires the generator to produce `target/opencode/`
- No dependency on 01, 03, 04, or 05

---

## Future Work

- **Watch mode**: `./pw generate -- --target opencode --watch` — auto-regenerate on source changes
- **Hot reload**: Investigate if OpenCode supports reloading skills without restart
- **opencode-marketplace publish --dry-run**: Validate the generated output before actual distribution
