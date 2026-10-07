envelope_version=1
sender_type=plan
sender_id=api-sheriff-pro-forma-integration-test-fixes
epic=truthful-signals
kind=finding
created=2026-09-15T17:20:00Z

component=plan-marshall:phase-6-finalize
category=bug

# pre-submission-self-review cannot close on a consumer project whose only resolvable surfacer is the plan-marshall one — the verifier's stop question has no reachable "yes", so the step loops to the ceiling unless the operator overrides

⛔ **FILED FROM A LIVE API-SHERIFF FINALIZE, by operator direction on 2026-09-15.** Plan
`pro-forma-integration-test-fixes` (`cuioss/API-Sheriff`, a Maven/Java project, plan-marshall
0.1.1670). The operator resolved it locally by accepting the coverage gap; **locally overridden is not
upstream fixed.**

## What happened

`default:pre-submission-self-review` ships `default_on: true` to consumers. Step 1 discovered exactly one
implementor of `ext-point-self-review-surfacing` — `pm-plugin-development:ext-self-review-plan-marshall`
(`source: bundle-optional`, `default_on: false`) — and, because its notation **resolves in the consumer's
executor**, took the resolvable-implementor path rather than the zero-generator fallback.

That surfacer is plan-marshall-domain by construction. Over the Java/AsciiDoc footprint it returned:

- `files_in_scope: 20`, `surface_scope: full`
- `delta_coverage.by_class`: `other` 19 files, `structured_config` 1; `python`, `skill_doc`,
  `standards_doc`, `markdown_other` all 0
- `counts.total: 5`, `by_family: structural=0, prose_contract=5` — all five `touched_claims`
- one of the five was `.plan/marshal.json:385 provisioned_version` — **not a plan change at all**: it
  entered the footprint because the surfacer's `base_branch: main` resolved to the stale LOCAL `main`
  (`a2969b9`) after `finalize-step-sync-baseline` had rebased the feature branch onto `origin/main`
  (`fb9e774`), so the upstream steward commit's files appear as plan-authored.

The author (inline branch, 5 ≤ gate) grounded all five and returned
`self-review clean: 5 candidates examined, no check matched`. The Step 3b verifier then returned:

```text
acceptance: accepted
may_close: no
rationale: "Verdict stays within 5 candidates at full scope. Still no: plan-marshall surfacer saw 19/20
            Java/adoc files as other, structural=0, stale base_ref - a proper round could find more"
```

## Why this is a deadlock, not a slow convergence

Per Step 4 Branch B, `accepted` + `may_close: no` records `loop_back` with target `6-finalize` and files
`further_round_owed`. The re-fired round has the **same code, the same surfacer, the same classification**
— nothing any round can do changes the verifier's reason, because the reason is the surfacer's domain,
not the diff. So every admitted iteration reproduces the refusal until `max_iterations` (5 here, ~40k
tokens per verifier round plus the author round) and then halts finalize with nothing pushed.

The only exit is an operator override the workflow does not document: this run resolved `8a569c` as
`accepted` and force-recorded `done` with `"self-review gap accepted: surfacer blind to Java, 5 candidates
clean"`. That is honest, but it is improvised — `pre-submission-self-review.md` has no branch for
*"the verifier's refusal names a property no further round can change"*.

## The three defects, separable

1. **Resolvable ≠ applicable.** Step 1 selects "the first implementor whose notation resolves in the
   current executor". On a consumer, a bundle-optional plan-marshall surfacer resolves but does not
   apply to the footprint's content classes. The selection should gate on the implementor's declared
   domain (or on `delta_coverage` showing the whole scope landed in `other`) and route to the
   zero-generator fallback's **not-run** verdict — which is exactly the truthful record for "no surfacer
   that understands this code ran".
2. **Stop question without a terminal "no".** The verifier contract distinguishes `verdict_refused`,
   `further_round_owed`, `verifier_unavailable`, but all three `loop_back`. A refusal whose rationale is
   a round-invariant property (surfacer domain, analysis class) needs a non-looping disposition —
   escalate once, or record the gap — rather than burning the ceiling.
3. **Stale surfacer base ref after sync-baseline.** After `finalize-step-sync-baseline` rebases onto
   `origin/{base}`, the surfacer (and `manage-references compute-footprint`, which reported
   `base_ref: main` with the same two upstream files `.gitignore` / `.plan/marshal.json`) still diffs
   against local `{base}`, attributing upstream commits to the plan.

## Adjacent consumer-degradations observed in the same finalize (context, not the filed defect)

- `pre-push-quality-gate`: `derive_gate_bundles` resolves marketplace bundles only, so all 17 Maven
  paths landed in `unresolved` (bundle set empty); the module-tests arm degraded because the Maven
  project exposes no `module-tests` at default scope (`available: clean, quality-gate, verify, install,
  compile, package, coverage`). Both were handled by documented honest-degradation branches — recorded
  here only because they share the root cause: finalize steps shipped `default_on` to consumers whose
  deterministic seams are marketplace-shaped.
- `worktree-rebase-to` executor refresh: `executor_drift: unknown` — *"Explicit marketplace anchor did
  not resolve to marketplace/bundles"* — expected on a consumer, reported as a degradation every rebase.

## Evidence

- Plan log: API-Sheriff `.plan/local/worktrees/pro-forma-integration-test-fixes/.plan/local/plans/pro-forma-integration-test-fixes/logs/decision.log`
  (entries `pre-submission-self-review` 2026-09-15T17:15–17:17Z)
- Finding store: `artifacts/findings/qgate-6-finalize.jsonl`, hash `8a569c` (`further_round_owed`, resolved `accepted`)
- Surfacer notation: `pm-plugin-development:ext-self-review-plan-marshall:self_review surface --contract-radius 3`
- HEAD at the round: `f031bbaa3d22866dabe166044e728b2ec7b1cd4b`
