# Aspect: LLM-to-Script Opportunities

Identify deterministic, repetitive work that the LLM performed which could be replaced by a script. LLM-driven; inputs are logs and the work log's `[ARTIFACT]` / `[DECISION]` entries.

## Inputs

- `work.log` — tagged entries reveal LLM action patterns.
- `script.log` — where scripts already covered the deterministic path.
- `references.json` `affected_files` — patterns in the file list.

## Detection Heuristics

An LLM action is a candidate for scripting when ALL of these hold:
1. Repeated 3+ times within the plan with near-identical inputs.
2. Outputs are deterministic (no judgement).
3. Inputs are machine-parseable (no free-text).

Common patterns to watch for:
- Manual TOON/JSON parsing or re-serialization.
- File-listing with filter logic.
- Metadata extraction from markdown frontmatter.
- Counting log entries by tag.
- Computing hashes or IDs.

## TOON Fragment Shape

```toon
aspect: llm_to_script_opportunities
status: success
plan_id: {plan_id}
candidates[*]{task,repetition_count,complexity,proposal}:
  "parse references.json affected_files",5,low,"add manage-references modified-files-summary subcommand"
  "enumerate lesson files by date",3,low,"extend manage-lessons list with --since filter"
findings[*]{severity,message}:
  info,"2 scripting opportunities identified"
```

## LLM Interpretation Rules

- `complexity: low` means < 50 lines of Python, no external deps. These are strong candidates.
- `complexity: medium` (50-200 lines) candidates MAY be proposed but flag as `info`.
- `complexity: high` candidates are NOT proposed from this aspect — they belong in a separate plan.
- At most 5 candidates per retrospective; prioritize by `repetition_count`.

## Finding Shape

```toon
aspect: llm_to_script_opportunities
severity: info
proposal: "{one-sentence script proposal}"
impact: "{estimated LLM calls saved per plan}"
```

## Out of Scope

- Refactoring existing scripts — this aspect only proposes new ones.
- Evaluating LLM prompt quality — that is logging-gap-analysis and chat-history-analysis.
