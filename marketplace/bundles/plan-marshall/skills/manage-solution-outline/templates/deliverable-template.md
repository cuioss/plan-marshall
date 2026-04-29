# Deliverable Template

Mandatory template for each deliverable in solution_outline.md. **ALL fields are required.** No field may be omitted.

## Template

```markdown
### {N}. {Deliverable Title}

**Metadata:**
- change_type: {analysis|feature|enhancement|bug_fix|tech_debt|verification}
- execution_mode: {automated|manual|mixed}
- domain: {single domain from config.domains}
- module: {module name from architecture}
- depends: {none|N|N,M|N. Title}

**Intent gloss:** {one-sentence disambiguation of compound-word titles, max ~15 words — required when title head morpheme is a planning-domain verb (review, check, validate, approve, merge, …)}

**Profiles:**
- implementation
- {module_testing - only if this deliverable creates/modifies test files}

**Affected files:**
- `{explicit/path/to/file1.ext}`
- `{explicit/path/to/file2.ext}`

**Change per file:** {Specific description of what changes in these files}

**Verification:**
- Command: `{resolved compile command from architecture}`
- Criteria: {success criteria}

**Success Criteria:**
- {criterion 1}
- {criterion 2}
```

### Resolving Verification Commands

Query the architecture for the module's canonical commands **before** writing deliverables:

```bash
# For implementation profile verification:
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --module {module} --audit-plan-id {plan_id}

# For module_testing profile verification:
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command module-tests --module {module} --audit-plan-id {plan_id}
```

Use the returned `executable` value as the Verification Command. Both Command and Criteria are MANDATORY — do NOT omit.

## Field Requirements

| Field | Required | Notes |
|-------|----------|-------|
| `change_type` | Yes | One of: analysis, feature, enhancement, bug_fix, tech_debt, verification |
| `execution_mode` | Yes | One of: automated, manual, mixed |
| `domain` | Yes | Single value from `config.domains` |
| `module` | Yes | Module name from architecture |
| `depends` | Yes | Use `none` if no dependencies |
| `**Intent gloss:**` | Conditional | Required when title head morpheme is a planning-domain verb; ≤15 words |
| `**Profiles:**` | Yes | At least `implementation`; add `module_testing` only if deliverable creates/modifies test files |
| `**Affected files:**` | Yes | Explicit paths only - NO wildcards, NO "all files in..." |
| `**Change per file:**` | Yes | What specifically changes |
| `**Verification:**` | Yes | Command and Criteria - both required |
| `**Success Criteria:**` | Yes | At least one criterion |

## Invalid Patterns

These will cause validation failure:

| Pattern | Problem |
|---------|---------|
| `- All files in path/to/dir/` | Vague - enumerate explicitly |
| `- path/to/*.md` | Wildcard - enumerate explicitly |
| `- Command: manual review` | Not automatable |
| Missing `**Verification:**` section | Required section |
| Missing `**Profiles:**` section | Required section |
| Empty `**Profiles:**` block | Must have at least one profile |

> **Complete anti-patterns**: See `standards/solution-outline-standard.md` for the full list of invalid patterns.
