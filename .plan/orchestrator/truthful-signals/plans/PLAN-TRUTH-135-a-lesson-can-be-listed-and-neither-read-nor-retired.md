# PLAN-TRUTH-135: A lesson can be listed and neither read nor retired

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-04 from inbox drain message `lessons-handling-26-09-04-01-004.md` (a `finding`,
> revision 1, amended by its sender), relayed from **Token-Sheriff**. ⭐ Discovered *while performing*
> a lessons-consolidation pass, not filed by a plan — **the pass would have silently dropped three of
> twenty-one lessons had the discrepancy not been checked.**

## Objective

**`manage-lessons list` and every id-addressed verb behind the shared resolver disagree about the same
population, and the disagreement is silent.** In the observed store, `list` returned **21 rows** and
`get` returned `not_found` for **3** of them — for files that are **present on disk, non-empty, and
well-formed markdown**.

The cause is an exact correlation over the whole corpus — two metadata formats coexist in one store:

| Format | `list` | `get` / `remove` |
|---|---|---|
| Bare `key=value` lines, no delimiters | ✅ 18 rows | ✅ success |
| **YAML frontmatter**, `---` delimited | ✅ 3 rows | ⛔ `not_found` |

Every YAML-frontmatter lesson is unreachable; every `key=value` lesson is reachable. The three
affected files also carry different filesystem permissions (`-rw-r--r--` vs `-rw-------`), consistent
with a **different producer** than the one the resolver expects.

⛔⛔ **It is not only `get` — `remove` is affected too, and that turns a read gap into a STUCK STORE.**
The sender amended its own finding after attempting the retirement: **18 of 21 retired normally with
tombstones; 3 could not be retired at all.** So the defect is **`list` vs every id-addressed verb**,
because they share the resolver. ⚠ **A fix that closes only `get` leaves `remove` broken.**

⛔ **The practical consequence is worse than a silent read gap.** A lesson in this state is
**permanently stuck in the corpus through the sanctioned interface**. The only ways out are to rewrite
the file's metadata by hand — **which bypasses the tombstone the store writes for every other
retirement, destroying the audit record the removal path exists to produce** — or to fix the resolver.
The reporting orchestrator declined the hand-edit for exactly that reason and left the three in place.

⭐⭐ **Two failure signatures compound, and both are this epic's own archetype one level down:**

1. **`get` returns `not_found`** — the vocabulary for *absent*, used here for *present but
   unparseable*. A caller cannot distinguish a lesson that was removed from one it cannot read: the
   same `absent`-vs-`unreadable` distinction the orchestrator's own corpus verbs are careful to keep
   separate (ADR-019).
2. **`list` fills the unparsed fields with empty strings** instead of marking the row degraded, so the
   three rows appear with **empty `component` and `category`** — which reads as *"this lesson has no
   component"* rather than *"this lesson could not be parsed"*. **The loss is invisible at the only
   surface that would show it.**

⛔ **The consumer this actually breaks is the lessons-handling mode itself.** Its Step 2 is *"list,
then read each lesson's full body, one `get` call per lesson id from the list output"* — precisely the
list→get walk that drops these. **A consolidation, dedup, or retirement sweep performed that way
operates on 18 of 21 lessons and reports success.**

### ⭐ Corroborated first-party — and this repository's corpus is CLEAN

This orchestrator ran the same list→get walk over **this** checkout before staging: **39 lessons
listed, 39 `get` successes, 0 `not_found`; 39 of 39 files in `key=value` form, 0 YAML-frontmatter, 0
other.** ⇒ **The resolver gap is REAL but LATENT here — no producer in this repository has written the
YAML form.** ⛔ That changes the priority, not the validity: there is no data loss to recover locally,
and the fix is still owed because the resolver is format-sensitive and the other store proves a
producer exists somewhere in the toolchain.

## Deliverables

1. **D0 — GATE: find the PRODUCER, and derive the affected store population.** ⛔ **The three files are
   readable markdown carrying complete, correct metadata in a format something in the toolchain
   wrote** — so a producer exists and D0 must name it before any resolver change is chosen. Sweep for
   every writer of a lessons file and report which format each emits, plus a list→get walk over every
   reachable store. ⛔ **Publish both populations with their sizes.**
