# CI Operations Architecture

Architecture for unified CI operations using static routing pattern.

---

## Design Decision: Unified Static Routing

**All domains use static routing** - config stores full commands, wizard generates provider-specific paths.

| Domain | Config Example |
|--------|----------------|
| **Build** | `"test": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"test\""` |
| **CI** | `"pr-create": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr create"` |

**Benefits**:
- Single mental model across all domains
- Config shows exactly what runs
- Maximum transparency
- Full command customization possible
- No runtime routing logic needed

---

## Skill Boundaries

### tools-integration-ci Skill Owns

| Responsibility | Description |
|----------------|-------------|
| Provider abstraction | Unified API across GitHub/GitLab |
| PR operations | Create, reviews |
| CI operations | Status, wait |
| Issue operations | Create |
| Provider detection | Detect from git remote |
| Tool verification | Check CLI tools installed and authenticated |

### tools-integration-ci Skill Does NOT Own

| Responsibility | Owner |
|----------------|-------|
| Menu presentation | marshall-steward |
| User interaction | marshall-steward |
| Configuration storage | plan-marshall-config |
| Timeout management | run-config |
| Build commands | pm-dev-builder |

---

## Static Routing Architecture

```
                    UNIFIED STATIC ROUTING

    ┌─────────────────────────────────────────────────────────────┐
    │                      marshal.json                           │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │  "ci": {                                            │    │
    │  │    "provider": "github",                            │    │
    │  │    "repo_url": "https://github.com/org/repo",       │    │
    │  │    "commands": {                                    │    │
    │  │      "pr-create": "...tools-integration-ci:github pr create",│    │
    │  │      "ci-status": "...tools-integration-ci:github ci status" │    │
    │  │    }                                                │    │
    │  │  }                                                  │    │
    │  └─────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  Config stores    │
                    │  full commands    │
                    └─────────┬─────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     tools-integration-ci                           │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
    │  │  ci_health  │  │   github    │  │   gitlab    │          │
    │  │ (detection) │  │ (gh CLI)    │  │ (glab CLI)  │          │
    │  └─────────────┘  └─────────────┘  └─────────────┘          │
    └─────────────────────────────────────────────────────────────┘
```

---

## Scripts Per Provider

| Script | CLI Tool | Purpose |
|--------|----------|---------|
| `ci_health.py` | git | Provider detection, tool verification |
| `github.py` | gh | GitHub operations |
| `gitlab.py` | glab | GitLab operations |

### Why Separate Scripts

| Aspect | Benefit |
|--------|---------|
| **Independence** | Each script handles one provider |
| **Maintainability** | Provider-specific logic isolated |
| **Testing** | Test each provider independently |
| **No runtime routing** | Config determines which script runs |

---

## Shared Infrastructure

All CI operations share:

| Component | Purpose |
|-----------|---------|
| **Timeout handling** | `plan-marshall:run-config` for adaptive timeouts |
| **Output format** | TOON for all script outputs |
| **Two-layer execution** | Outer Bash timeout + inner shell timeout |

---

## Wizard Responsibility

The steward wizard:

1. **Detects provider** via `ci_health detect`
2. **Generates full commands** with correct script paths
3. **Stores in marshal.json** under `ci.commands`

Example wizard step:
```markdown
1. Call: `plan-marshall:tools-integration-ci:ci_health detect`
2. Present detected provider to user
3. Call: `plan-marshall:tools-integration-ci:ci_health persist`
   (generates ci.commands for detected provider)
```

---

## Command Resolution

Callers resolve commands from config:

```bash
# Step 1: Get command from config
COMMAND=$(jq -r '.ci.commands["pr-create"]' .plan/marshal.json)

# Step 2: Execute with arguments
eval "$COMMAND --title 'Feature X' --body 'Description'"
```

This pattern:
- Works with any provider (command already contains correct script)
- Allows user customization (edit marshal.json)
- Provides full transparency (config shows exact command)

---

## Comparison with Build Handling

Both CI and Build use the same static routing pattern:

| Aspect | Build | CI |
|--------|-------|-----|
| **Config stores** | Full command strings | Full command strings |
| **Scripts** | `maven`, `gradle`, `npm` | `github`, `gitlab` |
| **Flexibility** | Profiles, flags, goals | Provider-specific options |

---

## Integration Points

### With marshall-steward

- Steward wizard calls `ci_health persist` to generate commands
- Steward health check calls `ci_health status`
- Steward does NOT contain CI detection logic

### With run-config

- CI operations use `run_config timeout get/set` for adaptive timeouts
- Particularly important for `ci wait` operations

### With plan-finalize

- Uses config commands for CI operations during finalization
- Resolves `ci.commands["pr-create"]` for PR creation

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
