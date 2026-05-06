# 05 — Distribution

## Objective

Design the complete distribution pipeline: how built artifacts reach end users, how users install plan-marshall into their AI assistant, and how updates are delivered.

## Scope

This cluster covers:
- CI/CD build and release automation
- Artifact hosting (GitHub Pages, GitHub Releases)
- End-user installation paths (Claude Code plugin mechanism, OpenCode plugin manager)
- Versioning and update strategy
- Installation documentation

This does NOT cover:
- Build system (see [02 — Build System](02-build-system))
- Target generation logic (see 02)
- Platform-runtime API (see [01 — Design Platform API](01-design-platform-api))
- Local developer deployment workflow (see [06 — Developer Workflow](06-developer-workflow))

---

## The Distribution Problem

plan-marshall is a **marketplace of skills, agents, and commands** for AI assistants. Unlike a traditional library distributed via npm/pip, it must integrate with the AI assistant's own plugin discovery mechanism. Each platform has different conventions:

| Platform | Discovery Mechanism | Installation Model | Update Model |
|----------|--------------------|--------------------|--------------|
| **Claude Code** | `marketplace.json` + bundle `plugin.json` | Claude plugin command from GitHub URL, or `git clone` | `git pull` in cloned repo |
| **OpenCode** | `~/.config/opencode/skills/`, npm plugins, git-based plugins | `opencode-marketplace install`, npm, git clone | `opencode-marketplace update`, npm update |
| **Cursor** | `.cursor/rules/`, `.cursor/skills/` | Manual copy | Manual update |
| **Future** | Unknown | Unknown | Unknown |

The challenge: produce artifacts in each platform's expected format, host them somewhere accessible, and document how users install them.

---

## Research: How Other Projects Distribute

### Claude Code Plugin Mechanism

Claude Code discovers plugins via **marketplace manifests** and **plugin manifests**. The marketplace manifest (`marketplace.json`) must live at `.claude-plugin/marketplace.json` at the **repository root** for Claude Code to auto-discover it when the marketplace is added.

#### Correct Directory Structure

Based on the Claude Code plugin specification and how other marketplaces (e.g., `TechDufus/oh-my-claude`, `mrlm-xyz/demo-claude-marketplace`) structure their repos:

```
plan-marshall/                           ← GitHub repo = marketplace root
├── .claude-plugin/
│   └── marketplace.json                 ← Marketplace manifest at REPO ROOT
├── marketplace/                         ← Source content directory
│   └── bundles/
│       ├── plan-marshall/
│       │   ├── .claude-plugin/
│       │   │   └── plugin.json          ← Bundle plugin manifest
│       │   ├── skills/
│       │   ├── agents/
│       │   └── commands/
│       ├── pm-dev-java/
│       │   ├── .claude-plugin/
│       │   │   └── plugin.json
│       │   └── skills/
│       └── ... (8 more bundles)
```

**Key rules from the spec:**
1. `marketplace.json` goes in `.claude-plugin/marketplace.json` at the **repo root** — NOT nested in a subdirectory
2. Each plugin (bundle) lives in its own subdirectory with `.claude-plugin/plugin.json`
3. `source` paths in `marketplace.json` are relative to the marketplace root (repo root)
4. `metadata.pluginRoot` can set a base prefix for shorter source paths

#### Current Structure Problem

plan-marshall currently places `marketplace.json` at `marketplace/.claude-plugin/marketplace.json`. This means:
- `/plugin marketplace add owner/repo` will NOT auto-discover it (Claude Code looks at repo root `.claude-plugin/marketplace.json`)
- Users must manually specify the full path: `/plugin marketplace add owner/repo/marketplace/.claude-plugin/marketplace.json`

**Fix required:** Move `marketplace/.claude-plugin/marketplace.json` to `.claude-plugin/marketplace.json` at repo root, and adjust source paths.

#### marketplace.json Structure

