---
lane:
  class: prunable
  tier: minimal
  prunable_when: footprint_no_lesson_component
  cost_size: L
name: finalize-step-lessons-housekeeping
description: Finalize-phase wrapper that reconciles the just-finished plan's outcome against the lessons-learned corpus, removing fully-covered lessons, promoting reusable residue into the governing skill before retiring the lesson, and trimming partially-covered ones
user-invocable: false
mode: workflow
allowed-tools: Bash, Read, Edit
order: 4
mutates_source: true
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step: lessons-housekeeping

## Purpose

Perform lessons-learned housekeeping after a plan finishes. Reason from the just-completed plan's outcome (what it changed, what it codified, which failure modes it eliminated) about the standing lessons-learned corpus, reconciling it into an actionable-by-construction queue rather than running a plain remove/trim pass:

- **Remove** lessons the plan made wholly redundant — the guarded failure mode can no longer occur, or the recommended practice is now codified/enforced, and no durable reusable rule remains to relocate.
- **Promote-then-retire** lessons that are completely covered *and* whose residue is a durable reusable rule — promote that rule into the governing skill's `standards/`/`references/` (or `CLAUDE.md` for repo-wide rules), then tombstone + remove the now-promoted lesson.
- **Trim** lessons the plan made only partly redundant, removing the now-covered portion while preserving the still-relevant guidance.
- **Retain** everything else, biasing toward retention whenever coverage is ambiguous.

