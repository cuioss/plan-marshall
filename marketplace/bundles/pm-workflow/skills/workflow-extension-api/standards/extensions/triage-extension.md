# Triage Extension Contract

Defines the structure and requirements for domain-specific triage extensions used during the finalize phase.

## Purpose

Triage extensions provide **decision-making knowledge** for handling findings during verification. They do NOT control workflow - the plan-finalize skill owns the workflow. Extensions provide domain-specific guidance for:

- How to suppress findings in that domain
- Severity guidelines for fix vs suppress vs accept decisions
- Situations where accepting a finding is appropriate

## Extension Loading

Triage extensions are loaded via the `workflow_skill_extensions.triage` field in marshal.json:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain java --type triage
```

**Output**:
```toon
status: success
domain: java
type: triage
extension: pm-dev-java:ext-triage-java
```

If no triage extension exists for a domain, `extension` returns `null`.

## Required Sections

Every triage extension MUST include these sections:

### 1. Suppression Syntax

Document how to suppress findings in this domain:

| Domain | Suppression Methods |
|--------|---------------------|
| Java | `@SuppressWarnings`, `// NOSONAR`, `@SuppressWarnings("all")` |
| JavaScript | `// eslint-disable-next-line`, `// @ts-ignore`, `// @ts-expect-error` |
| Python | `# noqa`, `# type: ignore`, `# pylint: disable=` |

**Required content**:
- Inline suppression syntax
- Block suppression syntax (if applicable)
- File-level suppression (if applicable)
- When each method is appropriate

### 2. Severity Guidelines

Document decision criteria based on finding severity:

| Severity | Default Action | Override Conditions |
|----------|----------------|---------------------|
| BLOCKER | Always fix | None - must be fixed |
| CRITICAL | Fix | Document exception required |
| MAJOR | Fix if reasonable | Suppress with documented reason |
| MINOR | Consider | Suppress if noisy or false positive |
| INFO | Accept | Fix if obvious improvement |

**Required content**:
- Severity-to-action mapping
- Override conditions
- Documentation requirements for suppressions

### 3. Acceptable to Accept

Document situations where accepting a finding (no fix, no suppress) is appropriate:

**Common acceptable situations**:
- Test code with intentional bad patterns (testing error handling)
- Generated code that will be regenerated
- Third-party code boundaries
- Legacy code with explicit tech debt tracking
- False positives that cannot be suppressed

**Required content**:
- List of acceptable situations
- Documentation requirements
- Tracking expectations (tech debt, issues)

## Triage Decision Flow

The plan-finalize skill uses triage extensions in this flow:

```
1. Run verification (build, test, lint, Sonar)
2. Collect findings from output
3. For each finding:
   a. Determine domain from file path/extension
   b. Load triage extension: resolve-workflow-skill-extension --domain {domain} --type triage
   c. If extension exists:
      - Load extension skill
      - Apply severity guidelines
      - Apply suppression rules if needed
   d. If no extension:
      - Use default severity mapping
   e. Decide: fix | suppress | accept
4. Apply fixes and suppressions
5. If changes made, re-run verification (iterate)
6. When all findings resolved, commit and create PR
```

## Example Triage Extension Structure

```
pm-dev-java/skills/java-triage/
├── SKILL.md                    # Extension definition
└── standards/
    ├── suppression.md          # Java suppression syntax
    └── severity.md             # Java severity guidelines
```

**SKILL.md template**:

```markdown
---
name: java-triage
description: Triage extension for Java findings during plan-finalize
allowed-tools: Read
---

# Java Triage Extension

Provides decision-making knowledge for triaging Java findings.

## Purpose

Loaded by plan-finalize when processing Java-related findings.
Provides domain-specific suppression syntax and severity guidelines.

## Standards

| Document | Purpose |
|----------|---------|
| suppression.md | @SuppressWarnings, NOSONAR, Sonar annotations |
| severity.md | Java-specific severity guidelines |

## Extension Registration

Registered in marshal.json:
\`\`\`json
"java": {
  "workflow_skill_extensions": {
    "triage": "pm-dev-java:ext-triage-java"
  }
}
\`\`\`
```

## Integration with Lessons Learned

Triage decisions can be informed by lessons learned:

1. Before deciding, query lessons for similar findings
2. If lesson exists with prior decision, apply learned action
3. If new situation, make decision and optionally record lesson
4. Lessons are stored per domain for context-aware decisions

See: [phase-5-finalize-contract.md](phase-5-finalize-contract.md) for lessons integration details.

## Validation Checklist

Triage extensions MUST:

- [ ] Include suppression syntax section
- [ ] Include severity guidelines section
- [ ] Include acceptable-to-accept section
- [ ] Be registered in marshal.json under `workflow_skill_extensions.triage`
- [ ] Use `allowed-tools: Read` (reference skill, no writes)
- [ ] Follow Pattern 10 (Reference Library) from plugin-architecture
