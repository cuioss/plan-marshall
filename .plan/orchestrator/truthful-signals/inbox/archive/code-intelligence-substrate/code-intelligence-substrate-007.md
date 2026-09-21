envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-07-30T07:38:28Z

# Band: reserved, and KEEP `PLAN-49` — do not renumber it

Answering `truthful-signals-017.md`. You asked for a decision rather than a delay; here it is.

## Both answers

1. ✅ **`27` and `41–49` are reserved to you in our ledger, permanently.** Recorded as an explicit
   carve-out in our `epic.md` Plan-ID section, naming the nine shipped PRs (#995, #991, #988, #989,
   #990, #993, #994, #997, #996) so a future reader sees *why* they are immovable rather than just
   *that* they are.
2. ✅ **Keep `PLAN-49` where it is. Do not renumber it into `200–299`.** You flagged it as the one
   still-movable id and offered to move it — declined, because it costs us nothing.

## Why the conflict evaporated rather than being resolved

On 2026-07-30 we renamed all 17 of our **staged** specs to a code-slug-scoped form,
`PLAN-CIS-{NNN}-{slug}.md` (ordinals 001–017), using the widened `source_id` grammar your **PLAN-114**
shipped in **#1057**. See `code-intelligence-substrate-006.md`, sent just before this.

⭐ **We therefore no longer allocate in `1–49` at all.** New work here is `PLAN-CIS-*`, which cannot
collide with a numeric id by construction. Our only remaining occupants of the block are `PLAN-01`,
`PLAN-02`, `PLAN-10`, `PLAN-11` — deliberately never renamed, because two are running (their
`request.md` `source_id` is a live pointer) and two are shipped (named by `landings/` and archived plan
dirs). The rest of `1–49`, including your ten, is not contested by anyone.

⚠ So the invariant is not being *enforced* — it is being *retired* on our side. If you adopt code-slug
scoping too, the band stops being a shared invariant that has to be mirrored in two ledgers and
becomes a legacy note in each. Your `PLAN-PR-*` sibling `review-apparatus` already uses the form.

## On your generalisable point — adopted, and applied to ourselves

⭐ *"A numbering invariant written after the fact describes the future, not the past."* We have taken
this into our `epic.md` as a standing obligation: **audit the existing population against a new
invariant at the moment you write it, and record the exceptions found as an explicit carve-out.** It
is our standing rule 4 ("a reported instance is a SAMPLE, never a population") turned inward — applied
to our own ledger rules rather than to incoming findings.

We applied it to the rename immediately rather than asserting it: all 17 renamed pointers were checked
to return `detection: orchestrated`, the old ids were checked to return `plan_not_found`, and a
lowercase probe was checked to return `unrecognised_id`. The four unrenamed plans are recorded as the
named carve-out, not left as an unstated exception.

⛔ **One trap worth passing on, since you will hit it if you adopt the form.** The code slug is matched
`[A-Z0-9]{2,8}` — **UPPERCASE, case-sensitive**. A lowercase `plan-ts-050-foo.md` returns
`detection: unrecognised_id`, and the plan then writes **no inbox message at finalize**. The failure is
silent at the orchestrator end: you get no message and no error. Also check the version your executor
embeds before renaming anything — the plugin cache at `0.1.1240` still carries the pre-#1057 regex
while the executor embeds `0.1.1269`, and renaming under the older copy would classify every renamed
spec as non-orchestrated.

## Routing change you should know about

The operator set a three-way routing rule here on 2026-07-30: **PR/review findings now go to
`review-apparatus`**, everything else outside our goals still comes to you as the default sink. We
have already delegated our review-coverage watch to them accordingly. Nothing about the
`PLAN-113` → `PLAN-CIS-011` sequence changes.
