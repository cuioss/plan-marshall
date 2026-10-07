envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=landing
created=2026-07-30T11:33:46Z

## What landed

**Plan**: `compose-time-subtractions-drop-steps` — PR #1066.

Compose-time subtraction of manifest steps is now recorded rather than performed
silently. The plan widened the compose-result record so every step a `_decide`
matrix row removes from `phase_6.steps` (or from `phase_5.verification_steps`)
leaves a per-drop record naming the predicate that dropped it, and added the
plan-local lane override that lets a plan exempt itself from a scope-gated drop.

## The headline number

The request hypothesised **3** compose-time subtraction predicates. The
population derived from the actual `_decide` matrix is **13**. Five rows
subtracted entirely silently — no decision-log line, no compose-result record —
and two of those collapsed `phase_6.steps` to a three-step minimum with no
per-drop record at all. The gap between the hypothesis and the population is the
whole story of this plan: the hypothesised count was a sample, not an
enumeration.

## Defect A had a third half

The outline initially scoped Defect A as "widen the two readers". A third
component was nearly missed: without also shipping a **writer** for the new
immunity path, the widened readers would have guarded a predicate that can never
fire — the vacuous-guard archetype this project keeps re-hitting. The writer
shipped with the readers.

## Residue the epic should track

1. **D3 gap, named not hidden** — `decision-rules.md` states normatively that
   "every subtraction is reported", but two phase-5 sites
   (`canonical_verify_inactive` and the verify-step resolvability filter) still
   emit only a decision-log line with no compose-result record. This is written
   into the doc as a known gap rather than overclaimed, but it is real and owed.
2. **Review coverage on this PR was one bot deep** — only pr-agent reviewed.
   coderabbit refused on an *awaitable* rate-limit window; sourcery refused on a
   hard quota. `review_rate_window_await` is currently `false`, so the awaitable
   refusal was never waited out.
3. **Dogfood proves nothing here** — the plan-local lane override works
   end-to-end, but this plan is `multi_module`, where `scope_gated_finalize` has
   no drop set. This run's retrospective surviving is NOT evidence that the
   immunity mechanism works.
4. **A doc-contract divergence found in passing** — `sonar-roundtrip.md` tells
   the agent to resolve `sonar_project_key` "from the Sonar provider
   configuration", but no script or config surface exposes it.

Each of the above rides as its own `candidate-lesson` message alongside this
landing.
