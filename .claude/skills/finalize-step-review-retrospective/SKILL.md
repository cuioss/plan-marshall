---
name: finalize-step-review-retrospective
description: Finalize-phase wrapper that compares the PR's automated and human reviewers — a deterministic per-reviewer metrics pass (raw vs actionable vs meta comments, resolution buckets, %-resolved-as-fixed) augmented by an LLM qualitative quality judgment and a comparative verdict, persisted as a review-retrospective artifact
user-invocable: false
mode: workflow
allowed-tools: Bash, Read, Write
order: 50
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step: review-retrospective

## Purpose

After a plan finishes, compare the PR's reviewers — the two automated reviewers
(CodeRabbit `coderabbitai`, Gemini Code Assist `gemini-code-assist`) plus any
human reviewer — on review quality, reading THIS plan's `pr-comment` findings
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

MUST be ordered (via its `order: 50` frontmatter) **after**
`default:automated-review` (30, which stages + resolves the pr-comment findings
this step consumes) and `default:sonar-roundtrip` (40), and **before**
`default:lessons-capture` (60).

## Reviewer comment-structure asymmetry

CodeRabbit and Gemini post structurally different comment layers per PR, all under
one login each, so a naive "every pr-comment finding = one actionable item" count
over-counts CodeRabbit. The aggregator discriminates on the first-class `kind`
field:

- **CodeRabbit** (`coderabbitai`): inline actionable comments (`kind=inline`, each
  wrapping nested `<details>` blocks that are ONE comment); a `review_body` status
  summary ("Actionable comments posted: N") that is META; an `issue_comment`
  walkthrough/poem that is also META.
- **Gemini** (`gemini-code-assist`): typically a single substantive `review_body`,
  frequently zero inline comments.

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
done and return — there is nothing to compare:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-review-retrospective \
  --outcome done --display-detail "0 pr-comment findings — nothing to compare"
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

### Step 4: Persist the retrospective artifact

Write `review-retrospective.md` under the plan dir, containing BOTH the
deterministic per-reviewer metrics table (raw vs actionable vs meta,
positives/false-positives, %-resolved-as-fixed) from Step 2 AND the LLM sections
from Step 3 as NAMED sections — `## Qualitative Quality Assessment` (per reviewer)
and `## Comparative Verdict`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id {plan_id} --file review-retrospective.md --content-file {temp_artifact_path}
```

Compose the artifact body with the Write tool to a temp file under `.plan/temp/`
first, then pass it via `--content-file` (multi-line markdown never goes through a
shell argument).

### Step 5: Record the step outcome

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-review-retrospective \
  --outcome done --display-detail "{N} reviewers compared, {M} actionable comments"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Zero pr-comment findings | Skip-clean exit — `mark-step-done --outcome done --display-detail "0 pr-comment findings — nothing to compare"` so the `phase_steps_complete` handshake counts the step as done |
| Aggregator returns `status: error` | Non-fatal — log the error, skip the qualitative pass, and `mark-step-done --outcome done` with a display detail noting the aggregator failure. The retrospective must never block finalize. |
| `manage-files write` failure | Non-fatal — log the failure and still `mark-step-done --outcome done`. The artifact is advisory; finalize must not abort. |

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
