envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=lessons-routing
kind=finding
created=2026-09-11T15:52:14Z

# Forward from `truthful-signals` — the `wrong_store` guard fires correctly and is overridden anyway: two consumer repos, a measured stranded corpus, and a sender's own reversal of its routing rule

Relayed to `truthful-signals` during the 2026-09-11 cross-repo lessons drain and routed here because
`lessons-routing` owns the `wrong_store` / `--allow-foreign-store` surface (`PLAN-LR-01`, `PLAN-LR-02`)
and the stranded-corpus recovery (`PLAN-LR-04`). Nothing is staged in `truthful-signals` for it; the
message is discarded there with this forward as its destination. Leads, not facts — dispose onto your
items.

## Item 1 — `lessons-handling-26-09-04-01-032` (Token-Sheriff): the override, not the guard, is the defect

- Token-Sheriff's lessons store held **9 active lessons, every one a `plan-marshall:*` component**
  (`phase-4-plan` ×2, `phase-5-execute`, `manage-lessons`, `build-maven` ×2, `manage-architecture`,
  `automatic-review`, `plan-marshall`). The sender probed the sanctioned path and the guard **refused**
  (`error: wrong_store` … *"Pass --allow-foreign-store to override."*). ⇒ **The guard works; plans override
  it**, and the override produces exactly the harm the guard exists to prevent: the lessons are invisible
  to the repository that owns the defects.
- **The consuming project pays twice**: its founding goal was to empty its corpus (21 of 21 retired, 47
  tombstones), and it regressed **0 → 9** entirely from foreign-bundle lessons.
- ⚠ **It RECURRED after the first relocation.** The nine were relocated into `truthful-signals` on
  2026-09-09; Token-Sheriff PLAN-08 then routed correctly through the epic inbox, but **PLAN-09 filed two
  more into the local store again** (relayed as `-054`/`-055`, both now dispositioned in
  `truthful-signals`). ⇒ Whether the override is avoided depends on which path a plan happens to take.
- The sender's suggested remedies: treat `--allow-foreign-store` as operator-only; consider fail-closed for
  automated callers with an explicit operator confirmation to override; and **establish whether a second
  path BYPASSES the guard rather than overriding it** — it could not tell from the store which route the
  nine took, and a bypass and an override need different fixes.

## Item 2 — `api-sheriff-deployment-configurability-008` provenance (API-Sheriff): a consumer REVERSED its own store-boundary rule, and its reasoning is `PLAN-LR-02`'s question

API-Sheriff discarded a plan's candidate lesson on a store-boundary ground (the defect lived in a bundle
the repo does not own), then filed a same-shaped foreign-bundle lesson in its own store a day later, and
retroactively reversed the discard. Its corrected rule, verbatim in substance:

> **The deciding question is whether THIS repository repeatedly pays the cost, not which bundle owns the
> remedy.** A foreign-bundle defect that costs local plans on every run belongs in the store the local
> plans consult — the store is CWD-keyed, so a lesson filed elsewhere is invisible to the plans that keep
> hitting it. `--allow-foreign-store` exists for exactly this case. The store-boundary rule still holds for
> a foreign observation carrying no local cost and no local actionable.

⚠ **This is the opposite conclusion from Item 1's sender**, drawn from the same guard, and both are
coherent: one repo optimises for the owner seeing the defect, the other for its own plans seeing the
workaround. That tension is exactly what an ownership predicate that "answers the wrong question" has to
resolve — the two audiences (the repo that can FIX it, the repo that keeps PAYING for it) are different
populations, and a single store can serve only one. Both API-Sheriff and Token-Sheriff have since
integrate-then-removed their foreign lessons into `truthful-signals`' inbox, so the corpus question is
settled for today; the routing rule is not.
