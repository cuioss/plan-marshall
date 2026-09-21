# PLAN-PR-070: Participation, and what the gate may credit as a review

epic: review-apparatus
workstream: WS-01

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `automatic-review` classification and gate surface — `review_completeness.py`, its state set, and its call surface.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Classify what a bot published in both directions, refuse to credit what was never reviewed, and make the gate invokable by its own documented callers.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D2 | Classify a bot's publication correctly **in BOTH directions** — three artifact classes fool a "the bot commented" predicate, a FOURTH (a thread acknowledgement) is credited as a fresh review, and inversely a genuine clean verdict is read as NO participation into an unclearable `participated_stale` | `PLAN-PR-048` §§ D0 + D0a + D0b | `PLAN-PR-057` D1 |
| D3 | A force-done override of `absent` must cite evidence the review HAPPENED | `PLAN-PR-048` § D1 | `PLAN-PR-057` D2 |
| D4 | An unregistered bot kind must fail LOUD, not be force-done past | `PLAN-PR-048` § D1a | `PLAN-PR-057` D3 |
| D5 | Decide the currency-blind disposition, with the rejected arms recorded | `PLAN-PR-045` § D1 | `PLAN-PR-056` D9 |
| D6 | Make the discriminator readable, whichever arm wins | `PLAN-PR-045` § D2 | `PLAN-PR-056` D10 |
| D7 | Reconcile declared `publish_shape` against the observed one, and REPORT the divergence | `PLAN-PR-047` § D4 | `PLAN-PR-061` D11 |
| D9 | A `malformed_bot_flag` refusal names the token, the shape, and an example | `PLAN-PR-051` § D1 | `PLAN-PR-058` D6 |
| D10 | Make the pair-shaped flags self-describing at the call site | `PLAN-PR-051` § D2 | `PLAN-PR-058` D7 |
| D11 | Prove the gate against its own documented invocations | `PLAN-PR-051` § D3 | `PLAN-PR-058` D8 |


**D0 — GATE, mutates nothing.** The merged re-grounding gate. From `PLAN-PR-053` D0: re-ground both
coverage claims at HEAD and derive the set of write sites that would have to split the two facts. From
`PLAN-PR-051` D0: re-ground both malformed-token claims against HEAD. **HALT and report** if either
population no longer reproduces.

⛔⛔ **D0 ALSO OWNS THE UNSAMPLED-MARKER GATE — folded 2026-09-13 from `plan-pr-046-012`, which exists
because the observation was carried only as a trailing aside in a message about the refusal detector
and would otherwise have been drained past.** As shipped on `main` at `77cb2e251`,
`github_pr.py` § `_is_participation_evidence` gates content with a **bare `in` test over the whole
body**: `return not marker or marker in str(comment.get('body') or '')`. Any occurrence of the declared
literal anywhere — inside quoted PR text, a nested block, or a user-authored excerpt the bot echoes —
satisfies it. CodeRabbit raised it twice on #1477 (`b131a3` round 1 Major, `c847ec` round 3 Major,
adding the quoted-PR-text vector); both were resolved `taken_into_account`, **never disputed**.

⭐ **The decline was correct and does NOT close it.** Tightening an unanchored match fails **CLOSED**: a
verdict comment that stops matching resolves a clean review `absent`, which BLOCKS a merge — and the
declared `recent_review_start` marker is **absent from CodeRabbit's live summary comment on #1477**, so
the gate is unexercised and its target layout has never been sampled. ⇒ **Sampling is the precondition
for anchoring, and it is this gate's job**: sample the live verdict-comment layout across several real
PRs, publish what was sampled and how many, and only then decide the anchored form. ⛔ Do not anchor
against an unsampled layout, and do not leave the substring test unanchored once the layout IS sampled
— the first blocks merges, the second credits a review that never happened. *Done when:* the sampled
population is published with its size, and the anchoring decision names it.

*(Carried verbatim from `PLAN-PR-058` D0 at the 2026-09-18 component re-cut.)*

**D1 — GATE, mutates nothing.** The merged re-grounding gate, carrying `PLAN-PR-052` D0 verbatim in
scope: re-ground all four refusal findings at HEAD, and for `PLAN-PR-052` defect 2 **derive** whether
`refusal_structural` is reachable at the shipped default configuration, publishing the configuration
population walked. Additionally re-ground `PLAN-PR-048`'s five scoring paths. **HALT and report** if
any no longer reproduces. ⛔ An unreachability claim asserted from one configuration is the
vacuous-authority archetype this epic keeps re-finding.

*(Carried verbatim from `PLAN-PR-057` D0 at the 2026-09-18 component re-cut.)*

