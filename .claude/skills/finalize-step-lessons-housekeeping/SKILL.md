---
lane:
  class: prunable
  tier: minimal
  prunable_when: footprint_no_lesson_component
  cost_size: L
name: finalize-step-lessons-housekeeping
description: Finalize-phase wrapper that reconciles the just-finished plan's outcome against the lessons-learned corpus — resolving that corpus through the explicit main-anchored store handle so the step's position in the finalize order cannot decide what it sees, then removing fully-covered lessons, promoting reusable residue into the governing skill before retiring the lesson, trimming partially-covered ones, and naming the substrate every reported count was computed from
user-invocable: false
mode: workflow
allowed-tools: Bash, Read, Edit
order: 4
mutates_source: true
head_dependent: true
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

Both removal dispositions run behind a **two-key retirement path**: Step 3's Evidence bar produces a verdict that names the covering clause and the concrete input its worked example resolves, and Steps 4.1 / 4b.2 turn the second key by independently re-reading that example before any `remove` call fires. A verdict that cannot be evidenced caps at *Partially covered* and is trimmed instead of deleted.

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

## HEAD-dependency

This step declares `head_dependent: true` in its frontmatter — that fact IS the membership declaration the dispatcher's re-entry check reads (see [ext-point-finalize-step.md](../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"; the governing discriminator lives there and is deliberately not restated here).

It matches on the settle-stage shape: this is a pre-merge settle-band step whose edits land directly in the worktree (`mutates_source: true` — the Step 4b promotions write governing-skill docs). Those edits were computed against the HEAD this step read, so a HEAD advance supersedes them. Concretely, the classification in Step 3 reasons about *what the plan changed* from `modified_files` and the plan outcome; a loop-back commit landing after this step recorded `done` changes that input, so a lesson that was correctly retained against the old HEAD may be completely covered against the new one — and the standing `done` record would let the corpus ship unreconciled. The empty-corpus skip-clean exit (Step 2) is the sharpest case, because it records `done` while having changed nothing.

Both `--outcome done` records therefore capture the worktree HEAD immediately before their `mark-step-done` call and forward it via `--head-at-completion {sha}`: the Step 7 completion record and the Step 2 empty-corpus skip-clean record. Re-firing is safe: the classification is a fresh read each time, and the pass is non-fatal throughout.

## Direct-file-access allowance

This step is granted **direct `Read`/`Edit` access to `.plan/local/lessons-learned/**`** as a documented exception to the CLAUDE.md "`.plan/` access: scripts only" hard rule. That rule itself carves out the exception: *"Never Read/Write/Edit `.plan/` files directly unless a loaded skill's workflow explicitly documents it."* This section is that explicit documentation.

The exception is deliberately narrow:

- **Removals still route through `manage-lessons remove`** — never delete a lesson `.md` file directly. The script writes an auditable tombstone carrying the retirement verdict and its evidence (`coverage_verdict`, `covering_clause`, `covering_input`), which the direct-`Edit` path cannot. Deleting the file directly would bypass the required `--coverage-verdict` and its evidence pair entirely — i.e. it would retire a lesson with no recorded justification, which is exactly what the two-key path exists to prevent. This applies equally to the promote-then-retire disposition (Step 4b): after the residue is promoted and the Step 4b.2 gate passes, the lesson is retired via `manage-lessons remove`, never by deleting the file. A removal the script **rejects** (a `completely_covered` verdict without both evidence flags) is likewise never to be completed by hand — see Error Handling.
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

The step runs inside the pre-merge settle band, so its promotion edits are linted by `default:pre-push-quality-gate` and shipped by the single `default:push` barrier. The step itself issues **no tree-mutating git call** — it reads HEAD (Steps 2 and 7) but never stages, commits, or pushes — and invents no push path: the dispatcher's commit instrumentation (phase-6-finalize Step 3 item 5f) commits every settle-band mutating step's edits onto the feature branch before the barrier runs.

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

### Step 2: Resolve the corpus substrate, then enumerate it

