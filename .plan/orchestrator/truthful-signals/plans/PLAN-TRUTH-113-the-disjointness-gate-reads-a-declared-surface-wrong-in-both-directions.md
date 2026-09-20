# PLAN-TRUTH-113: The disjointness gate reads a declared surface that is wrong in both directions

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-25 from the PLAN-TRUTH-094 drain (PR #1343, `1169fb5bf`), finding `c6ad9f`, on
**operator decision (`AskUserQuestion`, 2026-08-25): stage ONE plan covering BOTH footprint
directions**, because fixing either alone leaves epic disjointness unreliable. Folding into
`PLAN-TRUTH-098` was offered and declined.

⚠⚠ **A CORRECTION THE OPERATOR IS OWED, RECORDED HERE SO IT IS NOT LOST.** The escalation described
`-098` as *"carries no declared surface of its own"* — true of its queue row, **and incomplete about
its scope**: `-098` **Arm 2 already owns `references.affected_files` reconciliation**, one of the two
directions this plan was staged to cover. The decision **survives the correction** for a reason that
must stay explicit in this spec, because it is the only thing keeping the two plans apart:

| | `PLAN-TRUTH-098` | **This plan** |
|---|---|---|
| Consumer | A plan's **own graders** (retrospective, artifact-consistency, routing checks) | The **orchestrator's disjointness gate** — which plans may run concurrently |
| Artifact | `references.affected_files` + the squash-blind footprint resolver | The spec's `## Expected Surface` section |
| Tier | Plan lifecycle | Epic orchestration |

⛔ **`references.affected_files` belongs to `-098` and MUST NOT be re-scoped here.** This plan touches
it only as an INPUT it may not trust. If outline finds the two cannot be separated on that line, that
is a genuine finding — report it and re-scope, do not silently absorb `-098`'s arm.

## Objective

Epic disjointness — the rule deciding which plans may run concurrently — reads each spec's declared
`## Expected Surface`. That declaration is currently wrong in both directions at once, so the gate
neither prevents real collisions nor permits safe parallelism. Make the declared surface a measured
quantity with a known error, or replace it as the gate's input with something that is.

## Problem

**Measured first-party at `1169fb5bf` during the PLAN-TRUTH-094 drain.** `-094` declared a six-file
Expected Surface. Against the merged squash:

| Direction | Measured |
|---|---|
| Declared, never touched | **3 of 6** — `resolve_project_dir.py`, `doctor-marketplace.py`, `test_analyze_argument_naming.py` |
| Landed with >4 changed lines, never declared | **~70 of 76** |
| Landed at ≤4 changed lines (version-stamp sweep) | 40 |

⛔ **Both errors at once is the part that matters.** Over-declaration serializes sibling plans behind
files the plan never used — pure lost throughput. Under-declaration admits plans that genuinely
collide — the failure the gate exists to prevent. A gate wrong in one direction is conservative or
permissive; **wrong in both is uninformative**, and the current one is wrong in both by roughly an
order of magnitude on the under-declared side.

⚠ **The mirror is already known and already owned.** `references.affected_files` under-records
(`-098` Arm 2; recall measured at 13/16 on PLAN-TRUTH-074). So the declared side and the realized side
are each independently unreliable, and **no currently-recorded quantity is a trustworthy disjointness
input.** That is the state this plan must end.

## Deliverables

Five deliverables. D0 is a measurement gate and must complete before any remedy is designed.

**D0 — GATE: measure the declared-vs-realized error across the corpus, not on one plan.** For every
shipped plan with both a spec and a landing, compute declared-not-realized and realized-not-declared,
and **publish both directions with the population size** — never a single symmetric-difference number,
which cannot distinguish the two failure modes. ⛔ **One plan's 3-of-6 is an anecdote**; the remedy
depends on whether over-declaration or under-declaration dominates, and that is currently unknown.
⚠ Exclude the version-stamp sweep class (≤4-line mechanical edits) from the realized side, or it will
swamp every measurement — and **state that exclusion in the output**, since a filtered population that
does not name its filter is this epic's own archetype.

**D1 — the declared surface states its own confidence, and an ABSENT one stops reading as disjoint.**
A spec's `## Expected Surface` currently reads as a bare assertion. Give it a derivation status, so the
gate can tell a swept declaration from a guessed one, and so a spec with **no** expected surface is
distinguishable from one that declared an **empty** set. The queue renderer emits
`(no expected surface)` for **3 of the 23 staged specs** — `PLAN-TRUTH-098`, `PLAN-TRUTH-105`,
`PLAN-TRUTH-111`.

⛔ **SUPERSEDED IN PART — read § RE-SCOPE below before acting on that figure.** Those three are NOT
surfaceless: the `epic-surface-partition` classifier resolves paths for all three (`-098` resolves
**6**). The renderer and the classifier **disagree**, and the renderer is the one wired to the gate.
The number above is retained because it is what the GATE currently sees, which is the defect — it is
not a property of the specs.

⛔⛔ **This is not a cosmetic gap, and it was demonstrated first-party while this spec was being
staged** — see § Dependencies. A surfaceless spec is **invisible to `corpus cross-check`'s
`file_overlap_matches[]`**, so the machine reports no collision against it and the gate reads that
silence as disjoint. **A plan the gate cannot see is a plan the gate cannot serialize.** An absent
declaration must resolve to `indeterminate`, never to `disjoint`.

**D2 — the gate reports which input it used and how much of it it trusted.** Whatever D0 shows, the
disjointness verdict must publish the surfaces compared and the population they came from, so a
`disjoint` verdict is legible rather than vacuous. ⛔ An overlap check over an unreliable or absent
declaration must return `indeterminate`, **never `disjoint`** — the epic's canonical rule, applied to
the orchestrator's own gate.

**D3 — reconcile the declaration after scope moves, including scope the ORCHESTRATOR adds.** A spec's
Expected Surface is written at staging and never revisited, so scope added later cannot reach it.
⚠ **This is the same shape as `-098` Arm 2 but on the other artifact** — coordinate the remedy, do not
duplicate it, and if the two converge on one mechanism, say so rather than building two.

⛔ **There are TWO writers of post-staging scope, not one, and the second is invisible today.** The
known one is the plan itself during execute. The second is **the `analyze` drain folding a finding into
an already-staged spec**: the fold appends narrative naming new files and **never touches
`## Expected Surface`**, so the spec's real footprint grows while its declaration does not.

⭐ **Observed first-party in the drain that staged this plan (2026-08-25).** `ec6c97` was folded into
`PLAN-TRUTH-104`, bringing plugin-doctor provenance files into its real scope; `-104`'s declared
surface still lists only `review_commitments.py` and `finalize-step-simplify.md`. `corpus cross-check`
consequently reports **no overlap** between `-104` and `PLAN-TRUTH-112`, whose whole surface is
plugin-doctor. ⚠ Three folds landed in that one drain (`-101`, `-104`, `-111`), so this is the
**steady-state behaviour of a maturing corpus**, not a one-off: every drain widens real surfaces and
none widens declared ones, so the gate's error grows monotonically with epic age.

**D4 — state what the gate can and cannot promise.** Document the residual error D0 measured, so a
future reader knows the gate's precision instead of inferring soundness from its existence.

## Expected Surface

⚠ **Declared with deliberate irony and re-derived at outline** — this plan's own declaration is subject
to the defect it fixes, and D0 must include this spec in its own population.

- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/orchestrate.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md`
- `test/plan-marshall/plan-orchestrator/test_orchestrator_corpus.py`

## Out of scope

- **`references.affected_files` and the squash-blind footprint resolver** — `PLAN-TRUTH-098`'s, both
  arms. Consumed here as an untrusted input only.
- Changing `parallelization_scope` or the `N − R` slot arithmetic; this is about the eligibility
  input, not the concurrency cap.
- The prep-ready admission test — a separate gate, and separately vacuous (R97/R102).

## Claim Labels

- OBSERVED: `-094` declared 6 files and left 3 untouched — confirm/refute at `plans/PLAN-TRUTH-094-plugin-doctor-detector-coverage-residue.md` § `Expected Surface`, against `git show --name-only 1169fb5bf`.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Measured at the -094 drain: git show --name-only 1169fb5bf contains none of resolve_project_dir.py, doctor-marketplace.py, test_analyze_argument_naming.py; 3 of 6 declared paths absent
- OBSERVED: 76 files with >4 changed lines landed in #1343 against that 6-file declaration — confirm/refute at commit `1169fb5bf` § `--numstat`.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Measured at the -094 drain: git show --numstat 1169fb5bf yields 76 files with >4 changed lines and 40 at <=4 (version-stamp sweep), against a 6-path declaration
- OBSERVED: 4 of 21 staged specs render `(no expected surface)` — confirm/refute at `epic.md` § the `ordered-queue` generated block.
  - verdict: contradicted | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: yes | evidence: Wrong on BOTH numbers and on the underlying fact. The renderer emits (no expected surface) for 3 of 23 staged specs, not 4 of 21. And those three are NOT surfaceless: epic-surface-partition classify resolves paths for all three (-098 resolves 6). The renderer and the classifier disagree; the renderer is the one wired to the gate. Spec re-scoped in place at D1 and in the RE-SCOPE section
- OBSERVED: `references.affected_files` recall was 13/16 on PLAN-TRUTH-074 — confirm/refute at `plans/PLAN-TRUTH-098-plan-footprint-is-unknowable-to-its-own-graders.md` § Problem, Arm 2.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: The 13/16 recall figure is cited from PLAN-TRUTH-098's own Problem section, which is a spec document and not the implementing source. Per the verify-first contract a doc-to-doc check does not settle a claim, and PLAN-TRUTH-074's artifacts are archived, so the population could not be reached at this sha
- HYPOTHESIS: over-declaration and under-declaration co-occur corpus-wide rather than only on `-094` — confirm/refute at the D0 sweep output § the two published directions (verify-at-outline).
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Was HYPOTHESIS; now corroborated over three consecutive landings, all wrong in BOTH directions: -094 (3 of 6 declared unused), -087 (~26 substantive files undeclared), -086 (7 declared unused / 33 undeclared, recall 29/36). Co-occurrence is corpus-wide, not specific to -094
- HYPOTHESIS: the declared-side and realized-side remedies converge on one reconciliation mechanism — confirm/refute at `orchestrator.py` § the surface-comparison site, read against `-098` Arm 2's remedy (verify-at-outline).
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Whether the declared-side and realized-side remedies converge on one mechanism is settled by designing both, not by reading orchestrator.py today. NOTE the -086 drain sharpened the question: inbox -006 reports THREE finalize steps deriving three different footprints in one run, so the convergence question is now three-way rather than two-way
- OBSERVED: both measurement tables, the F1-trigger miss, the twice-fired plugin-doctor divergence, and the unwritten `realized_footprint` — each quoted from a lesson recording a live run at a named HEAD
- HYPOTHESIS: `2026-08-25-05-001`'s *"never rewritten after outline"* mechanism. ⛔ **Title-only stub — `add` allocated it, `set-body` never ran, no body exists.** The claim rests on its title alone. Confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage_references.py` § the `affected_files` write path, checking whether any post-outline caller rewrites it (verify-at-outline)
- HYPOTHESIS: `compute-footprint` is the correct substitute at every consuming site — ⛔ `26-06-002` establishes it for the plugin-doctor scope gate ONLY. Confirm per site.
- ⚠ **Sequencing:** `PLAN-TRUTH-098` (`plan-footprint-is-unknowable-to-its-own-graders`) is RUNNING and owns the footprint-derivation surface. ⛔ **This fold must NOT be scoped as a footprint fix** — it is the *disjointness-gate* consumer of one. Re-read `-098`'s landing before scoping, and re-run `corpus cross-check` at emit.

## Dependencies and Sequencing

**GENERATED by `corpus cross-check` at staging (2026-08-25), then read for collision-vs-duplicate.**
Population: 8 sibling epics, 2 live plans, 161 specs, 171 candidates.

**Live sequencing constraints — both must be honoured:**

- **`PLAN-TRUTH-099`** (`the-ledger-has-no-safe-single-row-append`) — 2-file overlap
  (`orchestration-model.md`, `orchestrator.py`). ⇒ **not concurrently emittable with this plan.**
- **`PLAN-TRUTH-100`** (`the-inbox-has-no-delivery-path-to-a-running-plan`) — same 2-file overlap.
  ⇒ **not concurrently emittable with this plan.**

**Terminal overlaps — historical, no constraint:** `-080` (shipped, #1215), `-085` (shipped, #1317),
`-096` (shipped, #1338). Each shares `orchestrator.py`; all three are shipped rows, so they constrain
nothing. Recorded so a future pass does not re-derive them as live.

### ⛔⛔ THE MACHINE MISSED THE MOST IMPORTANT ONE, AND THE REASON IS THIS SPEC'S SUBJECT

- **`PLAN-TRUTH-098` — SERIALIZE, `-098` FIRST.** It owns the realized-footprint arm this plan must
  treat as an untrusted input; running them concurrently risks two mechanisms for one reconciliation.

⛔ **`corpus cross-check` did NOT report this pair.** `-098` declares **no Expected Surface**, so it
contributes nothing to `file_overlap_matches[]` and the machine returned silence — which at the
disjointness gate is indistinguishable from *disjoint*. It was caught only by a human reading the two
subjects.

⭐⭐ **This is the defect this plan exists to fix, reproduced BY THE ACT OF STAGING THIS PLAN.** Keep it
here as the worked example: the generated map found 5 candidates, of which **2 were live constraints
and 3 were terminal noise**, and it **missed the single relationship that actually governs sequencing**.
⚠ **The standing rule that generation beats hand-reading (R48) still holds and is not weakened by
this** — the machine found `-080`/`-085`/`-096`, which a hand-read had missed. The correct reading is
narrower and both halves are load-bearing: **generate the map, then read the subjects, because the
generator is blind exactly where the declaration is absent.** Neither method alone was sufficient here.

## ⭐⭐ FOLDED 2026-08-27 — the gate's boolean is vacuous when THIS epic's own side is empty

From the `lessons-handling-26-08-26-01` cleanup pass, delivered by operator paste and
**re-corroborated first-party at `91a07aaa4`** (both the reproduction and the symbol).

`corpus cross-check --slug lessons-handling-26-08-26-01` returns:

```text
epics_scanned: 9   plans_scanned: 4   candidates_scanned: 337
specs_total: 0     specs_scanned: 0   collision_detected: false
```

⛔ **`collision_detected` never consults `specs_scanned`.** The symbol is one line —
`orchestrator.py`:1983, `'collision_detected': bool(origin_matches or overlap_matches)` — so an epic
that stages NO specs (a *router* epic, whose queue rows are routing decisions delivered as inbox
messages) can form no pair at all, and the boolean reports `false` over an **unexamined** population.
The three candidate populations are large and correctly named, which is what makes the zero read as a
checked negative.

⭐ **This is THIS PLAN'S D1 one level up**, and it is the reason the fold belongs here rather than in
`-104` (which is scoped to `review_commitments reconcile`): D1 already says *silence from the generator
reads as `disjoint` and must read as `indeterminate`*. D1 addresses silence caused by an **unresolvable
surface**; this addresses silence caused by an **empty own-side corpus**. One remedy shape covers both —
consult the population, and publish which kind of zero it is.

⭐⭐ **THE BLINDNESS IS DEMONSTRATED, NOT THEORETICAL, AND THE DEMONSTRATION SURVIVED CORRECTION.** Two
cluster slugs are byte-identical across two drains 18 days apart — `doc-contract-divergence`
(`PLAN-LH-19` → `PLAN-LH2-06`) and `review-bot-participation-and-reliability` (`PLAN-LH-05` →
`PLAN-LH2-10`) — and `cross-check` reported no collision over exactly that pair. ⚠ The reporter's
framing that *both* were routed here is **half wrong** (see § Dependencies); the blind spot is
unaffected, because the verb could not have seen either pair.

**Directive:** when `specs_scanned == 0`, `collision_detected` MUST NOT be `false` — report
`indeterminate`, or name the emptiness the way `inbox list`'s `inbox_state` names which kind of zero a
`count: 0` is. ⛔ Do not fix it by defaulting the boolean to `true`; that trades a false negative for a
false positive and this epic has recorded a fix re-introducing the archetype it was closing at least
twice.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-113-the-disjointness-gate-reads-a-declared-surface-wrong-in-both-directions.md"
```

## ⭐⭐⭐ RE-SCOPE — the parser this plan needed ALREADY SHIPPED, and two live readers now disagree (2026-08-25)

From the unanalyzed-landing sweep of **#1345** (`00b92fca3`) and **#1346** (`2b967e2e4`). Read this
section before outline: it changes what D0–D2 should build.

### 1. `tools-epic-surface-partition` (#1345) is D0's instrument, already built

A new `pm-plugin-development:tools-epic-surface-partition` skill parses every staged spec's
`## Expected Surface` and assigns a **three-class model** (`declarative` / `derived` / `prose`) plus
per-spec `claimed_count` / `excluded_count` / `unresolved_count`. It already honours this plan's
core rules: it keeps `unclaimed` and `not_derivable` as **verdicts that are never merged**, and it
**halts naming the spec** rather than defaulting a class it cannot determine.

⇒ **D0 must CONSUME this, not re-derive it.** Measured over `truthful-signals` at `a2be2691c`:

| Population | Result |
|---|---|
| whole corpus (161 specs) | `declarative` **118** · `prose` **43** · `derived` 0 |
| the 23 STAGED specs | `declarative` **23** · `prose` **0** |
| staged specs carrying UNRESOLVED entries | **5** — `-086` (7 unresolved of 39), `-090`, `-091`, `-092`, `-097` (1 each) |

⚠ **This CORRECTS an earlier claim in this spec.** D1 previously said *"3 of 23 staged specs are
surfaceless (`-098`, `-105`, `-111`)"*, taken from the `ordered-queue` block's
`(no expected surface)` column. **The classifier resolves paths for all three.** The live queue's
disjointness input is in better shape than that column implies — the 43 `prose` specs are all
terminal rows, not staged ones.

### 2. ⛔⛔ THE ACTUAL DEFECT IS SHARPER: TWO PARSERS, ONE SECTION, CONTRADICTORY ANSWERS

`PLAN-TRUTH-098`, read at the same HEAD by two readers in the same repository:

| Reader | Verdict on `-098`'s `## Expected Surface` | Consumed by |
|---|---|---|
| `orchestrator.py`'s queue renderer | **`(no expected surface)`** | ⛔ **the disjointness gate** |
| `epic-surface-partition classify` | **`declarative`, 6 resolved paths** | the partition/attribution report |

⇒ **The wrong reader is wired to the gate.** This is no longer "the declaration has no
machine-readable form" in the abstract — it is **two live readers disagreeing, with the losing one
governing concurrency.** It also explains, mechanically, the blind spot recorded above in
§ Dependencies: `corpus cross-check` missed the `-098` collision because it reads the renderer's
empty answer, not the classifier's six paths.

⭐ **Consequence for D2:** the remedy is smaller and more certain than when this plan was staged —
**re-point the gate at the shipped classifier** and delete the second parser, rather than design a
new declaration format. **Do not build a third reader.**

### 3. `plan_id` derivation does not recognise the `PLAN-{CODE}-{NNN}` form — a THIRD detector, and wrong

`classify`'s `plan_id` column returns the **whole filename** for every code-slug spec:

```text
plan_id = PLAN-TRUTH-113-the-disjointness-gate-...md      (expected: PLAN-TRUTH-113)
plan_id = PLAN-100                                        (older numeric form: correct)
```

⛔ Every `PLAN-{CODE}-{NNN}` spec becomes its own singleton key, so `attribution` and
multiply-claimed detection **cannot group by plan** for a code-slug epic — and `truthful-signals`
is entirely code-slug named, so the whole feature is inert here.

⭐ **The canonical grammar already exists and is documented**: `orchestrator inbox detect` accepts
exactly three forms (`PLAN-{DIGITS}`, `PLAN-{SLUG}-{DIGITS}`, `{SLUG}-{DIGITS}`) and is declared
*"the single detection seam — consumers never add a second detector"*. #1345 added one anyway and
got it wrong. ⇒ Route `plan_id` through the existing seam. ⚠ **Cross-bundle**: the defect is in
`pm-plugin-development`, the seam in `plan-marshall` — confirm ownership at outline before editing.

### 4. ADR-019 (#1346) is now the governing authority for D2 — cite it, do not re-derive it

*"An audit separates what it could not evaluate from what it evaluated and found wanting."* Status
**Proposed**; its `affects:` list already names `plan-orchestrator` **and**
`tools-epic-surface-partition`. Its rule is D2 verbatim: a surface that cannot establish its own
coverage reports a **distinct third state**, never the clean one, and *"the discriminator is whether
the predicate could be APPLIED, never whether it matched."*

⇒ D2 cites ADR-019 as authority. ⛔ **And `(no expected surface)` rendering as a silent pass at the
disjointness gate is a live ADR-019 violation inside the orchestrator's own machinery** — the ADR
names this component, so the gate is in its declared scope, not adjacent to it.

## ⭐⭐ FOLDED 2026-08-27 — two MORE both-directions measurements, and the mechanism behind them

From the `lessons-handling-26-08-26-01` drain, message `-005` (5 lessons, *"`affected_files` is a
plan-time projection, not an observed footprint"*).

⭐⭐ **This plan's D0 population goes from three landings to FIVE independent measurements**, and the two
new ones are *measurements* rather than landing narratives:

| Lesson | Plan | Recorded | Live | Live-only | Recorded-only |
|---|---|---:|---:|---:|---:|
| `2026-08-23-19-001` | `orchestrator-inbox-and-landing-residue` | 13 | 15 | 5 | 3 |
| `2026-08-26-06-002` | `config-seeding-effort-presets-steward-upgrade` | 52 | 54 | 6 | 4 |

⛔⛔ **NOTE HOW NEARLY THE TWO ERRORS CANCEL IN EACH ROW (13-vs-15, 52-vs-54): a check that compares SET
SIZES passes both wrongly.** That is the sharpest addition to this plan's D0 — the divergence is not
detectable by count, only by set difference, and a one-way *"recorded ⊆ live"* check **would have passed
on `26-06-002` and still missed the trigger.**

⭐⭐ **THE CONSEQUENCE WAS CAUGHT LIVE, and it is a scope gate missing its OWN trigger.**
`project:finalize-step-plugin-doctor` decides scoped-vs-whole-tree on an F1 trigger: does the changed
set touch `plugin-doctor/**`? **Read against `affected_files`, F1 does NOT fire** — `rule-catalog.md`
is one of the six live-only files — so the step would have run scoped over 12 skill dirs and **reported
a clean gate past a rule change**. Read against the live git footprint, F1 fires and whole-tree is
selected, which is what actually ran. ⇒ **Every `affected_files`-derived finalize step inherits this**;
the scope gate is merely the instance whose trigger happened to sit in the live-only set.

**Three further members:**

- `2026-08-25-05-001` — `affected_files` is **never REWRITTEN after outline**, so scope widened at 4-plan or at finalize entry never lands. ⭐ **The read is faithful, and re-reading a stale value cannot detect staleness** — which is exactly why every consumer-side *"did the read work?"* check passes. (⛔ Title-only stub; see Claim Labels.)
- `2026-08-25-09-012` — the escalation rule (*"whole-tree when the scope read is indeterminate"*) has **no mechanical indeterminacy test**. `finalize-step-plugin-doctor` fired **twice against the same `affected_files` value and the same footprint and reached OPPOSITE coverage decisions** — one leaf cross-checked against git, the other did not.
- `2026-08-25-09-004` — `branch-cleanup`'s merge-queue path leaves `realized_footprint` unwritten and records `merge_commit_sha` only on the synchronous path, so **all four resolver tiers miss** and every post-merge footprint read is unresolvable. Recorded twice; the second occurrence (PR #1349) adds that `branch-cleanup` reports `outcome: done` while writing **neither** key.

**The convergent directive:**

- **Derive finalize-time scope from the live git footprint**, not `references.json`. `manage-references compute-footprint --worktree-path …` already returns the git-derived set.
- A step that must use the recorded set MUST **reconcile and report the divergence**, never assume containment.
- **Publish `live_only` / `recorded_only` counts** so a silent scope narrowing becomes a legible one.
- **Matched pair required:** a file changed on the branch but absent from the record must be detected, AND a file present in the record but unchanged must be detected. **The two directions fail differently.**

## Claim Labels — folded 2026-08-27

> ↪ The bullets filed here on 2026-08-27 were merged into `## Claim Labels` above.
> `_parse_claims` reads ONE `## Claim Labels` section, so claims under a decorated
> second heading were structurally unstampable — the R97/R102 class, self-inflicted.

## ⭐ FOLDED 2026-08-27 (landing #1359) — the resolver should NAME the tier that answered

From the `PLAN-TRUTH-098` landing drain (message `-003`), and this fold is unusually well-evidenced
because `-098`'s own landing demonstrated the need.

**Directive: return the answering tier from `resolve_footprint`, so a grader can name its evidence.**

⭐⭐ **`-098`'s landing is the proof.** Its retrospective resolved a post-merge footprint — and the tier
that answered was **tier 2 (`realized_capture`), NOT the tier `-098` shipped** (tier 4, `pr_landing`).
`branch-cleanup` wrote the capture before removing the worktree, so the fall-through never reached tier
4. **Establishing that required reading `references.merge_commit_sha` by hand**; the resolver's own
return says nothing about which tier produced the answer.

⇒ **Directly serves this plan's D2** (*"the gate reports which input it used and how much of it it
trusted"*). A footprint with no provenance is exactly the unlabelled input D2 refuses to let the
disjointness verdict rest on. ⚠ **`-098` has SHIPPED**, so this is a successor to it, not a re-scope of
it — the resolver is now merged main and this is an addition to its return shape.

⚠ **Also unmechanised:** tier 3 independently reproduced tier 2 exactly (same 33 paths, symmetric
difference 0) — **done by hand by the retrospective agent; no aspect or script performs that
cross-check.** Mechanisable, not mechanised, and it is the cheapest available corroboration of a
footprint.
