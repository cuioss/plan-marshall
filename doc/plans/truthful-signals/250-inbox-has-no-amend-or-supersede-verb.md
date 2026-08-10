> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A filed inbox message cannot be corrected, and correcting it anyway leaves no trace

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

The orchestrator inbox exposes `{write, validate, list, archive, detect}`. **Nothing changes the body of
a message already filed.** A message found wrong after filing has two routes and both are defective:

1. **Write a successor** — the queue then holds **two green-validating messages with no relation between
   them**. The listing reports two independent items and nothing marks one superseded.
2. **Edit the file directly** — which violates the standing scripts-only access rule.
   ⛔ **A contract satisfiable only by breaking another contract is not a usable contract.**

⛔ **`archive` is NOT the missing verb.** It means **consumed**. Retiring an erroneous message through it
would record *"acted upon"* about a message nobody acted on, corrupting the exact signal the archive
carries. **Retired-because-wrong and retired-because-done are different facts.**

## The signal half — why this epic owns it

The envelope carries a `created` timestamp and **no amendment marker**. A message in this project's own
inbox was **materially rewritten after filing** — a whole provenance section inserted, two artifact
pointers re-anchored — and its envelope is **byte-identical** to how it would look had none of that
happened. Validation returns success on both forms.

⇒ ⭐ **A post-filing mutation is structurally invisible.** `created` reads as a fact about the content;
after an edit it describes only the content's **first version**. **A field that is not wrong, but has
quietly stopped meaning what its name says** — this epic's archetype.

⚠ **The consuming orchestrator read that amended message and could not have known it was amended.**

## ⭐ The sibling surface already solved this

The lessons skill carries `supersede`, `cleanup-superseded`, and a tombstone record: a replaced lesson
leaves a resolvable tombstone and its id keeps resolving. **The inbox has the *consumed* half and not the
*replaced* half.** The asymmetry looks accidental rather than designed — and **the reference
implementation is one skill over.**

## Goal

A filed message can be corrected through the sanctioned surface; a corrected message is visibly
different from an untouched one; a sender's stream can signal that it has ended; and all of that is
expressed in **one** message-state vocabulary rather than two.

## Deliverables

1. **D0 — GATE: design the message-state vocabulary ONCE, and record what was rejected.** Mutates
   nothing. Choose between:
   - **`amend`** — replaces the body in place, **preserves `created`**, stamps an `amended` marker plus a
     monotonic `revision`.
   - **`supersede --by {successor}`** — mirrors the tombstone model; the original stays resolvable and
     stops presenting as live.
   ⭐ **Derive from the lessons skill's model rather than re-inventing one.**
   ⛔ **The vocabulary must also be able to express *"this sender will send no more"*** — the
   stream-termination concept, which is a *sender-stream* state rather than a *message* state. **Design
   both into one vocabulary.** ⛔ **If the chosen model cannot express stream termination, say so
   explicitly at D0** and re-scope rather than bolting on a parallel enum later. *Neither half may invent
   a second enum* — that is the entire reason these were merged.
   *Done when:* the model is chosen, the rejected alternative is recorded, and stream termination is
   shown to fit.
2. **D1 — The envelope gains a field that makes post-filing mutation visible.**
   *Done when:* an amended or superseded message is distinguishable **from its envelope alone**.
   ⛔ **THIS IS THE LOAD-BEARING HALF.** A verb that edits the body but leaves the envelope unchanged
   **replaces an authorized bypass with an unauthorized one and fixes nothing about the signal.** If only
   one deliverable ships, it is this one.
3. **D2 — `validate` and `list` enforce and surface it.** Revision monotonicity asserted; a revised
   message surfaced in the listing so it is **visibly different from a virgin one**.
   *Done when:* both verbs reflect the new state, and the listing's row schema carries it.
4. **D3 — Stream termination and the drain.** Implement the terminal marker in D0's vocabulary, and
   whatever drain behaviour it enables.
   *Done when:* a sender can mark its stream ended, and the drain can tell an empty queue from a finished
   one.
   ⭐ **This is the concept that made two plans into one.** Expressed as one more value in an existing
   vocabulary, it is small; expressed as its own parallel mechanism, it is a second enum in one schema.
5. **D4 — Fold the archive into per-sender subdirectories.**
   *Done when:* the archive is foldered, the existing files are migrated, and **the count moved per
   sender is reported** — a silent relocation is indistinguishable from a lossy one.
   ⛔⛔ **THE LOAD-BEARING CONSTRAINT, and the reason this cannot be done as a plain file move.** The
   archive is a **load-bearing index**: sequence allocation takes the sender's highest number across
   **both** the live and archived directories. A move that hides archived messages from that scan
   **re-opens a retired sequence number** — a defect a previous plan already fixed once.
   ⛔ **The move must be ATOMIC with the function updates** — one commit. A move that lands without the
   code change is silently destructive.
   ⛔ **The naive failure is silent in four places**: the sequence allocator stops seeing archived twins
   (**this is the one that loses data**); the count collapses to zero; message resolution misses, so a
   consumed message reads as missing; and the archive-write path joins a flat destination whose conflict
   check assumes flatness.
   ⚠ **Confirm the sender identifier is safe as a DIRECTORY name.** It is validated today for use as a
   **filename component**, which is not the same check. **An asserted absence of traversal characters is
   verified exactly like an asserted presence.**
6. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) An amended message is distinguishable from a virgin one.
   - (b) `created` **survives** an amend.
   - (c) A superseded message stops appearing as live **while staying resolvable**.
   - (d) Revision monotonicity is **rejected** when violated.
   - (e) ⛔ **The control that pins D4:** allocate a sequence for a sender whose **only** prior message is
     archived **in a subdirectory**, and assert **no reuse**. **Verify this fails against the naive
     implementation** — without it the migration is unfalsifiable.
   *Done when:* all five pass, each seen red first.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables against a raised cap of twelve.
The source spec, after absorbing a sibling and receiving a third plan's foldering deliverable, was
counted at ten — **collapsed here, because the absorbed halves share one vocabulary rather than
concatenating two.** ⭐⭐ **The merge DELETED coordination machinery rather than adding it**: an
envelope-ownership split, a serialization note, and a notify-before-landing obligation all existed only
because two plans were editing one schema. **One plan needs none of them.**

## Out of scope

- ⛔ **Carving inbox messages out of the scripts-only access rule. DO NOT close this that way.** The rule
  is what keeps the store machine-readable and schema-valid. **The defect is the missing verb, not the
  rule.**
- **Using `archive` as the correction verb.** See above: it means consumed, and overloading it corrupts
  the archive's only signal.
- **Modifying the lessons skill.** It is **read as a reference implementation and not touched.**
- **The rest of the epic-compaction work** the foldering deliverable arrived from — the generated-block
  mechanism, settled-narrative relocation, the anchor shape. Those belong to their own plan; only the
  foldering came here, because **this is its declared surface**.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/orchestrator.py` and its
  `_orchestrator_inbox.py` module — the `inbox` verb group. ⭐ **All archive path logic lives in ONE
  module**; the top-level script only wires argument parsing. That is what makes D4 a surgical change
  rather than a migration.
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/standards/inbox-envelope.md` — the
  envelope schema.
- `marketplace/bundles/plan-marshall/skills/manage-lessons/**` — **read-only reference.**
- `test/plan-marshall/marshall-orchestrator/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The `inbox` verb group exposes exactly five subcommands, with no amend or supersede | OBSERVED | `inbox --help` — an asserted **absence**, cheap to re-check and worth re-checking |
| A materially amended message validates green and is byte-identical in its envelope | OBSERVED | ⛔ that message is under `.plan/` and **not reachable from this clone**. **Reproduce the shape instead**: file a message, edit it, validate — the claim is about the schema, not that file |
| The lessons skill carries a supersede/tombstone surface | HYPOTHESIS | that skill — ⭐ **read it first; it is the reference implementation and D0 should derive from it** |
| All archive read/write logic lives in one module, across four functions | HYPOTHESIS | `_orchestrator_inbox.py` — **by symbol.** ⛔ **D4's whole sizing rests on this**; if the logic is scattered, D4 grows and must be re-sized |
| Sequence allocation scans **both** the live and archived directories | HYPOTHESIS | the allocator — **by symbol.** ⛔⛔ **The load-bearing claim.** Its own docstring reportedly states the reason; if the scan does not do this, D4's hazard changes shape |
| The sender identifier's validation forbids traversal characters and separators | HYPOTHESIS | the validator — ⛔ **it was written for a FILENAME component, not a PATH component.** An asserted **absence** of unsafe characters, verified as a presence |
| The archive holds ~652 files across three epics, the largest ~428 across 36 senders | HYPOTHESIS | ⛔ **under `.plan/`, not reachable here.** Motivation for foldering; **re-derive the counts at migration time and report per sender** |
| Nothing currently mis-reports because of the missing verb | HYPOTHESIS | ⚠ accepted scope note: this is a **surface gap, not a mis-firing predicate**. **The failure it enables is prospective** — the next filer either dirties the queue or breaks the access rule. **Sizing it small is correct; leaving it unlogged is not** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(e) is the control assertion and the most important test here.** It is what distinguishes *"I
  changed four functions"* from *"I changed four functions correctly"*, and the failure it guards against
  — silent sequence reuse — does not surface until two messages collide.
- ⛔ **D1 must be verified from the envelope alone.** If an amended message is only distinguishable by
  diffing its body against a copy nobody kept, the field is decorative.
- **D4 must report the migrated count per sender.** D4's own rule — a silent relocation is
  indistinguishable from a lossy one — applies to D4 itself.
- **Confirm the archive claim is atomic**: one commit containing both the move and the code change. A
  reviewer should not be able to check out an intermediate state where the archive is foldered and the
  allocator is not.
- Python, documentation, and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **A residual cross-version hazard worth stating**: the code ships through a plugin cache while the
  archive lives in the repository, so a **stale pinned executor** would run flat-reading code against a
  foldered archive. It is bounded — only this repository, only after migration — and it is the standing
  plugin-pin issue rather than a new defect, **but note it in the report, because that pin recurs
  often.**
- ⛔ **Sequencing: serialize against the other plans touching this file** — the epic-compaction plan and
  the operator-report plan both reach `orchestrator.py` and the envelope schema. A skill-rename plan in
  this epic would also move every path here; **re-ground if it lands first.**
- ⛔ **Do not go looking for the orchestrator spec, the absorbed spec, the inbox contents, or any landing
  record.** They live under `.plan/`, which is git-ignored and absent from this clone. Everything needed
  is in this file.
