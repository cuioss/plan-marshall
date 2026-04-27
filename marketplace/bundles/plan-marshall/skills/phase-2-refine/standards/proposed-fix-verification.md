# Proposed-Fix Verification

Verification procedure that challenges whether a proposed fix actually solves the documented symptom. Activates during phase-2-refine after source premise verification (Step 3b) and before confidence aggregation (Step 4).

## Purpose

Source premise verification confirms that the **claims about existing code** are accurate. It does not confirm that the **proposed fix** is sufficient to address the symptom. A request can contain load-bearing claims that are all individually true while the proposed change still leaves a gap — especially when the source narrative is unusually well-specified, because the well-specified-ness itself becomes a confidence anchor that suppresses skepticism about completeness.

This step performs a targeted "would the proposed fix change behavior in the failure scenario?" check against the symptom before the request is accepted for planning.

## Trigger Condition

This step activates via **semantic LLM judgment** — not string matching on headers. Activate when the request narrative proposes a **specific code change**, including:

- Concrete command strings (e.g., "change `git diff --name-only {base}...HEAD` to `git diff --name-only {base}`")
- Regex or substitution patterns
- Function bodies, signatures, or patch snippets
- Config keys with new values
- Explicit step additions with named triggers and effects

The trigger is **source-agnostic** — it applies regardless of whether the plan originates from a lesson, GitHub issue, PR review, or user prompt. Narratives that describe a symptom without proposing a specific change skip this step entirely.

**Do not** gate activation on header tokens like `## Proposed fix` or `## Preferred fix`. Headers vary across sources (lessons use `proposed_improvement`, PR comments use free prose, etc.) — judge on semantic content instead.

## Proposed-Fix Extraction

Scan the request narrative and identify each proposed fix. Extract at most **3 proposed fixes** per request, prioritizing the ones that are **load-bearing** — a proposed fix is load-bearing if the plan's intent depends on it succeeding.

For each extracted fix, capture:

| Field | Content |
|-------|---------|
| `fix_description` | What the narrative says the change does |
| `fix_mechanism` | The concrete command / regex / code / config that implements it |
| `symptom_reference` | The failure scenario the fix is intended to address |

## Probe Construction

For each extracted fix, construct a synthetic "would this fix change behavior here?" probe:

1. **Re-read the symptom**: under what conditions does the bug manifest? Enumerate the triggering inputs (untracked files present, empty string argument, concurrent writer, etc.).
2. **Construct a concrete scenario**: a minimal case that reflects the symptom's triggering conditions (e.g., "a working tree with one tracked-file modification AND one untracked new file").
3. **Reason about the proposed fix against the scenario**: does the fix, as described, change behavior in the scenario? Reason about command/code semantics — do not execute code.
4. **Evaluate**: valid, insufficient, or inconclusive.

**Budget**: At most one probe per extracted fix. Do not cascade into multi-step execution traces — the goal is a quick sufficiency check, not a full trace.

## Result Handling

Each probe resolves to one of:

| Result | Meaning | Action |
|--------|---------|--------|
| **Valid** | Probe shows the fix changes behavior correctly in the triggering scenario | No action needed, continue |
| **Insufficient** | Probe exposes a gap — the fix does not cover a case the symptom includes | Flag as `CORRECTNESS: ISSUE` with evidence |
| **Inconclusive** | Cannot reason about behavior without executing code | Note as unverified, do not flag |

### Flagging Insufficient Fixes

When a probe exposes a gap, emit a `CORRECTNESS: ISSUE` finding with:

```
CORRECTNESS: ISSUE — Proposed fix incomplete
  Fix: "{fix_description}"
  Mechanism: {fix_mechanism}
  Scenario: {concrete scenario from probe}
  Gap: {what the probe showed is missing}
  Impact: {how this affects the plan's intent}
```

This finding feeds into the Step 10 confidence calculation under the **Correctness dimension** (20% weight, shared with Step 3b findings). A single insufficient load-bearing fix typically drops Correctness to 0, reducing overall confidence by 20 points.

### When All Probes Pass

If every extracted fix passes its probe, log the result and continue to Step 4 with no findings. The verification is silent on success — it does not inflate confidence.

## Integration with Refine Workflow

- **Position**: Step 3c, after Source Premise Verification (Step 3b) and before Load Confidence Threshold (Step 4)
- **Findings**: Feed into Step 8 (Analyze Request Quality) under the Correctness dimension, same as Step 3b
- **Confidence impact**: Insufficient proposed fixes reduce the Correctness score in Step 10, which may trigger clarification in Step 11
- **Clarification path**: If confidence drops below threshold due to an insufficient fix, Step 11 asks the user whether to broaden the fix, accept the gap, or abandon the plan

## Worked Example

The motivating case for this step:

**Symptom** (from lesson `2026-04-18-15-001`): `manage-references` only captures committed changes when the execute phase transition runs at `HEAD == base_branch`. Uncommitted working-tree state is missed.

**Proposed fix** (from the lesson): change the range `{base_branch}...HEAD` to `{base_branch}` (no dots) so `git diff --name-only` reports working-tree modifications.

**Probe construction**:
1. Symptom: uncommitted working-tree changes missed. Triggering inputs include both **modified tracked files** and **newly written untracked files** (because phase-5-execute `Write` operations create untracked sources/tests).
2. Scenario: working tree contains one tracked-file edit AND one untracked new file.
3. Reason about `git diff --name-only {base_branch}` against this scenario: `git diff` only reports modifications to tracked files; untracked files are **invisible** to plain `git diff`.
4. Evaluation: **insufficient**. The fix covers the tracked-edit case but misses the untracked-new-file case, which is exactly what phase-5-execute `Write` operations generate.

**Finding emitted**:
```
CORRECTNESS: ISSUE — Proposed fix incomplete
  Fix: "change `{base}...HEAD` to `{base}` (no dots) to capture working-tree state"
  Mechanism: git diff --name-only {base_branch}
  Scenario: working tree with tracked-file edit + untracked new file
  Gap: git diff does not report untracked files; needs union with `git ls-files --others --exclude-standard`
  Impact: phase-5-execute Write operations create untracked files — the fix would still miss them
```

Had this probe run during the original lesson's refine phase, the gap would have surfaced before phase-3-outline. The shipped fix ended up adding exactly the second probe the narrative missed.

## Logging

Log verification results to work.log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:3c] (plan-marshall:phase-2-refine) Proposed-fix verification: {N} fixes probed, {M} valid, {K} insufficient"
```

When probes reveal insufficient fixes, also log to decision.log at WARNING:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-2-refine) Insufficient proposed fix: {fix_summary} — gap: {gap_summary}"
```
