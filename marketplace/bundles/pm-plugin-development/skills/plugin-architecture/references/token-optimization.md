# Token Optimization Strategies

Patterns for minimizing token usage in large-scale marketplace analysis workflows.

## Standards Pre-loading

### Problem

Analyzing 45 commands where each agent loads standards independently:
- 45 agents × 2 standards files × ~300 lines = 27,000 lines read redundantly
- Multiplied by token overhead = 75% wasted tokens

### Solution: Pre-load Once

```markdown
Step 3a: Load Analysis Standards (ONCE)

Read: standards/command-quality-standards.md
Read: standards/command-analysis-patterns.md

Store in memory for all agents.

Step 3b: Process Commands in Batches

For each batch of 5 commands:
  Task: diagnose-command
    prompt: |
      Analyze command X using pre-loaded standards from memory.
```

### Benefits

- **75% reduction** in standards loading overhead
- Standards guaranteed consistent across all agents
- Single point of maintenance

## Streamlined Output Format

### Problem

Full diagnostic reports from 45 agents create massive payloads:
```json
{
  "command_name": "foo",
  "line_count": 234,
  "classification": "ACCEPTABLE",
  "issues": [],
  "bloat_score": 0,
  "analysis": "No issues found. Command follows all quality standards...",
  "recommendations": []
}
```

Multiplied by 21 CLEAN commands = ~15KB of "everything is fine" messages.

### Solution: Issues-Only Format

```json
// CLEAN command (minimal)
{
  "status": "CLEAN",
  "command_name": "foo"
}

// Command with issues (full details)
{
  "status": "ISSUES",
  "command_name": "bar",
  "issues": [...],
  "line_count": 621,
  "classification": "BLOATED"
}
```

### Benefits

- **60% reduction** in result payload size
- Focus attention on problems only
- Faster parsing and aggregation

## Filtered Inventory

### Problem

Loading entire inventory (90 commands, 54 skills, 30 agents) when only analyzing one component type wastes tokens.

### Solution: Type-Filtered Inventory

```bash
# Use the scan-marketplace-inventory.sh script with filtering
Bash(./.claude/skills/cui-marketplace-architecture/scripts/scan-marketplace-inventory.sh --resource-types commands --output-format json)
# Returns only commands (45 items)

Bash(./.claude/skills/cui-marketplace-architecture/scripts/scan-marketplace-inventory.sh --resource-types skills --output-format json)
# Returns only skills (54 items)
```

### Benefits

- **50% reduction** for single-type analyses
- Faster inventory loading
- More relevant context

## Batch Size Optimization

### Token Budget Analysis

```
Total budget: 415K tokens
Agent cost: ~12K tokens per agent
Batch of 5: 10 agents (5 diagnosis + 5 validation)
Batch cost: ~120K tokens
Safe batches: 3-4 concurrent

Selected: Sequential batches of 5
Reason: Maximizes progress visibility while staying well within limits
```

### Adaptive Batching

**Pattern**: Adjust batch size based on component complexity

```
Simple commands (<200 lines): Batch size 10
Standard commands (200-400 lines): Batch size 5
Complex commands (>400 lines): Batch size 3
```

## Conditional Standards Loading

### Pattern: Load Only What's Needed

Instead of:
```markdown
Read: standards/quality-standards.md (always)
Read: standards/analysis-patterns.md (always)
Read: standards/fix-patterns.md (always)
Read: standards/architecture-rules.md (always)
```

Do:
```markdown
Read: standards/quality-standards.md (always - core)
If fixing_bloat:
  Read: standards/fix-patterns.md
If validating_architecture:
  Read: standards/architecture-rules.md
```

### Benefits

- Load only relevant standards for current task
- 30-40% reduction in context size
- Faster agent initialization

## Result Aggregation Efficiency

### Problem

Collecting 45 individual results requires 45 parsing operations and storage.

### Solution: Streaming Aggregation

```
Initialize counters:
  clean_count = 0
  bloated_count = 0
  issues_list = []

For each batch result:
  If status == CLEAN:
    clean_count += 1
  Else:
    bloated_count += 1
    issues_list.append(result)

Final report uses aggregated data only.
```

### Benefits

- Constant memory usage
- Real-time progress metrics
- No redundant storage

## References

* Related standards:
  - orchestration-patterns.md - Batch processing patterns
  - agent-coordination-patterns.md - Multi-agent coordination
  - result-aggregation-patterns.md - Result collection