**Resolve the substrate FIRST.** This step's position in the finalize order must not determine which corpus it can see: it runs in the pre-merge settle band with cwd pinned to the plan's worktree, and a cwd-keyed corpus read there would reach a different — usually empty — store than the one the plan's lessons actually live in. Resolve the store through the explicit main-anchored handle and capture how it resolved:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list-stalled
```

Read `store_resolution` (`main_anchored` / `override` / `unresolved`) and `plans_root` from the payload. `list-stalled` is used here purely as the substrate probe — it resolves the same main-anchored store `list` reads and is the only verb that REPORTS the resolution. Retain both values as `{store_resolution}` and `{corpus_path}` (the lessons-learned sibling of the reported `plans_root`); every outcome line below names them.

The verb resolves two stores — the plans root and the lessons corpus — and reports the resolution of whichever one **failed**, so `store_resolution: unresolved` here means the corpus this step reconciles against was not reached, whether or not the plans root was. `unresolved_store` (`plans` | `lessons`) names which one, and `plans_root` is empty on that branch; both are for the log line, not for the branch. Branch on `store_resolution` alone.

**Unresolvable-store exit (`store_resolution: unresolved`)**: the corpus was never reached, so this step has classified nothing. It MUST NOT report a clean reconciliation. Record the step `done` (housekeeping is non-fatal and must never block finalize) with a `display_detail` that names the failure to look:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) Lessons corpus UNRESOLVED (unresolved_store={unresolved_store}) — nothing was read or reconciled, this is NOT a clean-corpus result"
```

Then mark done with `--display-detail "corpus unresolved — nothing read"` following the HEAD-capture sequence below.

**Enumerate** (only when the store resolved):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
```

**Empty-corpus skip-clean exit**: if zero lessons exist, log and record the step as done, then return. The line MUST name the substrate the zero was computed from — a bare "0 lessons" cannot be told apart from a corpus that was never read:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) 0 lessons in {corpus_path} ({store_resolution}) — nothing to reconcile"
```

Resolve the worktree HEAD SHA immediately before marking done, per § HEAD-dependency (substitute `.` for `{worktree_path}` on the main-checkout flow):

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "0 lessons in {store_resolution} corpus — nothing to reconcile" \
  --head-at-completion {sha}
