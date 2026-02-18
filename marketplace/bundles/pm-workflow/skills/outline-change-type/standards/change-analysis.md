# Change Analysis — Generic Outline Instructions

Instructions for `analysis` change type. Handles investigation, research, and understanding requests. This is a read-only type — no code changes.

## When Used

Requests with `change_type: analysis`:
- "Analyze why X is happening"
- "Investigate the root cause of Y"
- "Understand how Z works"
- "Research best practices for W"

## Discovery

Based on the request, determine:

1. **Investigation target** — What needs to be analyzed
2. **Information sources** — Where to look (code, logs, docs, external)
3. **Success criteria** — What questions need answering

Use appropriate tools:
- **Code analysis**: Use Glob/Grep to find relevant files
- **Architecture**: Use Read to examine key files
- **External research**: Document findings from domain knowledge

Log scope:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Investigation scope: {target}, sources: {sources}"
```

## Deliverable Structure

Create a deliverable that produces a findings report:

```markdown
### 1. Analyze: {Investigation Target}

**Metadata:**
- change_type: analysis
- execution_mode: automated
- domain: {domain}
- module: {module or "project-wide"}
- depends: none

**Profiles:**
- implementation

**Investigation:**
- Target: {what is being analyzed}
- Questions: {specific questions to answer}

**Affected files:**
- `{relevant/file/path1}`
- `{relevant/file/path2}`

**Change per file:**
- `{file1}`: Analyze for {specific aspect}
- `{file2}`: Analyze for {specific aspect}

**Verification:**
- Command: Review findings report for completeness
- Criteria: All investigation questions answered

**Success Criteria:**
- Investigation questions are answered
- Evidence is provided for conclusions
- Recommendations are actionable
```

## Guidelines

- Analysis only — do not propose code changes in deliverables
- Provide evidence-based findings
- Document investigation methodology
