# CI Operations Architecture

Architecture for CI operations using a provider-agnostic router pattern.

---

## Design Decision: Router Pattern for CI

CI operations use a **router pattern**: the `ci.py` router reads `ci.provider` from marshal.json and delegates to the correct provider script (`github.py` or `gitlab.py`). Unlike build commands, CI has no per-module variation — one provider per repo, fixed operation set.

| Aspect | Build | CI |
|--------|-------|-----|
| **Per-module variation** | Yes (paths, profiles, goals) | No (project-global) |
| **Config stores** | Full command strings per module | Provider name only |
| **Resolution** | `architecture resolve --command X` | `ci.py` router reads `ci.provider` |
| **Scripts** | `maven`, `gradle`, `npm` | `github`, `gitlab` |

**Caller pattern** (all skills use this):
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci {domain} {operation} [args]
```

**Benefits**:
- Provider-agnostic — same notation works for GitHub and GitLab
- No `eval` or `jq` needed in skill instructions
- Provider determined once during `/marshall-steward`, used transparently thereafter
- Minimal config — only `ci.provider` and `ci.repo_url` stored

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
    │  │  "ci": {                                            │    │
    │  │    "provider": "github",                            │    │
    │  │    "repo_url": "https://github.com/org/repo"        │    │
    │  │  }                                                  │    │
    │  └─────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  ci.py reads      │
                    │  ci.provider      │
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

---

## Shared Infrastructure

All CI operations share:

| Component | Purpose |
|-----------|---------|
| **Timeout handling** | `plan-marshall:manage-run-config` for adaptive timeouts |
| **Output format** | TOON for all script outputs |
| **Two-layer execution** | Outer Bash timeout + inner shell timeout |

---

## Wizard Responsibility

The steward wizard:

1. **Detects provider** via `ci_health detect`
2. **Persists provider** to marshal.json via `ci_health persist`

Example wizard step:
```markdown
1. Call: `plan-marshall:tools-integration-ci:ci_health detect`
2. Present detected provider to user
3. Call: `plan-marshall:tools-integration-ci:ci_health persist`
   (stores ci.provider and ci.repo_url)
```

---

## Command Resolution

Callers use the provider-agnostic `ci` router script:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Feature X" --body "Description"
```

The router:
1. Reads `ci.provider` from marshal.json
2. Imports the correct provider module (`github.py` or `gitlab.py`)
3. Passes all arguments through transparently

---

## Integration Points

### With marshall-steward

- Steward wizard calls `ci_health persist` to store provider
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
