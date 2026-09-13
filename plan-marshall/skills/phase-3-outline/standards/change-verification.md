# Change Verification — Generic Outline Instructions

Instructions for `verification` change type. Handles validation and confirmation requests. This is a read-only type — no code changes.

## Read-Intent-Only Invariant (normative)

A `verification` deliverable is read-only **by definition**: it consults its targets to determine a pass/fail verdict and produces no code changes. The per-file intent markers a deliverable carries (see the phase-3-outline SKILL.md § "Per-file intent marker") MUST therefore be consistent with that definition.

**Invariant**: when a deliverable is assigned `change_type: verification`, **every** entry in its `**Affected files:**` list MUST carry intent `read`. A `verification` deliverable that also carries any affected file with intent `write-new` or `write-replace` is **self-inconsistent** — it simultaneously claims "no code changes" (the change-type) and "this file is created/modified" (the write intent). This combination is an **outline authoring error**, not a legitimate deliverable shape. (A `delete` intent is likewise a mutation and is equally inconsistent with `verification`; the read-intent-only invariant admits `read` alone.)

**Corrective action**: do NOT soften the deliverable to make the inconsistency pass. Instead, **re-classify the deliverable** to the change-type that matches its actual intent:

- The deliverable both verifies a condition AND modifies code to satisfy it → it is not a verification deliverable. Re-classify to `bug_fix` (when the write fixes a defect), `feature` / `enhancement` (when the write adds or extends behaviour), or `tech_debt` (when the write is a non-behavioural cleanup) — whichever non-verification change-type the write intent actually expresses.
- If the verification and the write are genuinely separate concerns, **split** them into two deliverables: a `read`-only `verification` deliverable and a separate non-verification deliverable carrying the write-intent files.

Re-classification (or the split) is the only valid resolution — narrowing or relabelling the write-intent file to `read` so the invariant superficially holds, while the deliverable's `**Change per file:**` still describes a code change, re-introduces the same inconsistency and is prohibited.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`) — are documented inline in the step that issues them.

## When Used

Requests with `change_type: verification`:
- "Verify the migration completed successfully"
- "Check that all endpoints return valid JSON"
- "Confirm the refactoring didn't break tests"
- "Validate the configuration is correct"

## Discovery

Based on the request, establish:

1. **What to verify** — The specific thing being checked
2. **Success criteria** — What makes it "correct"
3. **Verification method** — How to check it

Log criteria:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Verifying: {target}, criteria: {criteria}"
```

## Analysis

Build a structured checklist:

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| {item1} | {command/inspection} | {what makes it pass} |
| {item2} | {command/inspection} | {what makes it pass} |

## Deliverable Structure

```markdown
### 1. Verify: {Verification Target}

**Metadata:**
- change_type: verification
- execution_mode: automated
- domain: {domain}
- module: {module or "project-wide"}
- depends: none

**Profiles:**
- implementation

**Verification Checklist:**
| Check | Method | Pass Criteria |
|-------|--------|---------------|
| {item1} | {method1} | {criteria1} |
| {item2} | {method2} | {criteria2} |
| {item3} | {method3} | {criteria3} |

**Affected files:**
- `{path/to/file1}` (verification target)
- `{path/to/file2}` (verification target)

**Change per file:**
- `{file1}`: Verify {specific aspect}
- `{file2}`: Verify {specific aspect}

**Verification:**
- Command: {primary verification command}
- Criteria: All checklist items pass

**Success Criteria:**
- All checklist items verified
- Evidence provided for each
- Clear pass/fail determination
```

## Guidelines

- Verification only — do not propose code changes
- Create clear pass/fail criteria
- Document verification methodology