**D8 — One reader for the reviewer-classification config (lesson `2026-09-05-07-009`, absorbed
2026-09-18).** Two readers of `required_bots` / `optional_bots` take **opposite dispositions on the same
unregistered token**: the shared contract refuses with `unregistered_kind`, while the second reader
folds the token into three participation-ratio denominators with no row of its own — so a typo'd bot
name blocks in one place and silently inflates a ratio in the other. The concrete instance closed in-run
(#1416 TASK-007, finding `e4aea1`); the structural half never did. *Done when:* the classification config
is read through ONE shared surface whose refusals every consumer inherits, and a test proves an
unregistered token reaches the same disposition on both paths. ⚠ Sits beside `epic.md`'s standing
`bot_kind`-rename-with-no-propagation entry — the same config, the same absence of a shared reader.

Thirteen deliverables. ⚠ The 12 ceiling is a **guideline, not a hard limit** (operator ruling 2026-09-15):
up to ~14 is acceptable when the aspects fit together — so a thirteenth is admissible only if it belongs
to the reviewed-at-all handoff this plan builds, never as a convenient home for an unrelated finding.

**Evidence amendment 2026-09-15** (from
[`findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md`](../findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md);
sizes D0's populations and supplies D1/D3/D4 negative controls — adds no deliverable, because every item
feeds an existing one):

- ⭐ **The collapsed state is the MAJORITY case, now at n = 156.** 152 of 156 pr-agent guides (97.4%) are
  the canned "No major issues / No security concerns" table; paired recall against CodeRabbit is 4 of
  123. A canned guide and a real clean review remain indistinguishable to every consumer D1 feeds.
- ⛔ **21 PRs had no baseline reviewer at all, 6 of them merged** (`plan-marshall` `#1380`, `#1406`,
  `#1407`, `#1438`; `API-Sheriff` `#288`, `#300`) — their only posted review is a canned guide. These are
  the D3/D4 fixtures: an empty required population rendered as positive.
- **Three distinct "nobody reviewed" shapes D1's handoff must keep apart from "reviewed clean":**
  - *never triggered* — `cui-http#185`: zero `pull_request`-event runs across every workflow for the
    opening window; the first runs follow a force-push `pr-agent.yml` does not subscribe to;
  - *re-review failed silently* — `plan-marshall#1479`: the `/review` re-review failed at step "Generate
    Review Token" and never recovered, so the guide shows only the opening commit;
  - *run stuck* — pr-agent run `34748813129` (issue_comment, `#1477`) `queued` since
    2026-09-13T09:01:19Z.
- **D9 (refusal MODE) has a measured split:** CodeRabbit refused-only on 22 PRs — 20 rate (expires), 2
  size (`#1407`, `#1432`, never expires); Sourcery quota on 103 PRs, size on 34, and a review on only 40
  of 181.

*(Carried verbatim from `PLAN-PR-061` D13 at the 2026-09-18 component re-cut.)*

12 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — ⭐ **this plan is its single owner**; `PLAN-PR-069` and `PLAN-PR-071` route SKILL edits here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_cli.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_state.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_verdicts.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_evidence.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_participation_site_population_guards.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_unknown_bot_kind_escalation.py`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping): this plan's declared
  surface is disjoint from every other live plan's in this epic. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus`.
- OBSERVED (first-party, 2026-09-15): `plan-marshall#1438` merged `2026-09-07T07:58:16Z` with no labels
  and zero `coderabbitai[bot]` reviews, after `#1407` made CodeRabbit required. Confirm/refute at
  `repos/cuioss/plan-marshall/pulls/1438` and its `/reviews`. ⭐ D0 derives, for every merged
  plan-marshall PR since `#1407`, whether each required bot actually reviewed.
- OBSERVED (corpus pass 2026-09-15): 74 of 181 PRs carry a CodeRabbit refusal inside the summary
  comment, 71 as in-place edits, 54 alongside real reviews; "Review skipped: No new commits" (×5) and
  "Review failed: The pull request is closed" (×1) sit in the same structural slot and are NOT
  refusals. This is D0's starting population for the marker sample, not the sample itself.
- OBSERVED (first-party, 2026-09-18): the `--measured-diff-size` crash half is SHIPPED
  (`review_completeness.py:1955-1970`, `nargs='?', const='', default=''`), landed undeclared by
  `PLAN-PR-033` (#1473). What remains for D10 is the empty-argument guarantee scope and its sweep.

## Dependencies and Sequencing

- ⛔ **D5 (`reviewed_commit_sha` records COVERAGE, not observation) is a precondition for the
  currency-blind disposition it carries.** The two were in different specs and the source stated the
  order outright: *"If both are staged, land this one first."* They are one deliverable here.
- ⛔ **Runs AFTER `PLAN-PR-069`**: D2 classifies what a refusal means, and 069 D2 decides what IS a
  refusal. Classifying against an unrecognised refusal set is the defect this epic already shipped once.
- ⭐ D0 additionally carries the `PLAN-PR-056` D6 AUDIT arm: that deliverable was SHIPPED undeclared
  by #1473, so D0 re-derives the `declined` classification end to end at HEAD rather than re-fixing it.
- ⚠ D6 settles the `_match_review` author-gate decision; `PLAN-PR-067` D2 rewrites the waiter that
  calls it. Sequence, never pair.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-070-participation-and-what-the-gate-may-credit.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
