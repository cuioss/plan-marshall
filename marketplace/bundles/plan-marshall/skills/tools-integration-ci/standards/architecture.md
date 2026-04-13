# CI Operations Architecture

Architecture for CI operations using a provider-agnostic router pattern.

---

## Design Decision: Router Pattern for CI

CI operations use a **router pattern**: the `ci.py` router finds the CI provider from the `providers[]` array in marshal.json (matching known CI skill_name with bundle prefix, e.g., `plan-marshall:workflow-integration-github`) and delegates to the correct provider script (`github.py` or `gitlab.py`). Unlike build commands, CI has no per-module variation — one provider per repo, fixed operation set.

| Aspect | Build | CI |
|--------|-------|-----|
| **Per-module variation** | Yes (paths, profiles, goals) | No (project-global) |
| **Config stores** | Full command strings per module | Provider entry in `providers[]` array |
| **Resolution** | `architecture resolve --command X` | `ci.py` router finds CI entry by bundle-prefixed skill_name in `providers[]` |
| **Scripts** | `maven`, `gradle`, `npm` | `github`, `gitlab` |

**Caller pattern** (all skills use this):
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci {domain} {operation} [args]
```

**Benefits**:
- Provider-agnostic — same notation works for GitHub and GitLab
- No `eval` or `jq` needed in skill instructions
- Provider determined once during `/marshall-steward`, used transparently thereafter
- Uses unified provider model — CI provider stored alongside other providers in `providers[]`

---

## Skill Boundaries

### tools-integration-ci Skill Owns

| Responsibility | Description |
|----------------|-------------|
| Provider abstraction | Unified API across GitHub/GitLab |
| PR operations | Create, view, merge, reviews, comments |
| CI operations | Status, wait, rerun, logs |
| Issue operations | Create, view, close |
| Provider detection | Detect from git remote |
| Tool verification | Check CLI tools installed and authenticated |

### tools-integration-ci Skill Does NOT Own

| Responsibility | Owner |
|----------------|-------|
| Menu presentation | marshall-steward |
| User interaction | marshall-steward |
| Configuration storage | manage-config |
| Timeout management | run-config |
| Build commands | pm-dev-builder |

---

## Router Architecture

```
                    CI ROUTER PATTERN

    ┌─────────────────────────────────────────────────────────────┐
    │                      marshal.json                           │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │  "providers": [                                     │    │
    │  │    { "skill_name": "plan-marshall:w...-github",  │    │
    │  │      "category": "ci",                           │    │
    │  │      "verify_command": "gh auth status",         │    │
    │  │      "url": "https://api.github.com",            │    │
    │  │      "description": "GitHub CI provider..." }    │    │
    │  │  ]                                               │    │
    │  └─────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  ci.py finds      │
                    │  CI entry by name │
                    └─────────┬─────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌─────────────────┐             ┌─────────────────┐
    │   github.py     │             │   gitlab.py     │
    │   (gh CLI)      │             │   (glab CLI)    │
    └─────────────────┘             └─────────────────┘
```

---

## Scripts Per Provider

| Script | CLI Tool | Purpose |
|--------|----------|---------|
| `ci.py` | — | Provider-agnostic router |
| `ci_health.py` | git | Provider detection, tool verification |
| `github.py` | gh | GitHub operations |
| `gitlab.py` | glab | GitLab operations |

### Why Separate Scripts

| Aspect | Benefit |
|--------|---------|
| **Independence** | Each script handles one provider |
| **Maintainability** | Provider-specific logic isolated |
| **Testing** | Test each provider independently |
| **Router simplicity** | Just reads config and imports |

### Provider Skills

Each provider has its own skill with dedicated workflow scripts:

- `workflow-integration-github` — GitHub operations via `gh` CLI, PR review workflows
- `workflow-integration-gitlab` — GitLab operations via `glab` CLI, MR review workflows

### Provider Implementation Details

- [github-impl.md](github-impl.md) — GitHub-specific CLI mappings and field names
- [gitlab-impl.md](gitlab-impl.md) — GitLab-specific CLI mappings and field names

---

## Shared Infrastructure

All CI operations share:

| Component | Purpose |
|-----------|---------|
| **ci_base.py** | CLI runner, auth, parser, polling framework, elapsed computation |
| **Timeout handling** | `plan-marshall:manage-run-config` for adaptive timeouts |
| **Output format** | TOON for all script outputs |
| **Two-layer execution** | Outer Bash timeout + inner shell timeout |

See [wait-pattern.md](../../tools-script-executor/standards/wait-pattern.md) for the await_until polling utility.

---

## Wizard Responsibility

The steward wizard:

1. **Detects provider** via `ci_health detect`
2. **Verifies the CI tool** via `ci_health persist` (persists `authenticated_tools` to `run-configuration.json`; provider identity stays in `providers[]`)

Example wizard step:
```markdown
1. Call: `plan-marshall:tools-integration-ci:ci_health detect`
2. Present detected provider to user
3. Call: `plan-marshall:tools-integration-ci:ci_health persist`
   (verifies the required CI tool and writes authenticated_tools to run-configuration.json; the CI provider identity and repo URL are read at runtime from providers[] in marshal.json)
```

---

## Command Resolution

Callers use the provider-agnostic `ci` router script:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Feature X" --body "Description"
```

The router:
1. Finds the CI provider entry in the `providers[]` array by matching known bundle-prefixed CI skill_names (`plan-marshall:workflow-integration-github` or `plan-marshall:workflow-integration-gitlab`)
2. Imports the correct provider module (`github.py` or `gitlab.py`)
3. Passes all arguments through transparently

---

## Integration Points

### With marshall-steward

- Steward wizard calls `ci_health persist` to verify tools and write `run-configuration.json` authenticated_tools
- Steward health check calls `ci_health status`
- Steward does NOT contain CI detection logic

### With run-config

- CI operations use `run_config timeout get/set` for adaptive timeouts
- Particularly important for `ci wait` operations

### With plan-finalize

- Uses `ci` router for all CI operations during finalization
- Example: `plan-marshall:tools-integration-ci:ci pr create`

---

## Error Handling

All scripts follow the output contract:

| Condition | Exit Code | Stream |
|-----------|-----------|--------|
| Success | 0 | stdout |
| Error | 1 | stderr |

Error output format (TOON):
```toon
status: error
operation: pr_create
error: Authentication failed
context: gh auth status returned non-zero
```
