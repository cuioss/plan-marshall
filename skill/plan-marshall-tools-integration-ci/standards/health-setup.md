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

## Workflow: Live Verify

**Pattern**: Command Chain Execution

Detect provider and verify CI tools live — no persistence, since tool/auth status is cheap to check on demand and varies per machine.

### Step 1: Run verify-all

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health verify-all
```

### Step 2: Process Result

```toon
status: success
provider: github
repo_url: https://github.com/org/repo
authenticated_tools[1]:
- gh
git_present: true
```

---

## Storage Pattern

| File | Content | Shared |
|------|---------|--------|
| `.plan/marshal.json` | CI provider entry in `providers[]` array (`provider`, `repo_url`, `detected_at`) | Yes (git) |
| `.plan/run-configuration.json` | Command timeouts and learned warnings | No (local) |

CI tool authentication status is verified live via `ci_health verify-all` — not persisted. CI operations are resolved at runtime by the `ci.py` router which finds the system CI entry in the `providers[]` array of marshal.json and delegates to the correct provider script.

---

## Tool Requirements

| Provider | CLI Tool | Auth Check |
|----------|----------|------------|
| github | `gh` | `gh auth status` |
| gitlab | `glab` | `glab auth status` |
