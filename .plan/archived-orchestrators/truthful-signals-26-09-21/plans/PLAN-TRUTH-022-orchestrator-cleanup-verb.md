# PLAN-TRUTH-022: A `cleanup` verb — regenerate the derivable ledger, relocate the settled narrative, delete nothing

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-30 from a standing operator request: *"Do complete, thorough cleanup. Remove all noise /
> historical / archaeological data from the ledger, archive if sensible. Persist everything so we can
> restart the orchestrator."* Given repeatedly by hand today; this makes it a verb.

## Objective

Add a tenth verb to `marshall-orchestrator` that compacts a **live** epic's ledger without losing
anything, and leaves the epic restartable from the persisted tree alone.

⚠ **`archive` does NOT already do this.** That verb is post-`close`, mechanical, and whole-tree: it
relocates a **closed** epic to `archived-orchestrators/`. This verb operates on a **live, mid-flight**
epic and touches content, not location. The two are complements, not overlaps.

## ⛔ The design constraint that makes or breaks it: the axis is DERIVABLE vs NARRATIVE, not OLD vs NEW

The request's own words — *"historical / archaeological"* — name the **wrong axis**, and following them
literally would produce a destructive verb. This ledger's highest-value content is old, settled, and
reads exactly like archaeology:

- *"PLAN-42 spec-corruption claim RETRACTED — don't re-flag it"*
- *"the `--enabled-bots` fold was MISATTRIBUTED — a TRUTH-012 deliverable aimed there would find nothing"*
- *"PLAN-105 was reading `staged` while CLOSED-SUPERSEDED — it was offered as an emit candidate because
  the row lied"*
- *"the gate itself may be stale rather than pending"*

**Every one of those exists to prevent rework, and a trim-by-age pass deletes all of them.** ⭐ The
correct discriminator is whether a statement is **re-derivable from `status.json` and the filesystem**:

| Class | Treatment |
|---|---|
| **Derivable** — counts, queue tables, per-plan status mirrors, PR/landing stamps | **REGENERATE**. Never curate; a hand-maintained copy of a derivable fact is the defect. |
| **Narrative** — decisions, retractions, refutations, standing rules, "do not re-derive this" | **PRESERVE**, regardless of age. Relocate if bulky; never drop. |

