---
lane:
  class: prunable
  prunable_when: no_code_delta
  cost_size: M
name: finalize-step-review-retrospective
description: Finalize-phase wrapper that compares the PR's automated and human reviewers — a deterministic per-reviewer metrics pass (raw vs actionable vs meta comments, resolution buckets, %-resolved-as-fixed) augmented by an LLM qualitative quality judgment and a comparative verdict, persisted as a review-retrospective artifact
user-invocable: false
mode: workflow
allowed-tools: Bash, Read, Write
order: 990
default_on: false
presets: []
mutates_source: false
post_run_review: true
head_dependent: true
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step: review-retrospective

## Purpose

After a plan finishes, compare the PR's reviewers — the three automated reviewers
(CodeRabbit `coderabbitai`, Sourcery `sourcery-ai`, PR-Agent `cuioss-review-bot`)
plus any human reviewer — on review quality, reading THIS plan's `pr-comment` findings
grouped by reviewer. The step is **HYBRID by construction**:

- A **deterministic numbers pass** (the backing `review_retrospective.py`
  aggregator) computes the per-reviewer, `(author, kind)`-grouped metrics. These
  counts are authoritative and are NOT recomputed by the LLM.
- An **LLM qualitative-judgment pass** (this workflow body) reads the comment
  titles/bodies/details + their resolutions + the deterministic metrics and writes
  a per-reviewer quality assessment plus a comparative verdict. This pass
  **AUGMENTS** the numbers — it never recomputes or overrides them.

Two layers of review-quality signal:

- **Deterministic signal** (from the aggregator): per reviewer — raw total
  comments; ACTIONABLE count (kind=inline + substantive review_body) reported
  SEPARATELY from raw total; meta/non-actionable count (CodeRabbit status-summary
  review_body + walkthrough issue_comment); resolution buckets; %-resolved-as-fixed;
  positives (resolution=`fixed`); false-positives (resolution in
  {`accepted`, `taken_into_account`}); suppressed=borderline; pending=excluded.
- **LLM qualitative signal** (this body): signal-to-noise (real bug/design issue
  vs nitpick vs style/lint/markdownlint trivia); depth and usefulness; accuracy of
  the deterministic false-positive inference; and a comparative verdict (which
  reviewer added more value on this PR and why).

Cross-plan aggregation is **out of scope** — see
`audit-archived-plan-retrospectives` for the corpus-wide quality-chain view.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include
`project:finalize-step-review-retrospective` in their `phase-6-finalize.steps`
list. Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required; used to read the pr-comment findings,
  scope the artifact, and mark the step done)
- `--iteration` — finalize iteration counter (accepted for contract compliance,
  no effect)

MUST be ordered (via its `order: 990` frontmatter) **after**
`plan-marshall:automatic-review` (30, which stages the pr-comment findings this
step consumes) and `default:sonar-roundtrip` (40), and **before**
`default:lessons-capture` (991).

The lower bound is stronger than those two producers alone. This step declares
`post_run_review: true`, so it MUST also be ordered after the merge gate
`default:branch-cleanup` (70): the gate hosts the pre-merge review-completeness
barrier and the bot re-review wait, which keep ADDING to the same `pr-comment`
findings store this step reads. Ordered ahead of the gate, the step would compare
reviewers over a store the gate had not finished filling and report a confident
verdict about evidence that did not exist yet. `order: 990` is that placement; the
governing contract is
[`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md`](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md)
§ "The reciprocal", and the membership discriminator is owned by
[`ext-point-finalize-step.md`](../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md)
§ "Implementor Frontmatter". Being post-merge-ordered, the step writes no tracked
source and declares `mutates_source: false` explicitly — the explicit declaration
is mandatory for any step ordered at or after the merge gate.

## HEAD-dependency

This step declares `head_dependent: true` in its frontmatter — that fact IS the membership declaration the dispatcher's re-entry check reads (see [ext-point-finalize-step.md](../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"; the governing discriminator lives there and is deliberately not restated here).

It matches on the verdict shape: the step records a pass/fail-style verdict over the **remote state of tracked source** — which reviewer added more value on this PR, computed from the `pr-comment` findings that review of the pushed diff produced. Push a different diff and the reviewers say different things, so the verdict is bound to the HEAD it was computed against.

**Why the declaration survives this step's post-merge placement (`order: 990`).** Loop-back is hosted by the merge gate `default:branch-cleanup` (70), so at 990 this step runs *after* the last point at which HEAD can advance within the run — no loop-back can follow it, and the declaration therefore no longer arms a live re-entry invalidation. Its remaining value is the recorded `--head-at-completion` **provenance stamp**: the artifact this step persists is a verdict about a specific tree, and the stamp is what ties it to that tree for anyone reading the retrospective later. This is stated explicitly so the declaration is not mistaken for a live loop-back guard, and so a future maintainer does not "fix" the apparent redundancy by deleting it — a later reordering that moves this step back above the gate would silently need the guard again.

