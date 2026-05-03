# Change Analysis — Generic Outline Instructions

Instructions for `analysis` change type. Handles investigation, research, and understanding requests. This type produces a committed findings document — no source code changes.

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
3. **Output location** — Where findings will be written
   Default: `doc/analysis/{investigation-topic}-findings.md`
   Ask user if they prefer a different location.
4. **Success criteria** — What questions need answering

Use appropriate tools:
- **Code analysis**: Use `architecture files --module X` / `architecture which-module --path P` for module-scoped discovery; fall back to Glob/Grep when narrowing to sub-module components, scanning content inside a known file, or when the architecture verb returns elision
- **Architecture**: Use Read to examine key files
- **External research**: Document findings from domain knowledge

Log scope:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Investigation scope: {target}, sources: {sources}, output: {output_path}"
```

## Deliverable Structure

Create a deliverable that produces a findings report as a committed file:

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

**Affected files:**
- `doc/analysis/{topic}-findings.md` (to be created)

**Change per file:**
- `{topic}-findings.md`: Create findings report covering {investigation questions}

**Verification:**
- Command: `test -f doc/analysis/{topic}-findings.md && wc -l doc/analysis/{topic}-findings.md`
- Criteria: File exists with substantive content (>20 lines)

**Success Criteria:**
- All investigation questions answered with evidence
- Recommendations are actionable
- Document committed to repository
```

## Guidelines

- Analysis only — do not propose source code changes in deliverables
- The findings document IS the deliverable — it must be a real file committed to the repository
- Provide evidence-based findings
- Document investigation methodology
- If user chose "analyze and implement fixes" in phase-2-refine, that request will have been reclassified to `enhancement` or `tech_debt` — it will not reach this template
