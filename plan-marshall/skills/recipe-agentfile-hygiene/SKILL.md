---
name: recipe-agentfile-hygiene
description: Domain-invariant cognitive sweep recipe that classifies every CLAUDE.md/AGENTS.md section against the shared ref-agentfile-hygiene rubric and emits one remediation deliverable per offending section
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Agentfile Hygiene

Domain-invariant cognitive sweep recipe that audits every always-on agentfile in a project — every `CLAUDE.md` at any nesting level plus `AGENTS.md` — against the shared agentfile context-hygiene rubric, and emits one remediation deliverable per offending section into `solution_outline.md` for phase-5 to apply.

The capability splits along the same cognitive/deterministic seam `recipe-security-audit` uses: this recipe is the **cognitive** half — an LLM classification pass over each agentfile section — while the `pm-plugin-development:plugin-doctor` rules `agentfile-line-count-over-budget` and `agentfile-directory-tree-present` are the fast deterministic backstop. Both halves consume the single normative rubric in `plan-marshall:ref-agentfile-hygiene`, so they stay in sync by construction.

Unlike the audit-recipe family (`recipe-code-review`, `recipe-security-audit`), which emit *findings* into the triage pipeline, this is a **plan-shape** recipe: it emits remediation *deliverables* into the outline, following the emit-deliverables model proven by `recipe-simplify-codebase`. It is a **sweep-all** recipe — there is no `scope × thoroughness` gather; every discovered agentfile is classified in full.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier — from phase-3-outline |

There is no `recipe_scope` / `recipe_thoroughness` input and no `recipe_package_source`: the sweep is a fixed full pass over every agentfile, not a package iteration. The recipe is plan-bound. Its discovery metadata (`key`, `default_change_type`, `scope`) is returned by the `plan-marshall-plugin` extension's `provides_recipes()`, not declared here.

## Enforcement

**Execution mode**: Deliverable-collection cognitive recipe — discover every agentfile, load the shared rubric, classify each section, emit one remediation deliverable per offending section, write the solution outline. Loaded by phase-3-outline's recipe path; not user-invocable.

**Prohibited actions:**
- Never restate, paraphrase, or inline the rubric's classification criteria, line budget, keyword lists, or decision guidance — load `plan-marshall:ref-agentfile-hygiene` and consume `standards/rubric.md` as the single source of truth. Duplicating the rubric here desynchronizes the cognitive sweep from the deterministic backstop rules.
- Never add project-specific path literals, agentfile content, or examples to this recipe — it is domain-invariant and ships to consumer repositories verbatim.
- Never run a dry-run / report-only mode — the outline-and-deliverable review gate IS the dry run; this recipe always emits deliverables.
- Never emit a remediation deliverable for a section the rubric classifies as `always-on-justified` — only `demotable-to-skill` and `inert/deletable` sections are offending.
- Never access `.plan/` files directly — all access goes through `python3 .plan/execute-script.py` manage-* scripts.

**Constraints:**
- Strictly comply with all rules from `plan-marshall:persona-plan-marshall-agent`, especially tool usage and workflow step discipline.
- The rubric (`plan-marshall:ref-agentfile-hygiene` `standards/rubric.md`) is the sole normative authority for every classification; this recipe only applies it and shapes the result into deliverables.
- Each emitted deliverable names its target agentfile, the offending section, the rubric classification, and the remediation action (trim / demote-to-skill / delete), with `change_type: tech_debt`.

## Workflow

### Step 1: Discover every agentfile

Find every always-on agentfile in the project — all `CLAUDE.md` at every nesting level plus every `AGENTS.md`. Agentfile discovery anchors at the repository root and recurses; agentfiles are not module components, so `Glob` is the correct discovery tool here (the structured-query-first rule applies to module-component lookup, not to root-anchored agentfile discovery):

```text
Glob: **/CLAUDE.md
Glob: **/AGENTS.md
```

Apply the standard exclusions — discard any match under `.plan/`, an archived-plans directory, a vendored directory, `node_modules/`, `target/`, or `.git/`. These directories hold generated, vendored, or planning-scratch content whose agentfiles are not the project's own always-on instructions.

When the discovery set is empty, write a minimal outline recording "no agentfiles found — nothing to remediate" and stop (Step 5 still runs to produce a valid, empty-deliverable outline).

### Step 2: Load the shared rubric (single source of truth)

