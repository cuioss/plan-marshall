---
name: recipe-fix-argparse-rejection
description: Remediation recipe for the exit_code=2 / argparse_rejection defect class — invented or paraphrased manage-* subcommands and flags that do not exist in the script's argparse choices
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Fix Argparse Rejection

This is a remediation recipe for the `exit_code=2` / `argparse_rejection` defect class: a `python3 .plan/execute-script.py {notation} {subcommand} …` call whose subcommand or flag *reads naturally in workflow prose* but does not exist in the script's argparse `choices`, so argparse rejects it before the script body runs. The call exits `2` silently — no script-side error, no partial work — and downstream behaviour corrupts because the intended mutation never happened.

This recipe is the **remediation procedure** invoked *after* a rejection has occurred to correct the offending call site in place. It is complementary to — and deliberately does NOT duplicate — the *prevention* guidance in [`plan-marshall:persona-plan-marshall-agent` § "Never invent script subcommands"](../../../plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md), which is the avoidance rule loaded into every agent context and the canonical home of the four recurrence signatures (verb-paraphrase; top-level `--plan-id`/`--project-dir` where the flag is verb-scoped; doubled bundle-prefix; missing required `--phase` / `--resolution`-vs-`--status` confusion). Cross-reference those signatures from there rather than restating them; this recipe walks the fix once the signature has already fired.

## Foundational Practices

```text
Skill: plan-marshall:persona-plan-marshall-agent
```

## Enforcement

**Execution mode**: Walk the three steps below in order — Catch → Locate → Fix-in-place. Each step has a single explicit job; do not improvise extra discovery passes or skip the locate step in favour of guessing a replacement verb.

**Prohibited actions:**
- Never replace a rejected call with another *plausible* verb. The replacement MUST be the verbatim canonical call resolved in Step 2 from the owning skill's authoritative source (or `--help`) — substituting one guessed verb for another reproduces the same defect.
- Never restate the four recurrence signatures here or in the fixed call site. They live in `persona-plan-marshall-agent` § "Never invent script subcommands"; reference that section instead of copying it.
- Never silently swallow or "log and continue" an `exit_code=2` rejection. The rejection is the signal that triggers this recipe — treat it as fail-loud, not as a transient to retry with the same shape.
- Never add per-script command catalogues, new tests, or script implementation as part of the fix. The remediation is confined to the calling skill's workflow document (or the inline instructions when no skill owns the call site).

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- One fix per rejecting call site — correct exactly the call that was rejected and any sibling occurrences of the identical invented shape in the same document; do not broaden scope to unrelated calls.

---

## Step 1: Catch — Recognize the Argparse-Rejection Signature

Identify the failing call from its output. The diagnostic signature is a `python3 .plan/execute-script.py` call that returns:

- `exit_code: 2` (argparse's reserved exit code for argument errors), often surfaced as `failure_kind: argparse_rejection` in the executor's standardized error envelope, and
- an argparse stderr line of the shape `… invalid choice: '{rejected}' (choose from '{a}', '{b}', …)` or `unrecognized arguments: {flag}` / `the following arguments are required: {flag}`.

The `choose from (...)` list — or the `required` / `unrecognized` flag name — is the **diagnosis signal**: it enumerates the subcommands or flags argparse *does* accept, against which the rejected token is the drift. Match the rejected token to one of the four recurrence signatures catalogued in `persona-plan-marshall-agent` § "Never invent script subcommands" to confirm the defect class and narrow the likely correction (verb-paraphrase, mis-scoped flag, doubled prefix, or missing/`--status`-confused flag).

**Accepted read-verb aliases — not a rejection.** Three single-record read verbs accept the sibling spelling as an argparse alias, so both forms are valid CLI and neither is in scope for this recipe: `manage-lessons read` (alias of canonical `get`), `manage-tasks get` (alias of canonical `read`), and `manage-status get` (alias of canonical `read`). These resolve to the same handler as their canonical verb and do NOT produce `exit_code: 2` — see [`plan-marshall:persona-plan-marshall-agent/standards/argument-naming.md` § "Rule 2 — Read-verb canonicalization"](../../../plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md) for the accepted-secondary-spellings contract. Do not "remediate" a call that already uses one of these accepted aliases. The recipe still governs genuinely-invented verbs — a paraphrased verb that argparse actually rejects remains in scope.

Proceed to Step 2 with the `{notation}`, the rejected `{subcommand}`/`{flag}`, and the captured `choices` list.

## Step 2: Locate — Find the Owning Skill's Authoritative Call Shape

Resolve the correct, canonical invocation from the **owning skill** of the rejecting `{notation}`:

1. **Identify the owning skill** from the notation `{bundle}:{skill}:{script}` — the middle segment is the skill directory under `marketplace/bundles/{bundle}/skills/{skill}/`.
2. **Read the owning skill's `## Canonical invocations` section** in its `SKILL.md` (or its `## Integration` → Script Notations table when no Canonical-invocations section exists). That section is the authoritative source for the exact subcommand and flag shapes, per the explicit-call-or-xref authoring contract in [`pm-plugin-development:plugin-script-architecture/standards/cross-skill-integration.md` § "Script invocation in documentation"](../plugin-script-architecture/standards/cross-skill-integration.md).
3. **When in doubt, ask argparse directly** — invoke the script's own help to read the live `choices`:

   ```bash
   python3 .plan/execute-script.py {notation} --help
   ```

   and, for the subcommand-level flags:

   ```bash
   python3 .plan/execute-script.py {notation} {subcommand} --help
   ```

   The live argparse declaration always supersedes any prose; if the Canonical-invocations section and `--help` disagree, the `--help` output is authoritative and the skill's section is itself a defect to be corrected separately.

Capture the verbatim canonical call (correct subcommand, correct flag names, correct flag scope) as the replacement shape.

## Step 3: Fix in Place — Replace the Invented Call and Import the Owning Skill

Apply the correction to the **calling** skill's workflow document (or the inline instructions when no skill owns the call site — e.g. an orchestrator prompt):

1. **Replace the rejected call** with the verbatim canonical call resolved in Step 2 — exact subcommand, exact flag names, exact flag scope. Fix every occurrence of the identical invented shape in the same document, not just the one that was caught.
2. **Add the owning-skill import when missing.** If the calling skill does not already load the owning `manage-*` skill via a `Skill:` directive, add that import (typically under the calling skill's `## Foundational Practices` or an equivalent skill-load block) so future agents have the canonical API loaded in context *before* reaching the call site:

   ```text
   Skill: {bundle}:{owning-skill}
   ```

   This closes the loop on the root cause: the rejection happened because the canonical surface was paraphrased from prose rather than read from the loaded API. Importing the owning skill makes the authoritative shape available at the point of use.
3. **Do not broaden scope.** The fix is confined to the calling document — no new tests, no script changes, no per-script command catalogues. If the owning skill's own Canonical-invocations section was wrong (Step 2 `--help` disagreement), record that as a separate defect rather than folding it into this fix.

---

## See Also

- [`plan-marshall:persona-plan-marshall-agent` § "Never invent script subcommands"](../../../plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md) — the prevention rule and the canonical home of the four argparse-rejection recurrence signatures.
- [`pm-plugin-development:plugin-script-architecture/standards/cross-skill-integration.md` § "Script invocation in documentation"](../plugin-script-architecture/standards/cross-skill-integration.md) — the explicit-call-or-xref authoring contract that a correct fix satisfies, plus the `manage-invocation-invalid` / `missing-canonical-block` rules that guard it at edit time.
