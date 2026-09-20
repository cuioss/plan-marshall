# PLAN-TRUTH-074: the cleanup reconciliation is a hand-run ritual with no verb

epic: truthful-signals
workstream: WS-01

> ⚠ **Slug note**: originally staged as `orchestrator-cleanup-verb` — which is **PLAN-TRUTH-022's exact
> slug**. Renamed at staging. Two specs one filename apart is how a duplicate survives a directory
> listing.

## ⭐ ABSORBS PLAN-TRUTH-034 — swept for orchestrator-surface overlap before emission

An `Expected Surface` sweep across all staged specs (not a title sweep — the `-069`/`-049` lesson)
returned **nine** other plans naming `marshall-orchestrator` or `orchestration-model.md`. Dispositions:

| Plan | Disposition | Why |
|---|---|---|
| **-034** orchestrator state is narrated where it should be typed | ⭐ **ABSORBED HERE** | Same files (`orchestrator.py resume-summary`, the START-HERE contract, `templates/epic.md`'s marker convention), and it is the **substrate this plan's report and restart-verdict stand on**. Building the verb over narrated state and re-typing it afterwards does D6/D7 twice. |
| **-022** the ledger `compact` verb | **boundary, NOT merged** | Different subject (ledger vs corpus) and already over the deliverable ceiling. See the boundary table below. |
| **-032** inbox has no emission-quiescence signal | ⛔ **HARD PRECONDITION, deliberately NOT absorbed** | The archive phase drains the inbox, and draining a plan whose finalize is still emitting is a recorded hazard — #1122's queue went **0 → 2 → 5 within minutes** while a check ran. So the verb needs it. But -032's D4(a) reaches `ref-workflow-architecture/standards/phase-lifecycle.md` and the phase SKILLs — **outside this component**, and component disjointness is what keeps the grouping parallel-safe. Absorbing it would widen the blast radius to buy nothing this plan can use earlier. |
| **-015** rename `marshall-orchestrator` → `plan-orchestrator` | ⛔⛔ **SEQUENCING BOMB — must not overlap** | **210 references across 54 files**, including 3 directory renames of the very component this plan edits. Whichever runs second rebases across a mass rename. **Serialize absolutely**; prefer -074 first (a rename over settled code is cheaper than a rename under an open feature branch). |
| **-038** inbox amend/supersede verb | not folded | Envelope-schema capability; the cleanup verb never amends a message, it only archives consumed ones. |
| -033, -036, -037, -050, -051 | not folded | Terminal-title, lane routing, and plan-side inbox emission — they mention the orchestrator, they are not about it. |

### What -034 contributes, and why it is not merely additive

-034's own OBSERVED evidence is that **hand-written prose was pasted INTO the generated block**, where
regeneration cannot correct it and nothing validates it. Every derived count in that block was wrong
**in the confident direction** (79 vs 81 rows, 43 vs 46 shipped, `R = 2 of N = 2 — AT CAP` against an
actual `R = 1 of N = 1`), and it **contradicted itself inside its own markers** — `R = 2 of N = 2 — AT
CAP` twenty lines above `R = 0 of N = 5 … three genuinely free`. A reader following the second sentence
would have emitted three plans while at cap.

⭐⭐ **And the failure is cross-epic and BIDIRECTIONAL**: `review-apparatus`'s block rendered *"both
slots are full → emit nothing"* while its authority said zero running and both named plans shipped —
**a free slot blocked by its own rendering.** Ours over-permitted; theirs under-permitted. **Both
directions cost, so this cannot be dismissed as cosmetic drift.**

⛔ **This plan is itself an instance.** While staging it, this orchestrator pasted the full
`resume_anchor` into the generated block and then had to restore the pointer convention by hand — the
exact defect -034 describes, committed by the party writing its fix, twice in one session. **That is the
argument for absorbing it rather than scheduling it: the contract cannot be enforced by discipline.**

## ⛔⛔ READ FIRST — THIS PLAN WAS ALMOST A DUPLICATE OF PLAN-TRUTH-022, AND THE BOUNDARY IS LOAD-BEARING

The operator asked for *"a single cleanup call"* covering: review and reconcile all outstanding plans;
check correctness against ground truth and applicability; check for ambiguity; check for duplication;
judge whether the distribution over plans is optimal; **apply the changes**; then fully clean the
ledger, archive what is done, persist, and prepare to restart.

**PLAN-TRUTH-022 already owns roughly half of that.** Its D1 even names `cleanup` as *"the operator's
word"* and recommends `compact` instead. Staging this as a fresh end-to-end plan would have filed a
duplicate of a 19-deliverable spec that is already owed a split — **the exact defect class this plan
exists to detect.** ⭐ The duplication check justified itself before the plan was written.

**The carve, and it is a real subject boundary, not a convenience split:**

| Half | Owner | Subject |
|---|---|---|
| **The LEDGER** — `epic.md` compaction, the GENERATED-block mechanism, `resume_anchor` shape, settled-narrative relocation with pointers, `inbox/archive` foldering, bidirectional invariant checks | **PLAN-TRUTH-022** (unchanged) | *the record of the work* |
| **The SPEC CORPUS** — re-grounding staged specs against HEAD, applicability, ambiguity, duplication, redistribution | **THIS PLAN** | *the work itself* |
| **The single entry point** that sequences both and ends in a restart-readiness verdict | **THIS PLAN** | *the operator's actual ask* |

⛔ **This plan does NOT re-implement -022's compaction stage.** It defines the phase and **calls what
-022 builds**. If -022 has not landed, the compaction phase reports `not_available` and the verb
completes without it — it never grows a second compaction implementation. See § Dependencies.

## OBSERVED — the ritual exists, is repeated, and is expensive

Every claim in this section is first-party, read from this epic's own persisted tree.

- **The `resume_anchor` in `status.json` currently contains FOUR hand-written blocks whose titles are
  literally `PRE-RESTART CHECK` or `RESTART-READY`** (dated 2026-08-08 twice, 2026-08-09 twice). Each
  one hand-enumerates: row/spec/table reconciliation counts, the running set, worktree cleanliness, HEAD
  sha, and a pin/marker survey. ⇒ **The verb already exists — it is being executed by hand, in prose,
  into a field that is not a report.**
- **The corpus-review pass has been run at least twice by hand and both times found real defects.** The
  `## Premise verification sweep — 2026-08-08, ALL 49 staged plans` section records: `-057` REFUTED and
  re-scoped (the defect was inconsistent writing plus silent under-recording, not absence — the original
  generalised from one plan), `-012` REFUTED (all 11 termination causes ARE documented), `-046` on the
  WRONG SURFACE (named `manage-status`; the fields live in `_invariants.py` and `manage-change-ledger.py`
  — **zero occurrences** in the named component), and `-015` understating its surface **by ~74%**
  (210 matches / 54 files, not 131/31).
- **The redistribution pass has been run once by hand and materially improved the queue.** The
  `## Condensation — 2026-08-08, 49 staged → 36` section records **13 plans absorbed into 12 receivers**,
  and — the part a count does not show — **three merges DELETED COORDINATION MACHINERY that existed only
  because two plans shared one surface**, and **two merges revealed a shared mechanism neither plan could
  state alone**.
- **The duplication check has a known blind spot with a shipped precedent.** `PLAN-PR-018` was retired as
  a duplicate of `PLAN-CIS-031`, caught only by a live `manage-status list` plus the running plan's
  `source_id`. ⛔ **A ledger cannot see a duplicate in another ledger** — so a corpus-local uniqueness
  check is *structurally incapable* of catching the cross-epic case.

⇒ **The capability is proven by use, and the cost of it being manual is proven by its own findings.**
This is not a speculative convenience verb.

## Deliverables

### D0 — GATE: boundary, verb name, and apply-policy (mutates nothing)

1. **Confirm the -022 boundary above against -022's landed or staged deliverable list.** If -022 has been
   split or re-scoped since this spec was written, re-derive the boundary before building anything.
   ⛔ Two implementations of ledger compaction is a worse outcome than no verb.
2. **Name.** The operator's word is `cleanup`. -022's D1 recommends `compact` for the ledger half because
   *cleanup implies deletion*. **Both can be true**: `cleanup` is the right name for the operator-facing
   orchestrator verb (it cleans the corpus AND the ledger), `compact` for -022's ledger stage it calls.
   Settle it; whichever wins, the SKILL router table, `orchestration-model.md`, and the workflow doc must
   agree — a verb named in one and not the others is this epic's doc-contract-divergence archetype.
3. **⛔ APPLY-POLICY — the single most consequential decision in this plan.** The operator said **"Apply
   all the changes"**, and that instruction is honoured, not softened. But *apply* means different things
   to different finding classes and the verb must not collapse them:

   | Finding class | Action | Why |
   |---|---|---|
   | Premise REFUTED at HEAD | **apply** — re-scope the spec in place | Mechanical and verifiable; leaving it is how a plan ships against a defect that no longer exists (`C9`: `-047` was staged on a premise its own inbox message had already disproved) |
   | Wrong surface / understated surface | **apply** — correct the Expected Surface | Verifiable by re-running the sweep |
   | Ambiguity (missing Objective / Expected Surface / unlabelled claim) | **apply** — add the missing structure, or mark the spec inadmissible | A spec with no Expected Surface is indistinguishable at the disjointness gate from "no candidate qualified" |
   | Duplication | **apply** — supersede one, ⛔ **never delete a spec file** | The retired spec is the audit record of why it was retired |
   | **Redistribution (merge / split / regroup)** | **apply, but every move enumerated in the report with source and destination** | This is the judgement-heaviest class and the only one that is hard to reverse |

   ⛔ **In every class the rule is the same: the change is applied AND named. A silent application is
   indistinguishable from a lossy one** — this epic's entire theme, and the reason `report` is a
   deliverable rather than a nicety.

### D1 — enumerate the corpus and re-ground every staged spec against HEAD

Enumerate from `status.json` `plans[]` (the machine authority), **not** from a `plans/` directory glob —
and then check both directions, because the bidirectional check is the one that bites: a row without a
spec file, and a spec file without a row, are different defects with different causes.

For each `staged` spec, verify its OBSERVED claims against the **implementing source** at current HEAD —
never against a standards doc, an ADR, or the spec's own prose, all of which restate the same inference.
Emit per spec: `corroborated` / `contradicted` / `unverifiable`.

⛔ **The denominator trap, and it nearly manufactured false refutations in the manual pass.** Several
specs state counts over a **scoped** population ("6 call sites") while a repo-wide sweep returns a much
larger number (257 refs / 54 files). **Those are different denominators, not refutations.** Where
populations cannot be matched the claim is recorded `unverifiable`, **never** `contradicted`.
⇒ **Every count this verb emits MUST carry its own population.**

### D2 — applicability: detect the already-fixed

A spec can be correct and still be dead work. Detect specs whose defect **no longer exists at HEAD** —
fixed incidentally by another plan, or by a landed sibling. ⭐ Precedent, first-party: the 2026-07-04
review retirement re-verified ~53 findings and found **8 already fixed**, one of them (`B4`) closed
incidentally by an unrelated `uv.lock` refresh in #1122 that nobody had connected to it.

⛔ **Absence is not the evidence a naive check assumes it is.** "The symbol is gone" is equally explained
by a fix, a rename, and a file move. Require a positive account of *what* closed it before marking a spec
`already_fixed`.

### D3 — ambiguity

Per spec, flag: no Objective; no `## Expected Surface`; claims not labelled `OBSERVED` / `HYPOTHESIS`; a
`HYPOTHESIS` with no named confirm/refute artifact (a file **plus the symbol within it**, not a directory
or a document title); a deliverable count disagreeing with the deliverables actually listed.

⭐ **This is population-derivable, so it must be population-derived** — publish the number of specs
scanned alongside every count. A check that can return `0` from an empty population must publish the
population size (standing rule; copy `test/_shared/_dispatch_roster.py`'s shape).

### D4 — duplication, in BOTH directions

1. **Within the corpus** — specs whose Expected Surfaces and objectives overlap.
2. ⛔ **ACROSS EPICS AND AGAINST LIVE PLANS — the direction a ledger structurally cannot see.** Check
   live `manage-status list` and each running plan's `source_id`, and check the sibling epics' queues.
   **This is not optional polish: it is the only arm that would have caught PLAN-PR-018.**

⇒ Report each candidate pair with the overlapping surface named. **Superseding is applied per D0.3;
deletion never is.**

### D5 — distribution: is the grouping optimal?

Propose and apply regrouping, **component-first, task-second** — component disjointness is what makes
parallel execution safe, and the split guard is **12 deliverables as a CEILING, not a target**.

⛔ **Two guards learned from the manual pass, both from its own recorded mistakes:**
- **A weak merge must be labelled weak in its own header** and licensed to split back at outline. The
  manual pass produced two (`-014+-021` tied only by component; `-030+-048` sharing a measurement
  substrate, not a cause).
- **Overlapping deliverables COLLAPSE rather than concatenate**, and every merged spec re-counts its
  deliverables at outline. A merge that concatenates two 7-deliverable plans into a 14-deliverable plan
  has made the queue worse while reporting a reduction.

### D6 — the `cleanup` verb: wiring and phase order

Add the verb to the router table, write `workflow/cleanup.md`, and add its **Canonical invocations**
block. Phase order, and it is load-bearing:

```text
D1 re-ground → D2 applicability → D3 ambiguity → D4 duplication → D5 distribution
   → [PLAN-TRUTH-022's ledger compaction stage]  → archive → persist → restart-readiness
```

**Corpus before ledger, always.** Compacting the ledger first would relocate settled narrative that the
corpus pass is about to contradict, and the pointer would then aim at a superseded claim.

⛔ **`archive` here means the EXISTING `orchestrator archive` verb's semantics — relocate, never
delete** — and it applies to *closed epics*, not to this epic's rows. Within a live epic, "archive what
is done" means: retire consumed inbox messages, and relocate settled narrative per -022. **Nothing is
deleted by this verb, ever.**

**Restart-readiness** ends the run and MUST assert, over the whole population and not a sample:
`executor MARSHALL_VERSION == registry installPath`, **naming the field** (`installPath` and `version`
disagree in 14 of 15 of our registry entries, and an oracle reading `version` false-alarms), plus the
**double-sample** rule (two reads seconds apart; a disagreeing pair is `indeterminate`, **never**
`fail`), plus the sample instant printed beside the verdict. ⚠ **The unmarked-dir set is a lagging
function of the registry, not an independent witness** — do not count it as corroboration.
⭐ This step is not new design: it is the fourth hand-written `PRE-RESTART CHECK` block, promoted to code.

### D8 — [FROM -034] make the generated block un-hand-writable, and validate it against the authority

The START-HERE contract says the block is *"GENERATED, never hand-written"*. **It is not enforced, and
it is violated in this epic today** — by design, with a recorded operator-owed decision: the anchor is
replaced by a pointer because pasting a multi-kilobyte anchor into `epic.md` would duplicate the machine
authority, and per-row annotations were moved out of the block into the Ordered Queue table.

⛔ **Do not "fix" this by pasting verbatim** — the annotations carry information the generator does not
produce, and a verbatim paste would destroy it. Settle it the way -022's D2 frames it: **either the
generator emits the annotations, or the contract permits an annotation zone OUTSIDE the markers.**
This plan owns the decision because it owns the verb that will regenerate the block.

Then add the check that bites: **compare every derived count in the rendered block against
`status.json` and fail on divergence.** The divergences seen were `79` vs `81` rows, `43` vs `46`
shipped, and an anchor narrating *"27 staged"* against the generator's own enumeration of **28** in the
**same emission** — narrated and derived copies disagreeing at zero distance.

### D9 — [FROM -034] self-contradiction detection within one rendering

A block that says `R = 2 of N = 2 — AT CAP` and `R = 0 of N = 5 … three genuinely free` twenty lines
apart is internally inconsistent, and **each half is individually plausible**. ⇒ Detect
mutually-exclusive claims inside a single rendering. ⭐ **This is the one detector that has to run on
the OUTPUT, not the inputs** — every input was fine; the rendering combined them wrongly.

### D7 — the report, idempotence, and tests

One TOON report: per-spec verdicts with populations, every applied change with source and destination,
every item **declined** and why, and the restart verdict. ⛔ **Anything the verb declined to touch is a
first-class report field** — a clean report that hides a skip is the failure mode this epic files
against everyone else.

**Idempotence:** a second run immediately after the first is a no-op. State the mechanism.
**Tests:** population-derived, with **matched positive and negative controls** — for each detector,
prove it fires on a seeded instance **and** stays silent on a legitimate near-miss (a scoped-denominator
count that must NOT be reported as a refutation is the obvious negative control, and it is the one the
manual pass nearly got wrong).

### ⚠ Deliverable count: 10 (D0–D9). Split guard evaluated at staging, split DECLINED — rationale recorded

Ten is under the 12 ceiling but close to it, so the guard is answered here rather than left to the plan
(a guard delegated to the party it constrains is not a guard — standing correction C1).

- **Declined because the grouping is component-first and the component is one**: every deliverable edits
  `marshall-orchestrator/**` or `persona-marshall-orchestrator/standards/orchestration-model.md`.
- ⛔ **D8/D9 must NOT be split back out.** They are the absorbed -034, and the whole reason for absorbing
  was that building the verb (D6/D7) over narrated state and re-typing afterwards does the work twice.
  Splitting them out re-creates the sequencing this merge deleted.
- ⭐ **Overlapping deliverables COLLAPSE rather than concatenate — re-count at outline.** D7's report and
  D8's block-validation both emit verdicts against `status.json`; if outline finds one mechanism serves
  both, that is a collapse to 9, not two implementations. **A merge that concatenates has made the queue
  worse while reporting a reduction.**
- **12 is a ceiling, not a target, and it does not license a wider blast radius** — which is precisely
  why -032 stayed a precondition rather than becoming D10–D12.

## Claim Labels

- **OBSERVED (this orchestrator, first-party, from the persisted tree)**: the four hand-written
  `PRE-RESTART CHECK` / `RESTART-READY` blocks in the live `resume_anchor`; the premise-sweep findings
  for `-057`, `-012`, `-046`, `-015` and their stated figures; the condensation section's 13→12 absorption
  and its three-merges/two-merges characterisations; the PLAN-PR-018 cross-ledger retirement; the ~53
  findings / 8-already-fixed re-verification; the registry `installPath` vs `version` 14-of-15 split.
- **OBSERVED**: that PLAN-TRUTH-022 exists, is staged, and its D1–D5 cover the ledger half — read from
  the spec file at `plans/PLAN-TRUTH-022-*.md`.
- **HYPOTHESIS**: that -022's deliverable set is still 19 and still un-split at the time this plan runs.
  Confirm/refute against `plans/PLAN-TRUTH-022-*.md`, section `## Deliverables` — **verify-at-outline**,
  because D0.1's boundary depends on it.
- **HYPOTHESIS**: that no orchestrator verb today performs any part of this. Confirm/refute against
  `marshall-orchestrator/SKILL.md`, the `## Verb Routing` table — **verify-at-outline**. The asserted
  *absence* is the higher-risk half: an unverified absence builds a second implementation of something
  that already exists.
- **HYPOTHESIS**: that the D1 re-grounding sub-step is dispatchable to an `execution-context-{level}`
  leaf under the Dispatch Decision Rule (depth: yes, per-spec source reading; fork-freedom: yes;
  write-freedom: yes, the leaf returns verdicts and the orchestrator records them). Confirm/refute
  against `persona-marshall-orchestrator/standards/orchestration-model.md` § Dispatch Decision Rule —
  **verify-at-outline**. ⭐ If it holds, D1 is the verb's parallelism and the whole run's cost profile
  changes; if it does not, D1 is inline and the verb is materially slower.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/SKILL.md` — the
  `## Verb Routing` table and the `## Canonical invocations` block
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/cleanup.md` (new)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/orchestrator.py`
  — the deterministic seams (corpus enumeration, bidirectional row↔spec check, marker/pin survey)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/persona-marshall-orchestrator/standards/orchestration-model.md`
  — the verb list and, if D0.2 changes it, the vocabulary
- **OBSERVED**: `test/plan-marshall/marshall-orchestrator/` — the population-derived detector tests
- **OBSERVED [from -034]**: `marshall-orchestrator/templates/epic.md` — the GENERATED-marker convention
- **HYPOTHESIS [from -034]**: `marshall-orchestrator/workflow/resume.md` and `workflow/orchestrate.md` —
  the sites that invoke regeneration (verify-at-outline)
- ⛔ **NOT** `epic.md` compaction internals — that is PLAN-TRUTH-022's surface.

## Dependencies and Sequencing

- ⛔⛔ **PLAN-TRUTH-022 shares the `marshall-orchestrator` component.** -022 is **staged**, not running,
  so there is no live collision today — but **these two MUST NOT run concurrently**, and if -022 is
  emitted first this plan re-grounds against it before starting. **Evaluate at D0.1 whether the two
  should merge**; the recommendation is **no** (the subjects are genuinely different and -022 is already
  over the deliverable ceiling), but the evaluation must be recorded either way.
- ⚠ **Currently DISJOINT from all three running plans** — `-055` (`manage-metrics`, `manage-status`,
  `phase-6-finalize/standards`, `plan-retrospective`), `-070` (providers / file-ops / findings / ci /
  architecture / opencode emitter), `-013` (`platform-runtime`) — and from both cross-epic worktrees
  (`executor-rejects-invalid-invocations-before-spawn`, `generic-charter-language-specific-defect`).
  ⛔ **Re-verify at emit from the live file lists, not from this line and not from plan titles** — a
  disjointness read off a title is the recorded `-069`/`-049` error.
- ⚠ **This plan will re-ground the whole corpus, including specs that other plans are executing
  against.** It must **skip any spec whose row is `running`** — re-scoping a spec mid-execution changes
  the brief under a running plan.

- ⛔⛔ **PLAN-TRUTH-032 IS A HARD PRECONDITION OF THE ARCHIVE PHASE, NOT A NICE-TO-HAVE.** Without an
  emission-quiescence signal the verb cannot know a plan's finalize has stopped emitting, and the
  standing rule — *never drain candidate-lessons from a plan whose finalize is still running* — becomes
  unenforceable in code. **If -032 has not landed when this plan reaches D6, the archive phase MUST
  refuse to drain and say so**, rather than draining on a timer or on a merge landing (a merge landing is
  NOT evidence the finalize is done — #1115 kept writing past its own landing message).
- ⛔⛔ **SERIALIZE ABSOLUTELY AGAINST PLAN-TRUTH-015** (the `marshall-orchestrator` → `plan-orchestrator`
  rename: 210 references / 54 files / 3 directory renames). These two cannot be concurrent under any
  pairing. **Recommend -074 first** — renaming settled code is cheaper than renaming under an open
  feature branch — but either order is acceptable if recorded; only concurrency is not.
- ⚠ **-038** (inbox amend/supersede) is adjacent on `orchestrator.py`'s `inbox` verb group but not
  required here; if both are ever in flight, they collide on that file.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-074-spec-corpus-review-and-cleanup-entry-point.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — ⛔ **note
the asymmetry deliberately: this plan BUILDS a verb that writes the ledger, but the plan itself must not
write the ledger.** Exercise the verb against a fixture epic, never against `truthful-signals`.
Qualifiers are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.


---

## ⭐⭐ WORKED EXAMPLE FOR D1, PRODUCED BY THE 2026-08-09 DRAIN — enumerate from the AUTHORITY, never from a derived index

Hours after this spec was staged, the inbox drain reproduced the exact defect D1 is written to prevent.

The drain built its clustering work list with a `^# ` title sweep across the 34 message files. **One
message — `daemon-…-016` — carries its title in a `title=` envelope header and has no `# ` line.** It
did not appear in the sweep, was not clustered, and was not dispositioned. It surfaced only because the
post-archive `inbox list` returned **`count: 1` against an expected `0`**.

⇒ **The convenience index silently had 33 of 34 members, and nothing in the index said so.** Had the
drain trusted its own list, the message would have been left in the queue with no disposition and no
defect recorded — indistinguishable from a message that had simply not arrived yet. (Its content was
substantive: it became `PLAN-TRUTH-076`.)

**Three requirements this puts on D1, all now first-party:**

1. ⛔ **Enumerate from `status.json` / `inbox list`** — the authority — **never from a grep, a glob, or
   any derived index.** A derived index has a coverage property nobody stated and nobody checked.
2. ⛔ **Reconcile counts at the end and fail loudly on a mismatch.** `scanned == dispositioned +
   invalid + archive_failed` is what caught this; it is cheap and it is the only thing that did.
3. ⚠ **A per-item index built by pattern-matching file CONTENT inherits every formatting assumption of
   the files.** Here the assumption was *"every message starts with a markdown H1"* — never stated,
   never true.

⭐ **Kept because it is embarrassing in the useful direction**: the pass that was filing instances of
*a check green because it examined an incomplete population* committed one, and was caught by
arithmetic rather than by judgement. **That is the argument for the verb over the ritual.**
