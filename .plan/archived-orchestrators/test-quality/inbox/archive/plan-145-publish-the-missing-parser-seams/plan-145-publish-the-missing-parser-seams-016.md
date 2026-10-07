envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=landing
created=2026-09-04T14:53:41Z

## What landed

plan-145-publish-the-missing-parser-seams shipped as #1395 (merged).

```landing-facts
schema=landing-facts/1
plan_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
pr=#1395
merge_state=merged
deliverables_total=1
deliverables_done=1
total_tokens=6171897
total_wall_seconds=493686
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_commit_sha=8d8c17bd19808c12d25546fb7987b5c6103f9f49
step.create-pr.pr_number=1395
step.record-metrics.total_tokens=6171897
step.record-metrics.total_wall_seconds=493686
```

## Residue

Items the epic should track that no step recorded as a fact.

- **The retrospective's lessons were misrouted out of this epic.** `plan-marshall:plan-retrospective`
  was dispatched with `orchestrated=false` / `epic=""` because the dispatcher resolved the
  orchestration verdict at item 4b.a0 (before `lessons-capture`) but AFTER the retrospective at
  order 995 had already run. Its 12 lessons — 4 new (`2026-09-04-14-006`..`-009`) and 8 recurrence
  appends — therefore landed in the GLOBAL lessons store instead of this inbox. `lessons-capture`
  recovered 6 of the 12 by carrying explicit pointers inside its own candidate-lesson messages;
  the remaining 6 have no signal-backed record to hang a message on and are reachable only from the
  global store: `2026-09-04-14-006`, `2026-09-03-19-005`, `2026-09-03-11-007`, `2026-08-25-09-004`,
  `2026-09-04-12-001`, `2026-09-03-22-002`. The structural fix is upstream: `plan-retrospective`
  must receive the same `orchestrated` / `epic` runtime inputs `lessons-capture` does.
  `2026-09-03-19-005` is the epic-relevant one — it is the recorded form of the re-firing cost
  story below, and this epic currently cannot see it.

- **66% of finalize token spend bought no new work.** 18 of 34 step firings were re-firings,
  worth 2,346,273 of 3,532,602 recorded finalize tokens. Three CodeRabbit quota-recovery
  force-pushes each advanced HEAD, and the verdict-currency classifier returned `invalidated` for
  every settle-band step because none declares a `verdict_inputs` surface. The one step that does
  — `project:finalize-step-era-stamp-fill` — resolved `preserved` and skipped at zero cost on every
  re-entry, so the remedy already exists as a working proof in-tree.

- **`refusal_pattern_drift`, third recurrence, now corrupting measurements.** Sourcery's hard-quota
  refusal notice was filed as a pending `pr-comment` finding (`222510`) instead of being recognised
  by the refusal stack. It then entered the review-retrospective's actionable numerator (producing a
  false 0.0% fix rate for Sourcery) and landed in the gate-delta as an `unpartitioned` escape. The
  remedy — adding the verbatim phrasing to `refusal_patterns` in
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md` — is outside this
  plan's footprint and its q-gate scope criterion, so it is owed to a follow-up plan.

- **The re-review trigger-B heuristic never reaches the blocking bot.** On two separate rounds it
  selected the wrong reviewer (first `sourcery`, then `coderabbit`) and consumed the
  `automatic-review` step budget without ever triggering `cuioss-review-bot`, which was the bot
  actually blocking the quorum. Both rounds required the dispatcher to drive
  `github_re_review re-review --bot-kind cuioss-review-bot` explicitly.

- **A stale bot-kind token in the plan-local step-params.** `required_bots` still named `pr-agent`
  after the rename to `cuioss-review-bot` landed in this branch's own rebase base. The dispatcher
  corrected it mid-run to `cuioss-review-bot,coderabbit`; no bot was moved to `optional_bots`.

- **`scope_creep_check` compared nothing.** It returned `could_not_look` / `no_baseline_sha` on both
  phase-5 firings because `references.json` carries no `plan_creation_sha`. Scope was confirmed by
  direct inspection instead — both changed files inside the declared three-file footprint, nothing
  under `marketplace/bundles/`.

- **The merge-queue landing wait has no sanctioned pacing primitive.** A standalone `sleep` is
  blocked by the harness outright, shell `until`-loops are forbidden by the project's hard rules,
  and the backgrounded fallback was killed twice citing low memory with ~19GB free. The landing was
  ultimately observed via the harness `Monitor` tool.

- **Review participation is not review coverage.** The quorum passed with `coderabbit:participated`
  and `cuioss-review-bot:participated_but_empty` — CodeRabbit contributed both substantive findings
  of the run (`ad7796` Major, `4fa036` Minor, both fixed); the other required bot published against
  the HEAD and raised nothing, and the optional `sourcery` was quota-refused for the whole run.