2. **D1 — close the resolver gap at the SHARED seam, not at one verb.** Whichever arm D0 selects, the
   fix lands where `get` and `remove` both read, and D3 must prove `remove` is fixed too. The two arms
   the sender names, and the choice is D0's:
   - **Make the resolver accept both formats** — the migration-tolerant reading, if the YAML form was
     ever legitimate; or
   - **Make `list` refuse to emit a row it cannot fully parse**, reporting it in a distinct
     `unreadable[]` population with its id and reason — so the walk sees a **stated failure** instead
     of a silent omission.
   ⛔ **What must NOT happen is the third option the sender explicitly rules out: leaving the resolver
   as-is and treating the files as corrupt.**
3. **D2 — `not_found` must stop meaning two things.** An id that resolves to a present-but-unparseable
   file returns a distinct state naming the parse failure, never the vocabulary for absence. ⭐ Adopt
   the discriminator vocabulary already in-tree (`inbox list`'s `inbox_state`, `corpus surfaces`'s
   `derivation_status`, `manage-lessons list-stalled`'s own `store_resolution`) rather than inventing
   a fourth.
4. **D3 — a retirement path for an already-stuck lesson, WITHOUT bypassing the tombstone.** The three
   observed files are the acceptance case: they must become retirable through the sanctioned interface
   **with their tombstone written**. ⛔ A fix that only prevents new occurrences leaves the existing
   population stuck forever.
5. **D4 — matched controls.** A `key=value` lesson must list, get, and remove exactly as today
   (**this is the load-bearing control — 39 of 39 lessons in this repository are that form and a
   regression would be total**), and a deliberately-malformed lesson must be reported as unreadable by
   `list` and by every id-addressed verb, in the same vocabulary.

## Claim Labels

- OBSERVED: the 21/18/3 split, the exact format correlation, and the permissions difference — reported first-party by the sending orchestrator over the Token-Sheriff store.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Foreign Token-Sheriff store; not reachable from this repo
- OBSERVED: `remove` refuses the same three with the same `not_found` — the sender's own amendment after attempting retirement (18 retired with tombstones, 3 not).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Sender own foreign-store amendment; not locally reachable
- OBSERVED: `list` renders the three rows with empty `component` and `category` rather than marking them degraded.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Foreign-store list rendering; not reachable from this repo
- OBSERVED (this orchestrator, first-party at HEAD): this repository's corpus is 39/39 `key=value`, 39/39 reachable, 0 YAML-frontmatter ⇒ **the gap is latent here, not live**.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: This repo 78 lesson files are all key=value, 0 YAML, all parse non-empty
- HYPOTHESIS: `get` and `remove` share one id-resolver. ⛔ The sender asserts it from behaviour; **not read at source here**. Confirm/refute at `manage-lessons` § the id-resolution helper (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: cmd_get and cmd_remove both call the shared read_lesson() in _lessons_io.py
- HYPOTHESIS: the YAML form was written by a plan-marshall producer rather than by hand. ⛔ NOT established by either side — the permissions difference is suggestive, not probative. D0 settles it (verify-at-outline).
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED: manage-lessons.py writers emit key=value only; no YAML producer exists in this source and all 78 local lesson files parse. Re-scoped.
- ⚠ Verify-first clause: this repository's `manage-lessons remove` is recorded in operator memory as **destroying a lesson while returning `not_found`**, which CONTRADICTS the sender's observation that `remove` refuses and leaves the file. ⛔ **Settle which behaviour is current at HEAD before D3 designs a retirement path** — the two readings imply opposite acceptance tests, and acting on the wrong one risks destroying the very records D3 exists to preserve.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED at HEAD: manage-lessons.py:912 read_lesson() then :913-919 returns not_found BEFORE any unlink. The destroy-while-reporting-not_found path is gone. Re-scoped: the standing rule is retired as historical and the spec is narrowed to the foreign-store half.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/` — the shared id-resolver behind `get` and `remove` (D1, D2, D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` — the `list` / `get` / `remove` payload contracts (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/lessons-handling.md` — Step 2's list→get walk, the broken consumer (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-lessons/` — the D4 controls (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py` — `consult`'s main-anchored plan-directory resolution; added 2026-09-11 by the fold of `lessons-handling-26-09-04-01-036`

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Overlaps `PLAN-TRUTH-121`** (producers report success over a write nothing can read) on `manage-lessons/**` — that spec's member 1 is `manage-lessons add` returning success for a body-less lesson. **Same store, adjacent defect, different verb.** ⛔ **SERIALIZE**; and D0 should read `-121`'s member 1 first, because a body-less lesson and an unparseable one may share a producer.
- ⚠ **Overlaps `PLAN-TRUTH-119`** on `manage-lessons/**`. Sequence at emit.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-135-a-lesson-can-be-listed-and-neither-read-nor-retired.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⛔⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (2 claims contradicted, and one of them RETIRES A STANDING RULE)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 5 | a YAML-front-matter producer exists and explains the unreadable lessons | **REFUTED** — `manage-lessons.py` writers emit `key=value` only; there is **no YAML producer in this source**, and all 78 local lesson files parse |
| 6 | `manage-lessons remove` **DESTROYS** a lesson while returning `not_found` | **REFUTED at HEAD** — `manage-lessons.py:912` calls `read_lesson()` and `:913-919` returns `not_found` **before any unlink**. Verified twice, independently. |

⛔⛔⛔ **Claim 6 retires a standing operational rule that has been carried in this epic and in operator
memory for weeks** (*"never retry on `not_found`, because the retry destroys"*). **The destructive path
is gone.** ⇒ **The rule is now HISTORICAL and must not be restated as live.** ⚠ **But do not delete the
record**: the reason a `not_found` retry was dangerous is the anti-rework note, and a future reader who
sees only the fix will not know why the guard is load-bearing.

⇒ **This spec is substantially narrowed.** What survives is the FOREIGN-store half — claims 0-2 are
Token-Sheriff's store and remain `unverifiable` from here — plus claim 3/4's local finding that
`cmd_get` and `cmd_remove` share one `read_lesson()`. **D0 must re-derive whether a listable-but-unreadable
lesson is still reachable at all**, because both mechanisms this spec was staged on are now refuted
locally. **If it is not, this spec is a candidate for supersession rather than execution.**

## ⭐⭐ FOLDED 2026-09-11 — cross-repo lessons drain (1 Token-Sheriff item): a LIVE member on the same skill — the corpus cannot be consulted from a worktree-resident plan

`lessons-handling-26-09-04-01-036`: during a phase-3-outline revision **looped back from phase 5**, the
plan directory had already been moved into its worktree by `prepare_execute` (the ADR-002 move-based
model), and `manage-lessons consult` returned `outline_not_found`.

- OBSERVED at `356973d80`: `manage-lessons/scripts/_lessons_query.py`:239-240 resolves
  `plan_dir = resolve_main_anchored_path('plans') / args.plan_id` — the **main-anchored** plans root only —
  and looks for `solution_outline.md` there, where a worktree-resident plan's directory no longer exists.
  The verb offers no `--project-dir` / worktree re-anchoring.
- ⇒ **The prospective-lessons consult is unavailable to every loop-back outline revision** — the passes
  most likely to benefit from prior lessons, because they exist since something went wrong.
- ⭐ The verb's own error discipline is CORRECT and must survive: it returns `error: outline_not_found`,
  never a `surfaced_count: 0` success. The hazard is the CALLER's natural recovery — recording a zero the
  verb never produced. The observed agent read the corpus by hand instead; the right call, and it should
  not have been necessary.
- Remedy directions: resolve through the same `locate-plan-checkout` resolution the orchestrator entry
  paths use to re-anchor, or a `--project-dir` override mirroring the Bucket B convention.

⭐ **Bearing on the supersession question above**: the `get`/`remove` mechanisms this spec was staged on
are refuted locally, but this member is live and on the same skill's read surface. D0 should decide
supersession with it in view — it may be the spec's remaining substance rather than a rider.

### Claim labels for this fold

- OBSERVED: `_lessons_query.py`:239 resolves the plan directory main-anchored only, at `356973d80`.
- HYPOTHESIS: a loop-back outline revision runs with the plan directory resident in the worktree — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-5-execute/` § `prepare_execute`'s move step and the phase-6 loop-back re-entry (verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-144-the-lessons-corpus-and-producers-that-report-success-over-a-write-nothing-can-read.md` (PLAN-TRUTH-144)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
