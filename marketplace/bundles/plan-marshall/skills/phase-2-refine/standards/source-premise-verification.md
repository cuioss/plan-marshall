# Source Premise Verification

Verification procedure for claims referenced in a plan's source narrative. Activates during phase-2-refine before quality analysis to catch stale or invalid premises early.

## Purpose

Plan sources (lessons, issues, PR reviews, free-form descriptions) capture observations at a point in time. The referenced code may have changed, flags may not exist, or the premise may have been wrong from the start. This step performs targeted verification against the current codebase before the request is accepted for planning.

## Trigger Condition

This step activates when the request narrative contains **verifiable code references** -- any of:

- File paths (e.g., `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md`)
- Flag or option names (e.g., `--force`, `--audit-plan-id`)
- API references (e.g., function names, class names, method signatures)
- Specific behavior descriptions tied to identifiable code (e.g., "the `add` subcommand ignores duplicates")

The trigger is **source-agnostic** -- it applies regardless of whether the plan originates from a lesson, GitHub issue, PR review, or user prompt. Plans whose narratives contain no verifiable code references skip this step entirely.

## Claim Extraction

Scan the request narrative (`description` and `clarified_request` fields from request.md) and identify each verifiable claim:

| Claim Type | Example | Verification Method |
|------------|---------|---------------------|
| File existence | "the file `path/to/foo.py` handles X" | `architecture which-module --path P` first; fall back to `Glob` for the path |
| Flag/option existence | "the `--bar` flag controls Y" | `architecture find --pattern '*{flag}*'` first; fall back to `Grep` for the flag in the referenced script or module |
| API/function reference | "the `process()` method does Z" | `architecture find --pattern '*{name}*'` first; fall back to `Grep` for the function definition |
| Behavior description | "subcommand `add` ignores duplicates" | `Read` the relevant code section and verify logic |

Extract at most **5 claims** per request. Prioritize claims that are load-bearing for the plan's intent -- a claim is load-bearing if the plan's proposed change depends on it being true.

## Verification Procedure

For each extracted claim, probe the architecture inventory first; only fall back to a shell tool when the architecture verb cannot answer (e.g., sub-module component lookup, content-search inside a known file, or the verb returns elision):

1. **File existence claims**: Use `architecture which-module --path P` to confirm the path is registered. Fall back to `Glob` when the file is sub-module-scoped or the architecture inventory returns elision.

2. **Flag/option claims**: Use `architecture find --pattern '*{flag}*'` to locate references inside the project's structured inventory. Fall back to `Grep` when the literal flag name is not in the inventory or when verifying that the flag is actively used (not commented out or removed) inside a specific known file.

3. **API/function claims**: Use `architecture find --pattern '*{name}*'` to find the definition. Fall back to `Grep` when the symbol is not surfaced by the inventory and verify the signature matches what the narrative describes.

4. **Behavior claims**: Use `Read` to examine the relevant code section. Verify the described behavior matches the implementation.

**Budget**: At most one tool call per claim. Do not cascade into deep code analysis -- the goal is a quick validity check, not a full audit.

## Result Handling

Each claim resolves to one of:

| Result | Meaning | Action |
|--------|---------|--------|
| **Valid** | Claim matches current codebase | No action needed, continue |
| **Stale** | Referenced artifact exists but has changed | Flag as `CORRECTNESS: ISSUE` with evidence |
| **Invalid** | Referenced artifact does not exist | Flag as `CORRECTNESS: ISSUE` with evidence |
| **Inconclusive** | Cannot verify with a single targeted read | Note as unverified, do not flag |

### Flagging Invalid Premises

When a claim is stale or invalid, emit a `CORRECTNESS: ISSUE` finding with:

```
CORRECTNESS: ISSUE — Source premise invalid
  Claim: "{original claim from narrative}"
  Expected: {what the narrative states}
  Actual: {what the codebase shows}
  Impact: {how this affects the plan's intent}
```

This finding feeds into the Step 10 confidence calculation under the Correctness dimension (20% weight). A single invalid load-bearing premise typically drops Correctness to 0, reducing overall confidence by 20 points.

### When All Claims Are Valid

If all extracted claims verify successfully, log the result and continue to Step 4 with no findings. The verification is silent on success -- it does not inflate confidence.

## Integration with Refine Workflow

- **Position**: Step 3b, after Recipe Shortcut (Step 3) and before Load Confidence Threshold (Step 4)
- **Findings**: Feed into Step 8 (Analyze Request Quality) under the Correctness dimension
- **Confidence impact**: Invalid premises reduce the Correctness score in Step 10, which may trigger clarification in Step 11
- **Clarification path**: If confidence drops below threshold due to an invalid premise, Step 11 asks the user whether the premise should be corrected, the plan intent adjusted, or the plan abandoned

## Logging

Log verification results to work.log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:3b] (plan-marshall:phase-2-refine) Source premise verification: {N} claims checked, {M} valid, {K} invalid"
```

When claims are invalid, also log to decision.log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-2-refine) Invalid premise: {claim_summary} — actual: {evidence_summary}"
```
