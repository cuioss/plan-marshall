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
records_facts:
  - classified_at
  - work_performed
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

The step is re-fired whenever HEAD advances. A re-fire does not judge the whole corpus again: the **delta rule** (Step 2b) names the lessons the advance could affect, the step judges those, and every other lesson keeps the result of the previous firing. When there is no trustworthy previous firing to carry results over from, the rule falls back to judging the whole corpus.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-lessons-housekeeping` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to read the plan outcome and to scope decision-log entries)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

This step edits tracked source (its Step 4b promotions write governing-skill docs), so it declares `mutates_source: true` and MUST run in the **pre-merge settle band** (`order < 11`):

- **before `default:pre-push-quality-gate` (5)** — so its promotion edits are linted in the same finalize run that wrote them, rather than surfacing as a lint failure on a later plan.
- **before `default:push` (11) and `default:branch-cleanup` (70)** — so those edits are pushable onto the still-open feature branch and covered by the PR's CI run and review.

This settle-band constraint **supersedes** the former requirement to run after `plan-marshall:plan-retrospective` (order 995): pushability of source edits outranks reading a retrospective artifact that this step already treats as best-effort. See [marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md) for the governing contract.

## HEAD-dependency

This step declares `head_dependent: true` in its frontmatter — that fact IS the membership declaration the dispatcher's re-entry check reads (see [ext-point-finalize-step.md](../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"; the governing discriminator lives there and is deliberately not restated here).

It matches on the settle-stage shape: this is a pre-merge settle-band step whose edits land directly in the worktree (`mutates_source: true` — the Step 4b promotions write governing-skill docs). Those edits were computed against the HEAD this step read, so a HEAD advance supersedes them. Concretely, the classification in Step 3 reasons about *what the plan changed* from the plan's realized footprint and the plan outcome; a loop-back commit landing after this step recorded `done` changes that input, so a lesson that was correctly retained against the old HEAD may be completely covered against the new one — and the standing `done` record would let the corpus ship unreconciled. The empty-corpus skip-clean exit (Step 2) is the sharpest case, because it records `done` while having changed nothing.

Every `--outcome done` record therefore captures the worktree HEAD immediately before its `mark-step-done` call and forwards it via `--head-at-completion {sha}`: the Step 7 completion record and the two Step 2 exits that examined no corpus (unresolved store, empty corpus).

Re-firing is safe, and bounded by the delta rule (Step 2b) rather than by re-reading everything. A lesson's coverage verdict is a function of two things: the lesson's own content, and the files the lesson is about. A re-fire re-judges every lesson for which either moved since the previous firing started — the lesson file was edited or added, or a changed path lies under its component's standards directory or under a path its body names — and carries the previous result over only for a lesson where neither moved. The rule's premise is stated rather than hidden: a commit can change a lesson's verdict only through a file the lesson is about. Whenever the previous firing cannot serve as a carry-over source — no record, no computable difference, or a record that did not finish cleanly under this rule — the whole corpus is judged, exactly as on a first firing. The pass is non-fatal throughout.

### Verdict-input surface — deliberately undeclared

This step declares **no** `verdict_inputs`, so the dispatcher's verdict-currency classifier never narrows its re-fire: every HEAD advance re-runs it. The absence is a recorded refusal on evidence, not a declaration left unwritten.

A `verdict_inputs` declaration is a set of globs over **tracked** paths, and the classifier decides currency from the tree difference between two commits (see [verdict-currency.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md) § "The classification"). Most of what this step's verdict reads is not in any tree:

- **The plan's own records.** Step 1 derives the plan's realized footprint and reads the request document. The request document lives in the plan directory under the git-ignored `.plan/local/`, so no commit carries it and no tree difference reports a change to it. The realized footprint is derived at run time from the worktree — the diff against a base ref that moves without any commit on this branch, plus the uncommitted working-tree state — so it is a discovered set rather than a fixed list of tracked paths.
- **The lessons corpus.** Step 2 enumerates the main-anchored corpus under `.plan/local/lessons-learned/`, and Step 3 classifies every lesson in it. The corpus is git-ignored too: a lesson added, trimmed or removed between two firings changes this step's verdict while the two trees compare equal.
- **Whichever standards clause a lesson names.** The Evidence bar re-reads the clause a completely-covered verdict cites and that clause's own worked example. Those files are tracked, but which ones are read is decided by the lessons in the corpus at run time, so the set cannot be written down ahead of the run.

A glob can name none of the first two inputs, and the third is discovered rather than fixed. An advance that touches no declared path would therefore be classified `preserved` while the corpus or the plan's records had moved underneath it — a skip the declaration could not license. Declaring nothing keeps the fail-closed default and says so.

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
...                                             (settle band, order < 11)
default:push                                    (11)
```