Every change — removal, promotion-then-retire, adaptation, or deliberate retain — is recorded to the decision log so the housekeeping is fully auditable.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-lessons-housekeeping` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to read the plan outcome and to scope decision-log entries)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

This step edits tracked source (its Step 4b promotions write governing-skill docs), so it declares `mutates_source: true` and MUST run in the **pre-merge settle band** (`order < 10`):

- **before `default:pre-push-quality-gate` (5)** — so its promotion edits are linted in the same finalize run that wrote them, rather than surfacing as a lint failure on a later plan.
- **before `default:push` (10) and `default:branch-cleanup` (70)** — so those edits are pushable onto the still-open feature branch and covered by the PR's CI run and review.

This settle-band constraint **supersedes** the former requirement to run after `plan-marshall:plan-retrospective` (order 995): pushability of source edits outranks reading a retrospective artifact that this step already treats as best-effort. See [marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md) for the governing contract.

## Direct-file-access allowance

This step is granted **direct `Read`/`Edit` access to `.plan/local/lessons-learned/**`** as a documented exception to the CLAUDE.md "`.plan/` access: scripts only" hard rule. That rule itself carves out the exception: *"Never Read/Write/Edit `.plan/` files directly unless a loaded skill's workflow explicitly documents it."* This section is that explicit documentation.

The exception is deliberately narrow:

- **Removals still route through `manage-lessons remove`** — never delete a lesson `.md` file directly. The script writes an auditable tombstone, which the direct-`Edit` path cannot. This applies equally to the promote-then-retire disposition (Step 4b): after the residue is promoted, the lesson is retired via `manage-lessons remove`, never by deleting the file.
- **Only the partial-coverage *adaptation* edits touch lesson `.md` bodies directly** — trimming the now-covered portion of a lesson is a surgical body edit that no `manage-lessons` verb expresses, so it is performed with `Edit` against `.plan/local/lessons-learned/{id}.md`.
- **Promotion edits target governing-skill docs — outside the lessons corpus.** The promote-then-retire disposition (Step 4b) uses `Edit` against the governing skill's `standards/*.md` / `references/*.md` (or `CLAUDE.md` for repo-wide rules) — a path *outside* `.plan/local/lessons-learned/**`. These are ordinary source-doc edits, not `.plan/` edits, so they fall outside the `.plan/`-scoped hard rule entirely; they are noted here only so the full set of files this step may write is documented in one place. The subsequent lesson retirement still routes through `manage-lessons remove`.
- **Reads** of lesson bodies for classification go through `manage-lessons list --full` / `manage-lessons get` where possible; direct `Read` of a lesson `.md` is permitted only to inspect the exact body region an adaptation will trim.

## Ordering

The canonical phase-6-finalize chain (resolved by each step's `order:` frontmatter):

```text
default:finalize-step-sync-baseline             (3)
project:finalize-step-lessons-housekeeping      (4)    <-- this step
default:pre-push-quality-gate                   (5)
...                                             (settle band, order < 10)
default:push                                    (10)
```

The step runs inside the pre-merge settle band, so its promotion edits are linted by `default:pre-push-quality-gate` and shipped by the single `default:push` barrier. The step itself issues **no git call** and invents no push path: the dispatcher's commit instrumentation (phase-6-finalize Step 3 item 5f) commits every settle-band mutating step's edits onto the feature branch before the barrier runs.

## Workflow

### Step 1: Read the just-finished plan's outcome

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field modified_files
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Read the retrospective's quality-verification report (written by `plan-marshall:plan-retrospective`, order 995). At this step's settle-band order the retrospective has not yet run, so this read is **best-effort**: the report is normally absent, and its absence is already non-fatal — see the "Missing `quality-verification-report.md`" row in Error Handling, which proceeds on `request.md` + `modified_files` alone.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file quality-verification-report.md
```

Together these establish what the plan changed (modified files), why (the request), and the verified outcome — the basis for coverage classification.

### Step 2: Enumerate the lessons corpus

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
```

**Empty-corpus skip-clean exit**: if zero lessons exist, log and record the step as done, then return:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) 0 lessons — nothing to reconcile"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "0 lessons — nothing to reconcile"
```

### Step 3: Classify each lesson's coverage against the plan outcome

For each lesson, classify it against the plan outcome using a **conservative subsumption bar**:

- **Completely covered** — requires that the lesson's guarded failure mode can no longer occur, **OR** its recommended practice is now codified/enforced by this plan. Nothing weaker qualifies. The residue is already codified elsewhere, so the lesson is removed outright (Step 4).
- **Completely covered, residue is a reusable rule** — the lesson's guarded failure mode can no longer occur (so it qualifies as completely covered) **AND** the lesson body still carries a durable reusable rule — an operating rule, a convention, an anti-pattern, or a contract-guard — whose correct home is the governing skill's `standards/`/`references/` (or `CLAUDE.md` for repo-wide rules) rather than the lessons queue. Distinguish it from plain "Completely covered" (residue already codified elsewhere → remove outright) using the **Placement test** below. This classification routes to the promote-then-retire disposition (Step 4b).
- **Partially covered** — the plan eliminated or codified *part* of what the lesson guards, but a residual concern remains.
- **Ambiguous / none** — anything that does not clearly meet the bar above. **Leave untouched (bias to retain)** and log the no-action decision.

When in doubt, retain. The cost of keeping a stale lesson is far lower than the cost of deleting a still-load-bearing one. Promote-then-retire fires only when the residue clearly maps to a load-bearing home; an ambiguous residue retains.

### Placement test: route durable knowledge to its load-bearing home

When a completely-covered lesson still carries durable knowledge, decide where that knowledge belongs by asking the single question: **"where is this knowledge loaded at the moment it must change behavior?"** Route by the answer:

| Residue kind | Load-bearing home |
|--------------|-------------------|
| Operating rule / convention / anti-pattern | The governing skill's `standards/*.md` |
| Contract + recurrence-guard | The owning skill's `references/*.md` |
| Repo-wide workflow / process hard rule | `CLAUDE.md` / `persona-plan-marshall-agent` |
| Decision with weighed alternatives | An ADR (NOT a convention/bug record) |
| Open, un-shipped recurrence | Stays in `lessons-learned/` (retain) |
| Pure "this bug was fixed", no reusable rule | Delete (remove outright, Step 4) |

**Promotion-vs-ADR note**: a closed lesson's residue is a **standard, not an ADR**. A standard codifies *what to do* (a rule, convention, or contract a skill loads to change behavior); an ADR records *why a decision was made among weighed alternatives*. Promote a reusable rule into `standards/`/`references/` (or `CLAUDE.md`); reach for an ADR only when the residue is genuinely a decision with documented trade-offs, not an operating rule.

### Step 4: Remove completely-covered lessons

For lessons classified **completely covered** whose residue is already codified elsewhere (no durable reusable rule to relocate):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
  --lesson-id {id} --force --reason "{why} (plan {plan_id})"
```

This writes a tombstone — the removal stays auditable. The owning `{plan_id}` is folded into the `--reason` text (the `remove` verb has no separate plan flag) and is also captured by the Step 6 decision-log entry.

### Step 4b: Promote-then-retire residue-bearing lessons

For each lesson classified **completely covered, residue is a reusable rule**, promote the residue into its load-bearing home *before* retiring the lesson — never the reverse, so the rule is never momentarily lost:

1. **Promote** the reusable rule into the home selected by the **Placement test** — the governing skill's `standards/*.md` / `references/*.md` (or `CLAUDE.md` for repo-wide rules) — using the `Edit` tool:

   ```
   Edit: marketplace/bundles/{bundle}/skills/{skill}/standards/{file}.md   (or references/{file}.md, or CLAUDE.md)
   ```

   Write the rule as a durable standard in the host doc's voice (not a transcription of the lesson record).

   The promoted rule MUST NOT embed a lesson identifier in its prose: the plugin-doctor `no-lesson-id-in-skill-prose` rule — build-failing under `quality-gate` — rejects exactly that citation shape in exactly the `standards/` / `references/` scope this step writes to. Provenance is already recoverable without an in-prose citation, from the Step 4b.2 tombstone's `--reason "residue promoted to {target}"` plus the Step 6 decision-log entry naming the retired lesson. A citation-bearing promotion is therefore an authoring error to be written correctly the first time, not a finding to suppress.

2. **Retire** the now-promoted lesson via the tombstone-writing `remove` verb — never by deleting the file:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
     --lesson-id {id} --force --reason "residue promoted to {target} (plan {plan_id})"
   ```

   The `{target}` names the doc the rule was promoted into, so the tombstone records *where* the knowledge went.

Keep the bias-to-retain posture: Step 4b fires only when the residue clearly maps to a load-bearing home per the Placement test. If the residue's home is ambiguous, **retain** the lesson untouched rather than guessing. A failed promotion (Step 4b.1) leaves the lesson in place and does NOT proceed to the retirement in Step 4b.2 — see Error Handling.

### Step 5: Trim partially-covered lessons

Use the `Edit` tool directly against the lesson body:

```
Edit: .plan/local/lessons-learned/{id}.md
```

Trim **only** the now-covered portion. Preserve the `key=value` header block at the top of the file verbatim, and preserve every still-relevant section of the body.

### Step 6: Log every change

Record a decision-log entry for **every** removal, **every** promote-then-retire, **every** adaptation, **and every** deliberate retain. For a promotion, name the target doc the residue was promoted into:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(project:finalize-step-lessons-housekeeping) {removed|promoted|adapted|retained} {id}: {reason}"
```

### Step 7: Record the step outcome

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "{N} removed, {P} promoted, {M} adapted, {K} retained"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Empty lessons corpus | Skip-clean exit — record `mark-step-done --outcome done --display-detail "0 lessons — nothing to reconcile"` so the `phase_steps_complete` handshake counts the step as done |
| Coverage ambiguous (including ambiguous residue home) | Retain the lesson untouched (bias to retain) and log the no-action decision via `manage-logging decision` |
| `manage-lessons remove` failure on one lesson | Non-fatal — log the failure, leave that lesson in place, and continue with the remaining lessons. Housekeeping must never block finalize. |
| Promotion `Edit` failure (Step 4b.1) on one lesson | Non-fatal — log the failure, leave the lesson in place, and **do NOT** proceed to the Step 4b.2 retirement for that lesson. A retirement without a successful promotion would lose the rule, so the two stay atomic-by-convention: no promotion, no retire. Continue with the remaining lessons. |
| Promote-then-retire disposition — commit carriage | The step issues no git call. Its promotion edits are committed onto the feature branch by the dispatcher's commit instrumentation (phase-6-finalize Step 3 item 5f); because the step runs in the settle band it never writes source after the push barrier, so a promotion whose commit is not carried by the dispatcher leaves no uncommitted edit behind. |
| Adaptation `Edit` failure on one lesson | Non-fatal — log the failure, leave that lesson untouched, and continue. |
| Missing `quality-verification-report.md` | Non-fatal — proceed using `request.md` + `modified_files` alone; log that the retrospective report was unavailable |
| Step completes | Record `mark-step-done --outcome done --display-detail "{N} removed, {P} promoted, {M} adapted, {K} retained"` |

The step's posture is **non-fatal throughout**: finalize must never abort because lessons housekeeping hit a snag on an individual lesson.

## Related

- [.claude/skills/finalize-step-plugin-doctor/SKILL.md](../finalize-step-plugin-doctor/SKILL.md) — sibling project-local finalize step (reads references.json, acts per-item)
- [.claude/skills/finalize-step-deploy-target/SKILL.md](../finalize-step-deploy-target/SKILL.md) — sibling project-local finalize step
- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling project-local finalize step
- `plan-marshall:manage-lessons` — lesson corpus management (list, remove with tombstone)
- `plan-marshall:manage-logging` — decision-log infrastructure used to audit every change
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
