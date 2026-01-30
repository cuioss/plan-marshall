# Triage Integration

Defines how domain-specific triage extensions integrate with the verify phase.

## Triage Extension Pattern

Each domain provides a triage extension skill:

```
{bundle}:ext-triage-{domain}
```

Examples:
- `pm-dev-java:ext-triage-java`
- `pm-dev-frontend:ext-triage-js`
- `pm-plugin-development:ext-triage-plugin`

## Loading Extensions

### Step 1: Get Domains from References

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

### Step 2: Resolve Extension for Each Domain

```
Skill: pm-workflow:workflow-extension-api
  resolve {domain} triage
```

Returns the skill name to load.

### Step 3: Load Extension

```
Skill: {resolved_skill_name}
```

---

## Finding Schema

Findings passed to triage extensions:

```toon
finding:
  id: finding-001
  source: quality_check
  rule: S1192
  file: src/main/java/Example.java
  line: 42
  message: String literal duplicated
  severity: major
  auto_fixable: true
  context:
    surrounding_code: "..."
    related_findings: [finding-002]
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique finding identifier |
| `source` | string | Verification step that found it |
| `rule` | string | Rule/check identifier |
| `file` | string | File path |
| `line` | int | Line number |
| `message` | string | Finding description |
| `severity` | enum | blocker, major, minor, advisory |
| `auto_fixable` | bool | Whether auto-fix is available |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `context` | object | Additional context |
| `fix_hint` | string | Suggestion for fixing |
| `related` | array | Related finding IDs |

---

## Triage Decisions

Extensions return one of three decisions:

### FIX

Create a fix task and loop back to execute.

```toon
decision: FIX
reason: Standards violation must be corrected
task_type: FIX
priority_boost: 0
```

### SUPPRESS

Add suppression and continue.

```toon
decision: SUPPRESS
reason: False positive in test code
suppression:
  type: annotation
  value: "@SuppressWarnings(\"S1192\")"
```

### ACCEPT

Log and continue without action.

```toon
decision: ACCEPT
reason: Acceptable technical debt
log_level: WARN
```

---

## Decision Factors

Triage extensions consider:

### 1. Severity

| Severity | Default Decision |
|----------|------------------|
| blocker | FIX |
| major | FIX or SUPPRESS |
| minor | SUPPRESS or ACCEPT |
| advisory | ACCEPT |

### 2. File Location

| Location | Bias |
|----------|------|
| Production code | FIX |
| Test code | SUPPRESS more lenient |
| Generated code | SUPPRESS always |
| Config files | Context-dependent |

### 3. Rule Type

| Rule Type | Bias |
|-----------|------|
| Security | Always FIX |
| Bug | Always FIX |
| Code smell | Context-dependent |
| Style | SUPPRESS if consistent |

### 4. Historical Context

Check lessons learned for previous decisions on similar findings.

---

## Fix Task Creation

When decision is FIX:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: Fix {finding.rule}: {finding.message}
deliverable: 0
domain: {domain}
profile: implementation
type: FIX
origin: fix
skills:
  - {domain_default_skill}
steps:
  - {finding.file}
verification:
  commands:
    - {verification_command}
  criteria: Finding {finding.id} resolved
description: |
  Fix finding from {finding.source}:

  Rule: {finding.rule}
  File: {finding.file}:{finding.line}
  Message: {finding.message}

  {finding.fix_hint if available}
EOF
```

---

## Suppression Types

### Annotation (Java)

```java
@SuppressWarnings("S1192")
```

### Comment (JavaScript)

```javascript
// eslint-disable-next-line rule-name
```

### Config (Various)

Add to .eslintrc, sonar-project.properties, etc.

---

## Iteration Loop

```
VERIFY
  ↓
[findings] → triage → [FIX decisions]
  ↓
Create fix tasks
  ↓
Transition to EXECUTE
  ↓
Execute fix tasks
  ↓
VERIFY (iteration + 1)
```

Max iterations: 5

After max iterations, remaining findings are reported for manual intervention.

---

## Logging

All triage decisions are logged:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(triage) {finding.id}: {decision} - {reason}"
```