The step runs inside the pre-merge settle band, so its promotion edits are linted by `default:pre-push-quality-gate` and shipped by the single `default:push` barrier. The step itself issues **no tree-mutating git call** — it reads HEAD (Steps 2 and 7) but never stages, commits, or pushes — and invents no push path: the dispatcher's commit instrumentation (phase-6-finalize Step 3 item 5f) commits every settle-band mutating step's edits onto the feature branch before the barrier runs.

## Workflow

### Step 1: Read the just-finished plan's outcome

Resolve the worktree path first — the footprint below is derived from that tree, and Steps 2 and 7 read HEAD from it:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

Capture `worktree_path` as `{worktree_path}` (substitute `.` on the main-checkout flow, where the returned path is empty). Then derive the plan's **realized footprint** — the files the plan actually changed, computed live from the worktree's git state rather than read from a stored list:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path}
```

On `status: success`, `files` is the realized footprint and `live_count` its size. **Branch on `status` before reading `files`**: an error payload carries no `files` key, and an absent footprint is never an empty one — "the plan changed nothing" and "the footprint could not be derived" demand different classifications in Step 3. Every error outcome is **non-fatal**: log the named error and continue on the request document alone, classifying under the bias-to-retain posture because what the plan changed is unknown.

| `error` | What it means | Action |
|---------|---------------|--------|
| `worktree_not_found` | `{worktree_path}` does not exist or is not a directory | Log the named error; continue on the request document alone |
| `references_not_found` | the plan has no `references.json`, so the diff base cannot be resolved | Log the named error; continue on the request document alone |
| `not_a_git_worktree` | `{worktree_path}` exists but is not inside a git worktree | Log the named error; continue on the request document alone |
| `git_error` | the base ref does not resolve in the worktree, or the diff itself failed — the payload's `message` says which | Log the named error with its `message`; continue on the request document alone |
| `files_out_refused` | a `--files-out` destination the verb declines to write | Log the named error; continue on the request document alone. This step passes no `--files-out`, so reaching it means the call was altered — do not retry with a different destination |
| `files_out_unwritable` | a `--files-out` destination that could not be written | Log the named error; continue on the request document alone. Same note as `files_out_refused` |

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) Realized footprint UNAVAILABLE: {error} — classifying on the request document alone, this is NOT an empty footprint"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Read the retrospective's quality-verification report (written by `plan-marshall:plan-retrospective`, order 995). At this step's settle-band order the retrospective has not yet run, so this read is **best-effort**: the report is normally absent, and its absence is already non-fatal — see the "Missing `quality-verification-report.md`" row in Error Handling, which proceeds on the request document and the realized footprint alone.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file quality-verification-report.md
```

Together these establish what the plan changed (the realized footprint), why (the request), and the verified outcome — the basis for coverage classification.

### Step 2: Resolve the corpus substrate, then enumerate it

**Resolve the substrate FIRST.** This step's position in the finalize order must not determine which corpus it can see: it runs in the pre-merge settle band with cwd pinned to the plan's worktree, and a cwd-keyed corpus read there would reach a different — usually empty — store than the one the plan's lessons actually live in. Resolve the store through the explicit main-anchored handle and capture how it resolved:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list-stalled
```

Read `store_resolution` (`main_anchored` / `override` / `unresolved`) and `plans_root` from the payload. `list-stalled` is used here purely as the substrate probe — it resolves the same main-anchored store `list` reads and is the only verb that REPORTS the resolution. Retain both values as `{store_resolution}` and `{corpus_path}` (the lessons-learned sibling of the reported `plans_root`); every outcome line below names them.

The verb resolves two stores — the plans root and the lessons corpus — and **both are required**, so `store_resolution: unresolved` here means *a required store* was not reached. It does **not** say which: the verb reports the first failing store, preferring `plans`, so `unresolved_store: plans` is silent about whether the lessons corpus resolved. Read `unresolved_store` (`plans` | `lessons`) as the name of the store that actually failed and carry it into every outcome line below, so this step names the store it observed failing instead of asserting a state it never observed. `plans_root` is empty on that branch.

Branch on `store_resolution` alone. Either store failing leaves this step with no scanned corpus, so `unresolved_store` selects the wording, never the branch.

**Unresolvable-store exit (`store_resolution: unresolved`)**: a required store was never reached, so this step scanned no corpus and classified nothing. It MUST NOT report a clean reconciliation. Record the step `done` (housekeeping is non-fatal and must never block finalize) with a `display_detail` that names the failure to look:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) Required store UNRESOLVED: {unresolved_store} — nothing was read or reconciled, this is NOT a clean-corpus result"
```