```

**Out of scope — the classify/apply split.** Resolving the substrate explicitly closes the *which corpus did I read* question, not the *where may I write* one. Splitting this step into a main-anchored classify pass and a separately-scheduled pushable apply pass is deliberately NOT done here: it is a finalize band-contract change (whether a `mutates_source: true` step may run post-merge, and the reordering that follows) owned by `PLAN-CIS-034`.

### Step 3: Classify each lesson's coverage against the plan outcome

For each lesson, classify it against the plan outcome using a **conservative subsumption bar**:

- **Completely covered** — requires that the lesson's guarded failure mode can no longer occur, **OR** its recommended practice is now codified/enforced by this plan. Nothing weaker qualifies, and the **Evidence bar** below must additionally be met. The residue is already codified elsewhere, so the lesson is removed outright (Step 4).
- **Completely covered, residue is a reusable rule** — the lesson's guarded failure mode can no longer occur (so it qualifies as completely covered, **Evidence bar** included) **AND** the lesson body still carries a durable reusable rule — an operating rule, a convention, an anti-pattern, or a contract-guard — whose correct home is the governing skill's `standards/`/`references/` (or `CLAUDE.md` for repo-wide rules) rather than the lessons queue. Distinguish it from plain "Completely covered" (residue already codified elsewhere → remove outright) using the **Placement test** below. This classification routes to the promote-then-retire disposition (Step 4b).
- **Partially covered** — the plan eliminated or codified *part* of what the lesson guards, but a residual concern remains.
- **Ambiguous / none** — anything that does not clearly meet the bar above. **Leave untouched (bias to retain)** and log the no-action decision.

When in doubt, retain. The cost of keeping a stale lesson is far lower than the cost of deleting a still-load-bearing one. Promote-then-retire fires only when the residue clearly maps to a load-bearing home; an ambiguous residue retains.

### Evidence bar: a completely-covered verdict must name its clause and its input

Both completely-covered classifications above carry an evidence requirement that a verdict must satisfy *before* it is allowed to become a removal. The verdict must be expressible as **one sentence** that names two things:

1. **The clause** that codifies the rule the lesson taught — a specific, re-readable location (a named section of a `standards/*.md`, a `SKILL.md` heading, a `CLAUDE.md` hard rule), not "the docs" or "the new implementation".
2. **The concrete input** on which *that clause's own worked example* produces the correct result — an actual value, invocation, or case, checked against the example the clause itself carries.

The second half is the load-bearing half. A clause can codify a rule correctly and still ship a worked example that contradicts it; a verdict resting on such a clause is asserting coverage the corpus does not actually have. Naming the input forces the claim to be checked against the example rather than against the clause's title.

**When that sentence cannot be written, the lesson does NOT qualify as completely covered.** It caps at **Partially covered** and routes to the Step 5 trim, not the Step 4 removal. This is a downgrade, not a failure: the covered portion is still trimmed, and the lesson survives to be re-evaluated by a later plan. Inability to name the clause, inability to name an input, or an example that does not resolve the named input are three separate ways to fall to this cap — all three cap.

The sentence's two halves become the `--covering-clause` and `--covering-input` arguments that Steps 4 and 4b pass to `manage-lessons remove`, so the evidence is recorded on the tombstone and survives the deletion it justified.

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

For lessons classified **completely covered** whose residue is already codified elsewhere (no durable reusable rule to relocate). Classifying and deleting are two separate keys: Step 3's Evidence bar produced the verdict, and the gate below is what turns that verdict into a removal.

**Step 4.1 — Independent reconfirmation (gate — run this BEFORE the removal call in Step 4.2).**

Re-open the clause named by the Step 3 evidence sentence and **re-read its own worked example**. Do not reuse the Step 3 reading or the recollection of it — the whole point of a second key is that it is turned independently of the first. Confirm both of the following against what the example actually says:

1. The clause is where the evidence sentence says it is, and it still codifies the rule the lesson taught.
2. Applying that clause's **own worked example** to the named `{input}` produces the correct result — the example agrees with the clause it illustrates.

**The gate FAILS** when any of these holds: the clause cannot be found at the named location; the example resolves a different input than the one named; or the example produces a result that contradicts its own clause. On failure, do NOT call `remove`. Downgrade the lesson to **Partially covered**, route it to the Step 5 trim, and log the downgrade via `manage-logging decision` naming which of the three failures fired. A contradicting example is precisely the case this gate exists to catch — a lesson whose retirement rested on it must survive, not be deleted on the strength of a clause the example does not support.

**Step 4.2 — Remove** (reached only when the Step 4.1 gate passed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
  --lesson-id {id} --force --reason "{why} (plan {plan_id})" \
  --coverage-verdict completely_covered \
  --covering-clause "{clause}" \
  --covering-input "{input}"
```

`{clause}` and `{input}` are the two halves of the Step 3 evidence sentence, re-confirmed by Step 4.1 — pass them verbatim, never a paraphrase or a placeholder. `--coverage-verdict` is required on every `remove` and `completely_covered` is rejected at argparse without BOTH evidence flags, so an unevidenced retirement cannot reach the corpus; see `plan-marshall:manage-lessons` § Retirement evidence. A rejection is non-fatal per-lesson — see Error Handling.

This writes a tombstone carrying `coverage_verdict`, `covering_clause`, and `covering_input`, so the evidence outlives the lesson it deleted and the removal stays auditable. The owning `{plan_id}` is folded into the `--reason` text (the `remove` verb has no separate plan flag) and is also captured by the Step 6 decision-log entry.

### Step 4b: Promote-then-retire residue-bearing lessons

For each lesson classified **completely covered, residue is a reusable rule**, promote the residue into its load-bearing home *before* retiring the lesson — never the reverse, so the rule is never momentarily lost:

1. **Promote** the reusable rule into the home selected by the **Placement test** — the governing skill's `standards/*.md` / `references/*.md` (or `CLAUDE.md` for repo-wide rules) — using the `Edit` tool:

   ```text
   Edit: marketplace/bundles/{bundle}/skills/{skill}/standards/{file}.md   (or references/{file}.md, or CLAUDE.md)
   ```

   Write the rule as a durable standard in the host doc's voice (not a transcription of the lesson record).

   The promoted rule MUST NOT embed a lesson identifier in its prose: the plugin-doctor `no-lesson-id-in-skill-prose` rule — build-failing under `quality-gate` — rejects exactly that citation shape in exactly the `standards/` / `references/` scope this step writes to. Provenance is already recoverable without an in-prose citation, from the Step 4b.3 tombstone's `--reason "residue promoted to {target}"` plus the Step 6 decision-log entry naming the retired lesson. A citation-bearing promotion is therefore an authoring error to be written correctly the first time, not a finding to suppress.

2. **Independent reconfirmation (gate — run this BEFORE the retirement call in Step 4b.3).** The promotion in 4b.1 is what makes the clause exist, so the gate turns its second key against the doc as just written. Re-open the promoted rule at `{target}` and **re-read the worked example it now carries**, independently of the text just authored. Confirm both: the clause codifies the rule the lesson taught, and applying that clause's own worked example to the named `{input}` produces the correct result.

   **The gate FAILS** when the promoted clause carries no worked example, when its example resolves a different input than the one named, or when its example produces a result that contradicts the clause it illustrates. On failure, do NOT call `remove`: leave the promotion in place (it is a correct standalone doc improvement), retain the lesson, log the retained-not-retired decision naming which failure fired, and continue with the remaining lessons. A promotion whose example contradicts its own clause has not actually relocated the knowledge, so retiring the lesson against it would lose the rule.

3. **Retire** the now-promoted lesson via the tombstone-writing `remove` verb — never by deleting the file — reached only when the Step 4b.2 gate passed:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
     --lesson-id {id} --force --reason "residue promoted to {target} (plan {plan_id})" \
     --coverage-verdict completely_covered \
     --covering-clause "{target} — {promoted rule heading}" \
     --covering-input "{input}"
   ```

   The `{target}` names the doc the rule was promoted into, so the tombstone records *where* the knowledge went; `--covering-clause` pins that to the specific heading a later reader must re-open, and `--covering-input` records the case its worked example was confirmed against in Step 4b.2.

Keep the bias-to-retain posture: Step 4b fires only when the residue clearly maps to a load-bearing home per the Placement test. If the residue's home is ambiguous, **retain** the lesson untouched rather than guessing. A failed promotion (Step 4b.1) leaves the lesson in place and does NOT proceed to the Step 4b.2 gate or the Step 4b.3 retirement; a failed gate (Step 4b.2) likewise leaves the lesson in place and does NOT proceed to the retirement — see Error Handling.

### Step 5: Trim partially-covered lessons

Use the `Edit` tool directly against the lesson body:

```text
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

**The outcome line MUST name the substrate the counts were computed from.** `0 removed, 0 promoted, 0 adapted` is the same sentence whether the corpus was read and found clean or was never reached at all, and the two demand opposite responses. Carry `{store_resolution}` and `{corpus_path}` from Step 2 into both the work-log line and the `display_detail`, so no count in this step's record is ever substrate-blind.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) {N} removed, {P} promoted, {M} adapted, {K} retained over {C} lesson(s) in {corpus_path} ({store_resolution})"
```

Resolve the worktree HEAD SHA immediately before marking done, per § HEAD-dependency (substitute `.` for `{worktree_path}` on the main-checkout flow):

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward it via `--head-at-completion`. The `display_detail` is capped at 80 ASCII chars, so it carries the resolution token rather than the full path — the work-log line above carries the path:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "{N} rm, {P} promo, {M} adapt, {K} keep ({store_resolution} corpus)" \
  --head-at-completion {sha}
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Unresolvable lessons corpus (`store_resolution: unresolved` from the Step 2 substrate probe) | Non-fatal, but **never reported as clean** — the corpus was never read, so nothing was classified. Record `mark-step-done --outcome done --display-detail "corpus unresolved — nothing read" --head-at-completion {sha}` and emit the WARNING work-log line naming the failure to look. Distinguishing this from an empty corpus is the whole point: the two produce identical counts and demand opposite responses. |
| Empty lessons corpus (store resolved, zero lessons in it) | Skip-clean exit — record `mark-step-done --outcome done --display-detail "0 lessons in {store_resolution} corpus — nothing to reconcile" --head-at-completion {sha}` so the `phase_steps_complete` handshake counts the step as done and a later HEAD advance re-fires it. The `display_detail` names the substrate so the zero is not substrate-blind. |
| Coverage ambiguous (including ambiguous residue home) | Retain the lesson untouched (bias to retain) and log the no-action decision via `manage-logging decision` |
| `manage-lessons remove` failure on one lesson | Non-fatal — log the failure, leave that lesson in place, and continue with the remaining lessons. Housekeeping must never block finalize. |
| `manage-lessons remove` **evidence rejection** on one lesson (`--coverage-verdict completely_covered` without both evidence flags — argparse exit 2, or `error: missing_coverage_evidence` on the handler path) | Non-fatal per-lesson — the lesson is left in place by construction (the rejection precedes any unlink). Treat it as a **classification defect, not a call-shape defect**: the verdict claimed coverage the Step 3 Evidence bar could not evidence, so downgrade the lesson to Partially covered and route it to the Step 5 trim. Never re-issue the call with invented or placeholder evidence values to get past the rejection. Log the downgrade and continue with the remaining lessons. |
| Independent-reconfirmation gate failure (Step 4.1 or Step 4b.2) on one lesson | Non-fatal — the named clause is missing, its worked example resolves a different input, or its example contradicts its own clause. Do NOT call `remove`. On the Step 4 path, downgrade the lesson to Partially covered and route it to the Step 5 trim; on the Step 4b path, keep the promotion and retain the lesson. Log which of the three failures fired via `manage-logging decision` and continue with the remaining lessons. |
| Promotion `Edit` failure (Step 4b.1) on one lesson | Non-fatal — log the failure, leave the lesson in place, and **do NOT** proceed to the Step 4b.2 gate or the Step 4b.3 retirement for that lesson. A retirement without a successful promotion would lose the rule, so they stay atomic-by-convention: no promotion, no retire. Continue with the remaining lessons. |
| Promote-then-retire disposition — commit carriage | The step issues no tree-mutating git call (its only git calls are the read-only `rev-parse HEAD` in Steps 2 and 7). Its promotion edits are committed onto the feature branch by the dispatcher's commit instrumentation (phase-6-finalize Step 3 item 5f); because the step runs in the settle band it never writes source after the push barrier, every promotion edit it makes is still ahead of that commit and is therefore carried onto the branch — no promotion can be stranded as an uncommitted edit. |
| Adaptation `Edit` failure on one lesson | Non-fatal — log the failure, leave that lesson untouched, and continue. |
| Missing `quality-verification-report.md` | Non-fatal — proceed using `request.md` + `modified_files` alone; log that the retrospective report was unavailable |
| Step completes | Record `mark-step-done --outcome done --display-detail "{N} rm, {P} promo, {M} adapt, {K} keep ({store_resolution} corpus)" --head-at-completion {sha}`, plus the Step 7 work-log line naming `{corpus_path}`. Every count this step reports rides with the substrate it was computed from. |

The step's posture is **non-fatal throughout**: finalize must never abort because lessons housekeeping hit a snag on an individual lesson.

## Related

- [.claude/skills/finalize-step-plugin-doctor/SKILL.md](../finalize-step-plugin-doctor/SKILL.md) — sibling project-local finalize step (reads references.json, acts per-item)
- [.claude/skills/finalize-step-deploy-target/SKILL.md](../finalize-step-deploy-target/SKILL.md) — sibling project-local finalize step
- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling project-local finalize step
- `plan-marshall:manage-lessons` — lesson corpus management (list, remove with tombstone)
- `plan-marshall:manage-logging` — decision-log infrastructure used to audit every change
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
