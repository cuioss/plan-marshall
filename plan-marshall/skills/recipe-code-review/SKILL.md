---
name: recipe-code-review
description: On-demand code-review recipe that runs a diff-aware structural/quality review over the current footprint and emits lint-issue findings into the triage pipeline
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Code Review

On-demand entry point for the plan-marshall code-review capability. This recipe runs a focused, diff-aware structural and quality review over the current footprint and emits each discovered issue as a `lint-issue` finding into the triage pipeline — the structural difference from external review tools, which print a report and stop.

The recipe is **standalone**: it does NOT load the shared security-audit engine (`recipe-security-audit/standards/audit-engine.md`). It reuses only the diff-aware shape that family shares — compute the live footprint, review it, emit findings, dispatch to triage — applied through the code-reviewer lens rather than the security one. The review itself is an **LLM cognitive review**, consistent with the recipe-skill design model (recipe skills are `mode: workflow` cognitive procedures, not deterministic scripts).

The reviewer reads the footprint through the `plan-marshall:persona-code-reviewer` lens — the meta/evaluator persona that composes the work personas (implementer, module-tester, integration-tester, documenter, security-expert) as evaluation lenses, judging correctness and intent rather than authorship.

## Foundational Practices

```text
Skill: plan-marshall:persona-plan-marshall-agent
```

## Enforcement

**Execution mode**: Walk the four steps below in order over the footprint — compute footprint, gather the reviewer lens, run the cognitive review, emit findings to triage. Each step has a single explicit job — no improvisation, no extra discovery passes.

**Prohibited actions:**
- Never load the security-audit engine (`recipe-security-audit/standards/audit-engine.md`) or emit `bug` / `anti-pattern` findings from this recipe. This is the code-review recipe — it is independent of the security family, and its findings type is `lint-issue`, full stop.
- Never emit a finding type other than `lint-issue` from this recipe. The `FINDING_TYPES` taxonomy is closed; a structural/quality observation maps onto `lint-issue` — it never adds a new type.
- Never print a prose review report and stop instead of emitting findings. Emitting into `manage-findings` is what buys triage, suppression, loop-back, and re-review for free (the universal-sink principle).
- Never mutate source files from within this recipe. The recipe is a findings producer — fixes flow from the downstream `ext-triage-*` FIX decision, not from this skill.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- Every run is plan-bound and operates inside its own plan directory — there is no plan-less special case.
- The cognitive review covers the footprint **completely** — every in-radius file is examined, not sampled.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier — every run is plan-bound. |
| `scope` | string | No | Optional path/file restriction. When supplied, the footprint is bounded to these paths. When omitted, the footprint is the full current-branch-vs-base diff. |
| `base_branch` | string | No | Optional explicit base ref for the diff. When omitted, defaults to `references.base_branch` (falling back to `main`). |

---

## Step 1: Compute the live footprint

Resolve the active worktree path, then derive the live footprint from the worktree git state — bounded to the optional `scope`, defaulting to the current-branch-vs-base diff:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

Capture the returned `worktree_path` (empty when `metadata.use_worktree == false` — the footprint is then computed against the main checkout). Then:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path} [--base-ref {base_branch}]
```

- Pass `--base-ref {base_branch}` only when an explicit `base_branch` input was supplied; otherwise omit it and the script defaults to `references.base_branch` (falling back to `main`).
- When a `scope` (path/file restriction) was supplied, intersect the returned footprint paths with `scope` and carry only the intersection forward.

The footprint is the review radius. An empty footprint means there is nothing to review — the recipe returns with zero findings.

---

## Step 2: Detect affected domains and gather the reviewer lens

For each footprint path, resolve its owning module:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture which-module --path {path}
```

Collect the distinct module values into the affected-domain set — this set keys the stage-4 finding dispatch to the right domain `ext-triage-*` extension.

Load the code-reviewer lens — the meta/evaluator persona whose composition supplies the evaluation standards the review reads through:

```text
Skill: plan-marshall:persona-code-reviewer
```

---

## Step 3: Run the cognitive review

Run the LLM structural/quality review across the full footprint, applying the code-reviewer lens. Read each in-footprint file and reason about it against the composed standards — correctness, single-responsibility, command-query separation, complexity thresholds, error handling, naming, test coverage, and documentation. The review covers the footprint completely — every file in radius is examined, not sampled.

This is a code-review pass, NOT a security audit: where a finding is fundamentally a security defect, that surface belongs to `recipe-security-audit`. This recipe's findings are structural/quality observations emitted as `lint-issue`.

---

## Step 4: Emit findings and dispatch to triage

Emit each identified issue as a `lint-issue` finding — one `add` call per finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add \
  --plan-id {plan_id} --type lint-issue --severity {error|warning|info} \
  --title "{short title}" --detail "{description}" \
  --file-path {file} --line {line} --module {module}
```

Then dispatch each finding to its domain `ext-triage-*` extension (keyed on the finding's module from Step 2) for the FIX / SUPPRESS / ACCEPT decision — the same resolution model every findings producer uses. The recipe adds a producer; it does not add a new resolution model.

After all findings are emitted, return the run summary as TOON:

```toon
status: success
plan_id: {echo}
review_summary:
  footprint_paths: N
  affected_modules: [module, ...]
  findings_emitted: N
next_action: findings_dispatched_to_triage
```

When the footprint is empty, return `findings_emitted: 0` with `next_action: nothing_to_review`.

## Why findings, not a prose report

Emitting into `manage-findings` (rather than printing a report and stopping) is what buys triage, suppression, loop-back, and re-review for free — the structural difference from external review tools. This is the universal-sink principle: anything that discovers a problem emits into the findings pipeline.

---

## Related

- `plan-marshall:persona-code-reviewer` — the meta/evaluator lens this recipe reads the footprint through (composes the work personas as evaluation lenses).
- `plan-marshall:manage-references` `compute-footprint` — the Step-1 footprint resolver.
- `plan-marshall:manage-architecture` `which-module` — the Step-2 domain detector.
- `plan-marshall:manage-findings` `add` — the Step-4 findings sink (`lint-issue` type).
- `plan-marshall:extension-api` `standards/ext-point-triage.md` — the domain `ext-triage-*` resolution model the findings flow into.
- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements.
- `plan-marshall:recipe-security-audit` — the sibling on-demand audit recipe; the security family this recipe is deliberately independent of.