```json
{
  "name": "plan-marshall",
  "owner": {
    "name": "https://github.com/cuioss/plan-marshall"
  },
  "metadata": {
    "description": "Comprehensive marketplace of development standards...",
    "version": "0.1-BETA",
    "pluginRoot": "./marketplace/bundles"
  },
  "plugins": [
    {
      "name": "plan-marshall",
      "source": "./plan-marshall",
      "description": "..."
    },
    {
      "name": "pm-dev-java",
      "source": "./pm-dev-java",
      "description": "..."
    }
  ]
}
```

With `metadata.pluginRoot: "./marketplace/bundles"`, each `source: "./plan-marshall"` resolves to `./marketplace/bundles/plan-marshall`.

**Alternative (without pluginRoot):**
```json
{
  "plugins": [
    {
      "name": "plan-marshall",
      "source": "./marketplace/bundles/plan-marshall"
    }
  ]
}
```

#### How Other Marketplaces Structure Their Repos

| Marketplace | Structure | marketplace.json Location |
|-------------|-----------|---------------------------|
| `jmanhype/claude-code-plugin-marketplace` | `plugins/{name}/.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` at repo root |
| `mrlm-xyz/demo-claude-marketplace` | `claude-plugins/{name}/.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` at repo root |
| `TechDufus/oh-my-claude` | `plugins/{name}/.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` at repo root |

All follow the same pattern: marketplace manifest at repo root, plugins in subdirectories.

#### Installation

**Via Claude Code plugin command:**
```bash
claude plugin install https://github.com/{org}/plan-marshall.git
```

Claude Code:
1. Clones the repository
2. Discovers `.claude-plugin/marketplace.json` at repo root
3. Reads `metadata.pluginRoot` and resolves plugin source paths
4. Registers all 10 bundles

**Via `/plugin marketplace add`:**
```bash
/plugin marketplace add {org}/plan-marshall
```

This adds the marketplace catalog. Then users can browse and install individual bundles:
```bash
/plugin install plan-marshall
/plugin install pm-dev-java
```

**Update:**
```bash
claude plugin update plan-marshall
```

Or if the marketplace source was added:
```bash
/plugin marketplace update {org}/plan-marshall
```

#### No Build Artifact Needed

For Claude Code, the source format in `marketplace/bundles/` IS the runtime format. Claude Code reads markdown skills, agents, and commands directly from the bundle directories. No generation step required — the GitHub repo itself is the distribution artifact.

### OpenCode Ecosystem

OpenCode has multiple installation paths:

**1. npm plugins**
```json
{
  "plugin": ["opencode-helicone-session", "@my-org/custom-plugin"]
}
```
Installed automatically at startup via Bun. Requires publishing to npm registry.

**2. opencode-marketplace CLI**
```bash
bunx opencode-marketplace install https://github.com/user/repo
bunx opencode-marketplace update my-plugin
```
Conventions-based discovery. Supports git URLs, local directories, and subfolders.

**3. opencode-remote-config plugin**
```json
{
  "repositories": [
    {
      "url": "git@github.com:company/shared-skills.git",
      "ref": "main",
      "skills": { "include": ["code-review"] }
    }
  ]
}
```
Git-based sync with selective import, ref pinning, and change detection.

**4. Local copy/symlink**
```bash
cp -r target/opencode/skills/ ~/.config/opencode/skills/
```

**Analysis:** OpenCode's ecosystem is more mature for distribution than Claude Code. The `opencode-marketplace` CLI and `opencode-remote-config` plugin provide established patterns we should support.

### Similar Projects

| Project | Distribution | Notes |
|---------|-------------|-------|
| **Superpowers** (Claude Code workflow) | GitHub repo + manual clone | Users clone into `.claude/skills/` |
| **opencode-agent-skills** | npm package + git clone | Published to npm as `opencode-agent-skills` |
| **opencode-marketplace** | CLI tool | Not a plugin itself, but a distribution tool |
| **Cursor rules** | GitHub repos | Users copy `.cursor/rules/` from examples |

---

## Distribution Architecture

### Overview

