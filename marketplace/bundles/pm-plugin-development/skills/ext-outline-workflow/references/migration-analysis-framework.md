# Migration Analysis Framework

Evidence-based classification for migration requests (change_type: tech_debt with migration pattern). Distinguishes files that need migration from files already in target format.

**Reference**: Based on Google's LLM migration system (FSE 2025) and OpenRewrite best practices.

## Step 1: Extract Format Parameters from Request

Parse the request to identify:

| Parameter | How to Extract | Example |
|-----------|----------------|---------|
| `source_format` | What is being migrated FROM | "JSON", "callbacks", "old API" |
| `target_format` | What is being migrated TO | "TOON", "async/await", "new API" |
| `scope_indicator` | What content type is affected | "output", "config", "imports" |

**Example request**: "Migrate outputs from JSON to TOON format"
- `source_format`: JSON (indicators: `json.dumps`, `json.loads`, ` ```json `)
- `target_format`: TOON (indicators: `serialize_toon`, `parse_toon`, ` ```toon `)
- `scope_indicator`: outputs (look in Output sections, return statements)

## Step 2: Evidence Extraction (Per File)

For each file, extract evidence BEFORE making classification decision:

| Evidence Type | What to Look For |
|---------------|------------------|
| `source_format_evidence` | Indicators of source format in scope areas |
| `target_format_evidence` | Indicators of target format in scope areas |
| `scope_relevance` | Does file have content in the scope area? |

**Document evidence with specific line numbers.**

## Step 3: Classification Decision Matrix

Apply this decision matrix based on extracted evidence:

```
IF NOT scope_relevance:
    → CERTAIN_EXCLUDE (no relevant content)
    Reasoning: "No {scope_indicator} sections found"

ELSE IF has_target_format_evidence AND NOT has_source_format_evidence:
    → CERTAIN_EXCLUDE (already migrated)
    Reasoning: "Already uses {target_format}, no {source_format} found"

ELSE IF has_source_format_evidence AND NOT has_target_format_evidence:
    → CERTAIN_INCLUDE (needs migration)
    Reasoning: "Uses {source_format}, needs migration to {target_format}"

ELSE IF has_source_format_evidence AND has_target_format_evidence:
    → UNCERTAIN (partially migrated)
    Reasoning: "Mixed formats - has both {source_format} and {target_format}"

ELSE:
    → UNCERTAIN (ambiguous)
    Reasoning: "Has {scope_indicator} but format unclear"
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|----------------|------------------|
| "Has output section" → INCLUDE | Ignores current format | Check WHICH format |
| Hardcoding format names | Not reusable | Extract from request |
| Single-pass classification | Misses evidence | Extract evidence first |
| Binary classification only | Ignores partial migrations | Support UNCERTAIN |
