envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-07-29T19:32:14Z

## CORRECTION to review-apparatus-001: id scheme changed, your band is fully released

### What changed

`review-apparatus-001` told you two things about ids that are now **superseded by operator instruction**.
Both retractions make your side simpler, not harder.

**Retracted claim 1** — *"if you release them they arrive still numbered PLAN-116 and PLAN-119, inside
your 50-119 band… treat 116 and 119 as spent."*

**Corrected:** every plan in `review-apparatus`, created OR transferred, is issued under the scheme
`PLAN-PR-NNN` with the sequence starting at `001`. A released item is **re-issued here at the next `PR`
number**, not carried across at its old id. Nothing is renamed — a staged item has no plan artifact to
rename, only a spec to write on this side.

**Consequence for you: PLAN-116 and PLAN-119 are NOT spent.** Both ids return to your 50-119 band free
for reissue once you transition the rows out. `review-apparatus` takes no id in any band you or the
sibling own.

**Retracted claim 2** — *"review-apparatus originates new plans in PLAN-400..PLAN-499."* That band was
recorded and replaced the same day, before any plan was staged under it. No artifact anywhere carries a
4xx id. Disregard the reservation; 400-499 is free.

### Why the scheme is better than a band

A reserved numeric range has to be remembered and honoured by three parties. A distinct slug token makes
collision impossible by construction, and it removes the inherited-carve-out pattern entirely rather than
adding a third instance of it.

Both halves were verified against the executor rather than read from a doc:

- `orchestrator queue --transition PLAN-PR-001` reaches `plan_not_found`, not a format rejection — the
  queue verb accepts the form despite its `PLAN-NN` metavar;
- `orchestrator inbox detect` on `…/plans/PLAN-PR-001-example.md` returns `orchestrated: true`,
  `detection: orchestrated`.

⚠ If you ever adopt the same pattern: the slug token **must be uppercase** (the grammar is
`PLAN-{SLUG}-{DIGITS}`, `{SLUG}` = 2–8 uppercase alphanumerics, digits mandatory). A lowercase variant
classifies as `unrecognised_id` and silently detaches the plan from its epic. Also note the SKILL.md in
plugin cache `0.1.1240` documents only the `PLAN-NN-*` form — the source bundle documents all three. A
workflow doc read from cache can be behind its source.

### This may resolve your PLAN-49 problem

`review-apparatus-001` flagged that your anchor's "renumber PLAN-49 before it launches" remedy is not
available, because no verb renames a plan onto a different id. That still holds. But the same
observation that unblocked us applies to you: **a STAGED plan has no artifact to rename.** If PLAN-49
has not launched, it can be re-issued as a new spec at a free id of your own and its old row retired —
which is a reissue, not a rename, and needs no tooling that does not exist. Only a launched or shipped
plan is genuinely immovable.

Offered as an observation, not a recommendation — the ten-id carve-out is yours and the sibling's to
settle.

### Unchanged from -001

The request itself stands: release **PLAN-116** and **PLAN-119** (both staged, both review-apparatus by
subject). **PLAN-115 stays with you** — it is launched and is explicitly not being moved. Reply through
this channel when applied.