```
Source (marketplace/bundles/)
    │
    ▼
Build System (02-build-system)
    │  ./pw generate -- --target {claude,opencode}
    ▼
GitHub Actions (this cluster)
    │  Build + test + package
    ▼
Artifact Hosting
    ├─ GitHub Releases (versioned tarballs)
    ├─ GitHub Pages (latest stable, installable URL)
    └─ npm registry (OpenCode npm plugin)
    │
    ▼
End User Installation
    ├─ Claude Code: plugin install from GitHub URL, or manual clone + discover
    ├─ OpenCode: opencode-marketplace install, npm, or git
    └─ Cursor: manual copy (future)
```

### Artifact Types

| Target | Artifact | Hosting | Consumption |
|--------|----------|---------|-------------|
| **Claude** | `marketplace/bundles/` (source is truth) | GitHub repo itself | `/plugin marketplace add {org}/{repo}` + `/plugin install` |
| **OpenCode** | `target/opencode/` directory (generated) | GitHub Pages + GitHub Releases | `opencode-marketplace install <pages-url>` |
| **Cursor** | `.cursor/` directory (future) | GitHub Pages + GitHub Releases | Manual copy |

**Key decision:** For Claude Code, the source format IS the runtime format. No build artifact needed — users clone the repo directly. For OpenCode, a build artifact IS needed because the format differs from source.

---

## CI/CD Pipeline

### Trigger

