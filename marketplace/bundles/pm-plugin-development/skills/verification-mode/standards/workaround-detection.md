# Workaround Detection Standard

Structured approach to detecting, analyzing, and handling workarounds during verification mode.

## Overview

A workaround occurs when the intended method fails or is unavailable, and an alternative approach would be used instead. In verification mode, workarounds must be detected and approved before execution.

## Workaround Definition

**Workaround**: Any deviation from the documented or intended method to achieve the same goal through alternative means.

**Key Characteristics**:
- Achieves similar outcome
- Uses different path/method than documented
- May mask underlying issues
- Often introduced to "make it work"

## Workaround Categories

### Category 1: Path Workarounds

**What It Is**: Using alternative file paths when primary path fails.

**Examples**:
- Using absolute path instead of relative
- Using hardcoded path instead of resolved path
- Copying file instead of referencing original
- Using different directory structure

**Detection Signals**:
- Path resolution fails, then alternative tried
- Path contains hardcoded user directories
- Path differs from documented pattern

### Category 2: Method Workarounds

**What It Is**: Using different approach when intended method fails.

**Examples**:
- Using Bash grep instead of Grep tool
- Manual parsing instead of using parser script
- Direct file read instead of using skill
- Shell commands instead of dedicated tools

**Detection Signals**:
- About to use Bash for file operations
- Skipping skill invocation
- Implementing logic that exists in script

### Category 3: Skip Workarounds

**What It Is**: Skipping steps that fail instead of fixing them.

**Examples**:
- Skipping validation step
- Ignoring failed test
- Omitting configuration step
- Bypassing permission check

**Detection Signals**:
- Step marked as failed but continuing
- "Optional" interpretation of required step
- Missing expected outputs

### Category 4: Substitution Workarounds

**What It Is**: Substituting different component for intended one.

**Examples**:
- Using different skill than documented
- Calling different script
- Using different output format
- Applying different template

**Detection Signals**:
- Component reference differs from documentation
- Output format unexpected
- Different behavior than documented

## Detection Triggers

Before any of these actions, STOP and analyze:

| Trigger | Indicates |
|---------|-----------|
| "Let me try a different approach" | Method workaround |
| Using path different from documented | Path workaround |
| "This step is optional" (when not marked so) | Skip workaround |
| Using different tool than specified | Substitution workaround |
| Implementing inline what script should do | Method workaround |
| Hardcoding value that should be resolved | Path workaround |

## Analysis Template

Use this template for workaround analyses:

```markdown
## WORKAROUND DETECTED - Analysis Required

### Situation
[What triggered the workaround detection]

### Intended Method
- **Documentation**: [What documentation says to do]
- **Component**: [Which skill/script/tool to use]
- **Expected Flow**: [How it should work]

### Why Intended Method Failed
[Analysis of what prevented intended method]

### Proposed Workaround
- **Alternative**: [What would be done instead]
- **Approach**: [How workaround works]
- **Trade-offs**: [What is lost by using workaround]

### Workaround Assessment
| Aspect | Impact |
|--------|--------|
| Correctness | [Does it produce correct results?] |
| Maintainability | [Does it create technical debt?] |
| Reproducibility | [Will it work in other contexts?] |
| Documentation | [Does it match documented behavior?] |

### Root Cause
[Why does intended method not work?]

### Options
1. **Fix intended method**: [How to make documented approach work]
2. **Approve workaround**: [Use alternative, document deviation]
3. **Abort operation**: [Stop and investigate further]

### Recommendation
[Which option and why]

---
**Verification Mode Active** - Workaround requires explicit approval before execution.
```

## Workaround Policies

### Policy 1: No Silent Workarounds

Workarounds must NEVER be applied silently. User must be informed and approve.

### Policy 2: Document All Approved Workarounds

When user approves workaround:
1. Note the deviation
2. Record why it was necessary
3. Create issue/task to fix root cause

### Policy 3: Prefer Fixing to Working Around

The recommended path is usually to fix the intended method, not approve the workaround.

### Policy 4: Time-Bound Workarounds

If workaround is approved, it should be:
- Temporary until proper fix
- Tracked for resolution
- Documented with context

## Common Workaround Scenarios

### Scenario: Script Not Found

**Intended**: Use script from skill
**Workaround**: Implement logic inline
**Recommendation**: Create/fix the script

### Scenario: Skill Not Registered

**Intended**: Load skill for standards
**Workaround**: Read files directly
**Recommendation**: Register the skill properly

### Scenario: Path Resolution Fails

**Intended**: Use bundle:skill notation
**Workaround**: Use absolute path
**Recommendation**: Fix resolution mechanism

### Scenario: Output Format Mismatch

**Intended**: Parse structured output
**Workaround**: Manual string parsing
**Recommendation**: Fix output format or parser

## Red Flags

These workaround patterns indicate significant issues:

| Pattern | Concern |
|---------|---------|
| Multiple workarounds in one operation | Systemic problem |
| Same workaround repeatedly | Unfixed root cause |
| Workaround requires permissions | Security concern |
| Workaround changes data format | Integration risk |
| Workaround skips validation | Quality risk |

## Integration with Verification Mode

When verification mode detects potential workaround:

1. Load this standard: `Read standards/workaround-detection.md`
2. Identify workaround category
3. Analyze intended vs actual approach
4. Assess impact and trade-offs
5. Format output using template
6. Present to user and require explicit approval
7. If approved, document the deviation
