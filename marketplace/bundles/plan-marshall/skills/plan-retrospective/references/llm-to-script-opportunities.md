# Aspect: LLM-to-Script Opportunities

Identify deterministic, repetitive work that the LLM performed which could be replaced by a script. LLM-driven; inputs are logs and the work log's `[ARTIFACT]` / `[DECISION]` entries.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `collect-fragments` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

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

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-llm-to-script-opportunities.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect llm-to-script-opportunities --fragment-file work/fragment-llm-to-script-opportunities.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
