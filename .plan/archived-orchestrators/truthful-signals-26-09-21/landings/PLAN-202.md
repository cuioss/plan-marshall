# Landing Analysis: PLAN-202 — Compose-time subtractions drop steps nobody authorised

epic: truthful-signals
workstream: WS-01
pr: 1066 — merged as `d04ac98ed`

## Ground-truth corroboration

- ✅ **PR #1066 merged** — `git log origin/main` shows `d04ac98ed fix(manage-execution-manifest): guard
  compose-time step subtractions (#1066)`. Verified independently of the landing message's claim.
- ⚠ Per-deliverable fidelity is the plan's own assertion; recorded as verification debt, consistent with
  PLAN-103 and PLAN-203.

## ⭐ The headline: the hypothesised count was a SAMPLE, 3 vs 13

The request hypothesised **3** compose-time subtraction predicates. The population derived from the
actual `_decide` matrix is **13**. Five rows subtracted **entirely silently** — no decision-log line, no
compose-result record — and two of those collapsed `phase_6.steps` to a three-step minimum with no
per-drop record at all.

⭐ **This is the third plan in a row whose gate refuted its own request's framing**, and the pattern is
now unmistakable enough to be a planning rule rather than an observation:

| Plan | Request framing | Derived population |
|---|---|---|
| PLAN-203 (#1064) | the inbox count is the only drifted count | 13 derivable vs 8 narrative across 7 files |
| **PLAN-202 (#1066)** | **3 subtraction predicates** | **13, five of them silent** |
| PLAN-115 (#1065, open) | a two-verb `ci` asymmetry | ~18 consumers across 11 skills |

⇒ **A request that states a count states a sample.** The mandated population-derivation gate is what
turns it into a scope, and in all three cases the gate was the highest-value deliverable in the plan.

## ⛔ CORRECTION — D2 SHIPPED PARTIAL, and this report over-credited it

**An earlier revision of this report said "the writer shipped with the readers", framing Defect A as
closed. That was wrong, and the error was mine: I took the landing message's account of the writer as
evidence the immunity path was reachable, without asking what invokes it.** Corrected from the operator's
report and from inbox message `-013`:

What shipped — the plan-local channel (`status.metadata.finalize_step_overrides`), **both** compose-side
readers through one seam, and a **manual CLI writer** (`manage-config finalize-steps set-lane`).

⛔ **What did NOT ship — any caller that writes the `phase-1-init` posture answer into that channel.** The
footprint touches no `phase-1-init` file and no posture-gathering workflow. ⇒ **Re-run the originating
Defect A scenario today and the operator-named step is still silently dropped**, unless the operator
separately knows to invoke `set-lane` — and nothing prompts them to. The originating scenario is explicit
in the request: the operator was asked at `phase-1-init`, answered, **named `pre-submission-self-review`
specifically**, and 27 minutes later an implicit gate removed exactly that step. **That is still live.**

⭐ **The vacuous-guard verdict inverts, and the corrected reading is more interesting than the wrong one.**
The writer that shipped is a writer *for a test*, not a **producer for the scenario the deliverable exists
to fix**. So the guard's predicate still cannot fire in the ordinary unprompted flow — the archetype was
not defeated, it was **relocated one level up**, from file granularity to deliverable granularity.

⛔ **The recursion is exact, and it is the actual finding.** The plan filed candidate-lesson `-004` about
precisely this failure mode — *"widening readers without shipping a writer builds a guard whose predicate
can never fire"* — caught the asymmetry **inside deliverable 1** (which is why the CLI writer shipped at
all), and **did not apply the same completing question to the deliverable as a whole**. Third recorded
instance of a plan reproducing its own target defect class inside its own work (cf. PLAN-86; and this
plan's self-review found 8 instances of its target class in its own diff).

⚠ **Why nothing caught it:** the request named **four** deliverables with individual acceptance language;
the outline produced **two**. The fold is individually defensible, but it **dissolved the boundary at
which each request deliverable would have been graded** — so a partial deliverable became structurally
ungradeable. Graded against the *request*: D1 met, **D2 partial**, D3 partial (11/13 sites, named in the
doc), D4 met. D3's partiality was caught and filed; **D2's was not.**

⇒ **Owed work STAGED as PLAN-TRUTH-021** — wire the `phase-1-init` execution-profile override answer into
`status.metadata.finalize_step_overrides` at the moment it is answered. **Until then D2 is open.**

## Residue accepted (each rides as its own candidate-lesson)

1. ⛔ **D3 gap, named rather than hidden.** `decision-rules.md` states normatively that *"every
   subtraction is reported"*, but two phase-5 sites (`canonical_verify_inactive` and the verify-step
   resolvability filter) still emit only a decision-log line with **no compose-result record**. ⇒ A
   normative doc claim that is broader than the shipped behaviour is a **doc-contract divergence in the
   fix's own documentation** — written down as a known gap, which is the right call, but it is real and
   owed.
2. ⚠ **Review coverage was ONE bot deep.** Only pr-agent reviewed; coderabbit refused on an **awaitable**
   rate-limit window and sourcery on a hard quota. ⭐ **`review_rate_window_await` is `false`, so the
   awaitable refusal was never waited out** — a recoverable gap left unrecovered by configuration.
   ⇒ Routes to `review-apparatus`.
3. ⭐ **"Dogfood proves nothing here" — the plan said so itself.** The plan-local lane override works
   end-to-end, but this plan is `multi_module`, where `scope_gated_finalize` has no drop set. **This
   run's retrospective surviving is NOT evidence the immunity mechanism works.** ⇒ Exemplary honesty:
   a passing self-test correctly refused as evidence. Keep this framing.
4. ⚠ **Doc-contract divergence found in passing:** `sonar-roundtrip.md` tells the agent to resolve
   `sonar_project_key` *"from the Sonar provider configuration"*, but **no script or config surface
   exposes it.**

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1066; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] landing message archived
- [ ] 7 candidate-lesson messages (002–008) — pending disposition in the drain
- [ ] post-merge PR revisit for #1066 — owed (ours: `manage-execution-manifest`, not a review PR)

## Parallelization Consequence

PLAN-202 held `manage-execution-manifest`. Its landing **unblocks the PLAN-202 half** of
PLAN-TRUTH-001's and PLAN-TRUTH-003's blockers — but **PLAN-57 still runs**, so TRUTH-003 remains
blocked on `manage-status`, and TRUTH-001's own spec sequencing must be re-derived at emit rather than
inferred from this sentence.
