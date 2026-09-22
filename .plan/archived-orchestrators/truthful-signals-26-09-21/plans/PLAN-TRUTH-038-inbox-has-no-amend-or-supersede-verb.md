# PLAN-TRUTH-038: a filed inbox message cannot be corrected, and correcting it anyway leaves no trace

epic: truthful-signals
workstream: WS-01

## Objective

`orchestrator inbox` exposes `{write, validate, list, archive, detect}`. **Nothing changes the body of a
message already filed.** A message found wrong after filing has two routes and both are defective:

1. **Write a successor** — the queue then holds two green-validating messages with **no relation
   between them**; `inbox list` reports two independent items and nothing marks one superseded.
2. **Edit the file directly** — violates the standing `.plan/` scripts-only hard rule. ⛔ **A contract
   satisfiable only by breaking another contract is not a usable contract.**

⛔ **`archive` is NOT the missing verb.** It means *consumed*. Retiring an erroneous message through it
would record "acted upon" about a message nobody acted on — corrupting the exact signal the archive
carries. **Retired-because-wrong and retired-because-done are different facts.**

## The signal half — why this epic owns it

The envelope carries `created` and **no amendment marker**. `barrier-override-not-head-bound-001.md`
was materially rewritten after its `created=2026-08-02T13:42:19Z` (a whole provenance section inserted,
two artifact pointers re-anchored) and the envelope is **byte-identical** to how it would look had none
of that happened. `inbox validate` returns `status: success` on both forms.

⇒ ⭐ **A post-filing mutation is structurally invisible.** `created` reads as a fact about the content;
after an edit it describes only the content's *first version*. **A field that is not wrong, but has
quietly stopped meaning what its name says** — this epic's archetype.

⚠ **This orchestrator consumed the amended message this drain and could not have known it was amended.**

## ⭐ The sibling surface already solved this

`manage-lessons` carries `supersede` + `cleanup-superseded` + `.tombstones/{id}.json`: a replaced lesson
leaves a resolvable tombstone and the id keeps resolving. The inbox has the *consumed* half and not the
*replaced* half. **The asymmetry looks accidental, not designed** — and the reference implementation is
one skill over.

## Deliverables

1. **D0 — GATE: choose `amend` vs `supersede`, and record the rejected one.**
   `inbox amend` replaces the body in place, **preserves `created`**, stamps `amended` + a monotonic
   `revision`. `inbox supersede --by {successor}` mirrors the tombstone model; the original stays
   resolvable and stops presenting as live. ⭐ **Derive from `manage-lessons` rather than re-inventing.**
2. **D1 — the envelope MUST gain a field that makes post-filing mutation visible.** ⛔ **This is the
   load-bearing half.** A verb that edits the body but leaves the envelope unchanged replaces an
   authorized bypass with an unauthorized one and fixes nothing about the signal.
3. **D2 — `validate` and `list` enforce and surface it.** Revision monotonicity asserted; `rev>1`
   surfaced in `list` so an amended message is visibly different from a virgin one. ⚠ **`list` is
   `PLAN-TRUTH-032`'s extension point too — coordinate, do not fork the row schema.**
4. **D3 — tests, verified to FAIL pre-fix.** (a) An amended message is distinguishable from a virgin
   one. (b) `created` survives an amend. (c) A superseded message stops appearing as live while staying
   resolvable. (d) Revision monotonicity is rejected when violated.

## ⛔ Prohibited remedy

Do **NOT** close this by carving inbox messages out of the `.plan/` scripts-only rule. The rule is what
keeps the store machine-readable and schema-valid. **The defect is the missing verb, not the rule.**

## Claim Labels

- **OBSERVED (first-party)**: `inbox --help` enumerates exactly five subcommands, no amend/supersede.
- **OBSERVED (first-party)**: the amended message is in this epic's own inbox and validates green.
- **OBSERVED**: `manage-lessons` carries the supersede/tombstone surface.
- **Scope note (from the filer, accepted)**: this is a **surface gap, not a mis-firing predicate** —
  nothing currently mis-reports. ⚠ **The failure it enables is prospective**: the next filer without an
  operator authorizing a one-off bypass either dirties the queue or silently breaks the access rule.
  **Sizing it small is correct; leaving it unlogged is not.**

## Expected Surface

- **OBSERVED**: `marshall-orchestrator/scripts/orchestrator.py` — the `inbox` verb group
- **OBSERVED**: `marshall-orchestrator/standards/inbox-envelope.md` — the envelope schema
- **HYPOTHESIS**: `manage-lessons` — read as reference, **not modified**