✅ **The population is ALREADY DERIVED — do not re-derive it from scratch.** #1064's D4 gate enumerated
**13 derivable assertion classes vs 8 genuinely narrative across 7 files**, and named three unprotected
derivable surfaces: the `epic.md` **Ordered Queue** (4 derivable columns, **no `BEGIN/END GENERATED`
guard**, and *strictly larger* than the inbox count #1064 fixed), the **Decisions** list, and the
**anchor's PR/CI clause**. **That enumeration is this plan's input.** Re-verify it at outline — it is
several days old by then — but start from it.

## ⭐ FOLDED 2026-07-30 — six drained candidate-lessons name the surfaces, one by one

Drained from PLAN-203's OUTBOX (`-002` … `-007`), all `component: plan-marshall:marshall-orchestrator`.
**This is the D4 enumeration resolved to individual surfaces** — take it as the working list, re-verified
at outline:

| Msg | Surface named | Class |
|---|---|---|
| `-003` | **`epic.md` Ordered Queue duplicates FOUR `status.json` columns with no generated-block guard** | derivable, unguarded |
| `-004` | **`epic.md` Decisions list is a second copy of the `logs/` decision store with no stated authority** | derivable, **and no authority declared** |
| `-005` | **the resume anchor asserts a PR number and CI state in prose that both sides could derive** | derivable, in the machine authority itself |
| `-006` | **the operator-confirmed `running` state has no machine field — anchor prose is its sole carrier** | narrative carrying what should be derivable |
| `-007` | **five emitted verb-output counts are LLM-tallied from free-text prose and cannot be checked** | derivable, unverifiable as produced |
| `-002` | *a hand-written count that drifted is a SAMPLE of narrative-outranks-derivable, never the population* | the **rule**, not a surface |

⭐ **`-002` is the one to read first, and it sharpens this plan's own framing:** the drifted inbox count
that motivated #1064 was **a sample of the class, not the class**. This plan must not repeat that — the
six rows above are *also* a sample until the outline re-derives them.

⚠ **`-004` adds something D4 did not:** the Decisions list is not merely duplicated, it has **no stated
authority** — so a reader cannot tell whether `epic.md` or `logs/decision.log` wins. **Declaring the
authority is a prerequisite to regenerating it**, and may be the cheaper half of the fix.

⚠ **`-006` is the odd one out and must NOT be "fixed" by regeneration.** `running` is operator-confirmed
and *nothing observes it* (no liveness signal exists — API-Sheriff round-4 #5). It is narrative because
the world offers no derivable source, **not** because someone wrote prose where a field belonged.
⇒ **Regenerating it would fabricate a fact.** Leave it narrative and say why, or fix the liveness gap
first. **This is the clearest illustration of why the derivable/narrative split cannot be applied
mechanically per-field.**

## Deliverables

### D1 — GATE: name, scope, and the relocation target (mutates nothing)

Settle four things before any edit:

1. **Verb name.** `cleanup` is the operator's word but implies deletion, which this verb must never do.
   **Recommend `compact`** (or `reconcile`, though the standard already uses "reconcile" for the
   status.json → epic.md direction, so it would collide). ⚠ Whichever wins, the SKILL router table, the
   standard, and the workflow doc must agree — a verb named in one and not the others is this epic's
   doc-contract-divergence archetype.
2. **Is `resume_anchor` in scope?** ⚠ **It should be, and it is the strongest single argument for this
   plan.** The anchor is the machine authority a fresh session reads first; on 2026-07-30 it was rewritten
   **eight times in one day** and grew past **12 KB**, accumulating settled content (full round-3/4/5
   verdicts, a semantic-merge audit) that belongs in `epic.md`. **An anchor that must be re-read in full to
   find the next action has stopped being an anchor.** Decide the target shape: a short next-action head
   plus pointers, or a bounded section set.
3. **Relocation target.** `history.md` is currently written only at `close`. Decide whether `compact`
   appends to it mid-life, uses a new `settled.md`, or moves items into the existing `landings/` records
   they belong to. ⚠ Whatever is chosen, **a pointer must remain at the origin** — a reader following the
   old path must land on the content, not on absence.
4. **Idempotence.** Running it twice must be a no-op. State how that is achieved (content-addressed
   markers, or a `compacted_at` stamp per section).

### D2 — extend the GENERATED-block mechanism to every derivable surface

`epic.md`'s START-HERE block already carries `BEGIN/END GENERATED: resume-summary` markers and a
regeneration invocation. **The Ordered Queue table — same file, same authority, 4 derivable columns — has
no such guard**, which is why it drifted to 8 rows for plans absent from `status.json` and 11 shipped
plans shown live. ⇒ Bring every derivable surface under the same marker-and-regenerate contract.

⚠ **Settle the known tension the operator is already owed a decision on:** the persist contract says the
generated block is *"GENERATED, never hand-written"*, yet the live block is **hand-annotated** and
substitutes a pointer sentence for the verbatim `resume-summary` output — a deliberate deviation to avoid
duplicating a 12 KB anchor into `epic.md`. **Either the generator must emit the annotations (blocked
reasons, per-row caveats) or the contract must permit an annotation zone outside the markers.** Pasting
verbatim as-is would destroy information the annotations carry.

### D3 — relocate settled narrative, with pointers

Move bulky settled narrative to the D1 target. **Preserve verbatim** — retractions, refutations, and
"do-not-re-derive" notes are the anti-rework record and must survive intact. A section is "settled" only
when its subject is closed (a shipped plan's residue, a resolved defect), **never merely because it is
old**.

### D4 — report what moved, never trim silently

Emit a TOON report: sections regenerated, items relocated (with source and destination), invariants
checked, and **anything the verb declined to touch and why**. ⛔ **A silent compaction is
indistinguishable from a lossy one** — this epic's entire theme. The report is the deliverable that makes
the verb safe to run unattended.

### D5 — invariant verification, and tests

Verify after compaction: queue rows ↔ `plans/` spec files **bidirectionally** (the check that bites — a
count match alone passes with a mismatched pair); no shipped rows in the live Ordered Queue; no orphaned
spec file; every relocated item reachable from its pointer. ⚠ **Use the proven procedure for any
whole-array write**: snapshot → write → diff, expecting only the intended change.

Tests: (a) idempotence — second run is a no-op; (b) a narrative retraction survives a compaction pass
verbatim; (c) a stale derivable row is corrected, not preserved; (d) the report names every mutation.

### D6 — fold the inbox archive into per-sender subdirectories ⭐ OPERATOR-RAISED 2026-08-03, MEDIUM priority

**Operator**: *"Looking at the inbox archive: it is currently crowded. Archive them into sub-directories
with `sender_id` as directory name."*

⭐ **Filed here rather than as a new plan**: this verb was staged from an operator request whose own words
were *"remove all noise / historical / archaeological data from the ledger, **archive if sensible**"* —
**this is that clause, made concrete.** ⚠ It is the verb's first **location**-level operation, which the
Objective currently excludes (*"touches content, not location"*). ⛔ **D1 must widen that sentence or
justify keeping D6 out** — an undeclared scope widening is exactly this epic's doc-contract-divergence
archetype.

**OBSERVED — the crowding is real, whole population, 2026-08-03:**

| Epic | Archived | Senders |
|---|---:|---:|
| `truthful-signals` | **428** | 36 |
| `code-intelligence-substrate` | 141 | 10 |
| `review-apparatus` | 83 | 8 |

⇒ **652 files in three flat directories**, the largest at 428 across 36 senders.

#### ⛔ OPERATOR CHALLENGE 2026-08-03 — *"why do consumers need to be depth-aware? Isn't it done by a script anyway? So this is a surgical update"* — CORRECT, and my framing below was wrong

✅ **Verified first-party after the challenge.** Every read and write of `inbox/archive/` lives in **ONE
module**, `_orchestrator_inbox.py`: `next_sequence` (:328), `inbox_counts` (:405), `resolve_message`
(:440), `cmd_inbox_archive` (:843). `orchestrator.py` holds **no archive path logic at all** — it wires
argparse. Everything else that mentions the path is **documentation** (`SKILL.md`,
`inbox-envelope.md`) plus four test files.

⇒ ⭐ **It IS a surgical update: four functions in one file, plus the docs and tests, in one PR.**

⛔⛔ **And the "coordinate with the siblings so a depth-aware reader doesn't meet a flat writer" warning
I sent them is REFUTED by the same read** — **there is one implementation serving all three epics**, and
all three archives live under this repo's `.plan/local/orchestrator/`. **The divergence I warned about
cannot occur.** Correction sent.

⚠ **What actually survives from the analysis below** — smaller, but real:

1. **The change must be ATOMIC**, not phased: `mv` the files without the code edit and you get silent
   sequence reuse. That is a *"do it in one commit"* requirement, **not** a two-phase migration.
2. **The control test still earns its place** — it is what distinguishes "I changed four functions" from
   "I changed four functions correctly".
3. ⚠ **One genuine cross-version residue**: the code ships in the plugin cache while the archive lives in
   the repo, so a **stale pinned executor** would run flat-reading code against a foldered archive.
   Bounded (only this repo, only after migration) and it is the standing plugin-pin defect rather than a
   new one — ⛔ **but note it, because that pin recurs roughly daily.**

⇒ **D6 is re-scoped from a phased migration to a single surgical change.** The section below is retained
because the MECHANISM it documents is still exactly right — it is the *size* I overstated, not the
failure mode.

#### ⛔ The mechanism (accurate) — the archive is a load-bearing INDEX, not a storage bin

Verified first-party in `_orchestrator_inbox.py`. **Four consumers read `inbox/archive/` with a flat
`iterdir()`**, and per-sender subdirectories break every one of them **silently**, because
`_MESSAGE_NAME_RE` simply fails to match a directory name and the entry is skipped:

| Site | Consequence of naive foldering |
|---|---|
| **`next_sequence` (:328-334)** | ⛔⛔ **stops seeing archived twins ⇒ SEQUENCE REUSE** |
| `inbox_counts` (:405-412) | archived count silently collapses to 0 |
| `resolve_message` (:440) | `inbox/archive/{name}` probe misses ⇒ a consumed message reads as `missing` |
| `cmd_inbox_archive` | writes `archive/` joined with the source name; the `archive_conflict` inode check assumes a flat destination |

⛔⛔ **`next_sequence` is the one that loses data.** Its docstring states the reason in as many words:

> *"Consulting the archive is load-bearing: a drain relocates a consumed message rather than deleting it,
> so a sender could otherwise reuse a sequence whose archived twin already exists."*

⇒ **This is the exact defect `PLAN-93` (SHIPPED) fixed** — *inbox-sequence-reuse-collides-with-the-archive*.
**A naive `mv` into subdirectories re-opens it**, and the failure is silent until two messages collide.

⭐⭐ **And note the archetype**: the rationale survives in the docstring while the guarantee is destroyed
by moving the files. **That is precisely the *"a comment explaining WHY a guard exists is load-bearing"*
class carried into `PLAN-TRUTH-050` from the `api-sheriff` report** — *deleting the guard while keeping
the reason.* Here the guard is a directory shape.

#### Requirements

1. **Make the four functions depth-aware and move the files IN THE SAME CHANGE.** `rglob`-style
   traversal, or an explicit `archive/{sender}/` join. ⛔ **Atomic, not phased** — the only ordering
   requirement is that a `mv` never lands without the code edit.
2. ⛔ **A test that FAILS pre-fix**: allocate a sequence for a sender whose only prior message is archived
   **in a subdirectory**, and assert no reuse. ⭐ **Verify it fails against the naive implementation** —
   this is the control assertion, and without it the migration is unfalsifiable.
3. **`inbox archive` writes into the per-sender subdir**, creating it on first use, preserving the
   no-replace hard-link claim and the inode-identity discriminator that make a repeated drain idempotent.
4. **Migrate the 652 existing files**, and ⛔ **report the count moved per sender** — a silent relocation
   is indistinguishable from a lossy one (D4's rule, applied to itself).
5. ⚠ **Decide whether `sender_id` is a safe directory name.** Senders are validated for `inbox write`
   (`invalid_sender_id`), but **that validation was written for a FILENAME component, not a path
   component.** Confirm it forbids traversal and separators before it becomes a directory. **An asserted
   absence is verified exactly like an asserted presence.**
6. ✅ **Cross-epic coordination is NOT required** — one implementation serves all three epics and all
   three archives live under this repo. The migration is one run of one script over all of them.
   ⚠ Courtesy notice already sent; **the divergence risk it warned about was refuted** (above).

⚠ **Priority MEDIUM, by operator designation** — and, after the challenge above, **the size matches the
priority**: four functions in one module, its docs, its tests, and a one-shot migration. ⛔ The only
non-obvious part is that the file move alone is silently destructive, which is what the control test
pins.

## Expected surface

- **HYPOTHESIS** — `marshall-orchestrator/SKILL.md` verb-routing table + a new `workflow/compact.md`
  (verified-at-outline; the router table is OBSERVED to exist, the new doc's shape is not yet decided)
- **HYPOTHESIS** — `persona-marshall-orchestrator/standards/orchestration-model.md` § Persist/Stop-Resume,
  which currently says only *close freezes* and *archive relocates*; a third content-level operation needs
  stating there
- **HYPOTHESIS** — `orchestrator.py`: the deterministic half (regeneration, invariant checks, the report)
  belongs in a script per the dispatch-granularity heuristics; the narrative-vs-settled judgement does not
- **REPORTED (not orchestrator-verified)** — #1064's D4 enumeration as the input population

**Disjointness:** `marshall-orchestrator` + `persona-marshall-orchestrator`. ⛔ **Collides with
PLAN-TRUTH-002**, which declares itself *exclusive against anything touching dispatched workflow docs* —
a new `workflow/compact.md` is exactly that. ⛔ **Collides hard with PLAN-TRUTH-015**, which renames the
whole skill. **Sequence: TRUTH-022 before TRUTH-015** (renaming a verb set is cheaper than adding a verb
to a renamed set), and never concurrent with TRUTH-002.

## Notes

- ⭐ **Evidence this is a real recurring need, not a nicety:** the operator issued this instruction by hand
  repeatedly, and in one day this epic's anchor was rewritten 8× past 12 KB, its Ordered Queue drifted to 8
  phantom rows plus 11 live-shown shipped plans, and its START-HERE block went stale while carrying a
  contract violation. The manual version is being performed; it is simply not repeatable or auditable.
- ⚠ **The verb must refuse to run on a `closed` epic** — that tree is the frozen audit record, and `close`
  already froze it. Compaction is a live-epic operation only.
- ⭐ **Do not let this verb infer "noise" with an LLM judgement over the whole file.** The derivable half is
  mechanical and must stay mechanical; only the settled-vs-live narrative call needs judgement, and it
  should be presented for confirmation rather than applied silently on first run.

## Write-Boundary

Repository source + tests only; NO writes into any epic's `.plan/local/orchestrator/` tree beyond what the
verb itself performs at runtime. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.


---

## ⛔ SPLIT APPLIED 2026-08-09 (PARTIAL) — D6 MOVED OUT, AND THIS SPEC IS STILL OVER THE CEILING

**D6 (fold `inbox/archive` into per-sender subdirs) is REMOVED from this spec and now belongs to
`PLAN-TRUTH-038`**, whose declared surface is exactly `orchestrator.py`'s `inbox` verb group plus
`inbox-envelope.md`. The load-bearing `next_sequence`-scans-both-directories constraint travelled with
it. **Do not re-implement it here.**

⚠ **HONEST ACCOUNTING: this spec goes 15 → 14 deliverables. The ceiling is 12, so it is STILL OVER.**
⛔ **A second cut is owed** and the review is recording that rather than reporting the split as solved —
declaring a bloat guard satisfied by a partial split is the vacuous-guard shape applied to process.

⭐ **Suggested second cut, for whoever takes it**: the **`resume_anchor` shape** question (D1.2) is
separable from `epic.md` compaction — it is a different file, a different authority, and its own
operator-owed decision. It is also the half `PLAN-TRUTH-074` D8 now depends on, which argues for cutting
it out and sequencing it early rather than leaving it inside a 14-deliverable plan.

⛔ **SERIALIZE with `-038` and `-050`** (shared `orchestrator.py` / `inbox-envelope.md`), and with
`-074`, which calls this spec's compaction stage.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