Every terminal `--outcome done` record therefore captures the worktree HEAD immediately before its `mark-step-done` call and forwards it via `--head-at-completion {sha}`: the Step 5 completion record, the Step 1 zero-findings skip-clean record, and both non-fatal Error-Handling paths that also mark done (aggregator error, artifact-write failure). Re-firing is safe and cheap: the step is non-fatal throughout and recomputes from the findings store each time.

## Reviewer comment-structure asymmetry

The three automated reviewers post structurally different comment layers per PR,
all under one login each, so a naive "every pr-comment finding = one actionable
item" count over-counts CodeRabbit. The aggregator discriminates on the
first-class `kind` field:

- **CodeRabbit** (`coderabbitai`): inline actionable comments (`kind=inline`, each
  wrapping nested `<details>` blocks that are ONE comment); a `review_body` status
  summary ("Actionable comments posted: N") that is META; an `issue_comment`
  walkthrough/poem that is also META.
- **Sourcery** (`sourcery-ai`): inline `<issue_to_address>` comments plus an
  **Overall Comments** `review_body`; its Reviewer's Guide `issue_comment` is META.
- **PR-Agent** (`cuioss-review-bot`): no inline comments at all — exactly one
  persistent `issue_comment` headed `## PR Reviewer Guide 🔍`, updated in place on
  re-review. Its findings live inside that one record, so a stage that counts
  inline comments will conclude this bot found nothing.

So `kind=inline` is actionable, a substantive `review_body` is actionable, and
CodeRabbit's status-summary `review_body` + walkthrough `issue_comment` are
meta/non-actionable — reported separately from the actionable counts so they never
inflate `actionable_count` or mis-rank reviewers. Records lacking `kind` are
bucketed as `unknown` and counted in the raw total only.

## Workflow

### Step 1: Read this plan's pr-comment findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type pr-comment
```

Read both resolved and pending findings (the retrospective wants the full
picture). The records carry first-class `author` and `kind` fields.

**Zero-findings skip-clean exit**: if `filtered_count` is 0, record the step as
done and return — there is nothing to compare. Resolve the HEAD SHA immediately
before marking done, per § HEAD-dependency. Read it from **`{main_checkout}`**:
this step is ordered at 990, after `default:branch-cleanup` (70) has merged and
REMOVED the worktree, so `{worktree_path}` no longer exists on disk and a
`git -C` against it fails — leaving the mandatory `--head-at-completion`
unresolvable. `{main_checkout}` is the tree the merge landed on and is present
on both the worktree and no-worktree flows:

```bash
git -C {main_checkout} rev-parse HEAD
```

Capture stdout as `{sha}` and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-review-retrospective \
  --outcome done --display-detail "0 pr-comment findings — nothing to compare" \
  --head-at-completion {sha}
```

### Step 2: Deterministic numbers pass

Invoke the backing aggregator. It groups the findings by `(author, kind)` and
emits the authoritative per-reviewer metrics as TOON:

```bash
python3 .plan/execute-script.py default-bundle:finalize-step-review-retrospective:review_retrospective run \
  --plan-id {plan_id}
```

Parse the TOON. Key fields:

- `total_findings`, `reviewer_count`
- `reviewers[]{author,raw_total,actionable_count,meta_count,fixed,accepted,taken_into_account,suppressed,pending,positives_count,false_positives_count,pct_resolved_as_fixed}`
- `by_author_kind[]{author,kind,count}` — the per-`(author, kind)` breakdown
- `kind_actionability` and `resolution_quality` — the mapping legends

`raw_total` and `actionable_count` are DISTINCT — the meta comments never inflate
`actionable_count`. These numbers are authoritative; do NOT recompute them.

### Step 3: LLM qualitative-judgment pass

Reading the comment titles/bodies/details (from Step 1) + their resolutions + the
deterministic metrics (from Step 2), produce per reviewer:

- **Signal-to-noise** — real bug/design issue vs nitpick vs style/lint/markdownlint
  trivia.
- **Depth / usefulness** — how substantive and actionable the comments were.
- **False-positive accuracy** — did the deterministic false-positive inference
  (resolution in {`accepted`, `taken_into_account`}) genuinely read as noise in
  the comment bodies, or were any of those acknowledged-without-change comments
  actually valuable?

Then a comparative verdict: which reviewer added more value on this PR and why.
This pass AUGMENTS — never replaces or overrides — the Step 2 counts.

#### Participation is UNMEASURABLE unless positively substantiated

An empty or thin slice of the findings store is **not** evidence that a reviewer
was absent, that its inline coverage was zero, or that the PR took a
"thin-review landing". Silence and non-participation are indistinguishable to a
comment count: a bot that reviewed and found nothing, a bot that was rate-limited,
a bot that refused, and a bot that was never enabled all present here as the same
zero. This is the same asymmetry the merge gate already documents for its own two
predicates — see
[`branch-cleanup.md`](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md)
§ "Pre-Merge Review-Completeness Barrier".