```text
Skill: plan-marshall:ref-agentfile-hygiene
```

The skill's `standards/rubric.md` carries the three section classifications (`always-on-justified` | `demotable-to-skill` | `inert/deletable`) with their objective criteria, the always-on line budget, and the directory-tree anti-pattern. Read it and apply it verbatim — do NOT restate it in this recipe or in any emitted deliverable.

### Step 3: Classify each agentfile section against the rubric

For every discovered agentfile, read it in full and split it into its natural sections (heading-delimited blocks). Classify each section as exactly one of `always-on-justified`, `demotable-to-skill`, or `inert/deletable`, applying the rubric's criteria. Bias toward removal per the rubric: when a section's always-on justification is uncertain, classify it `demotable-to-skill` rather than keeping it.

A section classified `always-on-justified` is compliant — it earns its always-on cost and produces no deliverable. A section classified `demotable-to-skill` or `inert/deletable` is **offending** and produces exactly one remediation deliverable in Step 4.

Also apply the rubric's whole-file signals: an agentfile over the line budget, or one containing a fenced directory-tree drawing, is a strong prompt to re-classify its sections — surface those as offending sections (the bloated body, the inert tree) rather than as a separate file-level deliverable.

### Step 4: Collect one remediation deliverable per offending section

Collect exactly one deliverable per offending section:

- **Title**: `Agentfile hygiene: {action} "{section}" in {agentfile_path}` where `{action}` is `trim`, `demote`, or `delete`.
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `module`: the module owning the agentfile (resolve via `architecture which-module --path {agentfile_path}`; the repo-root agentfile resolves to the root/meta module).
- **Affected files**: the agentfile itself (`write-replace`), plus the destination skill/doc (`write-new`) for a `demote` action.
- **Change per file**: the concrete remediation — for `demotable-to-skill`, extract the section into a named skill or doc and replace it with a one-line pointer; for `inert/deletable`, delete the section outright; for an over-budget `trim`, the specific sections to compress.
- **Classification**: the rubric classification that drove the action (`demotable-to-skill` or `inert/deletable`), cited as the deliverable's rationale — without restating the rubric criteria.

Sections classified `always-on-justified` produce no deliverable.

### Step 5: Write `solution_outline.md`

**5a. Read the deliverable template**:

```text
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**5b. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**5c. Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include, in order:
- A `# Solution: Agentfile hygiene` header with `plan_id`, `created`, and `compatibility` metadata.
- A `## Summary` — the count of agentfiles swept and the count of offending sections by classification.
- A `## Overview` — the discovered-agentfile list and the cognitive/deterministic seam (this recipe plus the plugin-doctor backstop rules).
- A `## Deliverables` section — one remediation deliverable per offending section (Step 4), ordered lowest-risk first: `inert/deletable` deletions, then `demotable-to-skill` extractions, then over-budget trims.

**5d. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

## Output contract

A `solution_outline.md` whose `## Deliverables` carry one remediation deliverable per offending agentfile section — each naming its target agentfile, the offending section, the rubric classification, and the remediation action (trim / demote / delete) with `change_type: tech_debt` — plus a `## Summary` of the sweep and a `## Overview` of the discovered agentfiles. Recipe metadata (`recipe_key`, `recipe_skill`, the resolved domain) is persisted to `status.json` per the ext-point-recipe post-conditions.

## Related

- `plan-marshall:ref-agentfile-hygiene` — the shared rubric (the single normative source) this recipe consumes; the deterministic backstop rules embody the same rubric.
- `pm-plugin-development:plugin-doctor` — the deterministic backstop rules `agentfile-line-count-over-budget` and `agentfile-directory-tree-present` that surface the same defects fast (the `analyze` command).
- `plan-marshall:recipe-simplify-codebase` — the sibling cognitive recipe whose emit-deliverables (plan-shape) model this recipe follows.
- `plan-marshall:recipe-security-audit` — the sibling cognitive recipe on the *findings*-emitting side of the seam (the contrast that places this recipe on the deliverable-emitting side).
- `plan-marshall:tools-sync-agents-file` — distinct concern: creates/updates `AGENTS.md` per the OpenAI spec (this recipe audits and trims existing agentfiles).
- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements; discovery metadata is returned by the `plan-marshall-plugin` extension's `provides_recipes()`.
- `plan-marshall:phase-3-outline` — loads this skill via the recipe path with the input parameters above.