## Dependencies and Sequencing

- ⛔ **SERIALIZATION PAIR with `PLAN-TRUTH-032`** — same file, same verb group, and both extend the
  `list` row schema. **Prefer 032 first** (it is the larger design and sets the row shape), then this.
  ⭐ **Evaluate folding this in as a 032 deliverable at outline** — that may be cheaper than two passes.
- ⚠ `PLAN-TRUTH-015` renames the skill; re-ground paths if it lands first.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-038-inbox-has-no-amend-or-supersede-verb.md"
```

## ⛔ ENVELOPE OWNERSHIP SPLIT 2026-08-08 — this plan lands FIRST and OWNS the message-state vocabulary

`PLAN-TRUTH-032` (inbox termination signal / autonomous drain / plan-side inbox) and this plan both
add verbs to `orchestrator inbox` **and both add fields to the envelope schema**
(`standards/inbox-envelope.md`). They are NOT duplicates — amend/supersede is *message* state,
032's terminal marker is *sender-stream* state — but shipped independently they would produce **two
overlapping message-state vocabularies in one schema**, which is the exact "neither side invents a
second enum" failure this fleet already guards against cross-epic.

**Decision: this plan lands FIRST and owns the envelope's message-state vocabulary** (the
`amend`/`supersede` model, the `revision` counter, the tombstone/superseded marker). Rationale:
a superseded/amended message is a property of a message that already exists, so it is the narrower
and more settled concept; 032's terminal marker is about when a *stream* ends, and it can be
expressed as one more value in a vocabulary that already exists — the reverse is not true.

⇒ **032 becomes a CONSUMER**: its terminal marker uses this plan's field and vocabulary rather than
adding a parallel one. ⛔ If this plan's D0 chooses a model that cannot express *"this sender will
send no more"*, say so explicitly at D0 and tell 032 **before landing** — that is the one event that
re-opens the split.

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -032

**Component:** `marshall-orchestrator (the inbox protocol)` · **Deliverables after merge: 10** (raised cap is 12).

⭐⭐ **This merge DELETES coordination machinery rather than adding it.** These two plans were carrying
an explicit envelope-ownership split, a serialization note, and a notify-before-landing obligation —
all of which existed only because two plans were editing one schema. **One plan needs none of it.**

- **`-038`** — nothing changes the body of a filed message; the two available routes are *write a
  successor* (two green messages, no relation between them) and *edit the file* (breaks the scripts-only
  rule). A contract satisfiable only by breaking another one.
- **`-032`** — the channel has no termination signal, no autonomous drain, and no plan-side inbox.

⇒ **Both add `orchestrator inbox` verbs and both add envelope fields.** Merged, the message-state
vocabulary (amend / supersede / revision / terminal) is designed **once, as one vocabulary**, which was
the entire risk the split was managing: *neither side invents a second enum.*

⛔ **Delete the ownership-split sections in both specs at outline** — they are now self-referential.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count at outline; overlapping deliverables COLLAPSE rather than concatenate.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
and the sole sanctioned write mechanism are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⭐⭐ SPLIT RECEIVER 2026-08-09 — ABSORBING `PLAN-TRUTH-022`'s INBOX/ARCHIVE FOLDERING (D6)

`PLAN-TRUTH-022` stands at **15 deliverables, over the 12 ceiling**, and has been owed a split since the
cap was raised. The full-corpus review resolves it here rather than deferring it again.

**This spec takes `-022`'s D6 — folding `inbox/archive` into per-sender subdirectories.** The rationale
is surface, not convenience: **D6 is four functions in ONE module (`orchestrator.py`'s `inbox` verb
group) plus the envelope schema — which is exactly this spec's declared surface** and is disjoint from
everything else `-022` does (`epic.md` compaction, the GENERATED-block mechanism, `resume_anchor` shape,
settled-narrative relocation).

⛔ **The load-bearing constraint travels with it**: the archive index is load-bearing — `next_sequence`
allocates above the sender's highest number across **both** `inbox/` and `inbox/archive/`, so a move that
hides archived messages from that scan **would re-open a retired sequence number** (this is how PLAN-93
was re-opened once). **The move must be atomic with the four function updates.** ✅ No cross-epic
coordination is owed: one implementation serves all three epics.

⇒ **This spec goes from 4 deliverables to 5; `-022` drops from 15 to 14.** ⚠ **14 is still over the
ceiling** — `-022` needs a second cut, and the review records that rather than pretending one split
solved it. ⛔ **SERIALIZE with `-022` and `-050`** — all three touch `orchestrator.py` and
`inbox-envelope.md`.
