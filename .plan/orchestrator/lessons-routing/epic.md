# Epic: Lessons Routing — a finding has an audience, and the store has no concept of one

slug: lessons-routing

> Ledger document for one epic under `.plan/local/orchestrator/lessons-routing/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

**Every finding plan-marshall produces lands in exactly one place — a git-ignored directory on the
machine that produced it — regardless of who can act on it.** In this repository that is tolerable: the
producer, the store, and the fixer are the same party. In a **consumer** repository it is not. A client
running plan-marshall accumulates findings about their own code (which they can fix) and findings about
plan-marshall itself (which they cannot) in one undifferentiated pile, invisible to their teammates and
invisible to plan-marshall's maintainers.

This epic gives a finding a **destination determined by who can act on it**: local findings stay
actionable for the client's team, upstream findings reach plan-marshall as issues, and neither depends
on one developer's untracked working directory to survive. **Done** looks like: no finding is stranded
by its own classification, no finding is lost by refusal, and no finding is visible to only one person.

⛔ It is more than one plan because it spans four independent surfaces — the classification predicate,
a new cross-repo transport, the durability substrate, and the already-stranded corpus — and because
the first of those must be re-derived before any of the others can be designed against it.

## Grounding — every claim below verified first-party at HEAD `77c9dc70a`, 2026-08-24

**1. The store is machine-local and cannot be shared.** `.gitignore:45` is `.plan/*` with exceptions
only for `marshal.json` and `project-architecture/`. `git ls-files .plan` returns **15 tracked files**,
none under `local/`. ⇒ `.plan/local/lessons-learned/` is untracked by construction, so a lesson exists
only on the machine that wrote it. **This is aspect 4's root cause and it is not a policy choice to be
argued with — it is the current design.**

**2. Consumer repos are already carrying stranded upstream findings.** Sampled two live consumer
checkouts:

| Repo | Lessons | Components |
|---|:--:|---|
| `cui-jsf-test-basic` | 4 | `cui-jsf-test-basic` · **`plan-marshall:recipe-refactor-to-profile-standards`** · **`plan-marshall:build-maven`** · **`plan-marshall:workflow-integration-sonar`** |
| `API-Sheriff` | 2 | `api-sheriff:maven-build` · `api-sheriff:ci-workflows` |

⛔⛔ **Three of the four lessons in `cui-jsf-test-basic` are about plan-marshall and that client can do
nothing with any of them.** They are not a hypothetical — they are on disk, in a git-ignored directory,
on one developer's machine, and plan-marshall's maintainers have never seen them. **This epic's first
deliverable is arguably to go and read them.**

**3. ⭐⭐ A discriminator EXISTS — and it discriminates the WRONG AXIS.** `manage-lessons add` carries a
cross-repo guard: a `--component` bearing a bundle prefix refuses with `error: wrong_store` when the
resolved main-anchored store repo *"does not own that bundle"*, and the ownership predicate is
**whether `marketplace/bundles/{prefix}` exists in that repo**. `--allow-foreign-store` bypasses it; a
prefix-less component (e.g. `integration-tests`) is treated as project-local and files freely.

⛔ **That predicate is plan-marshall-shaped.** Verified: `API-Sheriff` has **no `marketplace/bundles/`
directory at all**, so `api-sheriff:maven-build` — *the client's lesson about the client's own build* —
fails the ownership test exactly as `plan-marshall:build-maven` does. **In a consumer repo every
prefixed component is "foreign", including the client's own.** The guard answers *"is this bundle
mine?"* — a question only a marketplace repo can answer — where the question that matters is **"can the
reader of this store act on this?"**

**4. ⇒ The real defect is not that findings are mixed. It is that the upstream class has NO
DESTINATION.** The guard correctly notices that a `plan-marshall:*` lesson does not belong in a client
store, and then offers exactly two outcomes: **refuse** (the finding is lost) or **`--allow-foreign-store`**
(the finding is stranded in a store whose readers cannot act on it — the mixing the operator reports).
**Both are failures, and the second is how the three stranded lessons above got there.** A guard that
refuses without routing converts a finding into a dead end.

**5. The transport already exists.** `plan-marshall:tools-integration-ci:ci` exposes an `issue`
subcommand alongside `pr` / `checks` / `branch` / `repo`. ⇒ The issue-based approach the operator asks
for does not need a new integration — it needs a **route** that uses the one already there.

## Scope decisions taken at decomposition

Recorded so the run inherits them rather than re-deriving:

- **Issues are DECIDED as the upstream transport** (operator: *"We need an issue based approach here"*).
  Not re-opened.
- **Client-local sharing moves to issues LATER, not first.** The operator's *"eventually we should
  streamline here to issues anyway"* is read as a sequencing statement: WS-02 routes the upstream class
  to issues now; WS-03 addresses client-local durability, with the file store as the interim. ⚠ If that
  reading is wrong, WS-03's gate is where it surfaces cheaply — it is a gate precisely because this
  assumption is the one most worth testing early.
- **Per-component filing is a MEANS, not the goal.** The operator named it first among possible
  aspects, but grounding fact 3 shows component is already recorded and already load-bearing; what is
  missing is an *audience*, which component only proxies for. ⇒ WS-01 owns the axis question, and
  per-component directory layout is one candidate answer inside it, not a premise.

## Inbound routing — this epic is the FOURTH owner

Registered 2026-08-24 as a sibling of `truthful-signals`, `code-intelligence-substrate` and
`review-apparatus`. The canonical discriminator table lives in
[`truthful-signals/epic.md`](../truthful-signals/epic.md) § "Inbound routing rule" and was amended in
the same pass; `lessons` was removed from that epic's column and this one added.

**What routes HERE:** anything about **where a finding goes and whether it survives** — the lessons
corpus and its store resolution, audience/ownership classification, the upstream issue route out of a
consumer repo, lesson provenance (component, version), multi-developer durability, and the
consumer-repo corpus.

⭐ **The test is DESTINATION, not subject.** A defect *in* `manage-lessons`' behaviour that reads
confident while hiding a caveat is `truthful-signals`'. A question about *who should receive a finding
and whether it reaches them* is ours. ⚠ The two are easy to confuse on a keyword match — `PLAN-TRUTH-091`
carries a `lessons-housekeeping` deliverable that correctly stayed there, because its subject is verdict
currency over a mutable global store and lessons is merely the instance.

⛔ **What this epic does NOT own:** the plan-scoped findings store (`manage-findings` — Q-Gate and PR
findings, a different lifecycle), and the orchestrator inbox channel (`truthful-signals` owns it).
Cross-epic overlap is checked with `corpus cross-check` before any plan is emitted.

⚠ **Nothing was transferred at creation.** The `truthful-signals` corpus was searched first: of 17
staged rows, none carried a lessons subject, and the five historical lessons-subject plans are all
shipped. This epic starts from an empty inheritance, not from a migration.

## Standing Rule: Content Sweeps vs Router Infra

**(2026-09-21, operator directive — governs every future run over `.plan/local/lessons-learned/`, not
work already done.)** Operator's own words, recorded verbatim so a future run inherits the rule
rather than re-deriving it:

> Go through each lesson from `.plan/local/lessons-learned`. For each lesson, identify whether it is
> still valid (check ground truth). On first pass, do a consolidation/deduplication. You are
> authorized to use file-based access. Incorporate/ingest each lesson into this orchestrator (and move
> the lesson into the orchestrator's archive). Each handled lesson must be removed from the original
> location. You are explicitly allowed to use file-operations for this cleanup. If incorporated, group
> the extracted aspect into sensible deliverables/plans that suit together. The max number of
> deliverables is 12 per plan. Group them sensibly. **The orchestrator itself must not provide plans
> but act as a distribution point of the sibling orchestrators.**

⛔⛔ **The load-bearing sentence is the last one.** `lessons-routing` (this epic) is **permanent** and
owns only the routing/versioning **mechanism itself** — PLAN-LR-01..06 and any future infra plan about
*how* a finding gets classified, transported, or stamped. It never accumulates content-derived plans.

⛔⛔ **RULING 2026-09-22 (operator) — SUPERSEDES the "separate dated epic" model below. `lessons-routing`
is ALWAYS the orchestrator used for a lessons-corpus sweep, going forward. No new
`lessons-handling-YY-MM-DD-NN` epic is created.** A sweep runs AS this epic, not as a child of it: read
each lesson, check it against ground truth (still valid vs stale), deduplicate/consolidate, cluster,
and route each cluster via `orchestrator inbox write` to whichever sibling epic actually owns the
subject (or, when a cluster is a tooling defect in the routing/versioning mechanism itself rather than
lesson content, port it directly into `lessons-routing` as a new plan — see the `PLAN-LH2-18`/`PLAN-LR-06`
caution two paragraphs up: check both re-grounding AND the Inbound Routing rule before doing that,
never on the strength of "the sweep found it while reading lesson content" alone). Each handled lesson
is removed from `.plan/local/lessons-learned/` via a sanctioned `manage-lessons remove` call (never a
raw `rm`) once its routing message is queued. **The distribution discipline is unchanged — only the
epic wrapper is retired**: this epic still never accumulates content-derived plans from a sweep: every
cluster's disposition is a routing decision (`## Lesson Sweeps` below) or, rarely, a genuinely new
routing-mechanism infra plan, never a staged plan spec that just restates swept content.

Three epics ran the now-retired separate-epic pattern before this ruling and remain as closed history,
never reopened or reused as a template: `lessons-handling-26-08-08-01`, `lessons-handling-26-08-26-01`,
and the short-lived `lessons-handling-26-09-22-01` (opened and closed the same day this ruling landed —
its full record is inlined at `## Lesson Sweeps § 2026-09-22` below and its tree was removed, per the
operator, once inlined).

## Lesson Sweeps

One dated subsection per sweep, append-only, newest last. This is where a sweep's disposition record
lives now that a sweep runs AS this epic rather than as a separate dated epic (see the Standing Rule
above) — never in the generated START-HERE/Ordered-Queue blocks, which stay reserved for this epic's
own PLAN-LR-NN queue.

### 2026-09-22 — full corpus sweep (inlined from the retired `lessons-handling-26-09-22-01`)

Opened as a separate dated epic under the then-current model, closed the same day once the operator
ruled `lessons-routing` is always the orchestrator used; its record is inlined here verbatim and its
tree removed.

**Scan.** `manage-lessons list` → 45 total (44 active + 1 pre-existing `superseded` stub, unrelated).
`manage-lessons aggregate` clustered the 44 active into 10 shared-component/cross-ref groups (31
lessons) + 9 standalones (40 parseable) + 4 unresolvable (unparseable metadata header, all from plan
`tracked-orchestrator-store-resolver`, hand-authored directly into files rather than filed via
`manage-lessons add`).

**Ground-truth check.** Spot-checked the one claim closest to a known precedent: `2026-09-21-13-003`
(manage-lessons `set-body` destroys the metadata header `add` wrote) against the just-shipped
`PLAN-TRUTH-144`/PR#1560 (`05b5d1ac4`) — that fix touched `manage-lessons.py`, `_lessons_io.py`,
`_lessons_query.py` for `add`/`remove`/resolution only; `cmd_set_body` was untouched. Still live,
routed as-is. All 44 were 2026-08-24 through 2026-09-21 vintage, most from one recent retrospective
sweep.

⛔⛔ **CORRECTION (2026-09-22, via `truthful-signals`' own inbox forward, drained below): "no lesson found
already-covered" was FALSE for at least 7 of the 44, and possibly 11.** `truthful-signals` had itself
promoted 11 lessons into the corpus the day before (`2026-09-21-10-002`..`-012`, from its own 2026-09-21
inbox drain). This sweep never checked a lesson's provenance against its routing destination: 7 of those
11 (`10-002,003,005,006,007,009,011`) matched `truthful-signals`' own theme and were routed BACK to it as
if new, then deleted from the corpus once queued. `truthful-signals` caught the round-trip (dates one day
apart, thematically obvious) and restored all 7 from its own archived pre-promotion messages — no
permanent loss. The other 4 in that same promoted range (`10-004`→`process-compliance`, `10-008`→
`post-run-quality`, `10-010`/`10-012`→`orchestrator-refactor`) went to DIFFERENT epics and could not
self-detect the duplication; correction notices were filed to all three. See `## Open Defects` below.

**Routing** (5 destinations, one bundled `inbox write --kind candidate-lesson` message per epic,
matched against each epic's own stated ownership scope):

| Destination | Count | Subject |
|---|--:|---|
| `truthful-signals` | 18 | confident-signal-hides-a-caveat / prose-vs-structured-fact / doc-drift patterns, incl. the 4 unresolvable-header lessons forwarded verbatim |
| `process-compliance` | 12 | finalize/worktree mechanism defects + `persona-plan-marshall-agent` foundational-conduct corrections |
| `post-run-quality` | 6 | `plan-retrospective`/metrics/findings/archived-obligation-ownership |
| `review-apparatus` | 5 | `automatic-review`/review-retrospective |
| `orchestrator-refactor` | 3 | `plan-orchestrator`'s own mechanism, per that epic's own aspect 4 |

Plus a sixth, direct `--kind finding` message to `code-intelligence-substrate`: two of the routed
lessons (`2026-09-21-08-002`, `2026-09-21-08-003`) independently surfaced the same live,
already-diagnosed bug in that epic's own `cloud-runs/_audit/analyze.py` (hardcoded developer-machine
paths, confirmed present on `origin/main`) — sent directly rather than left to surface only inside the
process-angle lessons filed to `truthful-signals`.

One candidate was rerouted mid-analysis: `2026-09-20-08-011` (orchestrator-authored specs tripping
`phase-2-refine`'s suspicious-perfect-confidence heuristic) was initially considered for
`orchestrator-refactor` (its provenance names that epic's PLAN-04) but routed to `truthful-signals`
instead — its remedy is a `phase-2-refine` heuristic-tuning question, not an orchestrator-mechanism
one; `orchestrator-refactor` independently tracks the supporting staged-spec population as its own
Watch.

**Retirement.** All 44 routed lessons removed via `manage-lessons remove --coverage-verdict superseded`
(the convention the prior `lessons-handling-26-08-26-01` epic established — `completely_covered`/
`redundant`/`obsolete` don't fit a routed-not-yet-acted-on finding), each tombstone naming its
destination epic and inbox message; the 4 unresolvable ones used `--allow-unreadable`. All 44 calls
returned success with a tombstone written — **zero destroy-without-tombstone incidents**, confirming
`PLAN-TRUTH-144`'s fix holds under load, the exact failure mode that produced this epic's own retired
`PLAN-LR-06` the same day. Also pruned the one pre-existing `superseded` stub via `cleanup-superseded`.
`.plan/local/lessons-learned/` is now empty.

⚠ **Watch carried forward**: four lessons were hand-authored directly into the corpus without a
metadata header, bypassing `manage-lessons add`. Not treated as a script defect (no evidence `add`/
`set-body` themselves are broken for this case), but if it recurs across future sweeps it may be worth
a `manage-lessons` guard against a headerless file entering the corpus at all. *(re-check: next sweep.)*

⚠ **Watch carried forward**: none of the 6 destination messages was confirmed drained by its receiving
epic in this session. *(re-check: next `status`/`cleanup` pass on any of the 5 sibling epics, or
`code-intelligence-substrate`.)*

## START HERE

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- PLAN-LR-01 — the gate. Nothing else in this epic is designed until its two populations land.

## Ordered Queue

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- PLAN-LR-01 — blocks every other row. Its (b) population is a **cross-repo read** of live consumer
  checkouts, which no other plan in this epic performs.
- PLAN-LR-04 — deliberately last. Migrating the stranded corpus before the route exists would move
  findings from one dead end to another.

## Decisions

- 2026-08-24 — **Epic created** on operator direction combining four aspects (per-component filing, a
  separate structure for plan-marshall's own findings, an issue-based upstream channel, and
  multi-developer sharing). Alternative considered: fold into `truthful-signals` as a workstream —
  **rejected**, because that epic's theme is *a confident signal hiding a caveat* and this is a routing
  and durability problem, and because the surfaces (`manage-lessons`, `tools-integration-ci`) are
  disjoint from its live queue.
- 2026-08-24 — **The axis is AUDIENCE, not component.** Grounding fact 3 established that the existing
  guard already keys on component and still cannot answer the question that matters. Recorded so no
  plan re-proposes "add a component field" as the fix.
- 2026-08-24 — **`lessons-handling-26-08-08-01` is NOT the home.** That epic holds 24 staged plans
  drained *from* the lessons corpus — it consumes lessons as input. This epic owns the corpus's routing
  machinery. Different subjects; no merge.
- 2026-09-22 — **Operator-directed audit: are PLAN-LR-01..06 real work or an accident of
  over-decomposition?** Answer, verified against ground truth (all six spec bodies read, `corpus
  cross-check` run for the first time, and the two named plans' fate checked against `git log`): five
  of six are correctly homed here per this epic's own Inbound Routing rule above (no sibling owns
  audience/ownership classification, the upstream route, provenance, or corpus migration — that is
  *why* this epic exists) and were kept staged, untouched. **PLAN-LR-06 (`manage-lessons-corpus-integrity`,
  WS-05) was RETIRED**, not transferred: its subject (a `remove` call that destroys a lesson while
  reporting `not_found`, with no tombstone) is not a destination question at all — it is exactly the
  "confident signal hides a caveat" pattern this epic's own routing rule assigns to `truthful-signals` —
  and, independently, the fix had *already shipped* the same day the finding was ported in here
  (`truthful-signals-26-09-21/PLAN-TRUTH-144`, PR #1560, `05b5d1ac4`). Filing it as a new finding would
  have duplicated shipped work rather than routed a live one. WS-05 now has zero live plans.
- 2026-09-22 — **OPERATOR RULING: `lessons-routing` is ALWAYS the orchestrator used for a
  lessons-corpus sweep; the separate-dated-epic model is retired.** A sweep just ran as a fresh dated
  epic (`lessons-handling-26-09-22-01`, per the then-current Standing Rule) and completed — 44 lessons
  routed to 5 sibling epics, corpus emptied (full record: `## Lesson Sweeps § 2026-09-22` above). The
  operator then directed: inline that epic's full record into this one and remove its tree, and
  document that this epic is always used going forward. Alternative considered and rejected: keep
  opening a fresh dated epic per sweep — **rejected** by direct operator instruction, not by this
  epic's own reasoning; the Standing Rule section above is amended accordingly. The two PRIOR dated
  epics (`lessons-handling-26-08-08-01`, `26-08-26-01`) are NOT retroactively inlined — this ruling is
  prospective, and reopening closed history to backfill it would be pure churn with no reader benefit.
- 2026-09-23 — **PLAN-LR-07 SHIPPED (PR #1584, `179d4f7f3`), making R15's operator ruling structural in
  the `plan-orchestrator` skill source itself, not just this epic's prose.** Verified: the mode contract
  now states the Fixed-epic-sweep rule, `workflow/lessons-handling.md` routes clusters via `inbox write`
  instead of self-staging (one design refinement over the original spec: cluster routing uses
  `kind=finding`, not `candidate-lesson`, since a bundle isn't one lesson body), and the two stale
  `SKILL.md` cross-references are gone. Bundled an operator-directed `max_iterations: 20 → 5` fix (fully
  disclosed, confirmed as the sole undeclared-surface addition). The run itself cost ~8x its error
  anchor (10.46M tokens, 79% in `6-finalize`, 8 self-review loop-backs) — two off-subject
  candidate-lessons from it were PROMOTED to the global corpus (`2026-09-23-07-001/-002`) rather than
  staged here, since neither is this epic's own subject; the next sweep (now the shipped route-not-stage
  mechanism) carries them to `truthful-signals` and `process-compliance`. Full detail: `landings/PLAN-LR-07.md`.
- 2026-09-23 — **`cleanup` verb: full A1 re-grounding of all 30 claims across PLAN-LR-01..05 against
  HEAD `14d8f3ccd`** (dispatched to an `execution-context-level-5` leaf per the Dispatch Decision Rule —
  213,570 tokens, 103 tool uses). 18 corroborated, 8 contradicted, 4 unverifiable; every contradiction
  was absorbed into its spec (`rescoped: yes`) rather than left blocking. Four load-bearing findings:
  (1) **PLAN-LR-01 D2 is now SETTLED** — the `wrong_store` guard was introduced 2026-07-17, a month
  after the three `cui-jsf-test-basic` lessons were filed, so they predate it and were never routed
  through `--allow-foreign-store`; only `nifi-extensions`' own same-day-adjacent stranded lesson remains
  genuinely ambiguous. (2) **PLAN-LR-04's population claims were fully stale** — `API-Sheriff` moved
  2→16 live lessons (its two originally-named ones are both retired), and `nifi-extensions` (never
  sampled at staging) holds 2 more stranded `plan-marshall:*` findings; D0 must re-derive fresh at
  outline rather than inherit any count on record, including this one. (3) **PLAN-LR-05's cost model
  was INVERTED**, not merely imprecise — `MARSHALL_VERSION` cannot reach `manage-lessons` at all today
  across the executor's subprocess dispatch boundary, so D2's "rare degraded case" is the ONLY reachable
  branch until D1 adds real plumbing; **R11's version-SOURCE ruling is unchanged and was not re-opened**
  — only the effort estimate for reaching it was wrong. (4) **PLAN-LR-02's stale collision map and its
  `PLAN-TRUTH-091` ordering constraint are inert** (that epic closed, the constraint superseded), and
  its `#1050` CodeRabbit-findings caution is discharged (both findings resolved, re-review complete).
  A4 duplication reviewed 376 raw file-overlap rows across 24 active/archived sibling epics — all
  incidental broad-glob coincidences (LR-01's own `manage-lessons/**` recursive glob matching unrelated
  doc-sweep plans); nothing genuinely duplicates this epic's work, so nothing was superseded. A3
  (ambiguity) and A5 (distribution) were clean — no spec missing a required section, no redistribution
  needed. Settled-narrative relocation deferred this pass (no candidate confirmed with the operator) per
  the safe default. Ledger compacted, idempotent. `restart_verdict: not_ready` — 3 new inbox messages
  (sender `api-sheriff-deployment-configurability`) arrived mid-pass, unanalyzed, and this pass's own
  spec edits left 29 uncommitted paths; neither blocks, both are routine follow-ups.

## Open Defects

- ⛔⛔ **Three stranded upstream lessons exist RIGHT NOW** in `cui-jsf-test-basic` — `plan-marshall:recipe-refactor-to-profile-standards`, `plan-marshall:build-maven`, `plan-marshall:workflow-integration-sonar` — in a git-ignored directory, unread by this project. *(source: first-party sample, 2026-08-24. Owned by PLAN-LR-01 (b), routed by PLAN-LR-04.)*
- ⛔ **The `wrong_store` ownership predicate mis-classifies a client's OWN prefixed component as foreign**, because it tests for `marketplace/bundles/{prefix}` which no consumer repo has. Verified against `API-Sheriff` (`api-sheriff:maven-build`, no `marketplace/` directory). *(source: first-party, 2026-08-24. Owned by PLAN-LR-02.)*
- ⚠ **`--allow-foreign-store` is the only escape and it launders the distinction it bypasses** — a lesson filed with it is indistinguishable afterwards from a genuinely local one. *(source: first-party read of `manage-lessons/SKILL.md:108`. Owned by PLAN-LR-02.)*
- ⛔⛔ **A lesson sweep has no way to detect it is re-routing content a destination epic already owns —
  confirmed, not hypothetical.** The 2026-09-22 sweep routed 7 of `truthful-signals`' own 2026-09-21
  promotions (`2026-09-21-10-002,003,005,006,007,009,011`) back to `truthful-signals` as new candidates,
  then deleted the corpus copies once queued; 4 more from the same promoted range went to 3 OTHER epics
  undetected. Root cause: no field on a lesson records which epic (if any) already promoted/dispositioned
  it, so even a same-sender "is this a boomerang" check has no field to read. *(source: `truthful-signals`
  inbox forward, drained 2026-09-22, archived at `inbox/archive/truthful-signals/truthful-signals-002.md`.
  Not yet owned by a staged plan — candidate for a PLAN-LR-07 D6 or a new PLAN-LR-08; do not fold into
  PLAN-LR-07 while it is running, per the operator's parallel launch.)*
- ⚠ **Two consumer repos independently reached OPPOSITE conclusions about the `wrong_store` guard's
  right axis** (Token-Sheriff: refuse harder, treat the override as operator-only; API-Sheriff: file
  locally whenever THIS repo pays the recurring cost, regardless of bundle ownership) — both coherent,
  because "who can fix it" and "who keeps paying for it" are different populations a single store can
  serve only one of. Token-Sheriff's override also RECURRED after a first relocation (PLAN-08 routed
  correctly, PLAN-09 filed two more locally). *(source: `truthful-signals` inbox forward dated
  2026-09-11, drained 2026-09-22 — leads, not independently corroborated from this checkout. Owned by
  PLAN-LR-01 D1/D4 and PLAN-LR-02 D0/D1; PLAN-LR-04 should not assume one-time migration is sufficient
  given the recurrence.)*

## Watches

- ⚠ **How the three stranded lessons were filed at all is UNESTABLISHED** — with `--allow-foreign-store`, or before the guard existed. The answer changes whether the guard is being routinely bypassed in practice or was simply added later. *(re-check: PLAN-LR-01 (b), which reads them.)*
- ⚠ **Cross-org issue creation permissions are unverified.** WS-02 assumes a client repo can open an issue on `cuioss/plan-marshall`. The `ci issue` surface exists, but whether a client developer's token can write to a foreign repo is not established. *(re-check: PLAN-LR-03's gate, before any transport is built.)*
- ⚠ **Consumer-repo count is unknown.** Four are named in project memory (`nifi-extensions`, `cui-jsf-test-basic`, `TokenSheriff`, `API-Sheriff`); two were sampled here. The real population bounds how much stranded corpus exists. *(re-check: PLAN-LR-01 (b).)*
