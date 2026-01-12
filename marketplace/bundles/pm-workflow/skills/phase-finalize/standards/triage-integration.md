# Triage Integration

How the plan-finalize skill integrates domain-specific triage extensions for findings handling.

## Purpose

During verification (Step 2), the finalize skill may encounter various findings:
- Build errors and warnings
- Test failures
- Sonar issues (if CI enabled)
- PR review comments

Triage extensions provide **decision-making knowledge** for each domain to help determine whether to fix, suppress, or accept each finding.

## Extension Loading

### When to Load Triage Extensions

Load triage extensions when findings are detected during verification:

```
Verification runs → Findings detected → Load triage extensions → Apply decisions
```

### How to Load

For each domain in `config.toon.domains`:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain {domain} --type triage
```

**Output**:
```toon
status: success
domain: java
type: triage
extension: pm-dev-java:java-triage
```

If `extension` is `null`, no domain-specific triage is available - use default severity rules.

### Loading the Extension Skill

When extension is found:

```
Skill: {extension}
```

Example: `Skill: pm-dev-java:java-triage`

## Triage Decision Flow

### Step 1: Collect Findings

After running verification command, categorize findings by:

| Source | Examples |
|--------|----------|
| Build output | Compilation errors, warnings |
| Test output | Failed assertions, errors |
| Lint output | ESLint violations, Sonar issues |

### Step 2: Route to Domain

Determine domain for each finding:

| File Pattern | Domain |
|--------------|--------|
| `*.java` | java |
| `*.js`, `*.ts`, `*.tsx` | javascript |
| `*.py` (in marketplace/) | plan-marshall-plugin-dev |
| `*.md` (in marketplace/) | plan-marshall-plugin-dev |

### Step 3: Load Extension

Load triage extension for the finding's domain.

### Step 4: Apply Triage Knowledge

From the loaded triage skill, apply:

1. **Severity guidelines** - Determine action based on severity
2. **Suppression syntax** - If suppressing, use correct syntax
3. **Acceptable to accept** - Check if accepting is appropriate

### Step 5: Execute Decision

| Decision | Action |
|----------|--------|
| **Fix** | Create fix task or fix immediately |
| **Suppress** | Add appropriate suppression |
| **Accept** | Document and continue |

## Iteration Loop

```
While findings exist and iteration < MAX_ITERATIONS (5):
  1. Run verification
  2. Collect findings
  3. For each finding:
     a. Route to domain
     b. Load triage extension
     c. Apply triage knowledge
     d. Execute decision (fix/suppress/accept)
  4. If fixes or suppressions made:
     Continue loop (re-verify)
  5. If only accepts or no findings:
     Exit loop

If MAX_ITERATIONS reached:
  Accept remaining findings with documentation
```

## Example: Java Finding

**Finding**: Sonar BLOCKER - SQL Injection vulnerability

```
1. Domain: java (from *.java file)
2. Load: pm-dev-java:java-triage
3. Apply severity.md:
   - BLOCKER → Fix (mandatory)
4. Decision: FIX
5. Action: Fix the SQL injection issue
```

## Example: JavaScript Warning

**Finding**: ESLint warning - prefer-const

```
1. Domain: javascript (from *.js file)
2. Load: pm-dev-frontend:javascript-triage
3. Apply severity.md:
   - warn → Fix or suppress
4. Apply context: New code
5. Decision: FIX (low effort)
6. Action: Change let to const
```

## Example: Test Failure

**Finding**: Test failure - AssertionError in CacheTest.java

```
1. Domain: java (from *.java file)
2. Load: pm-dev-java:java-triage
3. Apply severity.md:
   - Test failure → Fix
4. Decision: FIX
5. Action: Fix test or code causing failure
```

## Triage Without Extension

If no triage extension exists for a domain, apply default rules:

| Severity | Action |
|----------|--------|
| BLOCKER/ERROR | Fix |
| CRITICAL | Fix |
| MAJOR/WARNING | Fix if low effort |
| MINOR/INFO | Accept |

## Configuration

### config.toon Fields

| Field | Description |
|-------|-------------|
| `domains` | List of domains (set during outline) |
| `verification_required` | Whether to run verification |
| `verification_command` | Command to run |

### marshal.json Configuration

```json
"java": {
  "workflow_skill_extensions": {
    "triage": "pm-dev-java:java-triage"
  }
}
```

## Logging

Log triage decisions to work-log:

```bash
python3 .plan/execute-script.py plan-marshall:logging:manage-log \
  work {plan_id} INFO "[TRIAGE] (pm-workflow:phase-finalize) {file}:{line} - {finding_type}: {decision} - {reason}"
```

## Related Documents

- [pm-workflow:plan-wf-skill-api/standards/triage-extension-contract.md](../../plan-wf-skill-api/standards/triage-extension-contract.md) - Extension contract
- [pm-workflow:plan-wf-skill-api/standards/extension-api.md](../../plan-wf-skill-api/standards/extension-api.md) - Extension API
- [pm-dev-java:java-triage](../../../pm-dev-java/skills/java-triage/SKILL.md) - Java triage
- [pm-dev-frontend:javascript-triage](../../../pm-dev-frontend/skills/javascript-triage/SKILL.md) - JavaScript triage
- [pm-plugin-development:plugin-triage](../../../pm-plugin-development/skills/plugin-triage/SKILL.md) - Plugin triage