This pass therefore MUST NOT:

- infer that a reviewer was **absent** / did not participate from a zero or
  missing slice of the store;
- report **"zero inline coverage"**, "no findings", or any equivalent
  quantified-absence claim about a reviewer whose participation is not
  positively substantiated;
- characterise the run as a **"thin-review landing"** (or any comparable
  whole-PR quality claim) on the strength of a low aggregate count alone.

Instead, classify each reviewer into exactly one of two states and report the
state explicitly:

| State | Substantiation | How the artifact reports it |
|-------|----------------|-----------------------------|
| **measured** | At least one record attributed to that reviewer is present in the store, so its output can be judged. | Normal per-reviewer assessment. |
| **unmeasurable** | No record attributed to that reviewer is present. | Report participation as `unmeasurable`, naming the reviewer and stating that the store substantiates neither participation nor absence. Do NOT score it, rank it, or count it as a negative. |

The **comparative verdict** MUST name every reviewer it could not measure and
MUST scope its claim to the measured ones — a verdict silent about an
unmeasurable reviewer reads as a verdict that measured it and found nothing.
When NO reviewer is measurable, the verdict itself is `unmeasurable`; do not
manufacture a ranking from an empty store.

### Step 4: Persist the retrospective artifact

Write `review-retrospective.md` under the plan dir, containing BOTH the
deterministic per-reviewer metrics table (raw vs actionable vs meta,
positives/false-positives, %-resolved-as-fixed) from Step 2 AND the LLM sections
from Step 3 as NAMED sections — `## Qualitative Quality Assessment` (per reviewer)
and `## Comparative Verdict`:

Both LLM sections carry the participation state Step 3 assigned: every reviewer
classified `unmeasurable` is named as such, and the comparative verdict states
which reviewers it could not measure. The artifact's **closing recommendation**
is bound by the same rule as the verdict — it MUST NOT recommend acting on an
inferred absence ("drop reviewer X", "coverage was thin, tighten Y") when the
input for that reviewer was `unmeasurable`. A recommendation derived from an
unmeasured input is the actively-misleading shape this constraint exists to
remove; recommend only what the measured reviewers substantiate, and say plainly
that the rest could not be measured.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id {plan_id} --file review-retrospective.md --content-file {temp_artifact_path}
```

Compose the artifact body with the Write tool to a temp file under `.plan/temp/`
first, then pass it via `--content-file` (multi-line markdown never goes through a
shell argument).

### Step 5: Record the step outcome

Resolve the HEAD SHA immediately before marking done, per § HEAD-dependency.
Read it from **`{main_checkout}`** — at `order: 990` the worktree
`default:branch-cleanup` (70) removed is gone, so `{worktree_path}` cannot be
read; see the Step 4 note for the full reasoning:

```bash
git -C {main_checkout} rev-parse HEAD
```

Capture stdout as `{sha}` and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-review-retrospective \
  --outcome done --display-detail "{N} reviewers compared, {M} actionable comments" \
  --head-at-completion {sha}
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Zero pr-comment findings | Skip-clean exit — `mark-step-done --outcome done --display-detail "0 pr-comment findings — nothing to compare" --head-at-completion {sha}` so the `phase_steps_complete` handshake counts the step as done |
| Aggregator returns `status: error` | Non-fatal — log the error, skip the qualitative pass, and `mark-step-done --outcome done --head-at-completion {sha}` with a display detail noting the aggregator failure. The retrospective must never block finalize. |
| `manage-files write` failure | Non-fatal — log the failure and still `mark-step-done --outcome done --head-at-completion {sha}`. The artifact is advisory; finalize must not abort. |

The step's posture is **non-fatal throughout**: finalize must never abort because
the review retrospective hit a snag.

## Canonical invocations

The canonical argparse surface for the backing aggregator `review_retrospective.py`.

### review_retrospective — run

```bash
python3 .plan/execute-script.py default-bundle:finalize-step-review-retrospective:review_retrospective run \
  --plan-id PLAN_ID
```

## Related

- [.claude/skills/finalize-step-lessons-housekeeping/SKILL.md](../finalize-step-lessons-housekeeping/SKILL.md) — sibling project-local `mode: workflow` finalize step (reads data via scripts, reasons, persists an artifact, ends with `mark-step-done`)
- [.claude/skills/finalize-step-deploy-target/SKILL.md](../finalize-step-deploy-target/SKILL.md) — sibling project-local finalize step
- `plan-marshall:manage-findings` — the pr-comment finding store this step reads (first-class `author` / `kind` fields)
- `plan-marshall:manage-files` — plan-dir artifact persistence
- `.claude/skills/audit-archived-plan-retrospectives/SKILL.md` — the cross-plan, corpus-wide quality-chain view (this step is single-plan)
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