Resolve the worktree HEAD SHA immediately before marking done, per § HEAD-dependency (`{worktree_path}` is the value Step 1 resolved):

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}`, then record the exit. It examined no corpus, so it records `work_performed=false` and no `classified_at` — the next firing finds no carry-over anchor and judges the whole corpus:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "{unresolved_store} store unresolved — nothing read" \
  --head-at-completion {sha} \
  --fact work_performed=false
```

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

Capture stdout as `{sha}` and forward it via `--head-at-completion`. An empty corpus was looked at but nothing in it was judged, so the record carries `work_performed=false` and no `classified_at`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "0 lessons in {store_resolution} corpus — nothing to reconcile" \
  --head-at-completion {sha} \
  --fact work_performed=false
```

**Out of scope — the classify/apply split.** Resolving the substrate explicitly closes the *which corpus did I read* question, not the *where may I write* one. Splitting this step into a main-anchored classify pass and a separately-scheduled pushable apply pass is deliberately NOT done here: it is a finalize band-contract change (whether a `mutates_source: true` step may run post-merge, and the reordering that follows) owned by `PLAN-CIS-034`.

### Step 2b: Select what this firing judges (the delta rule)

A re-fire judges only the lessons the HEAD advance could affect. Call the script **once**, after the corpus is enumerated and before any lesson is judged:

```bash
python3 .plan/execute-script.py default-bundle:finalize-step-lessons-housekeeping:affected_lessons resolve \
  --plan-id {plan_id} --worktree-path {worktree_path}
```

**The call is also the firing-start capture.** The script stamps the time on entry, before it reads the corpus, and returns it as `firing_started_at` on every payload — `mode: full`, `mode: delta` and `status: error` alike. Retain it as `{firing_started_at}`; Step 7 records it as the `classified_at` fact, which is what the next firing measures "edited since" against. Because it is the *start* of the firing, a lesson this firing itself trims in Step 5 is later than it and is re-examined next time.

Read `status` first, then `mode`.

**`mode: delta`** — the payload carries `recorded_head`, `live_head`, the counts `examined` and `carried_over`, and `affected`: the lessons to judge, each with the `reason` it was selected for.

| `reason` | The lesson is affected because |
|----------|--------------------------------|
| `edited_since_last_firing` | its file was modified after the previous firing started — which also covers a lesson added since |
| `standards_dir_changed` | a changed path lies under the standards directory of the lesson's component |
| `named_path_changed` | a changed path equals, or lies under, a path the lesson body names in backticks |

Run Steps 3 to 5 over the lessons in `affected` **only**. Every other lesson keeps the result of the previous firing: it is not re-read, not re-judged and not edited. Retain `carried_over` as `{X}` for the Step 7 outcome line.

**The empty delta is an answer, not a gap.** When the commit touched only files that match no lesson and no lesson changed, `affected` is absent and `examined` is `0`. The answer is **none — carry the previous result**: skip Steps 3 to 5 entirely, and proceed to Step 7 with zero removed, promoted, adapted and retained and `{X}` equal to the corpus size.

**`mode: full`** — judge the whole corpus as enumerated in Step 2, exactly as a first firing does; `{X}` is `0`. The payload names why in `reason`. There are exactly three full-run conditions:

1. **First firing** (`first_firing`) — the step has no record for this plan.
2. **No computable difference** (`diff_unavailable`) — the difference between the previous firing's commit and the live HEAD could not be computed.
3. **The previous firing did not finish cleanly under this rule** — reached by three routes, each with its own `reason`:
   - `last_firing_not_done` — the previous record is not a completed one, or carries no commit.
   - `classified_at_absent` — the previous record is complete but carries no `classified_at` fact.
   - `classified_at_unreadable` — the fact is present but is not a timestamp.

A record without a readable `classified_at` always forces a full run. The script never infers a carry-over anchor from `head_at_completion` alone: that SHA says which tree the record was computed against, not which lessons had been judged by then.

**The commit re-stamp is a known, accepted route into the third condition.** This step declares both `mutates_source` and `head_dependent`, so whenever a firing edits source the dispatcher commits the edit and re-stamps the step record with the new HEAD and no fact arguments (see [phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) Step 3 item 5f). The re-stamped record carries neither `classified_at` nor `work_performed`, so the next firing after a source-editing firing reports `classified_at_absent` and runs in full. That is the fallback working as designed, not an error. It follows that the delta rule saves work only after firings that edited no source. The facts are deliberately not carried through the re-stamp: doing so would mean editing the dispatcher and `manage-status`, and a full run after a firing that changed governing docs is the conservative answer anyway.

**`status: error`** — the script could not look at something it needs (the change list, the lessons store, a lesson file, or the component-to-directory mapping); `error` names which. Treat every error as `mode: full`: judge the whole corpus and log the named error. Non-fatal.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) Delta rule unavailable: {error} — judging the whole corpus"
```

