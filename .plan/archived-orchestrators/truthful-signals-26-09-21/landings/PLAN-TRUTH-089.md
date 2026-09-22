# Landing analysis — PLAN-TRUTH-089

**Plan:** `planning-lane-change-type-scope-execution-manifest`
**Spec:** `plans/PLAN-TRUTH-089-planning-lane-change-type-scope-and-execution-manifest.md`
**PR:** #1399 · **Merge commit:** `d03ca621c` · **Workstream:** WS-01

## ⭐⭐⭐ The first COMPLETE landing this epic has drained in the current series

`landing-check`: **`complete: true`, `missing_keys[0]`.** The previous two landings (`-126`, `-093`)
each failed on `merge_state` alone. This one supplies it — and supplies it from the right place:

```text
step.branch-cleanup.merge_mechanism = merge_queue
step.branch-cleanup.merge_state     = merged
step.branch-cleanup.work_performed  = true
merge_commit_sha                    = d03ca621cac8e18feb0762df63b27cc7ca13a7f1
```

The archived record confirms it structurally: `branch-cleanup`'s `phase_steps` entry now carries
`['outcome', 'display_detail', 'facts']` with a **populated `facts` map** — where `-093`'s carried
`head_at_completion` outside any map and `-126`'s carried none at all.

⛔⛔ **But this does NOT close the Open Defect, and reading it as a fix would be wrong.** The
prescription was already in place when the other two ran: `branch-cleanup.md` was last modified at
`cc5ea40a1` (#1392, 2026-09-03), and it carries 24 references to `merge_mechanism`. **Both `-126` and
`-093` finalized on 2026-09-05, after that.**

⇒ **The defect is a COMPLIANCE gap, not a missing capability: the standard prescribes typed facts,
three runs met the same prescription, and only one emitted them.** That is R75's archetype exactly —
*a mandatory emission with no post-condition check is a promise, not a contract.*

⚠ **One alternative cause, stated rather than dismissed:** seating is per-envelope, not per-session, so
`-126` and `-093` may have run against seated skill bodies predating #1392. **Not corroborated** — the
seated version of a finalize envelope is recorded nowhere reachable. Either way the remedy is the same:
a post-condition check on the emission, not more prose.

## Merge corroboration

| Source | Result |
|---|---|
| `git log main` | `d03ca621c fix(planning-lane): stop reporting confidence inputs don't support (#1399)` |
| `ci pr view --pr-number 1399` | `state: merged`, `merge_commit_sha: d03ca621cac8e18feb0762df63b27cc7ca13a7f1` |
| the landing's own `merge_state` | `merged` — ⭐ **and it agrees with both**, the first landing in this series where the message could be checked rather than substituted for |
| `manage-status list` | absent from the live store |

## Deliverable fidelity — 11 of 13, and the shortfall is DISCLOSED

`deliverables_total=13`, `deliverables_done=11`. **Two partial, zero missed**, named in the Residue:
`shim-marker-convention.md` was never written, and two declared test files were never touched.

⭐ **Publishing 11/13 rather than rounding to `done` is the behaviour this epic asks for.** A landing
that reported 13/13 would have been unfalsifiable from the payload alone.

⚠ **Scope note:** at 13 deliverables this plan sat at the operator-raised split guard (12) and above it.
The Residue's own account — 81% of spend in finalize, five self-seeding chains — is the cost profile the
guard exists to predict. **Worth carrying into the next split decision as evidence, not as a rule.**

## ⛔⛔ Re-firing: 124 firings across 22 steps — FOURTH instance, and the series has doubled

| Plan | firings | steps | headline |
|---|:-:|:-:|:-:|
| `-075` | 29 | 22 | `23/23` |
| `-126` | 67 | 23 | `23/23` |
| `-093` | 75 | 23 | `23/23` |
| **`-089`** | **124** | **22** | `23/23` |

Eleven steps re-fired. `project:finalize-step-plugin-doctor` **19×**, `pre-submission-self-review`
**19×** (15 `loop_back`), `pre-push-quality-gate` **18×**, `lessons-housekeeping` **17×**,
`automatic-review` **10×** (including two `failed`).

⇒ **124 firings to complete 22 steps is a 5.6× multiplier**, and it is the direct cause of the cost
profile below. The `23/23`-style headline has now under-reported by 7, 44, 52 and **102** firings across
four consecutive landings.

## ⭐⭐⭐ The plan reproduced its own subject matter, and named the terminating move

**14 of 51 finalize Q-Gate findings (27%) are SELF-SEEDED** — a finding on prose a previous round's own
fix authored — forming **five chains across four files**. The longest ran four consecutive rounds in
`pre-submission-self-review.md`. One chain **oscillated**: `manage-execution-manifest/SKILL.md:330` was
fixed by DELETION in one round and by RESTORATION in the next.

⭐⭐ **The transferable finding is the terminating move, and it was the same in every chain:**

> **Replace the restatement with a pointer at its declaring source.** Correcting it authors a new claim
> to audit; deleting it under-declares the payload.

⇒ Promoted to the global lessons corpus. **This is the third independent confirmation in this epic that
the vacuous/self-seeding archetype recurs INSIDE its own fix** (`-055`, `-075`, now `-089`) — treat it as
expected, not as a surprise.

## ⛔ `done` does not distinguish converged from budget-exhausted

`pre-submission-self-review` fired 19 times; `loop_back_iteration` reached **17 of `max_iterations: 17`
— the ceiling was fully consumed.** The last three closes were OUT OF BUDGET, and the ledger spells them
`outcome: done`, byte-identical to a converged close. The final `display_detail` even reads *"agent
stalled before filing, findings NOT recorded"* — a partial round, stored under `done`.

⭐ **The plan's own finding `28e6e8` names the distinction while fixing a different instance of it.**
The round-loop termination rule exists; **the ledger that would carry its outcome does not.** Folded to
`PLAN-TRUTH-108`, whose subject is exactly a self-decided close.

## Review coverage is narrower than the participation guard proves

`sourcery` refused **STRUCTURALLY on every round** (cause `size`, cap 150 000 diff characters against
5073 changed lines) and reviewed none of this diff; optional, so it never gated, and **waiting cannot
cure a size refusal.** CodeRabbit ran **seven review rounds with disjoint commit ranges**, so **no single
tree was reviewed in full** — and the retrospective's gate-delta is `excluded` with `structural_share`
**WITHHELD rather than reported as 0.**

⭐⭐ **Withholding rather than zeroing is the correct behaviour and should be protected in any fix.**

Two instrumentation blind spots, both filed by the run and both bearing on `review-apparatus`:
`142a26` — a refusal or re-review published as an in-place comment **EDIT** is invisible to BOTH
`wait-for-comments`/`rate_limited_bots[]` (samples newest by `created_at`) and `ci pr reviews`
(enumerates submissions only), observed on both bots through different readers; and `3d9d19` —
`head_sha_verified` is hard-coded to `matched_signal == 'review'`, so a comment-path review reads as
declined, **which would have stalled this PR if read at face value.**

## Reconciliation actions

- Queue: `PLAN-TRUTH-089` → `shipped`; `pr` = `1399`; `landing` = `landings/PLAN-TRUTH-089.md`.
- Inbox: 9 messages drained (8 candidate-lessons + the landing).
- Capacity: R 3 → 2 of N=3. **One slot frees.**

## Parallelization consequences

No collision observed with `-125` or `-099`, which started during this plan's finalize. ⭐ Both are now
store-corroborated (`one-format-several-implementations-that-disagree` @ `3-outline`,
`the-ledger-has-no-safe-single-row-append` @ `3-outline`) — **the pending attestation recorded at the
last verb is discharged**, and both rows now name their live plan.

## Open items this landing leaves

| Item | Owner |
|---|---|
| `branch-cleanup` fact emission is a COMPLIANCE gap, not a capability gap | Open Defect — **reframed**, still UNOWNED |
| `23/23` under-reports by up to 102 firings — fourth instance | Open Defect — **UNOWNED**, series updated |
| `done` conflates converged with budget-exhausted | folded to `PLAN-TRUTH-108` |
| post-merge `--base-ref` empty diff reported `diff_available: true` | folded to `PLAN-TRUTH-104` |
| a `not_evaluated` fragment is dropped, erasing its declared coverage gap | folded to `PLAN-TRUTH-104` |
| `changed_files` never persisted ⇒ `ARTIFACT_EMISSION` can never run | folded to `PLAN-TRUTH-138` |
| finalize cost share, dispatch-audit confidence, unmeasured decomposition | forwarded to `code-intelligence-substrate` |
| the pointer-not-restatement rule | promoted to the global lessons corpus |

## Metrics

**52h49m wall (190 105 s) · 13 916 554 tokens · 81% of it in `6-finalize`** — 11.27M / 2245 tool uses to
the gate versus **507K / 194 to the implementation**, against a ~2.0M anchor (**~7×**).

⛔ **The 11.27M is a FLOOR and the run says so: `6-finalize` never recorded an end time, so the phase is
open in the metrics.** ⭐ Publishing an open phase as a floor rather than closing it silently is correct;
do not "fix" it by stamping an end time after the fact.

⇒ **This is `PLAN-TRUTH-107`'s cost case at its strongest yet, and the re-fire table above is the
mechanism**: 124 firings for 22 steps, with the two most expensive steps firing 19 times each.
