# Health Check & Setup

Provider detection, tool verification, and configuration persistence.

## Workflow: Health Check

**Pattern**: Command Chain Execution

Detect CI provider and verify tools are available and authenticated.

### Step 1: Run Health Check

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health status
```

### Step 2: Process Result

```toon
status: success
provider: github
repo_url: https://github.com/org/repo
confidence: high
required_tool: gh
required_tool_ready: true
overall: healthy

tools[2]{name,installed,authenticated}:
git	true	true
gh	true	true
```

---

## Workflow: Detect Provider

**Pattern**: Command Chain Execution

Detect CI provider from git remote URL.

### Step 1: Run Detection

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health detect
```

### Step 2: Process Result

```toon
status: success
provider: github
repo_url: https://github.com/org/repo
confidence: high
```

---

## Workflow: Persist Configuration

**Pattern**: Command Chain Execution

Detect provider and persist to marshal.json with static commands.

### Step 1: Run Persist

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health persist
```

### Step 2: Process Result

```toon
status: success
persisted_to: marshal.json

ci_config{key,value}:
provider	github
repo_url	https://github.com/org/repo

ci_commands[19]{name,command}:
pr-create	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr create
pr-view	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr view
...
```

---

## Storage Pattern

**Split storage** (shared vs local):

| File | Content | Shared |
|------|---------|--------|
| `.plan/marshal.json` | `ci.provider`, `ci.repo_url`, `ci.commands` | Yes (git) |
| `.plan/run-configuration.json` | `ci.authenticated_tools`, command timeouts | No (local) |

---

## Tool Requirements

| Provider | CLI Tool | Auth Check |
|----------|----------|------------|
| github | `gh` | `gh auth status` |
| gitlab | `glab` | `glab auth status` |