When the call returns no payload at all, there is no `{firing_started_at}` either: judge the whole corpus and record Step 7 without the `classified_at` fact, so the next firing runs in full too.

### Step 3: Classify each lesson's coverage against the plan outcome

For each lesson Step 2b selected — the `affected` lessons on `mode: delta`, the whole corpus on `mode: full` — classify it against the plan outcome using a **conservative subsumption bar**:

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
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) {N} removed, {P} promoted, {M} adapted, {K} retained, {X} carried over from the previous firing — {C} lesson(s) in {corpus_path} ({store_resolution})"
```

`{X}` is the Step 2b `carried_over` count (`0` on a full run). A carried-over lesson was not judged by this firing, so it is counted apart from `{K}`: a retained lesson was examined and kept, a carried-over one was not examined at all.

Resolve the worktree HEAD SHA immediately before marking done, per § HEAD-dependency (substitute `.` for `{worktree_path}` on the main-checkout flow):

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward it via `--head-at-completion`. The `display_detail` is capped at 80 ASCII chars, so it carries the resolution token rather than the full path — the work-log line above carries the path.

The record carries two facts. `classified_at` is the `{firing_started_at}` Step 2b returned — the anchor the next firing's delta rule measures against. `work_performed=true` says this firing examined a corpus, which the two Step 2 exits did not:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "{N} rm, {P} promo, {M} adapt, {K} keep, {X} carried ({store_resolution} corpus)" \
  --head-at-completion {sha} \
  --fact classified_at={firing_started_at} \
  --fact work_performed=true
```

Omit `--fact classified_at=…` only when Step 2b returned no payload at all and so no `{firing_started_at}` exists; `work_performed=true` is still recorded.

## Error Handling

