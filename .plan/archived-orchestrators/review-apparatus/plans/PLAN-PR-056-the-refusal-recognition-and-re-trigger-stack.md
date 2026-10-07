# PLAN-PR-056: The refusal-recognition and re-trigger stack, end to end

epic: review-apparatus
workstream: WS-01

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-069 (D0/D1/D2/D7/D8/D11 — refusal recognition + rate window), PLAN-PR-070 (D9/D10 — the currency-blind disposition and its readable state), PLAN-PR-067 (D3 — the enumerative-arm veto, absorbed into the pre-filter).
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-043` and `PLAN-PR-045` whole**, under the operator's
> 2026-09-12 decision to raise the split guard to **12 deliverables** and group staged work by
> shared target surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text, exactly as `PLAN-PR-028` remains the
> authoritative text of its own halves. Retyping a deliverable body is the reconstruction drift this
> epic forbids at every hand-off — follow the pointer.

## Objective

Make a review refusal recognisable, make the re-trigger reach the bot that actually gates, and make a
credit that was never currency-tested say so. These were two specs because the guard was six; they are
one plan because they edit the same six files and a fix in either direction moves the other.

## Why these were grouped

Derived from `corpus surfaces`, not judged: the two sources share **seven** declared paths —
`bot_registry.py`, `review_completeness.py`, `bot-participation-contract.md`, `coderabbit.md`,
`sourcery.md`, `github_pr.py`, `workflow-integration-github/SKILL.md` — plus both test trees. ⛔ The
sources' own sequencing notes already said *"never concurrent"*, so they could never have been
parallelised; merging costs no throughput and removes one hand-off.

⚠ **Both failure directions live here simultaneously** — `PLAN-PR-043` D5 fails toward BLOCKING, its
D2 fold fails toward MERGING. Any recognition change needs a control in BOTH directions; that
constraint is now inside one plan rather than split across two.

## Deliverables

**D0 — GATE, mutates nothing.** The merged re-grounding gate. Re-read every symbol
`PLAN-PR-043` § Claim Labels and `PLAN-PR-045` D0/D0a name, at HEAD, and publish the affected
population `PLAN-PR-045` D0 requires **before** any disposition is chosen. ⛔ Anchor on SYMBOLS, never
on line numbers — this spec's ancestors carried three line references that had all moved while the
mechanism held. **HALT and report** if a named symbol no longer resolves.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | Select the trigger-B bot from the gating set, not from comment recency | `PLAN-PR-043` § D1 |
| D2 | Close the refusal-recognition gap the three arms each missed differently | `PLAN-PR-043` § D2 |
| D3 | Stop the enumerative arm being vetoed by the code-anchor marker | `PLAN-PR-043` § D3 |
| D4 | One conflation, three consumers: a refusal treated as review evidence | `PLAN-PR-043` § D4 |
| D5 | A false `declined` from an in-place re-review | `PLAN-PR-043` § D5 |
| D6 | ⚠ **SHIPPED BY #1473 — re-scoped to audit, see below** | `PLAN-PR-043` § D5a |
| D7 | The rate window is a retry policy, not a flat timeout | `PLAN-PR-043` § D6 |
| D8 | The rate window's own instruments are deaf — ⭐ **+ the measured cost of the window itself, folded 2026-09-13** | `PLAN-PR-043` § D7 |
| D9 | Decide the currency-blind disposition, with the rejected arms recorded | `PLAN-PR-045` § D1 |
| D10 | Make the discriminator readable, whichever arm wins | `PLAN-PR-045` § D2 |
| D11 | Name the composition — neither path alone predicts the failure | `PLAN-PR-045` § D3 |

**D13 — A per-bot completion signal that is actually per-bot (lesson `2026-09-08-22-002`, absorbed
2026-09-18).** `github_re_review.py` § `await_fresh_review` credits a review by ANY author as the
awaited bot's completion: `_match_review` carries no author gate, and its docstring records that as a
decision — *"There is deliberately NO author gate on this path — the SHA match already establishes
provenance."* ⛔ A SHA match establishes WHICH COMMIT was reviewed, never WHO reviewed it, so a
CodeRabbit review at the right sha satisfies a wait on `cuioss-review-bot` and the waiter returns
complete for a bot that never posted. *Done when:* the decision is settled explicitly — either the
author gate is added, or the docstring's claim is narrowed to what a sha match actually establishes and
the per-bot caller is given a signal that does gate on author — and a test fails on the current code
with a foreign-author review at the awaited sha. ⚠ Reproduces at HEAD; the epic had zero coverage of
this path (`await_fresh_review` appears in no spec, landing, or `epic.md` section).

Thirteen deliverables. The 12 ceiling is a guideline (operator ruling 2026-09-15) and D13 belongs to
the same re-trigger/await stack the other twelve rewrite. ⛔ **Absorb no fourteenth.** A further fold
goes to a successor spec, or displaces one of these with the displacement recorded.

### ⛔⛔ D6 WAS SHIPPED BY ANOTHER PLAN — re-scoped 2026-09-13, do not re-implement

**`PLAN-PR-033` (#1473, merged `38af136ed`) fixed this defect**, under an operator-directed in-PR scope
expansion at that plan's merge gate — and **declared it nowhere**: the PR's own Changes section names
only its two foreign-gate/`cleanup_owed` deliverables, and `references.affected_files` recorded 14 of
the 28 files that landed.

⭐ **Corroborated first-party at HEAD `38af136ed`, not relayed**: the `issue_comment` branch of
`github_re_review.py` no longer hard-codes the verdict — `head_sha_verified` is decided by
`_verifies_head_sha(matched_signal, record, head_sha)`, which runs the SAME `_references_head_sha`
predicate over the comment BODY, recognising the `…/commit/{sha}` permalink form `cuioss-review-bot`
publishes. The module's docstring now records the correction in its own words: *"an issue comment
carries no reviewed-commit SHA" was a premise, not an observation, and it is false.*

⇒ **D6's original scope is DISCHARGED.** What remains for this plan is the audit half, which the
shipping plan did not do and could not have: **confirm the fix reaches every consumer this deliverable
named.** *Done when:* the `declined` classification is re-derived end to end at HEAD for a
`cuioss-review-bot` re-review — producer verdict, both consumer sites, and the barrier — and a test
pins that a comment naming the awaited HEAD does NOT resolve `declined`; **or** the re-derivation shows
a consumer still reading the retired premise, in which case that consumer is the deliverable. ⛔ Run
this against the code, never against the docstring: a described fix reads as a complete one.

⚠ **Its claim's verdict is stamped `contradicted` / `rescoped: yes`** in § Claim Labels — the mechanism
the claim named no longer exists at HEAD, and this block is the re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` — D7: the rate-window knobs become an interval plus an attempt ceiling
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — D7: the barrier's refusal names the remedy available under the live configuration
- OBSERVED: `.github/workflows/`
- OBSERVED: `test/plan-marshall/automatic-review/`
- OBSERVED: `test/plan-marshall/workflow-integration-github/`
- OBSERVED: `test/plan-marshall/manage-locks/`

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-043` § Claim Labels and
  `PLAN-PR-045` § Claim Labels, carried unchanged with their labels and their stamped verdicts.
  Confirm/refute at those two sections — they are the authoritative record and this plan re-states none
  of them.
- OBSERVED: the two sources share seven declared paths and both test trees, so no pairing of them was
  ever admissible. Confirm/refute at `corpus surfaces` over the retired source rows.
- HYPOTHESIS: merging the two costs no throughput — confirm/refute at each source's
  § Dependencies and Sequencing, both of which already forbid concurrency with the other
  (verify-at-outline).
- OBSERVED (D6, re-grounded first-party 2026-09-13 at HEAD `38af136ed`): `head_sha_verified` is NO
  LONGER hard-coded to `matched_signal == 'review'` — `github_re_review.py` decides it through
  `_verifies_head_sha`, which runs `_references_head_sha` over the comment body on the `issue_comment`
  path. The premise that a re-review by that bot can never verify is DEAD at HEAD. Confirm/refute at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
  § `_verifies_head_sha`.
  - verdict: contradicted | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: yes | evidence: HOLDS CONTRADICTED at HEAD, no movement since prior stamp. github_re_review.py did not change this window and _verifies_head_sha still resolves there (3 occurrences), so the once-hard-coded head_sha_verified premise stays dead. Both touched declared paths are inert to the claim: .github/workflows/ carries only the v0.28.0-to-v0.29.0 SHA-pin bump, branch-cleanup.md only the new ADR duplicate-number gate. The two-implementation residue named at the prior re-scope is unchanged.
- OBSERVED: `PLAN-PR-033` (#1473) landed 28 files while its `references.affected_files` recorded 14,
  and the undeclared half carried this plan's D6. Confirm/refute at `git show --stat 38af136ed`
  against that plan's landing message `-008` § Residue.

## Dependencies and Sequencing

- ⛔ **Overlaps `PLAN-PR-057`, `PLAN-PR-058` and `PLAN-PR-059`** on the `automatic-review` and
  `github_pr` families — sequence, never pair.
- ⭐ **Internal order: D0 → D2/D3/D4 (recognition) → D1 (selection) → D5/D6 (decline) → D7/D8 (window)
  → D9–D11 (currency).** Recognition first: D1's selector and D9's discriminator both read a verdict
  D2 produces.
- Supersedes: `PLAN-PR-043`, `PLAN-PR-045`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-056-the-refusal-recognition-and-re-trigger-stack.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
