# WS-01: Audience classification — the axis the store has no concept of

epic: lessons-routing
status: active

## Charter

Establish **who can act on a finding** as a first-class, recorded property, and make every downstream
route a function of it.

⛔ **This is NOT "add a component field."** Component already exists, is already recorded on every
lesson, and already backs a guard — and grounding fact 3 shows that guard still cannot answer the
question that matters, because it tests *bundle ownership* (`does marketplace/bundles/{prefix} exist
here?`) rather than *actionability* (`can a reader of this store fix this?`). In a consumer repo the
first question is always "no", including for the client's own components. **A proxy that returns the
same answer for both classes is not a discriminator.**

## In scope

⭐ **The charter is what a lesson RECORDS at filing time**, of which the audience axis is the first and
largest question — but not the only one. A field added by any plan in this epic that is stamped when the
lesson is written belongs here.

- The audience axis itself: its values, where it is recorded, and whether it is derived or declared.
- **Provenance: the plan-marshall version the observation was made against** (PLAN-LR-05), which is
  mandatory and script-determined. ⚠ It sits here rather than under the transport workstreams because it
  must be stamped on EVERY lesson — a client-local finding needs it as much as an upstream one — and
  because it is written at `add` time, not at route time.
- Correcting the `wrong_store` ownership predicate so a client's own prefixed component is local.
- Retiring or re-scoping `--allow-foreign-store`, which today launders the very distinction it bypasses.
- Per-component / per-audience directory layout **as a candidate answer**, not as a premise.

## Out of scope

- The upstream transport (WS-02) and the durability substrate (WS-03) — both consume this axis and
  neither may define its own.
- `manage-findings` (plan-scoped Q-Gate / PR findings): a different store with a different lifecycle.

## Done when

A finding's audience is recorded at filing time, derivable without guessing, and no route in this epic
infers it independently.
