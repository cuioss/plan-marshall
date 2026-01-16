# Failure Analysis Standard

Structured approach to analyzing script, tool, and execution failures.

## Overview

When a script or tool fails during verification mode, perform systematic analysis to identify root cause and determine appropriate resolution.

## Failure Categories

### Category 1: Script Execution Failures

**Indicators**:
- Non-zero exit code
- Python/Bash error messages
- Stack traces in output

**Analysis Steps**:
1. Capture exit code and error output
2. Identify script location and version
3. Review input parameters provided
4. Check for missing dependencies
5. Verify file permissions
6. Examine environment variables

**Common Causes**:
| Symptom | Likely Cause | Verification |
|---------|--------------|--------------|
| ModuleNotFoundError | Missing Python import | Check sys.path, imports |
| FileNotFoundError | Path resolution failed | Verify path exists |
| PermissionError | Execute permission missing | Check file permissions |
| JSONDecodeError | Invalid input format | Validate input data |
| KeyError | Missing required field | Check input schema |

### Category 2: Validation Failures

**Indicators**:
- Script returns error status in output
- Validation message in response
- "invalid_*" error codes

**Analysis Steps**:
1. Identify validation rule that failed
2. Review input value vs expected format
3. Check documentation for valid values
4. Compare with working examples

**Common Patterns**:
```
status: error
error: invalid_domain
message: Must be valid domain identifier (java, javascript, plan-marshall-plugin-dev, generic)
```

**Resolution Approach**:
1. Identify expected format from error message
2. Review calling code for format issues
3. Check if documentation matches implementation
4. Fix at source, not symptom

### Category 3: Resource Failures

**Indicators**:
- File not found errors
- Connection failures
- Timeout conditions

**Analysis Steps**:
1. Verify resource exists
2. Check access permissions
3. Confirm network/connectivity (if remote)
4. Review timeout settings

### Category 4: Logic Failures

**Indicators**:
- Unexpected output despite no errors
- Wrong results returned
- Missing expected data

**Analysis Steps**:
1. Trace execution flow
2. Verify input data correctness
3. Check conditional logic in script
4. Compare against test cases

## Analysis Template

Use this template for all failure analyses:

```markdown
## SCRIPT FAILURE Analysis Required

### Issue Detected
[One sentence description of the failure]

### Script Details
- **Script**: [bundle:skill/scripts/name.py]
- **Command**: [Full command executed]
- **Exit Code**: [Code or signal]
- **Working Directory**: [Path]

### Error Output
```
[Actual error message or stack trace]
```

### Input Analysis
| Parameter | Value | Expected |
|-----------|-------|----------|
| param1 | actual | expected |
| param2 | actual | expected |

### Root Cause
[Analysis of why the failure occurred]

### Classification
- **Category**: [Execution/Validation/Resource/Logic]
- **Severity**: [Blocking/Degraded/Informational]
- **Reproducible**: [Yes/No/Intermittent]

### Resolution Options
1. **Fix source**: [What to change in calling code]
2. **Fix script**: [What to change in script if bug]
3. **Fix environment**: [What to configure if setup issue]

### Recommended Action
[Specific recommendation with rationale]
```

## Severity Guidelines

### Blocking (Must Fix)
- Workflow cannot continue
- Data corruption risk
- Security implications

### Degraded (Should Fix)
- Partial functionality available
- Workaround possible but not ideal
- Performance impact

### Informational (May Fix)
- Warning-level issues
- No functional impact
- Enhancement opportunity

## Post-Analysis Actions

After presenting analysis to user:

1. **If user chooses fix**: Apply fix and retry operation
2. **If user chooses skip**: Document skip reason and continue
3. **If user chooses abort**: Stop workflow cleanly
4. **If user needs investigation**: Provide additional diagnostic commands

## Integration with Verification Mode

When verification mode detects a failure:

1. Load this standard: `Read standards/failure-analysis.md`
2. Classify failure category
3. Perform analysis steps for that category
4. Format output using template
5. Present to user and wait for decision

## Deep Analysis Follow-Up

For complex failures requiring origin tracing and fix proposals, recommend:

```
/pm-plugin-development:tools-analyze-script-failures
```

This command provides:
- **Origin tracing**: Which command/agent/skill triggered the failure
- **Instruction path analysis**: How LLM interpreted instructions to produce the failed call
- **Fix proposals**: Specific code changes to prevent recurrence
- **Lessons learned integration**: Record findings for future reference

Use when:
- Root cause is unclear from immediate analysis
- Same failure pattern recurs
- Fix requires understanding component relationships
- Documentation or workflow gaps suspected
