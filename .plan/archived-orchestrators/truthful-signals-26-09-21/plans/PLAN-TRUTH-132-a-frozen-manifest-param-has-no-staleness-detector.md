# PLAN-TRUTH-132: A frozen manifest param has no staleness detector

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-03 from inbox drain message `deployment-and-refresh-gaps-017.md`, relayed from the
> **Token-Sheriff** repo (epic `deployment-and-refresh-gaps`, plan
> `outbound-hostname-verification-quarkus`, PR #694 merged `cd36dd24`) after `manage-lessons add`
> refused it there with `wrong_store`.

## Objective

**`manage-execution-manifest reconcile` is the only mechanism that exists to detect snapshot staleness
between a phase-4-frozen manifest and the live upstream, and its comparison domain is the step
ROSTER. A frozen step PARAM therefore has no detector at all.**

Observed: the plan-local execution manifest was composed at phase-4 and froze the step param
`required_bots: coderabbit,pr-agent`. Mid-finalize, a rebase pulled in an upstream **rename of that
token**. `reconcile` was run and reported `reconciled: false` — **correctly, by its own contract**,
because no step was added, removed, or reordered. The stale param was invisible to it.

⛔ **This is the epic's archetype in its purest form: a verdict that is correct by its own contract and
read as an answer to a question it never asked.** `reconciled: false` says *"the step list is
unchanged"*. The caller needs *"the manifest still matches upstream"*, and nothing distinguishes the
two. The first symptom is a downstream barrier misbehaving — in the source run, a `required_bots`
false-`absent` chased through an unrelated diagnosis.

⭐ **The failure mode generalises past `required_bots`: every frozen step param is exposed.** Any
upstream rename, enum-value change, or default change to a param a manifest snapshotted is silently
carried forward **for the life of every in-flight plan**. The remediation is a `reconcile` extension,
not a per-plan fix.

## Deliverables

1. **D0 — GATE: derive the exposed param population.** Enumerate every param a phase-4 manifest
   freezes, and for each, whether its value space is closed (an enum, a registry key, a step name) or
   open (free text, a number). ⛔ **Publish the population and its size.** A closed-value param is
   mechanically checkable against the live declaration; an open one is not, and conflating them would
   produce a detector that reports `indeterminate` for most of the manifest. D0 decides the scope of
   D1 and may legitimately conclude that only a minority of params are checkable — **that is a result,
   not a shortfall, and it must be published as one.**
2. **D1 — extend `reconcile`'s comparison domain to the checkable params**, comparing each frozen value
   against the live step declaration. ⛔ **Keep the roster verdict and the param verdict SEPARATE
   fields with separate causes.** Collapsing them into one boolean recreates the defect: a caller
   could no longer tell *"the list changed"* from *"a value went stale"*, and the two have different
   remedies (recompose vs. re-resolve).
3. **D2 — an unchecked param is DISCLOSED, never silently omitted.** Where D0 finds a param whose value
   space is open, `reconcile`'s payload states that it was not verified, with the population it belongs
   to. ⛔ **This is the deliverable that closes the defect even if D1 lands narrowly** — the current
   payload's sin is not that it fails to check params, it is that it does not say it did not. Adopt the
   discriminator vocabulary already in-tree (`inbox list`'s `inbox_state`, `corpus surfaces`'s
   `derivation_status`) rather than inventing a third.
4. **D3 — matched controls.** A manifest whose param genuinely matches upstream must still reconcile
   clean, and a manifest with a renamed token must now report the divergence naming the param.
   ⛔ **The negative control is load-bearing**: a detector that flags every frozen param as suspect
   would make `reconcile` unusable and is as wrong as the blind spot it replaces.

## Claim Labels

- OBSERVED: `reconcile` reported `reconciled: false` for a manifest whose `required_bots` param was stale after an upstream rename, with the step list unchanged — first-party from the sending run.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The specific Token-Sheriff PR #694 reconcile output is a foreign-repo run, not reproducible from this checkout
- OBSERVED: `reconcile`'s comparison domain is the step roster — stated by the sender as the verb's own contract.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-execution-manifest/SKILL.md reconcile section only diffs phase_6.steps (stale/broken/backfill), never step params
- HYPOTHESIS: `reconcile` is the ONLY snapshot-staleness detector between a frozen manifest and live upstream. ⛔ The sender asserts this; **this orchestrator did not corroborate it**. Confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` § the `reconcile` subcommand and its siblings (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: No sibling verb in manage-execution-manifest.py reconciles frozen vs live params; reconcile is the sole such comparator
- HYPOTHESIS: every frozen step param is exposed, not only `required_bots`. ⛔ This orchestrator's generalisation from one instance. D0 settles it (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: step_params snapshots any step params at compose time (e.g. branch-cleanup pr_merge_strategy) and reconcile never touches step_params
- HYPOTHESIS: the upstream `required_bots` token rename the sender names actually occurred in this repository. ⛔ **NOT corroborated — the sender's evidence is foreign-repo.** Confirm/refute against `git log` on the bot registry and the finalize step declarations (verify-at-outline). If no such rename exists here, the mechanism claim stands on its own reading of `reconcile` and the instance is dropped.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: git show cc5ea40a1 confirms the pr-agent.md to cuioss-review-bot.md rename plus a .plan/marshal.json update in this repo (re-verified independently this pass)

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — the `reconcile` verb (D1, D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` — the `reconcile` canonical block and its payload contract (D2) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py`:320 — `VALID_RECORD_OUTCOMES`, which has no value for a lost return path; added 2026-09-11 by the fold of `api-sheriff-deployment-configurability-005`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` — the prose-only "this resolve wins" rule at step 2 that no script enforces against the frozen `step_execution_tier` stamp; added 2026-09-11 by the fold of `-005` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md` — the freeze/reconcile contract (D0) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-execution-manifest/**` — the D3 controls (verify-at-outline)

## Dependencies and Sequencing

- ⛔⛔ **BLOCKED ON `PLAN-TRUTH-089` (LAUNCHED).** `-089` claims
  `manage-execution-manifest/SKILL.md`, `manage-execution-manifest/scripts/**`,
  `manage-execution-manifest/standards/decision-rules.md` and
  `test/plan-marshall/manage-execution-manifest/**` — **this spec's entire declared surface.**
  **DO NOT EMIT until `-089` lands**, and re-ground this spec against the post-`-089` tree before
  emitting: `-089` reworks the manifest's change-type and execution-tier composition and may move,
  rename, or already close part of this surface.
- Adjacent to: `PLAN-TRUTH-128` (the freshness gate says fresh for a tree it never examined) — the same
  archetype (a staleness gate whose comparison domain excludes what actually went stale) at a different
  gate. ⛔ **Keep separate**: `-128`'s surface is `manage-tasks` / `manage-change-ledger` and does not
  meet this one. The shared archetype is worth naming in both shipped docs; the code is not shared.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-132-a-frozen-manifest-param-has-no-staleness-detector.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`deployment-and-refresh-gaps-021`** (relayed from Token-Sheriff, plan `plan-09-local-gate-truthfulness`, PR #699, promoted there as lesson `2026-09-04-07-004`) — *`reconcile` heals the manifest step LIST but not step PARAMS, so a plan that FIXES a config value still runs against the frozen defective one.*

  ⭐⭐⭐ **This is the same defect this spec already owns, arriving with the sharpest possible instance: the plan whose deliverable 3 CORRECTED `required_bots` in `.plan/marshal.json` then had its own `automatic-review` step read the FROZEN, PRE-CORRECTION value.** The whole point of that deliverable was that the value named an **author_login** where it should have named a **bot_kind**. The manifest is a compose-time snapshot taken at outline, *before* the correction landed; `reconcile` did not heal it, **because `reconcile` heals the step LIST, not step PARAMS.**

  ⛔⛔ **The plan came within ONE manual override of reproducing the very defect it was fixing.** The run caught it and applied an explicit step-param override at the dispatch site (`coderabbit,cuioss-review-bot` → `coderabbit,pr-agent`), reasoning recorded in the decision log. **Had it not, `automatic-review` would have gated on an author_login that names no bot_kind — the misconfiguration deliverable 3 existed to remove.**

  ⭐⭐ **The generalisation is broader than manifests and is the form worth carrying into D0:** *“any compose-time snapshot of a value the run is AUTHORISED TO CHANGE needs either a re-derivation path or an explicit statement of what it does not heal.”* The snapshot semantics are **correct in general** — they are what makes a run reproducible — **but they create a specific blind spot for exactly the class of plan whose deliverable IS a config correction.**

  **Two candidate responses, matching this spec’s D1/D2 split:** cheap and local — a plan whose declared surface includes a `marshal.json` key feeding a finalize step’s params must re-check that step’s params before dispatch (what this run did by hand); structural — extend `reconcile` (or add a companion verb) to re-derive step PARAMS from live config for steps whose param source is `marshal.json`, **so the healing surface matches the drift surface.** ⛔ *“The asymmetry between ‘heals the list’ and ‘does not heal the params’ is not documented at the point of use, which is why the gap had to be discovered by inspection rather than reported”* — that sentence is D2’s justification in the sender’s own words.

## ⭐⭐ FOLDED 2026-09-11 — cross-repo lessons drain (1 API-Sheriff item): a SECOND frozen param, and its failure is mis-recorded as the command's

`api-sheriff-deployment-configurability-005`: API-Sheriff PLAN-15's frozen manifest carried
`step_execution_tier` = `"verify:module-tests",per_task` while the live architecture resolve said
`orchestrator`. The phase-5 runner followed the stamp: a multi-minute build ran on a synchronous per-task
budget, the host auto-backgrounded it, the dispatch lost its return path, and the row was recorded
`"verify:module-tests",5-execute,error,0,0,1355000` — **the module tests were fine** and PR #267 merged.

⇒ **This spec's archetype with a second param.** `required_bots` was the first frozen param; the
execution tier is the second, and it is the more dangerous one because the stale value decides *how the
work runs*, not merely who reviews it. Two findings, both re-grounded at `356973d80`:

1. **The live-resolve-wins rule is prose only.** OBSERVED: `phase-5-execute/standards/canonical_verify.md`
   step 2 says the resolve is the routing authority and wins over the stamp; nothing cross-checks the stamp
   against the resolver, and the observed run did not follow the rule. Instruction, not mechanism — the
   pattern this epic records as *script-emitted survives, prose-instructed does not*.
2. **The outcome vocabulary cannot name what happened.** OBSERVED: `_manifest_core.py`:320
   `VALID_RECORD_OUTCOMES = ('executed', 'skipped', 'loop_back', 'failed', 'error')`; a lost return lands in
   `error`, naming the command as the culprit. The signature is distinctive and machine-readable —
   **`total_tokens: 0` + `tool_uses: 0` + `duration_ms` beyond the tier budget** — so a distinct outcome
   (e.g. `return_lost`) keyed on it names the dispatch, not the work. `PLAN-TRUTH-089` (shipped #1399)
   already split `loop_back`/`failed` out of `error` on the same reasoning.

⚠ Directive for readers until this lands (from the sender): before attributing an `error` row to its
command, check `duration_ms` against the step's tier; never re-run the command on the strength of such a
row — the work most likely completed.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-145-declarations-that-cannot-learn-and-cannot-go-stale.md` (PLAN-TRUTH-145)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
