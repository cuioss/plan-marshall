envelope_version=1
sender_type=plan
sender_id=domain-post-plan-narrow
epic=operator-ux
kind=landing
created=2026-09-06T07:32:13Z

## What landed

domain-post-plan-narrow shipped as #1422 (merged). The domain-selection lifecycle
gains its missing narrowing leg: `manage-config domain-narrow`, a read-only
safety-bounded verb, plus the end-of-outline site that invokes it in every lane.

```landing-facts
schema=landing-facts/1
plan_id=domain-post-plan-narrow
epic=operator-ux
pr=#1422
merge_state=merged
deliverables_total=2
deliverables_done=2
total_tokens=7103472
total_wall_seconds=68668
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
merge_commit_sha=80f0b5a79dc4c30b35244d2874913c59790441b1
```

## Residue

Items the epic should track that no step recorded as a machine-readable fact.

**The PLAN-03 spec's deferred design question is settled, and the recorded verdict
closes it rather than deferring it.** The spec required outline to choose between
narrowing at end-of-outline from the derived footprint (shape i) and letting the
agent narrow at init on explicit grounds (shape ii), and named a two-plan split as
the default if both were adopted. Outline adopted shape (i) ONLY and declined (ii)
outright — shape (ii) narrows at the point of maximum ignorance, which is the same
information deficit that causes the over-provisioning. **No successor plan is
implied**, and the scope-bloat split guard was never triggered.

**The spec's two verify-first HYPOTHESIS claims were both CONFIRMED against the
post-PLAN-01 tree**, so the plan kept its full "narrow" scope and was not re-scoped
down to "report the over-provision and let the operator narrow". Claim 2 carries a
consequence worth keeping: at the end-of-outline site zero tasks exist, so the
task leg of the safety bound is vacuously satisfied there — that is what makes the
site the safest available one rather than merely a convenient one.

**A required reviewer contributed zero findings across the whole run.**
`cuioss-review-bot` participated at every head it was asked about and reported "no
major issues detected" every time, filing nothing, while CodeRabbit filed 12 (all
triaged FIX) and the plan's own pre-submission self-review found 7 more that no bot
found. It has no push auto-review, so each currency refresh needed an explicit
orchestrator-issued `/review` — three were issued. `sourcery` was quota-refused from
first contact and never reviewed this PR at all. The merge gate's participation
quorum passed; it proves participation, not review quality, and the epic should not
read the green quorum as a well-reviewed diff.

**The plan's own output reproduced the failure class the plan exists to remove —
nine times.** Instances were fixed during the run (three by the self-review, five by
CodeRabbit, one the orchestrator introduced into its own remedy: a strip-check
asymmetry where the sibling guard written in the SAME commit tested `.strip()` and
this one stopped at truthiness). Holding the rule in working memory did not prevent
emitting it. Recorded as inbox message 001.

**Orchestrator error, self-reported.** The finalize dispatcher forwarded
`orchestrated=false` / `epic=""` to `plan-marshall:plan-retrospective` without ever
running the Step 4b.a0 resolution, although the epic staged-spec `source_id` was
visible in the run's own hand-off command. The nine lessons that step recorded
therefore went to the GLOBAL corpus instead of this inbox. `lessons-capture` ran
afterwards with the corrected values, so messages 001-004 are here; the
retrospective's are not. The retrospective caught the error itself and filed lesson
`2026-09-06-07-002`.

**Cost ran 3x over the calibrated ceiling** — 7.1M tokens against a 2.5M error
anchor, with 6-finalize outspending 5-execute 3.74x. The retrospective's judgement,
which the epic should weigh before cutting rounds: the re-firing was PRODUCTIVE
(five review rounds carrying findings, zero error-attributed tokens), so this does
not support reducing the round count.

**Two adjacent defects found in machinery this plan does not own**, recorded rather
than fixed: `automatic-review/SKILL.md` documents `--measured-diff-size "{value}"`
as safe-when-empty although the flag takes a required argument (two agents hit the
argparse rejection independently), and trigger-B selects ONE bot — the newest
bot-authored finding's kind — so it structurally cannot reach a DIFFERENT bot that
is the stale one, while the prose names the trigger as that bot's remedy.

**The reviewer-yield instrument undercounts by 35% on this PR.** All five CodeRabbit
`review_body` records were bucketed `meta` because each opens with an
`Actionable comments posted: N` line; four carried real findings behind it. True
actionable yield 17, measured 11. The review-retrospective recorded the caveat
rather than silently recomputing the authoritative numbers.
