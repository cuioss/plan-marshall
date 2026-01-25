# Verification Steps

Defines the verification pipeline steps and their execution requirements.

## Step Types

| Type | Purpose | Can Block | Creates Tasks |
|------|---------|-----------|---------------|
| `build` | Build/compile verification | Yes | Yes |
| `quality` | Code quality checks | Yes | Yes |
| `test` | Test execution | Yes | Yes |
| `advisory` | Documentation, specs | No | No (logs only) |

## Default Pipeline

```
[quality_check] → [build_verify] → [technical_impl] →
[technical_test] → [doc_sync] → [formal_spec]
```

### Step 1: Quality Check

**Purpose**: Static analysis, linting, formatting

**Domain Commands**:

| Domain | Command |
|--------|---------|
| java | `./pw quality-gate {module}` |
| javascript | `npm run lint && npm run format:check` |
| plugin | `Skill: pm-plugin-development:plugin-doctor` |
| generic | Skip |

**Findings**:
- Lint errors/warnings
- Format violations
- Static analysis issues

### Step 2: Build Verify

**Purpose**: Compilation and basic build

**Domain Commands**:

| Domain | Command |
|--------|---------|
| java | `./pw compile {module}` |
| javascript | `npm run build` |
| plugin | Skip (no compilation) |
| generic | Skip |

**Findings**:
- Compilation errors
- Type errors
- Missing dependencies

### Step 3: Technical Implementation

**Purpose**: Domain-specific implementation checks

**Domain Commands**:

| Domain | Agent/Skill |
|--------|-------------|
| java | `pm-dev-java:java-verify-agent` |
| javascript | Domain standards check |
| plugin | Component validation |
| generic | Skip |

**Findings**:
- Standards violations
- Pattern mismatches
- Security issues

### Step 4: Technical Test

**Purpose**: Test execution and coverage

**Domain Commands**:

| Domain | Command |
|--------|---------|
| java | `./pw module-tests {module}` |
| javascript | `npm test` |
| plugin | `./pw module-tests {bundle}` |
| generic | Skip |

**Findings**:
- Test failures
- Coverage gaps

### Step 5: Doc Sync (Advisory)

**Purpose**: Documentation consistency check

**Command**:
```
Skill: pm-documents:ext-triage-docs
```

**Behavior**: Advisory only - logs findings but never blocks or creates tasks.

### Step 6: Formal Spec (Advisory)

**Purpose**: Specification drift detection

**Command**:
```
Skill: pm-requirements:ext-triage-reqs
```

**Behavior**: Advisory only - logs findings but never blocks or creates tasks.

---

## Step Execution Rules

### Blocking vs Advisory

**Blocking Steps** (1-4):
- Must pass for verify to succeed
- Create fix tasks on failure
- Can loop back to execute

**Advisory Steps** (5-6):
- Always run but never block
- Log findings for awareness
- No task creation

### Short-Circuit on Failure

If a blocking step fails:
1. Stop pipeline (don't run remaining steps)
2. Create fix tasks for findings
3. Loop back to execute phase

Exception: If `--full-scan` flag is set, run all blocking steps before creating tasks.

### Parallel Execution

Steps 1-4 are sequential by default.
Steps 5-6 run in parallel after blocking steps complete.

---

## Finding Categories

### Blocker (Must Fix)

- Compilation errors
- Test failures
- Security vulnerabilities (critical/high)

### Major (Should Fix)

- Lint errors
- Coverage below threshold
- Standards violations

### Minor (May Fix)

- Lint warnings
- Code smells
- Documentation gaps

### Advisory (Info Only)

- Suggestions
- Optimization opportunities
- Documentation notes

---

## Domain-Specific Thresholds

### Java

| Check | Threshold |
|-------|-----------|
| Coverage | 80% line |
| Complexity | 15 cyclomatic |
| Duplication | 3% |

### JavaScript

| Check | Threshold |
|-------|-----------|
| Coverage | 70% line |
| ESLint | 0 errors |
| TypeScript | strict mode |

### Plugin

| Check | Threshold |
|-------|-----------|
| Frontmatter | Valid YAML |
| References | All resolvable |
| Scripts | All pass mypy |
