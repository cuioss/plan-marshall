# Script Standards

Supplementary script standards covering SKILL.md documentation requirements, shell scripts, and architectural rule enforcement.

For Python implementation patterns, testing, output contracts, and cross-skill integration, load the dedicated skill:

```
Skill: pm-plugin-development:plugin-script-architecture
```

That skill is the single source of truth for Python script development. This document covers only the topics not addressed there.

## Documentation Requirements in SKILL.md

All scripts MUST be documented in SKILL.md.

### Required Documentation

**For Each Script**:

1. **Purpose**: One-sentence description of what script does
2. **Input**: Parameters, types, formats
3. **Output**: Return format (typically TOON with schema)
4. **Usage**: Example invocation from workflow

**Template**:
```markdown
## External Resources

### Scripts (in scripts/)

**1. {script-name}.py**: Brief purpose statement
- **Input**: parameter1 (type), parameter2 (type)
- **Output**: TOON with {field_names}
- **Usage**:
  ```bash
  python3 .plan/execute-script.py {bundle}:{skill}:{script} {subcommand} --param1 {value1}
  ```
- **Example Output**:
  ```toon
  status: success
  field1: value
  field2: 123
  ```
```

## Shell Script Standards

### Stdlib-Only Requirement

**Allowed**:
- Standard Unix utilities (grep, sed, awk, find, cat, etc.)
- jq (widely available JSON processor) - documented exception
- Bash built-ins (if, for, while, functions, etc.)

**Prohibited**:
- External tools requiring installation (yq, xmllint, etc.)
- Language-specific tools (npm, pip, cargo) unless wrapper scripts

### Common Pitfalls

**Counting with `set -euo pipefail`**:

```bash
# FAIL WRONG (causes duplicate output or failures):
set -euo pipefail
COUNT=$(grep -c "pattern" file || echo "0")  # Fallback runs even on success

# PASS CORRECT:
set -euo pipefail
if [ -z "$VAR" ]; then
    COUNT=0
else
    COUNT=$(printf "%s" "$VAR" | wc -l)
fi
```

**Variable Construction — Newlines**:

```bash
# FAIL WRONG (literal string, not newline):
ITEMS="item1\nitem2"

# PASS CORRECT (actual newline):
ITEMS="item1"$'\n'"item2"
```

**JSON Building with Pipes**:

```bash
# FAIL WRONG (trailing newline breaks JSON):
echo "$VAR" | jq -Rs .

# PASS CORRECT (no trailing newline):
printf "%s" "$VAR" | jq -Rs .
```

**Frontmatter vs Content Analysis**:

Always separate frontmatter from body content to avoid false matches:

```bash
# Extract body only (skip frontmatter)
BODY=$(awk '/^---$/{if(++count==2) {getline; body=1}} body' "$FILE")
```

## Architectural Rule Enforcement

Scripts should validate architectural rules automatically:

- **Rule 6**: Agents cannot use Task tool
- **Rule 7**: Only maven-builder can use Maven
- **Pattern 22**: Agents must report to caller, not self-invoke

```python
def check_rule_6(content, component_type):
    """Agents CANNOT use Task tool."""
    if component_type != "agent":
        return None
    if "Task" in extract_tools(content):
        return {
            "rule": "Rule 6",
            "severity": "error",
            "message": "Agents cannot use Task tool"
        }
    return None
```