```yaml
on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### Jobs

#### Job 1: Build

```yaml
build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -e .
    
    - name: Generate OpenCode output
      run: |
        python marketplace/targets/generate.py --target opencode --output dist/opencode/
    
    - name: Generate Cursor output (future)
      run: |
        python marketplace/targets/generate.py --target cursor --output dist/cursor/
    
    - name: Package artifacts
      run: |
        tar czf dist/plan-marshall-opencode-${GITHUB_SHA}.tar.gz -C dist/opencode .
        tar czf dist/plan-marshall-cursor-${GITHUB_SHA}.tar.gz -C dist/cursor .
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v4
      with:
        name: target-artifacts
        path: dist/*.tar.gz
```

#### Job 2: Drift Check (Claude)

Same as 02's local validation, but run in CI:

```yaml
drift-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Check Claude drift
      run: |
        python marketplace/targets/generate.py --target claude
        # Exit 2 if drift detected
```

#### Job 3: Publish to GitHub Pages (on main push)

```yaml
publish-pages:
  needs: [build, drift-check]
  if: github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  permissions:
    contents: read
    pages: write
    id-token: write
  steps:
    - name: Download artifacts
      uses: actions/download-artifact@v4
      with:
        name: target-artifacts
    
    - name: Prepare Pages directory
      run: |
        mkdir -p _site/opencode/latest
        tar xzf dist/plan-marshall-opencode-*.tar.gz -C _site/opencode/latest
        cp docs/install.md _site/index.md
    
    - name: Upload to GitHub Pages
      uses: actions/upload-pages-artifact@v3
      with:
        path: _site
    
    - name: Deploy to GitHub Pages
      uses: actions/deploy-pages@v4
```

**GitHub Pages URL:** `https://{org}.github.io/{repo}/opencode/latest/`

This becomes the canonical URL for `opencode-marketplace install`.

#### Job 4: Publish GitHub Release (on tag)

```yaml
release:
  needs: [build, drift-check]
  if: startsWith(github.ref, 'refs/tags/v')
  runs-on: ubuntu-latest
  permissions:
    contents: write
  steps:
    - name: Download artifacts
      uses: actions/download-artifact@v4
    
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*.tar.gz
        body: |
          ## Installation
          
           ### Claude Code
           ```bash
           /plugin marketplace add {org}/plan-marshall
           /plugin install plan-marshall
           ```
           
           ### OpenCode
           ```bash
           opencode-marketplace install {pages-url}/opencode/{version}
           ```
```

---

## npm Package (OpenCode)

For OpenCode users who prefer npm over git-based installation:

### Package Structure

```
plan-marshall-opencode/
├── package.json
├── opencode.json
├── skills/
│   └── (all skills)
├── agents/
│   └── (all agents)
├── commands/
│   └── (all commands)
└── README.md
```

### package.json

```json
{
  "name": "plan-marshall-opencode",
  "version": "{version}",
  "description": "plan-marshall marketplace for OpenCode",
  "main": "opencode.json",
  "files": [
    "opencode.json",
    "skills/",
    "agents/",
    "commands/"
  ],
  "repository": {
    "type": "git",
    "url": "https://github.com/{org}/plan-marshall.git"
  },
  "keywords": ["opencode", "skills", "plan-marshall"],
  "license": "Apache-2.0"
}
```

### Publishing

```bash
# In CI, after build:
cd dist/opencode
npm publish --access public
```

**Note:** npm requires a build artifact. The source repo cannot be published directly because OpenCode expects a different directory layout than Claude Code.

---

## Versioning Strategy

### Schema

`{major}.{minor}.{patch}`

| Component | Meaning |
|-----------|---------|
| **Major** | Breaking change to skill API, removed skills, renamed bundles |
| **Minor** | New skills, new bundles, non-breaking additions |
| **Patch** | Bug fixes, documentation updates, drift corrections |

### Tag Format

`v{major}.{minor}.{patch}` — e.g., `v2.1.3`

### Release Cadence

| Type | Trigger | Action |
|------|---------|--------|
| **Patch** | Fix merged to main | Tag `v{current}.patch+1`, release |
| **Minor** | Feature complete | Tag `v{current}.minor+1.0`, release |
| **Major** | Breaking change planned | Tag `v{current}.major+1.0.0`, release notes |

### What Gets Versioned

The **entire marketplace** is versioned as a unit. Individual bundles do not have independent versions. This is because bundles have cross-dependencies (e.g., `plan-marshall` skills reference `pm-dev-java` skills).

**Rationale:** Independent versioning would require a dependency resolver. Single-version is simpler and matches how Claude Code's plugin cache works (one directory per marketplace).

---

## Installation Documentation

### Primary/Tested Paths

These are the installation methods we validate in CI and recommend to users.

#### Claude Code: `/plugin marketplace add` + `/plugin install`

```bash
# One-time: add the marketplace catalog
/plugin marketplace add {org}/plan-marshall

# Install all bundles
/plugin install plan-marshall

# Or install specific bundles
/plugin install pm-dev-java
/plugin install pm-dev-oci

# Update
/plugin marketplace update {org}/plan-marshall
```

Claude Code discovers `.claude-plugin/marketplace.json` at the repo root, reads `metadata.pluginRoot: "./marketplace/bundles"`, and registers all bundles.

#### OpenCode: `opencode-marketplace` CLI

```bash
# Install from GitHub Pages (build artifact)
opencode-marketplace install https://{org}.github.io/plan-marshall/opencode/latest/

# Update
opencode-marketplace update plan-marshall
```

Content-hash comparison avoids re-downloading unchanged files.

### Alternative Installation Methods

The following methods work but are **not tested in CI**. Documented for reference; users report issues via GitHub.

| Platform | Method | When to Use |
|----------|--------|-------------|
| Claude Code | `claude plugin install {repo-url}` | Direct install without marketplace catalog |
| Claude Code | `git clone` + manual discovery | Development, custom forks, air-gapped environments |
| OpenCode | `npm install -g plan-marshall-opencode` | Organizations with npm proxy/mirror |
| OpenCode | `opencode-remote-config` | Auto-sync on startup; ref pinning for stability |
| OpenCode | `OPENCODE_CONFIG_DIR` pointing to build output | Local development (see [06 — Developer Workflow](06-developer-workflow)) |

See `doc/distribution.md` (produced from this plan; see [04 — Validate and Document](04-validate-and-document)) for full alternative method instructions.

---

## Plugin Manager Integration

### opencode-marketplace

The `opencode-marketplace` CLI expects a directory with `skills/`, `agents/`, and `commands/` subdirectories.

**Our GitHub Pages output:**
```
https://{org}.github.io/plan-marshall/opencode/latest/
├── skills/
├── agents/
├── commands/
└── opencode.json
```

This matches the expected structure exactly.

### npm

npm packages need a `package.json` at the root. Our npm artifact:
```
plan-marshall-opencode-{version}.tar.gz
├── package.json
├── opencode.json
├── skills/
├── agents/
└── commands/
```

The `package.json` main field points to `opencode.json` so OpenCode's plugin loader can find the config.

---

## Hosting Options Comparison

| Host | Pros | Cons | Best For |
|------|------|------|----------|
| **GitHub Pages** | Free, versioned paths, custom domain, easy CI integration | Static only, no server-side logic | Primary host for OpenCode artifacts |
| **GitHub Releases** | Attached to git tags, automatic changelog, artifact storage | Manual download, no directory listing | Versioned tarballs, npm packages |
| **npm Registry** | Native OpenCode integration, semver, easy updates | Requires npm account, build artifact needed | OpenCode users who prefer npm |
| **Git Repo (source)** | No build needed for Claude, always latest | Requires git, manual clone | Claude Code users, developers |
| **jsDelivr CDN** | CDN edge caching, serves GitHub repos directly | Read-only, 24h cache delay | High-traffic installations |

**Recommendation:**
- **OpenCode Primary:** GitHub Pages (browsable, versioned, CI-driven)
- **OpenCode Secondary:** GitHub Releases for tarballs and npm packages
- **OpenCode Tertiary:** npm registry for npm plugin users
- **Claude Code:** GitHub repo itself (source format IS runtime format; no build or hosting needed)
  - Users install via `/plugin marketplace add {org}/{repo}` + `/plugin install`
  - Updates via `/plugin marketplace update {org}/{repo}`

---

## Update Strategy

### Claude Code (Primary)

```bash
/plugin marketplace update {org}/plan-marshall
```

### OpenCode (Primary)

```bash
opencode-marketplace update plan-marshall
```

Content-hash comparison avoids re-downloading unchanged files.

### Alternative Update Methods

| Platform | Method | Command |
|----------|--------|---------|
| Claude Code | `claude plugin update` | `claude plugin update plan-marshall` |
| Claude Code | Manual clone | `git pull origin main` |
| OpenCode | npm | `npm update -g plan-marshall-opencode` |
| OpenCode | opencode-remote-config | Restart OpenCode (auto-sync on startup) |
| OpenCode | Re-install from URL | `opencode-marketplace install {url}` |

---

## Verification

This cluster is complete when:
1. GitHub Actions workflow builds and publishes OpenCode artifacts on push to main
2. GitHub Pages hosts browsable `target/opencode/` output at a stable URL
3. GitHub Releases attach versioned tarballs to tags
4. npm package `plan-marshall-opencode` is published and installable
5. Installation documentation exists for both Claude Code and OpenCode
6. `opencode-marketplace install {pages-url}` succeeds and produces working skills
7. Update path is documented and tested
8. **Claude Code:** `.claude-plugin/marketplace.json` is at repo root with correct `source` paths
9. **Claude Code:** `/plugin marketplace add {org}/{repo}` discovers and registers all bundles
10. **Claude Code:** `/plugin install plan-marshall` installs all bundles
11. **Claude Code:** `/plugin marketplace update {org}/{repo}` updates successfully
12. **OpenCode:** `opencode-marketplace install {pages-url}` succeeds and produces working skills
13. **OpenCode:** `opencode-marketplace update plan-marshall` updates successfully

---

## Dependencies

- [02 — Build System](02-build-system) — must have the target generator working before CI can build artifacts
- Can be designed in parallel with 02, but CI integration requires 02 complete

---

## Risks

| Risk | Mitigation |
|------|------------|
| npm registry requires separate artifact maintenance | Automate in CI; fail build if `npm publish` fails |
| GitHub Pages cache delay (up to 10 min) | Document; users can use `jsDelivr` for immediate updates |
| OpenCode plugin format changes | Pin to OpenCode version in CI; test against latest stable |
| opencode-marketplace not widely adopted | Primary path tested in CI; alternatives documented for user choice |
| Cursor format unknown | Defer Cursor target until format stabilizes |

---

## Future Work

- **Cursor target:** When Cursor's skill/agent format is documented, add `cursor` target to the generator and publish `.cursor/` artifacts
- **MCP server:** Expose plan-marshall skills as MCP tools for any MCP-compatible client
- **Web UI:** A simple web page listing all skills with search and filter (hosted on GitHub Pages)
- **Semver resolver:** If independent bundle versioning becomes necessary, implement dependency resolution
