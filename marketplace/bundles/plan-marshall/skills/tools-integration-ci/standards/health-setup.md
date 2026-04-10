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

Detect provider and persist to marshal.json.

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
```

---

## Storage Pattern

**Split storage** (shared vs local):

| File | Content | Shared |
|------|---------|--------|
| `.plan/marshal.json` | CI provider entry in `providers[]` array (`provider`, `repo_url`, `detected_at`) | Yes (git) |
| `.plan/run-configuration.json` | `ci.authenticated_tools`, command timeouts | No (local) |

CI operations are resolved at runtime by the `ci.py` router which finds the system CI entry in the `providers[]` array of marshal.json and delegates to the correct provider script.

---

## Tool Requirements

| Provider | CLI Tool | Auth Check |
|----------|----------|------------|
| github | `gh` | `gh auth status` |
| gitlab | `glab` | `glab auth status` |