| Scenario | Action |
|----------|--------|
| Unresolvable required store (`store_resolution: unresolved` from the Step 2 substrate probe; `unresolved_store` names whether the `plans` root or the `lessons` corpus failed) | Non-fatal, but **never reported as clean** — no corpus was scanned, so nothing was classified. Record `mark-step-done --outcome done --display-detail "{unresolved_store} store unresolved — nothing read" --head-at-completion {sha} --fact work_performed=false` and emit the WARNING work-log line naming the store that failed. Distinguishing this from an empty corpus is the whole point: the two produce identical counts and demand opposite responses. |
| Empty lessons corpus (store resolved, zero lessons in it) | Skip-clean exit — record `mark-step-done --outcome done --display-detail "0 lessons in {store_resolution} corpus — nothing to reconcile" --head-at-completion {sha} --fact work_performed=false` so the `phase_steps_complete` handshake counts the step as done and a later HEAD advance re-fires it. The `display_detail` names the substrate so the zero is not substrate-blind. |
| Coverage ambiguous (including ambiguous residue home) | Retain the lesson untouched (bias to retain) and log the no-action decision via `manage-logging decision` |
| `manage-lessons remove` failure on one lesson | Non-fatal — log the failure, leave that lesson in place, and continue with the remaining lessons. Housekeeping must never block finalize. |
| `manage-lessons remove` **evidence rejection** on one lesson (`--coverage-verdict completely_covered` without both evidence flags — argparse exit 2, or `error: missing_coverage_evidence` on the handler path) | Non-fatal per-lesson — the lesson is left in place by construction (the rejection precedes any unlink). Treat it as a **classification defect, not a call-shape defect**: the verdict claimed coverage the Step 3 Evidence bar could not evidence, so downgrade the lesson to Partially covered and route it to the Step 5 trim. Never re-issue the call with invented or placeholder evidence values to get past the rejection. Log the downgrade and continue with the remaining lessons. |
| Independent-reconfirmation gate failure (Step 4.1 or Step 4b.2) on one lesson | Non-fatal — the named clause is missing, its worked example resolves a different input, or its example contradicts its own clause. Do NOT call `remove`. On the Step 4 path, downgrade the lesson to Partially covered and route it to the Step 5 trim; on the Step 4b path, keep the promotion and retain the lesson. Log which of the three failures fired via `manage-logging decision` and continue with the remaining lessons. |
| Promotion `Edit` failure (Step 4b.1) on one lesson | Non-fatal — log the failure, leave the lesson in place, and **do NOT** proceed to the Step 4b.2 gate or the Step 4b.3 retirement for that lesson. A retirement without a successful promotion would lose the rule, so they stay atomic-by-convention: no promotion, no retire. Continue with the remaining lessons. |
| Promote-then-retire disposition — commit carriage | The step issues no tree-mutating git call (its only git calls are the read-only `rev-parse HEAD` in Steps 2 and 7). Its promotion edits are committed onto the feature branch by the dispatcher's commit instrumentation (phase-6-finalize Step 3 item 5f); because the step runs in the settle band it never writes source after the push barrier, every promotion edit it makes is still ahead of that commit and is therefore carried onto the branch — no promotion can be stranded as an uncommitted edit. |
| Adaptation `Edit` failure on one lesson | Non-fatal — log the failure, leave that lesson untouched, and continue. |
| Missing `quality-verification-report.md` | Non-fatal — proceed using the request document and the realized footprint alone; log that the retrospective report was unavailable |
| `compute-footprint` error in Step 1 (`worktree_not_found`, `references_not_found`, `not_a_git_worktree`, `git_error`, `files_out_refused`, `files_out_unwritable`) | Non-fatal — log the named error and continue on the request document alone. Never treat the missing footprint as an empty one: the Step 1 table states the action per error |
| `affected_lessons resolve` returns `status: error` in Step 2b (the change list, the lessons store, a lesson file, or the component-to-directory mapping could not be looked at) | Non-fatal — fall back to a full run: judge the whole corpus, log the named `error`, and record Step 7 with the returned `{firing_started_at}`. An error is never read as an empty delta. |
| `affected_lessons resolve` returns `mode: full` in Step 2b | Not an error — one of the three full-run conditions holds (see Step 2b). Judge the whole corpus. `classified_at_absent` after a source-editing firing is the expected consequence of the dispatcher's commit re-stamp. |
| `affected_lessons resolve` returns `mode: delta` with no `affected` lessons | The empty delta: none — carry the previous result. Skip Steps 3 to 5 and record Step 7 with every count but `{X}` at zero. |
| Step completes | Record `mark-step-done --outcome done --display-detail "{N} rm, {P} promo, {M} adapt, {K} keep, {X} carried ({store_resolution} corpus)" --head-at-completion {sha} --fact classified_at={firing_started_at} --fact work_performed=true`, plus the Step 7 work-log line naming `{corpus_path}`. Every count this step reports rides with the substrate it was computed from. |

The step's posture is **non-fatal throughout**: finalize must never abort because lessons housekeeping hit a snag on an individual lesson.

## Canonical invocations

The canonical argparse surface for the one script this skill registers, `affected_lessons.py`. A project-local script is registered under the `default-bundle:{skill}:{script}` notation.

### affected_lessons — resolve

```bash
python3 .plan/execute-script.py default-bundle:finalize-step-lessons-housekeeping:affected_lessons resolve \
  --plan-id PLAN_ID --worktree-path WORKTREE_PATH
```

Returns `mode: full` (with a `reason`), `mode: delta` (with `affected`, `examined` and `carried_over`), or `status: error` (with a named `error`). Every payload carries `firing_started_at`. The exit code is `0` on all three; branch on `status`, then `mode`. See Step 2b for the contract.

## Related

- [.claude/skills/finalize-step-plugin-doctor/SKILL.md](../finalize-step-plugin-doctor/SKILL.md) — sibling project-local finalize step (reads references.json, acts per-item)
- [.claude/skills/finalize-step-deploy-target/SKILL.md](../finalize-step-deploy-target/SKILL.md) — sibling project-local finalize step
- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling project-local finalize step
- `plan-marshall:manage-lessons` — lesson corpus management (list, remove with tombstone)
- `plan-marshall:manage-logging` — decision-log infrastructure used to audit every change
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
