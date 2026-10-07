# Epic: Post-Run Quality Analysis

slug: post-run-quality

> Ledger document for one epic under `.plan/orchestrator/post-run-quality/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

**Everything this project does to judge a run AFTER it has finished — and whether any of it is
trustworthy.** Fourteen distinct aspects exist today across four surfaces: the 16-aspect
`plan-retrospective`, the 24-check archived-plan corpus auditor, the metrics/findings measurement
substrate, and the lessons corpus that is supposed to close the loop. They were built one at a time, and
the evidence says the seams between them leak: a producer publishes a confident figure over a population
it never read; an auditor's own census cannot census itself; a process lesson reaches the governing
contract **1 time in 5**; and an obligation a finished plan left behind has no owner once that plan is
archived.

Too large for one plan because the aspects share no owner and no vocabulary: each is a separate producer,
several were built by different plans in different epics, and the fixes span `plan-retrospective`,
`.claude/skills/audit-archived-plan-retrospectives`, `manage-metrics`, `manage-findings` and
`manage-lessons`. **Done at the epic level** means: every post-run producer states the population it read,
every post-run verdict is derivable rather than self-reported, the loop from finding → lesson → governing
contract is measured rather than assumed, and an obligation that outlives its plan has a tracker.

⭐ **The epic's own instrument is the honest zero.** Every deliverable here is judged by one question:
after it lands, can a reader tell *"checked and clean"* from *"never looked"*? That is ADR-019 applied to
the machinery that grades us.

## START HERE

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- PLAN-PRQ-01 — carries the substance of `truthful-signals` PLAN-TRUTH-152 (itself the merge of
  PLAN-TRUTH-123 + PLAN-TRUTH-130). Its 11 deliverables were re-grounded at transfer; see the transfer
  record under `## Decisions`.
- PLAN-PRQ-05 — carries the substance of `next-level` PLAN-09.
- PLAN-PRQ-07 — operator-directed addendum (not epic-derived like PRQ-01..06). Spans TWO repos: this one
  (relocating `audit-archived-plan-retrospectives`, staging `analyze-marshall-quality`) and a NEW
  `plan-marshall-telemetry` repo the executing plan creates with operator confirmation. See `## Decisions`
  for the split-placement call (folded into this epic as WS-05, not a separate epic).

## Ordered Queue

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- **Scope is 1 — strictly sequential** (operator decision at init). Most of this corpus shares
  `plan-retrospective/**`, so the disjointness gate would serialize the majority regardless; the knob
  makes that explicit rather than discovered per round.
- PLAN-PRQ-01 ↔ PLAN-PRQ-02 — both touch `plan-retrospective/scripts/`; never pair.
- PLAN-PRQ-03 is the only spec whose surface is entirely project-local (`.claude/skills/`), so it is the
  natural partner if the scope knob is ever raised.
- ⛔ **PLAN-PRQ-15 — NOT a `next` candidate, and NOT a `/plan-marshall` plan. Do not emit it.** Same lane
  as PRQ-13: a standalone session in `plan-marshall-telemetry`, hand-off in the spec. Its surface is
  entirely out-of-repo, so it will read `prose` and the gate will refuse it forever — correctly. It does
  **not** occupy the `parallelization_scope: 1` slot, so `PLAN-PRQ-14` may run concurrently with it.
- ✅ **PLAN-PRQ-14 — the one ordinary `/plan-marshall` candidate in the queue.** In-repo surface, 7 declared
  paths, `declarative`. Expect the usual `candidate_comparison_determinate: false` plus a `manage-findings`
  overlap against `review-apparatus` `PLAN-PR-072` and `truthful-signals` `PLAN-TRUTH-146`/`-178` — all
  staged, none running.
- ⛔ **PLAN-PRQ-13 — shipped; was NOT a `next` candidate and never a `/plan-marshall` plan.** Re-cut
  2026-10-04 to run as a standalone Claude Code session inside `plan-marshall-telemetry`; the earlier
  `/plan-marshall` emit is void. Two consequences for this queue, both deliberate: its surface is
  `derivation_status: prose` (0 resolved, 5 unresolved — every entry prefixed `plan-marshall-telemetry/`
  so it cannot be mistaken for an in-repo path), so `admits_disjointness_check` is **false** and the gate
  will refuse it **forever**; and it **does not occupy the `parallelization_scope: 1` slot**, because that
  knob bounds concurrent plan-marshall plans contending for *this* repository's worktrees and a session in
  another repository contends for none of them. So a plan-marshall plan MAY run concurrently with it. Its
  row tracks lifecycle state only — move it to `running` when the operator starts the session, and
  `shipped` when it lands.
- ✅ **PLAN-PRQ-07 — SHIPPED 2026-10-04, PR #1694.** Un-parked and emitted 2026-10-02 by operator decision
  with the disjointness gate overridden on a stated basis and the PRQ-01/PRQ-03 dependency discharged; the
  override held and nothing collided. See `landings/PLAN-PRQ-07.md`. **WS-05 is complete** — it was a
  single-plan workstream. The queue is back to 9 parked and 3 shipped, with nothing live.
- PLAN-PRQ-07 ↔ PLAN-PRQ-01, PLAN-PRQ-03 — both touch `.claude/skills/audit-archived-plan-retrospectives/**`,
  the exact skill PRQ-07 relocates out of this repo. PRQ-07 is a hard DEPENDENCY on both landing first, not
  a mere disjointness overlap — never emit PRQ-07 while either is staged/launched/running. ✅ **Discharged
  2026-10-02**: both are `parked`, so neither can be in flight and the hazard cannot occur. ⛔ Un-parking
  either one makes this binding again.
- PLAN-PRQ-07 ↔ PLAN-PRQ-04, PLAN-PRQ-06 — conditional overlap on `phase-6-finalize/**`, pending whether
  PRQ-07's finalize step lands marketplace-bundled (HYPOTHESIS, verify-at-outline in its spec). ✅ **Moot
  2026-10-02**: PRQ-06 is `shipped`, PRQ-04 is `parked`; same for the `parked` PRQ-08/PRQ-10 overlaps on the
  same surface.
- ⛔ **PLAN-PRQ-07 ↔ `code-intelligence-substrate` PLAN-CIS-036/050/052/054/056 — the one UNSERIALIZED risk.**
  Those specs are staged in ANOTHER ledger and declare the same `audit-archived-plan-retrospectives` skill
  and test mirror PRQ-07 relocates. No gate serializes across ledgers, and each ledger's own "no known
  overlap" line is scoped to its own queue. Re-read that epic's live queue at PRQ-07's outline.

## Decisions

- 2026-10-05 — **WS-05 closed out for real: the telemetry repo has run against live data for two projects,
  and all three outstanding Watches are retired.** Operator: *"the repo is there, we did some more
  iteration in it. Consider the item to be closed."* ⚠ **Checked which Watches the evidence actually
  closes rather than closing three on one sentence** — two are first-party verified, one is
  operator-confirmed, and the ledger distinguishes them. ⛔⛔ **The headline is the vindication, not the
  closure**: the first real run found **false measured zeros** — a recorder placeholder `total_tokens: 0`
  treated as a figure on **11 plans**, and `main_context_tokens` measured-0 on **45 plans** — the precise
  defect class this epic exists to eliminate, shipped inside the instrument built to detect it, invisible
  to 924 green tests, and surfaced only by real data. ⭐ **A fixture corpus cannot contain the shapes a
  real corpus has**, and this is the epic's own evidence for it.
  **Iterations beyond the plans, recorded because the ledger describes none of them:** a `doc/audits/`
  content audit drove most of the fixes; an **`adjudicate`** surface arrived with ground truths, verdicts
  and worklists — a concept no PRQ spec anticipated; monthly project reports, incremental runs, `--pending`
  / `--force`, and a `dry-run/` tree were added; the project archives moved from `{project-slug}/` to
  **`projects/{project-slug}/`**, so the README invariant PRQ-15 honoured now reads one level deeper; and
  findings handling was corrected repeatedly (process records are not findings, a failing build is one
  finding not many, a build finding takes no severity band). ⚠ **`54ea27f` deleted both the PRQ-13 and
  PRQ-15 run reports from the telemetry repo**, so `landings/PLAN-PRQ-13.md` and `landings/PLAN-PRQ-15.md`
  are now the only durable record of those runs. That is the correct arrangement — the ledger is the record
  and the repo is the work — but it means the landings must not be trimmed as duplicates of something that
  no longer exists.
- 2026-10-04 — **`PLAN-PRQ-15` SHIPPED (telemetry `0965060..0adc341`, 8 commits, no PR), and it found a
  `PLAN-PRQ-13` defect.** All seven deliverables; `landings/PLAN-PRQ-15.md` is the record; WS-05 complete.
  Suite **924 passed / 20 skipped** (from 873/20), green before every commit — ⚠ the run's figure, not
  re-verified here, since the system `python3` has no pytest. **D6 verified in the tree**: skills are now
  exactly `analysis-engine`, `analyze`, `transfer`; test dirs mirror them exactly and ⭐ **the mirror got
  stronger** — `test/analyze/` is new, carrying the control that fails if a slash-command usage example
  returns; the rename commit shows **126 rename-detected paths**, so `git mv` moved both trees in one
  commit as required; the engine reads `user-invocable: false`. ✅ The rename is complete — the old name
  survives in exactly two files, both correctly (the two run reports, one historical and one documenting
  the rename). ⛔ **THE FINDING THAT MATTERS: `plan_rollup` reported `complete: true` over floor
  summands** — a sum built from lower bounds published as complete, because the roll-up ignored
  `floor: true`. **A PRQ-13 defect, found by reusing PRQ-13's own pattern**, and it is the
  *floor-propagation* form of this epic's founding class: not a false zero but a **false certainty**. Also
  fixed: the severity roll-up silently dropped out-of-vocabulary values, and the engine's usage examples
  still showed it run as a slash command — a second front door surviving in the docs after D6(a) closed
  the real one, now with a control. ⭐ **`aborted` is reachable but has never occurred**, and the
  distinction was preserved: derivable only from an explicit `metadata.archived_reason` other than
  `normal_completion`, which **none of 70** archived plans has (the 7 that record a reason all say
  `normal_completion`). Producible-but-never-produced is a different fact from unreachable, and different
  again from "nothing was ever aborted". ⛔ And the rule held — **a plan with zero deliverables done is
  never treated as `aborted`**; the 4 `indeterminate` results are exactly where a lesser implementation
  would have guessed. Completion over the real corpus: 63 fully, 3 partially, 0 aborted, 4 indeterminate.
  ⚠ **The run corrected my blast-radius figure**: 38 across 14 files, not my 46 across 15, because D6(b)'s
  fold removed references before (c) ran. My measurement was right when taken and stale when used — **a
  blast radius measured before an earlier step runs is a moving figure, and a spec quoting one should say
  which step it was measured at.** Mine did not.
- 2026-10-04 — **`PLAN-PRQ-15` gains D6: the skill-layout cleanup, three parts.** Operator asked whether
  the telemetry repo's four project skills are all necessary. Read all four. **`transfer` and the engine
  are clearly necessary** (write path, read path). **`analyze` is justified** — its 106 lines and zero
  scripts look like a veneer, but the value is behavioural discipline the engine does not hold (run exactly
  once, add no unrequested flags, surface verbatim, read `corpus-selection` / `run-summary` /
  `subject-reports` first) — ⛔ **except that BOTH declare `user-invocable: true`, so the engine is a
  second front door and that discipline is bypassable by design.** **`era-stamp-fill` is the questionable
  peer**: a sibling skill that rewrites *another skill's source*, which is a layering inversion — and the
  coupling is already mutual, since the engine's own SKILL.md and `audit.py` reference the era-stamp
  mechanism in return. ⚠ Separately, **the engine's name no longer describes its job**: inherited from
  plan-marshall where it audited archived plan retrospectives, while here it writes outcome and quality
  reports — its own description already opens *"The telemetry repository's single analysis engine"*, so the
  description has outgrown the name. ⇒ D6 does all three, (c) last and in one commit. ⭐ **The operator
  caught what I under-specified: the TEST directories rename too.** Verified — `test/` holds a same-named
  directory for each skill that has tests, so **the test tree mirrors the skill tree one-to-one and that
  mirror is an invariant, not a coincidence.** D6 now states it as a two-directory move per change, with
  the rule that a rename leaving `test/audit-archived-plan-retrospectives/` behind is **worse than not
  renaming**: the tree would assert a mirror it does not have, and the next reader could not tell which
  name is current. Blast radius measured rather than estimated — **46 occurrences across 15 files**, plus
  the two directories; `pyproject.toml` does not reference the name, though its `testpaths` means
  collection must be re-confirmed after the move.
- 2026-10-04 — **`PLAN-PRQ-15` staged: a project-level AsciiDoc aggregate, and the three identity facts the
  outcome report does not carry. WS-05 reopened.** Operator-directed. ⭐ **Two of the three requested facts
  are genuinely absent and the third is partial** — checked against `doc/outcome-report.md` at `5546bde`
  rather than assumed: there is **no completion state** (`deliverables_total`/`done` make *partial*
  derivable, but ⛔ **`aborted` is not** — a zero may mean abandoned, never-started or unmeasurable, which
  are three different facts); **no repository identity at all**; and `prs` carries numbers, `sources` and
  `landed` but **no URLs**. ⛔ **A URL cannot be built without the repository, so that ordering is binding
  inside the plan.** ⛔⛔ **A naming collision had to be caught before anything was written**: the
  operator's word for the first fact is `state`, but `state` is **already the envelope key on every
  field** (`measured`/`not_measured`/`not_applicable`), so a top-level `state` would be two different
  things one key apart — D0 must rename it rather than shadow the envelope. The aggregate is specified as
  **a VIEW that computes no fact of its own**, generated **by the engine, not `analyze`** (which declares
  no report format of its own — the same trap PRQ-13 D1 was corrected for), regenerated before every
  commit so a stale aggregate can never sit beside fresh JSON, and ⛔ **carrying the measurement states
  through**: it reuses `plan_rollup`'s population-plus-`complete` floor pattern and renders an incomplete
  sum visibly as a floor, because summing a `not_measured` as zero in *the artefact a human actually
  reads* would be this epic's founding defect doing maximum damage. It also owes a named
  could-not-be-measured section. ⚠ Three HYPOTHESES left for outline: whether the archive carries positive
  evidence for `aborted` at all (if not, the value ships documented-but-unreachable rather than silently
  never emitted), whether the repo identity is derivable, and that no project has been transferred yet — so
  a fixture corpus and D5's controls may be the only evidence available, which the plan says rather than
  claiming a verified aggregate.
- 2026-10-04 — **PLAN-PRQ-13 SHIPPED in the telemetry repo (commits `5546bde`, `0965060`), and the
  out-of-lifecycle lane worked.** All ten deliverables landed; `landings/PLAN-PRQ-13.md` is the record.
  ⭐ **The first plan this epic landed outside the plan-marshall lifecycle** — no phases, no finalize steps,
  no PR, no CI, no retrospective, no inbox landing — and every substitute the brief named was honoured and
  is checkable: deliverable order with D0 as gate, `pytest` green before every commit (**873 passed, 20
  skipped**, from 784/19), one deliberate self-review pass, direct commits to `main`, and a 253-line run
  report standing in for the machinery. ✅ **The report-location invariant was honoured, not amended** —
  reports land beside the archive under `reports/{project-slug}/`, so `{project-slug}/` stays written only
  by `transfer`. ✅ **The mechanism-order control passed against the real thing**: run with
  `--plan-marshall-root`, it confirms step orders **5, 7, 8, 30, 40** agree with plan-marshall's
  finalize-step orders — so the taxonomy's claim that its order is *derived* is now mechanically checked
  across two repositories. ⭐ **D0 corrected my partition in three places and two corrections were against
  me**, which is a gate behaving as a gate should: `input-integrity` KEPT (it is the no-false-healthy floor
  the kept `metrics`/`token-*` checks stand on), `merge-window-accounting` DROPPED (its merge-lock logs are
  never transferred, so it fails *the brief's own* "does not survive archival" test — I had read the name
  as outcome-shaped), and `cross-check-synthesis` RE-SCOPED (7 of 10 couplings need a retired check; it now
  reports `evaluated: yes/partial/no` so an unevaluable coupling is never counted as a clean one).
  ⛔ **Self-review found SEVEN defects and six are this epic's founding class, in the instrument built to
  detect it**: a measured `0` over an empty population; unknown gates folded into clean ones; a mechanism
  masked by its gate; a compatibility policy misread as a contract break (19 of 63 plans wrongly
  `critical`); a leaked machine path; a stale doc count. ⛔ **And the seventh is a pre-existing defect in
  the relocated check**: all **820** `assessments.jsonl` records were counted as findings, which made **255
  of PLAN-PRQ-07's 255 "actionable pending" items** assessments rather than findings — so every
  `quality-chain` reading of this corpus taken before `5546bde` overstated actionable chain debt. See the
  Watch; re-derive rather than cite any such figure.
- 2026-10-04 — **`PLAN-PRQ-14` staged from PRQ-13's D4a hand-back: the producers do not say which gate
  caught it, and Sonar's severity is thrown away at the door.** Five items, three required and two
  recommended, staged in THIS repository because that is where the producer surfaces live — which is
  exactly what D4a was for: PRQ-13 classified on the reading side and handed the producer-side work back
  rather than reaching across for it. ⛔ **Item 3 is the one with a deadline**, because it is lossy rather
  than merely absent: `simplify` and `security-review` omit a marker that could in principle be
  back-derived, while Sonar's collapse **destroys information at ingestion**, so every day it does not land
  is another day of findings whose `critical`-versus-`major` distinction can never be recovered. ⛔ The
  spec states plainly that it fixes findings from the day it lands and that **every already-archived plan
  stays `not_measured` forever** — no back-fill from the mapped value, because `error` → `major` would be a
  fabrication. It also declines to widen `FINDING_SEVERITIES` (a tree-wide blast radius for a provenance
  problem) and declines to pick up the parked `PLAN-TRUTH-146`'s vocabulary work. ⚠ Two of its claims are
  the hand-back's own and are labelled HYPOTHESIS rather than inherited as fact: that simplify files *no*
  findings rather than untagged ones (the two need different fixes), and the `39 of 55` fingerprint figure.
- 2026-10-04 — **PLAN-PRQ-13 trimmed of historical fluff; the brief and the record had been conflated.**
  Operator challenge: *"is there still historical fluff in the plan, like change at ot the operator said
  that has no benefit for the plan?"* It was right. Measured rather than eyeballed: 691 → 667 lines, with
  all **8** self-referential passages removed — *"the first draft said X"*, *"CORRECTED 2026-10-04"*,
  *"RE-CUT 2026-10-04 (operator)"*, *"an earlier draft carried…"*, the gate-override-no-longer-needed note,
  and the scope-guard-overridden-by-operator-decision note. ⭐ **Every conclusion was kept and only the
  narrative around it deleted**: the report-location invariant stays without the story of a draft that
  broke it; the engine-not-wrapper fix site stays without *"CORRECTED"*; the adapted-in-transit finding
  stays, re-labelled from the re-grounding token `CONTRADICTED` to the claim-label token `OBSERVED`, which
  is the correct vocabulary for a spec claim; the prefix and `EXCLUDED` warnings stay as imperatives
  because both protect a future *editor* of the spec; and *"do not split this work"* stays as a design
  constraint without the guard/count/operator framing. ⚠ **What stayed is not fluff**: every remaining date
  is an `OBSERVED 2026-10-04` observation timestamp, which the verify-first contract requires — an
  `OBSERVED` claim with no date cannot be assessed for staleness by the session that reads it. ⛔ **Root
  cause, and it is mine: I conflated the brief with the record because I was editing under correction.**
  The spec is the BRIEF for an implementing session; `epic.md` Decisions and `logs/decision.log` are the
  RECORD — and they already carried every deleted passage in full, so removing them from the spec lost
  nothing. **A correction belongs in the ledger, not in the artefact it corrects.**
- 2026-10-04 — **Severity axis added to PLAN-PRQ-13, and the answer to "do we already have a unified
  ontology for that" is NO — with one vocabulary that is actively LOSSY.** Operator wanted a
  minor/major/critical scale so the corpus can be asked *"how many major changes"*. Verified in the code:
  what exists is `scope_estimate` (`none`/`surgical`/`single_module`/`multi_module`/`broad` — a **SIZE**
  scale, already audited), `VALID_CHANGE_TYPES` (a **KIND** scale), `VALID_TRACKS` (`simple`/`complex`),
  and `FINDING_SEVERITIES` (`error`/`warning`/`info`) which grades **findings, not changes**. So that
  question is unanswerable today. ⛔⛔ **And the real finding is worse than a gap**:
  `workflow-integration-sonar`'s `_map_severity` collapses Sonar's five bands into three — **`BLOCKER`,
  `CRITICAL` and `MAJOR` all become `error`** — so the critical/major distinction is **destroyed at
  ingestion**, not merely unreported, and for an already-archived plan it is unrecoverable. ⇒ Axis 4
  reports `not_measured` with a `collapsed_at_ingestion` basis for such subjects, and a control
  specifically asserts it does **not** emit `critical: 0`, which a reader would take as a checked zero.
  **ADR-019 at its sharpest: the population was overwritten, not merely unread.** The axis itself is a
  closed four-band set (`trivial`/`minor`/`major`/`critical`) applied to both changes and findings,
  **derived with its inputs published and never self-reported** — a self-reported severity is exactly the
  producer-publishes-a-confident-figure defect this epic exists to fight — with a control that recomputes
  the band from `derived_from` and asserts equality. ⛔ **Severity is NOT scope**: a broad formatting sweep
  is `broad` + `trivial`, a one-line contract change is `surgical` + `critical`, and folding them would
  lose exactly the cases that matter most in both directions. Operator also confirmed the
  build-through-human-review mechanism axis stays in full — axes 3 and 4 are additions, not replacements.
  **D8 added**: document all four axes in their own document(s) in the telemetry repo, each stating its
  closed value set, its derivation rule where derived, and ⛔ **what the axis is NOT** — every one of the
  four has a near neighbour it is confused with, and those distinctions are the first thing lost when an
  ontology is summarised. A doc-vs-code control asserts each documented value set equals the constant the
  code validates against, in both directions.
- 2026-10-04 — **PLAN-PRQ-13's taxonomy written out as a normative section — it had only been
  REFERENCED.** Operator question: *"is the created taxonomy already part of the plan?"* Honest answer was
  no. D4 named the existing `quality-chain` axes and described a prose delta — add `simplify`,
  `security-review`, `sonar`; carry bot identity; add a scope-stability axis — which is not a
  specification, and the reader this plan hands to is a session in another repository with none of this
  epic's context, so a reference was the wrong carrier. ⭐ **Three things the writing-out produced that the
  reference could not.** (1) **The mechanism order is DERIVED, not judged**: it is the composed finalize
  step order (`simplify` 5, `security-review` 7, `self-review` 8, `auto-review` 30, `sonar` 40), which is
  the same cost-and-lateness ordering `quality-chain` already claims — so the two new pre-push mechanisms
  sit before self-review *because their steps fire earlier*, and a D7 control asserts the axis and the step
  order agree, so "derived" cannot decay into "asserted once". (2) **`bot` is a field on an `auto-review`
  row, not a mechanism value**, over a closed set plus `required: true|false|unknown` — `unknown` is
  *required*, because an archived plan's bot roster at run time is not recoverable from the records.
  (3) **The scope-stability axis is defined for the first time**, with direction, discovering phase and a
  basis line per instance. ⛔ Its justification is PRQ-07's own drop of deliverable 3 by operator ruling:
  that event appears in **no findings file at all**, so an ontology built only on findings cannot see the
  largest scope change that plan had. Also: `gates[]` makes PRQ-01 D2's discipline **structural** — `ran`
  is signal presence, `findings` is yield, separate fields never folded — and a stale `{subject}/quality.json`
  path left over from the report-location correction is fixed.
- 2026-10-04 — **PLAN-PRQ-13 RE-CUT as a standalone session in the telemetry repo; the `/plan-marshall`
  emit is VOID.** Operator decision, prompted by the operator's own reading of the Expected Surface — which
  was the right diagnostic. ⭐ **The repo's README is the evidence, not architectural preference:** it
  declares the skills *"need neither a plan-marshall checkout nor the plan-marshall plugin"* and that the
  repo is *"`main` only … no feature branches, no pull requests, no branch protection, and no review
  bots."* It carries no `.plan/` and no `.github/`, so there is no `marshal.json`, no generated executor
  and no CI for a lifecycle to drive. ⛔ **The decisive argument is first-party**: PRQ-07 ran this exact
  shape *through* the lifecycle, and its footprint resolver could not see the sibling repo — 111 declared
  paths invisible, `affected_files_recall` **27.3%** graded as an *error*, three instruments reporting a
  silent descope on a plan where everything shipped. Running the plan that **builds outcome measurement**
  under a lifecycle whose measurement is known-broken for this shape is self-defeating. ✅ **One consequence
  is a strict improvement**: the in-repo work is split out to a new D4a — if the three new mechanisms need
  a producer-side `manage-findings` change, that is handed back as a separate `/plan-marshall` task in this
  repo — so PRQ-13 declares **no in-repo surface** and **the disjointness-gate override is no longer
  needed**. ⛔ **Three defects in my own rework, caught by re-running the parser rather than trusting the
  edit**: (1) the first draft wrote reports to `{subject}/outcome.json`, violating the README's invariant
  that entries under `{project-slug}/` are *"written only by `transfer` and are never modified or deleted
  by analysis"* — making analysis a writer of the archive it exists to measure; D0 now owns the location
  call, with honouring the invariant preferred and amending it the only alternative. (2) A draft declared
  the telemetry paths **relative**, so the parser resolved `test/` and `README.md` against THIS repo —
  declaring this repo's whole test tree as surface. Every entry is now prefixed `plan-marshall-telemetry/`
  and resolves to nothing, which is the honest answer. (3) A `⛔ EXCLUDED` bullet naming `manage-findings`
  was **still declared by the parser** — the section is read mechanically and an annotation excludes
  nothing. Exclusions now live in D4a and in prose, never as an entry.
- 2026-10-04 — **PLAN-PRQ-13 staged: re-scope the telemetry `analyze` onto outcomes, plus a unified quality
  report. WS-05 reopened.** Operator-directed, immediately after PRQ-07 landed. Two halves: drop the
  runtime/process aspects and emit one outcome report per plan and per orchestrator (time, tokens, PRs,
  lines added/modified/removed, project kind), and add a **separate quality file** on a unified ontology
  (requirement changes, specification changes discovered at execute, and the review results — simplify,
  self-review, security-review, PR agents, Sonar), leaving unmeasured and not-applicable distinct.
  ⭐ **The find that shaped the spec: the ontology already exists and already ships.** The relocated
  `quality-chain` check classifies every `artifacts/findings/*.jsonl` record on a mechanism axis
  (`build` → `self-review` → `auto-review` → `human-review`, ordered by cost and lateness) and an 8-bucket
  resolution axis, and already splits `pending` into an actionable and a structural half. So D4 EXTENDS a
  shipped classifier — adding `simplify`, `security-review` and `sonar` as mechanisms, carrying bot
  identity, and adding the scope-stability axis the findings axes have no home for — rather than inventing
  a vocabulary. ⛔ **Two parked specs' substance is CARRIED rather than awaited, because neither can land**:
  `PLAN-PRQ-01` D2 (signal presence first, yield second, never folded into one number) and D3 (the corpus
  quality report) are parked here, and `truthful-signals` `PLAN-TRUTH-146` — the unified findings
  vocabulary PRQ-01 D10 was to consume and explicitly must not re-implement — is **`parked` in its own
  epic**, so that vocabulary will never be built there. Waiting on it would have made this plan
  permanently unstageable. **Format settled** (operator): report files are JSON, the skill's own stdout
  stays TOON. **Scope-bloat guard overridden** (operator): eight deliverables against the ~6 presumption,
  rationale recorded — D1–D4 share one subject resolver, one report writer and one ontology, and splitting
  them would put the shared engine in one plan and its second consumer in another, which is the
  "two independently-authored formatters" failure PRQ-07's own deliverable 4 was written to prevent.
  ⚠ **Not emitted.** The staging was the request; the disjointness gate's verdict on it is recorded in the
  Open Defect below and the emit decision is the operator's.
- 2026-10-04 — **PLAN-PRQ-07 SHIPPED — PR #1694 (`b3aba30aa`) after split part #1692, and the inbox channel
  worked for the first time.** 13.1M tokens, 26.6 h wall, merged via merge queue, `cleanup_owed=false`;
  `landings/PLAN-PRQ-07.md` is the full record. ⭐ **Three firsts for this epic, and they are the headline
  rather than the shipping:** the landing arrived *through the inbox* (PRQ-06's never fired; PRQ-02's came as
  9 messages), `inbox landing-check` returned **`complete: true` with `missing_keys[0]`** — every required
  fact key present with a real value, no `n/a` and no `unknown` — and the orchestration-detection control
  recorded at launch **predicted exactly this and held**. ⛔ **Deliverable 3 was DROPPED by an operator
  ruling at refine**, not silently: `request.md:15-16` records *"Do not create a finalize step. Make it only
  an explicit command in the new repo."* The surface-delta mechanism is what surfaced it — a single
  declared-but-untouched path (`finalize-step-analyze-marshall-quality/`) out of 4 declared against 152
  realized, with 44 undeclared additions (`expansion_detected`, the gate's documented under-declaration
  class at roughly its documented magnitude). ⚠ **Two of five deliverables were recorded UNVERIFIABLE, not
  shipped** — the `transfer` and `analyze` skills live in the private `cuioss/plan-marshall-telemetry` —
  ✅ **and both are now VERIFIED PRESENT**: a local checkout was found at
  `/home/oliver/git/plan-marshall-telemetry` later the same day, carrying four skills and all 24 relocated
  checks. ⚠ One sub-claim is refuted in the same reading: the corpus did **not** arrive verbatim
  (`quality-chain.md` was adapted in transit), so "relocated" is not "unchanged". The landing record
  carries the correction. ⭐ That is the intended lifecycle of an ADR-019 `unverifiable` verdict — the
  honest record of what was reachable, revisited the moment the population became reachable, rather than a
  permanent label. ✅ **The emit-time gate
  override held**: nothing collided, exactly as its stated basis predicted. ⚠ The cross-ledger exposure it
  did not cover also did not materialise — but it was never serialized, so that is luck, not a guarantee,
  and `code-intelligence-substrate`'s five specs now declare a surface this repository no longer contains.
- 2026-10-04 — **Inbox drained: 9 messages, the landing plus 8 candidate lessons, all dispositioned.**
  Fold (4, every one into a PARKED spec, deliberately — those specs are the PM-MCP carry-over's evidence
  chain): `-001` re-fire-on-a-verdict-irrelevant-delta → `PLAN-PRQ-10`, supplying the mechanism D1 lacked
  (`verdict_inputs` already exists; the re-fire rule keys on HEAD movement alone) with
  `verdict-currency.md` added to its Expected Surface in the same act; `-004` operator escalations
  classified `error` instead of the already-existing `blocked_user_review` (**1,285,813 tokens** reported as
  waste that was not) and `-007` all 33 dispatch-boundary rows keyless, **0 of 33** joined, recording dead
  after 13:16:33Z → `PLAN-PRQ-08`, one onto each half of its title; `-006` the footprint resolver sees
  neither a split landing's earlier PR nor a sibling repo, so three instruments graded a complete plan as a
  descope (recall **27.3%**) → `PLAN-PRQ-09`, with `manage-references/scripts/` added in the same act;
  `-008` lessons-housekeeping Step 1 prescribes the retired `modified_files` read, six firings each
  improvising a replacement → `PLAN-PRQ-05`. Promote (1): `-002` required-bot size caps and
  dependency-aware splitting → corpus lesson `2026-10-04-09-001`. Forward-and-discard (2): `-003`
  rate-window await blocking inside a leaf → `review-apparatus` (PR/CI territory per the standing routing
  rule); `-005` `scope_creep_check` → `truthful-signals`, as a **recurrence** of the signal routed there on
  2026-09-26 **plus a second defect** that one did not carry (the residual set is diffed from
  `plan_creation_sha`, so upstream drift counts as creep — fixing only the finding type would make the
  guard persist a wrong number instead of failing to persist one). ⚠ The TRUTH-178 ownership claim is read
  from this epic's own ledger and is **not** independently verified; the forwarded message says so.
- 2026-10-02 — **PLAN-PRQ-07 started** (operator confirmation, *"plan started"*); `staged → running`, plan id
  `cross-repo-telemetry-archive-and-analyze` stamped on the row, pre-flight `client.toon` written
  (`degraded: false`). The intermediate `launched` state is deliberately not in the row's history: `auto_emit`
  is `false`, so nothing was stamped at emit time, and the operator's confirmation arrived as a START
  confirmation — recording `launched` retroactively would assert an observation that was never made. ✅
  **First-party control for this epic's own orchestration-detection Open Defect:** `inbox detect` on the
  plan's persisted `source_id` returns `orchestrated: true`, `epic: post-run-quality`,
  `detection: orchestrated`. PRQ-06's landing was lost precisely because its `request.md` carried no
  `source_id` and the detector answered a confident "not orchestrated"; this plan carries one, so
  `emit-landing` should fire and this epic should receive its landing through the inbox rather than by manual
  filing. ⚠ That is a prediction from the detector's verdict, not an observed landing — it is confirmed only
  when the message actually arrives.
- 2026-10-02 — **PLAN-PRQ-07 un-parked and emitted; the disjointness gate overridden on a stated basis and
  the hard dependency discharged.** Operator decision, two forks surfaced and both answered. **(1) Why this
  row and not the others:** the 2026-09-26 supersession's ground is that `plan-marshall-mcp` replaces the
  process prose and the Python scripts the parked plans edit — PRQ-07 stands up a NEW repository and
  relocates a skill OUT of this one, so that ground never fitted it. The blanket park swept it in with the
  rest; this corrects that. The other nine rows stay parked. **(2) The gate was refused and overridden, not
  passed:** `corpus cross-check` returns `candidate_comparison_determinate: false` — 96 sibling-epic specs
  and 3 live plans declare no comparable surface, so the admission test fails closed per ADR-019 rather than
  calling an unexamined population disjoint. The override's basis is recorded because it is the whole
  warrant: **zero** overlap rows against any live plan, and every in-corpus overlap is against a `parked` or
  `shipped` sibling that cannot be in flight. ⛔ The indeterminacy is NOT fixable from here — it is 96 other
  ledgers' specs declaring prose surfaces — so "resolve it first" would mean "never". **(3) The dependency
  on PRQ-01/PRQ-03 is DISCHARGED, not overridden:** the hazard it names is relocating the skill out from
  under their *in-flight edits*, and a parked plan is never in flight. The rule is left in the spec intact
  and becomes binding again if either is un-parked. **(4) What the override does NOT cover, and it is a real
  exposure:** `code-intelligence-substrate` carries five staged specs (`PLAN-CIS-036/050/052/054/056`)
  declaring the same skill and test mirror. No gate serializes across two ledgers, and each ledger's
  "no known overlap" statement is scoped to its own queue — the exact blind spot this epic exists to name.
  PRQ-07's spec carries a re-check-at-outline obligation for it. **(5) Prep-readiness passed on its own
  terms** (8 claims, 0 blocking) but every verdict is STALE at `7d82d5d90` against HEAD `59ad113e2`;
  staleness is reported, never promoted, and the spec carries a re-ground-all-eight obligation. `auto_emit`
  is `false`, so the command is emitted and the `launched` transition waits on operator-confirmed launch.
- 2026-10-02 — **Ledger restored after the #1641 revert, then the inbox drained (3 messages).** Two
  operator decisions this session. (1) **Restore.** `process-compliance-001.md` reported that PR #1641
  (`945e59287`), squash-merged from a branch cut before #1643, had reverted this epic's 2026-09-26 PM-MCP
  supersession. The claim was corroborated first-party (`git diff 88fcfc9ef..HEAD` over this tree) and was
  still live on `main`: every parked row flipped back to `staged`, the SUPERSEDED banner stripped from each
  spec, `settled.md` and `inbox/archive/review-apparatus/review-apparatus-001.md` deleted, two
  already-dispositioned `lessons-routing` messages un-archived back into `inbox/`, and `resume_anchor.md`
  reduced to its oldest entry. ⛔ **The operational consequence is what made this urgent rather than
  cosmetic**: the queue presented ten superseded rows as emittable, so a `next` would have handed out a
  plan whose spec says "do not emit". Restored from `88fcfc9ef` after verifying that the only commits
  touching this tree after the revert were #1649/#1655/#1660, each adding exactly one `process-compliance`
  inbox message and nothing else — 27 paths, commit `13e3d2426`, `queue-view.md` regenerated rather than
  restored. (2) **Landing.** Committed and pushed on `chore/orchestrator-ledger` in the `_orchestrator`
  worktree; the branch had no upstream, so the push also published eight sibling-session commits, a trade
  the operator took explicitly. ⚠ **The revert itself is a merge-gate defect this epic does not own** — a
  squash merge from a stale branch silently reverting a newer landing, unflagged at merge, is orchestrator
  /merge-queue mechanics. `process-compliance` restored its own tree the same way (operator rule: each
  epic restores its own), so this is the second instance of the same mechanism, not an isolated accident.
- 2026-10-02 — **PLAN-PRQ-12's D1 premise refuted at HEAD; D2 is the only live deliverable.** Found while
  draining `process-compliance-002.md`/`-003.md`, which folded two further pre-fix instances of the
  chat-signal truncation into PRQ-12 (five in total). ⛔ **The root cause PRQ-12 identified has been fixed
  elsewhere**: `_chat_signal_reducer.py:406` now returns `BlockScalar(reduced_text)`, landed by PR #1646
  (`56add3faf`, 2026-09-29T16:56:43Z) with the multi-line round-trip regression test PRQ-12 D1 asked for.
  Verdict persisted on claim 2 as `contradicted` / `rescoped: yes`; D1 marked SHIPPED ELSEWHERE, D0 moot,
  D2 (the delivery-integrity lower bound plus the `transcript_undelivered` token) left live and still
  unimplemented. ⚠ **Both recurrences are PRE-FIX and neither re-opens anything** — the date ordering
  settles it: `-003.md` was filed 2026-09-29T16:59:25Z, two minutes and forty-two seconds AFTER the fix
  merged, so the run it reports cannot have exercised post-fix code. This is also the second time a
  third-party recurrence report has independently confirmed this spec's own root-cause correction while
  stating the cause as unestablished on its own evidence.
- 2026-09-17 — **Epic created, and it OWNS the subject end to end.** Operator decision at init, chosen
  over two alternatives: (a) staging only unowned aspects and leaving the subject split across three
  ledgers, and (b) a narrower retrospective-plus-audit cut. Rationale: a single ledger cannot see a
  duplicate held in another ledger, and this subject was already split three ways — the split is what let
  the same defect class (a producer publishing a confident figure over an unread population) be
  re-discovered independently in `truthful-signals`, `next-level` and `code-intelligence-substrate`.
- 2026-09-17 — **`parallelization_scope: 1`** (operator). Surface concentration, as recorded in the queue
  annotations above.
- 2026-09-17 — **Two transfers IN, and they are transfers rather than offers.** `truthful-signals`
  PLAN-TRUTH-152 → `PLAN-PRQ-01`; `next-level` PLAN-09 → `PLAN-PRQ-05`. Each source spec is retired in
  its own ledger with a pointer here, and its substance is carried in the receiving spec — not merely
  named. ⛔ **A mechanical limitation is recorded with them**: `orchestrator.py queue --transition` accepts
  only `staged|launched|running|parked|shipped|landed`, so the historical `transferred` status the ledgers
  already contain **cannot be written by the sanctioned verb**. The source rows are therefore `parked`
  with the transfer recorded in narrative. This is exactly `truthful-signals` PLAN-TRUTH-143 D9 ("the
  queue's single-row writer cannot write three statuses the ledger already holds") — first-party evidence
  for it, recorded here rather than re-staged.
- 2026-09-17 — **Reviewer-quality measurement stays with `review-apparatus`.** `finalize-step-review-retrospective`
  grades PR reviewers, and the standing three-way routing rule gives anything PR-review to that epic —
  the PR test wins outright. This epic owns the *plan-side* post-run surfaces and consumes the reviewer
  signal; it does not own it. ⚠ One seam sits exactly on that boundary and is named in PLAN-PRQ-04 rather
  than silently claimed: `review_completeness`'s `bot_states` classification has no persisted handoff an
  `order: 990` step can read, so the zero-findings grade fails closed to `indeterminate`.

- 2026-09-17 — **`lessons-capture` must be off when configured off; the mechanism is reclassification off
  the floor class.** Operator ruling, in two parts: the outcome (*"lessons capture should be off if
  configured off"*), then the mechanism, chosen from three with their blast radii stated. Rejected: a
  per-element immunity opt-out (would have changed the `ext-point-lane-element` contract every lane element
  inherits) and reclassify-plus-pinned-tier (would have preserved today's minimal-profile behaviour at the
  cost of a class declaration that no longer means what it says). ⚠ **Accepted side effect**: a non-immune
  class defaults to tier `standard`, so `lessons-capture` will also stop running under an
  `execution_profile: minimal` plan with no override at all — a change every consumer inherits on upgrade.
  PLAN-PRQ-06 D3 carries the ruling and D4 pins the side effect with a control. ⛔ The immunity rule itself
  is CORRECT and stays — it is the element's classification that was wrong.

- 2026-09-19 — **Inbox drain: 23 `PLAN-PRQ-06` messages, 13 distinct signals, all dispositioned and
  archived.** Discard (3, already tracked/owned elsewhere): orchestration-detection (this epic's own new
  Open Defect, forwarded to `truthful-signals` as `post-run-quality-001.md`); `record-dispatch-boundary`
  (`PLAN-PRQ-08`'s existing claim); agent-initiated-re-dispatch (`code-intelligence-substrate`
  `PLAN-CIS-052` D7-D10 + shipped `PLAN-CIS-035`). Fold (5): 2 into `PLAN-PRQ-02` (D3's second corrupted
  aspect; D1's second defect + new claim, the `forwarded_to_manifest` dead-letter), 3 into `PLAN-PRQ-09`
  (D4's third denominator-pollution class; two NEW claims — script-failure misclassification,
  wait-time-rollup honesty — split out to `PLAN-PRQ-11` per the scope-bloat guard rather than pushing
  PRQ-09 to 8 deliverables). Stage (1 signal → 2 specs): **`PLAN-PRQ-10`** (finalize re-fire convergence +
  self-review coverage honesty — the self-review standard's own `:222` deferral of a per-detector reach
  map is directly challenged, with the registry named that undercuts its feasibility premise) and
  **`PLAN-PRQ-11`** (spend/diagnostic-tier population miscounts, split from PRQ-09). Promote (4): new
  corpus lessons `2026-09-19-21-003`..`-006` — co-reference-population fix scoping, only/all/none
  claim-scope discipline, verify-the-gate-before-writing-the-deliverable, mock-insulates-a-boundary.
  Lesson `2026-09-19-12-001` (duplicate of the PRQ-10 payload) superseded, redirecting to PRQ-10.
  Two further residuals (executor path-scoping, executor diagnostics, phase-5-yield-reason) forwarded to
  `code-intelligence-substrate` as `post-run-quality-001.md`. ⚠ **Correction**: the live lessons corpus was
  found to be ~4-6 entries during this drain, not the 172 an earlier resume_anchor claimed — confirmed
  legitimate (860+ surviving tombstones), drained by other activity between 2026-09-18 and 2026-09-19, not
  a wipe; this epic did not cause and does not own that drain.
- 2026-09-19 — **PLAN-PRQ-06 SHIPPED** — PR #1541 (`a1dd4901f`), merged via merge queue, 10 self-review
  rounds, one real CodeRabbit fix-task loop-back (3 findings), 9.56M tokens / 34h wall / 6h10m worked.
  `landings/PLAN-PRQ-06.md` is the full reconciliation record. `emit-landing` never fired (see the new
  Open Defect below) — reconciled from the operator's paste, verified against the merge commit, PR state
  and the archived plan directory before recording anything.
- 2026-09-18 — **PLAN-PRQ-06 launched** (operator confirmation, "plan 006 started"); `staged → launched`.
- 2026-09-18 — **Inbox drain: `truthful-signals-001.md`.** Forwarded 2 lessons at the end of that epic's
  own corpus sweep. Folded lesson `2026-09-15-08-003` (oversized plan, no pre-execution anchor check) into
  `PLAN-PRQ-08` D4 — same clock as the post-merge check D4 already covered, one phase earlier — with the
  Expected Surface updated in the same act (`phase-4-plan/SKILL.md`, verified via `corpus surfaces`).
  Discarded lesson `2026-09-18-06-001` (the restored "verify a handed claim" standing rule) from further
  corpus-work consideration: `PLAN-PRQ-09` D5 already owns writing the governing clause it asks to be
  preserved as, so landing D5 resolves the tension the forwarding message raised without a second action.
- 2026-09-18 — **Cleanup A1/A4 (corpus set-verdict + duplication cross-check), `checked_at: 1605831c5`.**
  Dispatched `execution-context-level-5` to re-ground all 9 staged specs' Claim Labels against HEAD: 37
  rows, 21 corroborated / 6 contradicted / 10 unverifiable; all 36 addressable verdicts persisted (0
  blocking). Applied 5 `rescoped: yes` corrections in place (PRQ-01, PRQ-02 ×2, PRQ-03, PRQ-04, PRQ-09) —
  see each spec's Claim Labels for the verdict lines and the inline corrections. Also added PRQ-08's
  missing never-retry-`remove`-on-`not_found` guard (safety, PRQ-09 already carried it). **A4 duplication
  cross-check**: 0 within-epic duplicates (this epic's own 9 specs are mutually disjoint in subject); 4
  `source_origin_matches` are the two already-recorded, already-reconciled transfers (PRQ-01←truthful-signals,
  PRQ-05←next-level); 852 `file_overlap_matches`, the overwhelming majority against `code-intelligence-substrate`
  plans that are already `shipped` (moot — historical surface, not a live collision) or against broad
  recursive test-mirror globs (`test/plan-marshall/plan-retrospective/**` etc., structural over-declaration
  noise per the gate's own documented residual-error classes) — no new supersede action warranted. One
  live, modest overlap worth a Watch: `code-intelligence-substrate` `PLAN-CIS-050` (staged, 14
  deliverables) shares several `plan-retrospective` scripts with PRQ-01; different epic's business, noted
  rather than resolved here.
- 2026-09-17 — **WS-05 / PLAN-PRQ-07 added: cross-repo telemetry, folded into this epic rather than split
  into a new one.** Operator-directed addendum: a new `plan-marshall-telemetry` repo, its `transfer` and
  `analyze` project-level skills, a new `analyze-marshall-quality` finalize step here, and relocating
  `.claude/skills/audit-archived-plan-retrospectives` into the telemetry repo. Two placement questions were
  put to the operator and both were answered: (1) new epic vs. new workstream here — **workstream**, on the
  thematic overlap (this epic already owns "everything this project does to judge a run after it has
  finished"); (2) one plan vs. two (repo+transfer, then analyze+finalize+migration) — **one plan**, kept
  under the ~6-deliverable split guard at 5 deliverables. ⛔ PRQ-07 carries a hard sequencing dependency on
  PRQ-01 and PRQ-03 (both edit the skill PRQ-07 relocates) recorded in its own spec and in the queue
  annotations above — this is NOT a mere disjointness overlap the `next` gate would otherwise catch on its
  own, since PRQ-01/03 sit in WS-01/WS-02 and the gate reasons per-surface, not per-dependency-chain.

- 2026-09-17 — **Lessons-corpus sweep: 16 candidate lessons analyzed against this epic's scope.** 8 moved
  into `archive/lessons/{id}.md` and incorporated into Open Defects (below); 2 removed outright as
  duplicates of already-staged PLAN-PRQ-02 deliverables (D2, D3); 6 left untouched — their subject is
  `review-apparatus` (reviewer-quality metrics, review-pipeline carry-forward discipline) or fleet-wide
  orchestrator mechanics (spec staleness, inbox-detect argparse), not this epic's. All 10 removed lessons
  carry a `completely_covered` tombstone in `.plan/local/lessons-learned/.tombstones/` pointing back at
  either the archive copy or the covering PRQ-02 deliverable. Two corpus entries (`2026-09-08-22-006/-007`)
  surfaced a `list`/`get` inconsistency and were deliberately left untouched — see Watches.

- 2026-09-21 — **Cleanup pass 2 (restart preparation), `checked_at: e8a71650`.** Dispatched A1
  corroboration across the 10 non-`PLAN-PRQ-02` specs (that one excluded — actively launched/running).
  22 claims corroborated (19/3 corroborated/contradicted), 0 blocking. Five specs corrected in place:
  `PLAN-PRQ-01` (restored the source's hard `PLAN-TRUTH-146` dependency and a dropped Expected Surface
  glob, both softened/lost at the 2026-09-17 transfer), `PLAN-PRQ-05` (corpus size has moved ~5× since
  staging — flagged as must-re-derive, not trust; `PLAN-TRUTH-144` moved `staged → RUNNING`, hardened
  from a theoretical collision to a live block), `PLAN-PRQ-07` (wrong citation for the archived-plans
  layout), `PLAN-PRQ-10` (registry population corrected from 5 to 6 content classes; D1 narrowed to two
  of its three proposed shapes, the third refused by the finalize-step facts contract; D0(b)'s Expected
  Surface pointed at the wrong file for `CANDIDATE_LISTS`; three more cross-epic collisions declared —
  `truthful-signals` `PLAN-TRUTH-173`/`-167` and `review-apparatus` `PLAN-PR-074`, all staged, all
  touching the same self-review files no single gate can see across three ledgers), `PLAN-PRQ-11` (D1's
  premise materially refuted — the partition it proposed to add already exists in the classifier; narrowed
  to publishing it plus one further subtype split). A4: 0 new within-epic duplicates; one missing overlap
  note added to `PLAN-PRQ-11`. This is the SECOND time a corroboration pass has found and corrected a
  transfer-softened dependency and a dropped Expected Surface entry (`PLAN-PRQ-01`) — worth naming as a
  pattern: a spec TRANSFER is not merely a copy, and each one needs its own re-grounding pass rather than
  being trusted as verbatim.

- 2026-09-21 — **Ledger store relocated to a tracked address; PLAN-PRQ-02 landed and reconciled.**
  `orchestrator-refactor` PLAN-01 (PR #1557/#1558, landed on `main` ahead of this reconciliation) moved
  the orchestrator store from the git-ignored `.plan/local/orchestrator/{slug}/` to the git-tracked
  `.plan/orchestrator/{slug}/` — this epic's canonical tree is now version-controlled. The migration
  landed from a snapshot taken BEFORE cleanup pass 2 completed, so this epic's tracked copy briefly
  diverged from the pass-2-complete content that remained only in the old, now-orphaned local path;
  reconciled here by porting every pass-2 correction (specs `PLAN-PRQ-01/03/05/07/10/11`, this Decisions
  entry) into the tracked tree and updating every spec's `Hand-Off Command` path to drop the `local`
  segment. `PLAN-PRQ-02` (retrospective-aspects-publish-verdict, PR #1550) shipped in the same window;
  its landing (`landings/PLAN-PRQ-02.md`) and inbox drain are reconciled in this same pass — see the
  landing record for the 9-message disposition. This reconciliation itself runs inside a worktree on
  branch `chore/post-run-quality-ledger-relocation`, landed via its own PR with bot review skipped (a
  ledger-only relocation, not reviewable content) — the pattern PLAN-01 itself established for its own
  landing. The old `.plan/local/orchestrator/post-run-quality/` tree is now ORPHANED — do not read or
  write it going forward.

- 2026-09-26 — **THE WHOLE STAGED QUEUE IS PARKED — superseded by PM-MCP.** Inbox `review-apparatus-001.md`
  (rev 1, relaying a binding operator ruling): `plan-marshall-mcp` replaces both the Python scripts and the
  process prose, so every Python- or prose-bound plan is legacy work. All 10 staged rows (`PLAN-PRQ-01`, `-03`,
  `-04`, `-05`, `-07`, `-08`, `-09`, `-10`, `-11`, `-12`) were classified per deliverable by four read-only
  sub-agents and mapped against PM-MCP `7e13ea1`: **148 rows, 116 carry, 32 none; 52 gap, 58 partial, 6
  covered; 14 contradictions** (6 hard, 5 tensions, 3 weak/internal — e.g. assessments merged into findings,
  `FIX|SUPPRESS|ACCEPT` losing "refuted", a clean delta self-review round allowed to close, the retrospective
  ordered before `record-metrics`). Counts re-derived from the filed tables. **No emission exception applied**
  to any spec (no foreign-repo config, no coexistence enabler, no delivery-breaking defect). Filed as
  `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md` (the one
  operator-authorized write there; NOT committed — the operator commits it). No copy kept in this tree. Each
  spec carries a SUPERSEDED BY PM-MCP banner; bodies intact as the evidence chain. Un-park only by explicit
  operator decision. ⚠ The message's coexistence framing (`co-exist.lock`, cross-runtime `flock`) is refuted by
  PM-MCP itself: PM-MIG-2 is a hard per-machine cutover and PM-MIG-3 needs no cross-runtime locking
  (`11-migration.adoc:16/25/37`); recorded in the carry-over intro.
- 2026-09-26 — **Inbox `lessons-routing-001.md` → discarded.** Lead verified: `2026-09-21-10-008` was promoted
  by `truthful-signals` (2026-09-21) and re-promoted here as `2026-09-22-08-003` (2026-09-22), which tombstoned
  the original — the corpus holds one copy, so no live duplicate. Rule carried as Part B row 1 of the carry-over.
- 2026-09-26 — **Inbox `lessons-routing-002.md` → discarded.** `scope_creep_check` / `scope_creep_warning` is
  owned by `truthful-signals` PLAN-TRUTH-178 (parked, superseded) and already carried as its 178.D0; recorded
  here as a `none (dup)` row.

## Open Defects

- ✅ **RESOLVED 2026-10-07 — both inbox defects fixed and merged as PR #1700 (`78ba60f41`); issue
  [#1697](https://github.com/cuioss/plan-marshall/issues/1697) is closed.** ⚠ **Verified behaviourally on
  this epic's own queue, not from the landing report** — which is the right test, because this epic's
  inbox is the exact state both defects were found in.
  - **Closure now survives the drain.** `inbox list` reports `count: 0`, `live_count: 0` and
    `closed_senders: [cross-repo-telemetry-archive-and-analyze]` — the sender is named **with its marker
    archived**, where before the fix this read `closed_senders: []`. The FINISHED zero is reachable after a
    complete drain, which is precisely what the issue said was impossible. ⭐ **The fix also added a
    coverage discriminator nobody asked for**: `archive_readable: true`, so an archive that could not be
    scanned can never masquerade as *"no closed senders"* — the honest-zero discipline applied to the fix
    itself.
  - **`restart-check` now names the zero, not just the count.** Its inbox row reads
    `ready, "FINISHED: 1 sender(s) closed (cross-repo-telemetry-archive-and-analyze) with no live
    message", "inbox/: 0 live of 0 total and 1 closed and 0 invalid"`. ⭐ **That exceeds the remedy the
    issue proposed** — it was asked to score on `live_count` and report the neighbours; it reports the
    state by its vocabulary word with the whole population spelled out.
  ⚠ **One observation from the fixing run, recorded as an instance rather than a complaint**: its own
  `record-metrics` step reported **`40h31m / 0 tokens`** with every phase blank in the Phase Breakdown. A
  measured `0` over an unread population — the founding defect of this epic — in the run that fixed two
  instances of it. Exactly what `PLAN-PRQ-13`'s reports would classify `not_measured` rather than zero.
  ⚠ The run also filed 4 `process-compliance` findings (`issue-1697-001`..`-004`), **including one against
  itself** for holding the merge lock across operator waits. Found by draining this epic's last message. Before the
  drain the queue read `live_count: 0` with `closed_senders: [cross-repo-telemetry-archive-and-analyze]` —
  the **FINISHED** zero, meaning *that sender will send no more*. Archiving the marker, which is exactly
  what the drain contract prescribes for a `stream-end` row, moved it to `count: 0` with
  `closed_senders: []` — the **EMPTY** zero, which asserts *a later message is still possible*. ⛔ **So a
  closure declaration is either queued-and-undrained or archived-and-no-longer-declaring; there is no
  state in which it is both recorded and consumed.** The envelope doc states the mechanism ("a marker the
  drain has already archived no longer closes the stream") without naming the consequence: a drained queue
  **cannot** report FINISHED, so the three-zero vocabulary's middle value is unreachable after any complete
  drain. ⚠ Harmless for this instance — the sender is a landed, archived plan that can never write — but it
  means `inbox write` would no longer refuse that sender with `stream_closed`. ⇒ **Not owned here**;
  `plan-orchestrator` inbox mechanics, same family as the two defects below.
- ✅ **RESOLVED 2026-10-07 by PR #1700 — see the entry above for the verified behaviour.** The account
  below is retained as the evidence trail: it is how the defect was found, and it carries the warning that
  the green verdict after the 2026-10-05 drain was **not** resolution — which remained true for two days,
  until the signal itself was fixed. ⛔ **The original entry read:** `cleanup restart-check`'s inbox signal
  reads `count`, not `live_count`, so a stream-end marker holds an epic at `not_ready` forever. ⚠ **STILL
  REAL after the 2026-10-05 drain, and the drain did not fix it.** Archiving the marker cleared the *instance* — the verdict is now `ready` with
  `inbox: 0 queued and 51 archived` — but the defect is in the signal, not in the queue: any `stream-end`
  marker filed and not yet drained will hold its epic at `not_ready` again, and a FINISHED queue is by
  definition one that still holds its marker. ⛔ **Do not read the green verdict as this defect being
  resolved.** Found by this epic's own cleanup pass:
  `restart-check` returns `verdict: not_ready` on a single signal — *"1 message(s) still queued"* — and that
  message is the `lifecycle=stream-end` marker filed on the landed `cross-repo-telemetry-archive-and-analyze`
  plan's behalf. `inbox list` reports the same queue as `count: 1, live_count: 0, closed_senders: [that
  sender]` — the **FINISHED** zero. ⭐ **So the readiness instrument cannot tell which zero it is looking
  at**, which is this epic's founding subject reproduced in the instrument that grades restart-readiness.
  ⛔ **The marker was NOT archived to clear the signal.** Archiving it would delete the closure record —
  the inbox contract is explicit that a marker the drain has archived no longer closes the stream — and
  gaming a readiness signal by removing the thing it misreads is precisely the move this epic exists to
  catch. The `not_ready` verdict therefore stands, honestly, on a defect in the signal rather than on
  unfinished work. ⇒ **Not owned here** — `plan-orchestrator` mechanics, in the same family as the
  `registry_parity` row that already reports `not_available` and names another spec as its owner. Small and
  concrete: read `live_count` and `closed_senders` instead of `count`.
- ⛔ **NEW 2026-10-04 — two parked specs now point at code this repository no longer contains, and one of
  them is 80% stranded.** `OBSERVED` from `corpus surfaces` after PRQ-07's relocation landed:
  **`PLAN-PRQ-03`** declares 5 paths and **4 of them are gone** — the whole
  `audit-archived-plan-retrospectives` tree plus its test mirror moved to the telemetry repo with PR #1694
  — leaving only `.claude/skills/recipe-plan-review/SKILL.md`. **`PLAN-PRQ-01`** has 4 of its 21 paths in
  the same moved tree. ⚠ **Neither is a spec-authoring error**: both declared correctly when staged, and
  PRQ-07 moved the ground under them. ⛔ **What makes this more than bookkeeping**: PRQ-03's subject is the
  **suspect-zero census excluding itself from its own population** — the detector-inside-its-own-population
  failure, which the auditor's own SKILL.md states outright — and that instrument now lives in a
  repository where this epic stages nothing. ⇒ **Partly addressed, not owned**: `PLAN-PRQ-13` inherits the
  census defect as a binding constraint on its own reports (its reports cover a corpus containing the
  subjects that produced them, so it sits in the same blast radius), and explicitly declines PRQ-03's other
  half — `recipe-plan-review` persisting nothing. Re-pointing PRQ-01 and PRQ-03 themselves is **not** done:
  they are parked, and re-scoping a parked spec onto another repository is a decision about the PM-MCP
  carry-over, not a reconciliation.
- ✅ **RESOLVED 2026-10-04 — `PLAN-PRQ-13` emitted, gate overridden on a stated basis, and my own
  characterisation of it corrected.** ⛔ **The correction first, because it is the substantive part:** I
  told the operator this was a *weaker* override case than PRQ-07's, on the strength of the ~45 overlap-row
  count. Separating the rows by class shows it is **comparable, and arguably safer**. PRQ-07 also carried a
  large sibling-epic-spec volume (186 rows) with zero live-plan overlaps and in-corpus overlaps only against
  parked or shipped siblings; PRQ-13 has **zero** live-plan rows, **one** in-corpus row (`PLAN-PRQ-01`,
  parked), and ~40 sibling-ledger rows. ⭐ **The real difference runs the other way**: every PRQ-13 overlap
  is driven by ONE declared path, `manage-findings`, which the spec declares a HYPOTHESIS — so if it
  resolves false the in-repo surface is **empty** and the collisions do not exist. PRQ-07's surface was
  unconditional. A row count compared across two candidates without separating its classes is exactly the
  under-derived figure this epic exists to catch, and I published one. ⇒ The emitted spec carries the
  override, its basis, and a concrete obligation: settle the `manage-findings` hypothesis at D0/outline
  before touching that file, and re-check the live plan set if it resolves true.
- ⚠ **SUPERSEDED by the entry above — the original gate-refusal record for `PLAN-PRQ-13`.** `candidate_comparison_determinate: false` again (96 sibling-epic specs and 3 live plans
  declare no comparable surface), so the test fails closed. ⛔ **But unlike PRQ-07, PRQ-13 DOES have overlap
  rows** — roughly 45 of them, including `PLAN-PRQ-01` in this corpus and ~40 sibling-epic specs across
  `review-apparatus`, `truthful-signals` and others. ⭐ **Every one of them is driven by a single path**,
  `manage-findings`, which PRQ-13 declares as a **HYPOTHESIS** — it is only in scope if D4's three new
  mechanisms need a producer-side vocabulary change rather than reading-side classification. The other four
  declared entries are `plan-marshall-telemetry/` paths the parser reports as **unresolved** (4 unresolved
  spans, 1 resolved path), because they are outside this repository. So the honest statement is: *if the
  hypothesis resolves false, this plan has no in-repo surface and collides with nothing; if it resolves
  true, it joins a crowded file.* The gate cannot express a conditional surface. ⇒ Emit decision is the
  operator's; D0 and outline settle the hypothesis either way.
- ✅ **RESOLVED 2026-10-02 — #1641 reverted this epic's ledger state.** Filed as
  `process-compliance-001.md` (2026-09-28), corroborated first-party and repaired the same session; the
  full account is the 2026-10-02 Decisions entry. Retained as the record of why `settled.md`,
  `inbox/archive/review-apparatus/review-apparatus-001.md` and the ten SUPERSEDED banners have a
  restore commit (`13e3d2426`) in their history rather than a continuous one. ⇒ **The mechanism remains
  unowned by this epic**: a stale-branch squash merge silently reverting a newer landing, unflagged at the
  merge gate, is orchestrator/merge-queue mechanics. Second observed instance (`process-compliance`
  restored its own tree the same way), so it is a recurring class, not an accident.
- **2026-09-26 — Whole queue parked (see Decisions).** Every row but the two shipped ones is `parked`; nothing
  is emittable. The Open Defects below are now each owned by a parked spec, i.e. by the PM-MCP carry-over, not
  by pending plan-marshall work.
- **The census does not census itself.** `audit-archived-plan-retrospectives` SKILL.md:231-236 states it
  outright — the suspect-zero census is excluded from its own population, "the detector-inside-its-own-
  population failure mode, standing unresolved in the instrument built to surface it." — source: inventory
  sweep 2026-09-17. ⇒ Owned by PLAN-PRQ-03.
- **Deterministic computation sited in retrospective reference prose instead of a script.** Filed 2026-09-21
  (inbox `retrospective-aspects-publish-verdict-007.md`, actions #1/#2 — action #3 already folded into
  `PLAN-PRQ-09` D4). Two members: (1) `references/plan-efficiency.md` Sections 1-2 compute four ratios
  against a 35-row static anchor table entirely in prose, with three separate arithmetic-hazard warnings
  (ms-vs-seconds, string-typed plan-level keys silently defeating `max(denominator, 1)`, numerator must be
  worked not wall time) that exist only because the computation lives in a doc instead of code; (2)
  `request-result-alignment`'s scope-creep set-difference re-derives by hand what `manage-references`
  already ships as a three-way (declaration/structured-derivation/realized-footprint) reconciliation — on
  this run the hand computation and the existing reconciliation returned different-but-both-correct figures
  (8 vs 10 creep paths) for a legitimate reason (differing read-intent declarations), which is exactly the
  second-producer risk `plan-efficiency.md` itself warns against for denominators. ⇒ **Unowned** — the
  filing message itself frames this as lower priority than its action #3; no spec staged.
- ✅ **RESOLVED-AS-REFUTED 2026-09-17, and re-staged on its true mechanism as `PLAN-PRQ-06`** (operator
  reported the same observation independently; analyzed the same day). The entry as filed read: *"either
  the lane resolution does not drop a non-ceremony step at `off`, or the landing's step list is not
  derived from the composed manifest."* ⛔ **BOTH readings are refuted**, and the refuting evidence is
  retained here per the standing convention:
  - `_manifest_lanes.py:171-172` + `:37` — an `off` on a `core` / `derived-state` element is **immune by
    contract**, documented in `ext-point-lane-element.md:50-51, 70, 90`. `lessons-capture` declares
    `lane.class: core`, the same class as `push` / `create-pr` / `branch-cleanup`.
  - The archived plan's `execution.toon` composed the step (lines 33, 84, 118) and recorded it `executed`
    (line 158); its `logs/decision.log` entry `4a5900` carries the neutralization warning verbatim. **The
    landing told the truth.**
  ⇒ The real defect is that the neutralization is invisible to the operator — both config writers validate
  the lane value space and never read the element's class, and the one honest record is a compose-time log
  line inside a plan directory that is then archived. Owned by **PLAN-PRQ-06**.
  ✅ **SHIPPED 2026-09-19, PR #1541 (`a1dd4901f`).** All 7 deliverables (D0-D4, D3a, D2a) landed —
  write-side refusal, read-side surfacing, `lessons-capture` reclassified `core → prunable` (the
  2026-09-17 operator ruling), and the manifest now carries the effective lane with the requested value
  preserved separately. See `landings/PLAN-PRQ-06.md` for the full reconciliation.
- ⛔ **NEW 2026-09-19 — orchestration detection fails open for a plan with no `source_id`.** Confirmed
  first-party on `PLAN-PRQ-06`'s own landing: its `request.md` carries no `source_id` section, so whatever
  detector `emit-landing` consults for the orchestration verdict answered a confident "not orchestrated"
  rather than "indeterminate" — `emit-landing` never fired, and this epic never received its landing
  notification. 23 messages (10 retrospective-lesson observations + 13 lessons-capture findings) had to be
  filed to this epic's inbox manually as a workaround. Same shape as corpus lesson `2026-09-09-06-001`
  ("orchestrator inbox detect cannot be called for a plan with no source_id, which is every
  description-sourced plan"), which the 2026-09-17/18 lessons sweep correctly excluded as fleet-wide
  orchestrator-mechanics — this entry is NOT a reversal of that call, it is a second, costlier instance of
  the same excluded defect, recorded here because it directly hit this epic's own pipeline. ⇒ **Unowned by
  this epic** — the fix belongs wherever orchestrator-platform mechanics live (`truthful-signals`, on
  precedent), not staged here.
- **An obligation that outlives its plan has no owner.** `truthful-signals` epic.md records four owed
  `architecture enrich insight` calls whose owning plan was archived before they were issued, against a
  git-TRACKED file — "the obligation has no owner" — and a deferred `marshalld` reconcile marked
  `owed: true` that nothing re-checks. — source: `truthful-signals` epic.md D-087-e / D-087-f. ⇒ Owned by
  PLAN-PRQ-04.
- **`recipe-plan-review` persists nothing.** An LLM-only request-vs-landed re-check whose result exists
  only in the session that ran it, so no corpus question can ever be asked of it. — source: inventory
  sweep. ⇒ Owned by PLAN-PRQ-03 D0's population.
- **No mechanical achieved-thoroughness measurement exists** (`plan-retrospective/SKILL.md:215`) — the
  achieved side of coverage is a floor-graded self-report. — source: inventory sweep. ⇒ Unowned; candidate
  for a later PRQ spec, deliberately not folded into PLAN-PRQ-01 to keep its 11 carried deliverables from
  growing.

### Moved in from the global lessons corpus (2026-09-17)

> ⛔ **RECONCILED 2026-09-17 after a concurrent-session collision.** Two orchestrator sessions swept the
> corpus against this epic at the same time. The entries below were written by one of them; the other
> staged `PLAN-PRQ-08` / `PLAN-PRQ-09` and consolidated the archive. **Each entry now names its owning
> spec** — per this document's own contract, a defect folded into a plan spec is owned there and is no
> longer an unowned Open Defect:
>
> - handed-claim restated as fact (`2026-08-27-16-003`) ⇒ **PLAN-PRQ-09 D5**
> - producerless `SECTION_SPEC` row (`2026-08-31-09-001`) ⇒ **PLAN-PRQ-09 D3**
> - `affected_files_recall` denominator (`2026-09-03-23-004`) ⇒ **PLAN-PRQ-09 D4**
> - plan-level recall hides a 67% deliverable (`2026-09-05-07-006`) ⇒ **PLAN-PRQ-09 D4**
> - footprint resolver has no landed-commit tier (`2026-09-04-08-004`) ⇒ **PLAN-PRQ-02 D1**
> - lesson-creation Gate 2 blind population (`2026-09-03-23-006`) ⇒ **PLAN-PRQ-05**
> - manifest order inverted (`2026-09-04-08-001`) and the deep-lane assessment gap ⇒ ⚠ **still unowned**;
>   both are the other session's classification and neither is folded into a spec yet.
>
> The full disposition table, including which session retired which lesson and under which verdict, is
> `lessons/README.md`.

Eight lessons analyzed against this epic's scope, moved into `archive/lessons/{id}.md` (this epic's own
tree), incorporated below, and tombstoned in the global corpus as `completely_covered` pointing back here.
Two further lessons (`2026-09-04-08-003`, `2026-09-13-20-004`) were duplicates of already-staged
deliverables and were tombstoned directly without an archive copy — see the tombstones at
`.plan/local/lessons-learned/.tombstones/` for their covering clauses. Six other candidates that matched on
keyword but not on subject (reviewer-quality metrics, qgate reopen, orchestrator-mechanics bugs) were left
untouched in the corpus — their territory is `review-apparatus` or fleet-wide orchestrator mechanics, not
this epic's.

- **A defect claim handed to a retrospective is restated as fact without verification.** A dispatch-context
  claim asserted the lessons corpus was filing body-less stubs; a one-call census refuted it (6 of 6
  lessons carried full bodies). Standing rule: treat a supplied defect claim as a hypothesis with a named
  verification, never as a finding — derive a set property, don't restate it. — source:
  `archive/lessons/2026-08-27-16-003.md` (also `lessons/2026-08-27-16-003.md` in the peer session's
  consolidated archive). ⇒ Owned two ways, not in conflict: **PLAN-PRQ-09 D5** carries the defect half
  (verify before filing), and the standing rule itself was **RESTORED to the live lessons corpus as
  `2026-09-18-06-001`** by the peer session with operator approval — it is agent-facing guidance, not a
  work item, so it belongs where sessions recall it rather than only in a staged spec. My original
  `completely_covered` retirement of `2026-08-27-16-003` is superseded by that restoration; see
  `lessons/README.md` for the full record, including the peer's flag that my ten `completely_covered`
  tombstones (this one and nine siblings below) assert the rule now lives in a codified clause when in
  fact it lives in a staged, not-yet-implemented spec — a fair correction I cannot retract (no tombstone
  edit path exists) but record here so it is not read as settled coverage.
- **A producerless `SECTION_SPEC` row is an operator proposal, not an in-plan decision.** When a
  `plan-retrospective` row's renderer is live but its producer does not exist, record both options
  (register vs. delete) with a recommendation and escalate — deciding it in-plan silently settles an
  architecture question (whether the compiler stays a pure assembler) as a side effect. Observed twice
  (`_executive-summary`, `dispatch_boundaries`); both escaped four self-review rounds and 42/42 mutation
  kills because the row reads as benign in every report. — source: `archive/lessons/2026-08-31-09-001.md`.
  ⇒ Governance constraint on PLAN-PRQ-02 D0: if D0's 16-aspect sweep finds a producerless row, escalate it,
  don't fix it in-plan.
- **`affected_files_recall`'s denominator excludes read-intent only, not delete-intent or foreign-checkout
  declarations.** A plan that correctly deleted a file or wrote to another repository is scored down for
  it — `recall_pct: 89.5` on a plan whose per-deliverable coverage was 96-100%. The by-construction argument
  `request-result-alignment.md` already states for the read case applies verbatim to the other two classes
  but was never generalised. — source: `archive/lessons/2026-09-03-23-004.md`. ⇒ Feeds PLAN-PRQ-02 D0 as a
  fourth population-denominator instance (alongside D1-D3).
- **Plan-level `affected_files_recall` hides a deliverable that shipped two thirds of its declared sites.**
  The check unions every deliverable's declared surface, so one deliverable at 67% (the one whose title
  asserted completeness) is invisible inside a plan-level 86%. Real cost: a same-day follow-up commit was
  needed post-merge. — source: `archive/lessons/2026-09-05-07-006.md`. ⇒ Feeds PLAN-PRQ-02 D0 as a fifth
  instance (granularity, not exclusion-class).
- **The composed manifest ran `plan-retrospective` (order 995) before `lessons-capture` (order 991), so the
  once-per-run orchestration verdict was never resolved before its first consumer.** Verified three ways
  (declared frontmatter order, the composed manifest's actual step order, the execution log). Root cause
  located at compose time but NOT established — two leads named, neither tested. — source:
  `archive/lessons/2026-09-04-08-001.md`. ⇒ **Unowned** — new defect, not covered by any staged PRQ. A
  candidate for a future PRQ spec or a PLAN-PRQ-04 D0 population member (it is an obligation-adjacent
  ordering defect, but the mechanism is orchestration compose, not archival).
- **The footprint resolver has no landed-commit tier, so a post-merge or archived-plan retrospective cannot
  resolve a footprint once the worktree is gone.** `branch-cleanup` destroys the resolver's only evidence
  source before `plan-retrospective` runs; every `RESOLVING_TIERS` member is worktree-bound. Proposed fix:
  add a tier that diffs the merge commit against its first parent. — source:
  `archive/lessons/2026-09-04-08-004.md`. ⇒ Cross-referenced from PLAN-PRQ-02 D1 (same resolver file,
  `_cmd_compute_footprint.py`) **and** PLAN-PRQ-07 (the telemetry `analyze` engine needs this exact tier to
  measure archived plans whose worktree has been gone for months — this lesson is the first-party evidence
  that the gap is real and already load-bearing on live plans, not merely a future concern for PRQ-07).
- **The deep planning lane records no per-file assessments, so `outline-vs-shipped` measures against an
  empty denominator.** A 12-deliverable, 100 KB deep-lane outline left `assessments_store_present: false`;
  the aspect degraded honestly (published its zero denominators) rather than faking a pass, which is why
  this is a measurement gap rather than a false green. — source: `archive/lessons/2026-09-15-08-007.md`.
  ⚠ **POSSIBLE DUPLICATE of PLAN-PRQ-01 D8 ("Close the outline write-back gap")** — verify-at-outline
  whether D8 already subsumes the write-back-never-happens case before treating this as separate work.
- **Gate 2 of lesson creation cannot read a worktree-resident plan's scope from the main checkout, so it
  silently under-covers.** `manage-plan-documents request read` (unlike `manage-findings`'s five read
  verbs) has no `--any-checkout` fallback, so Gate 2's covering-plan check ran against 2 of 5 active plans
  on first observation and 2 of 6 on a ten-day-later recurrence — unfixed and reproducing identically. The
  recurrence adds a sharper finding: the failing call's `suggestions[]` recommend creating a duplicate
  request document that already exists in the other checkout. — source:
  `archive/lessons/2026-09-03-23-006.md`. ⇒ New candidate deliverable for PLAN-PRQ-05 (lessons corpus
  provenance and quality) — Gate 2 is exactly the epic's own "verdict over an unread population" archetype,
  applied to the lessons corpus's own filing gate.

## Watches

- ✅ **RESOLVED 2026-10-05 — the reports have now run in anger, on two projects, and the run vindicated the
  Watch.** Verified first-party in the telemetry repo: `bcd0da5` transferred **70 archived plans and 16
  orchestrator records**, `83d1e93` committed the first fully-adjudicated reports, and `reports/` now holds
  both `plan-marshall` and `cui-http`, each with a `project-report.adoc` plus monthly variants. ⛔⛔ **The
  first real run found false measured zeros that 924 green tests did not**: `eab509f` records that a
  recorder placeholder `total_tokens: 0` is no figure — **11 plans carried a measured 0** — and that
  `main_context_tokens` must be `not_measured` with no phase figure and a floor when a phase is
  unclassified — **45 plans carried a measured 0**. ⭐ **This is the strongest single argument this epic has
  produced**: the reports shipped with the exact defect class the epic exists to eliminate, their own test
  suite could not see it, and only real data exposed it. A fixture corpus cannot contain the shapes a real
  corpus has.
- ✅ **RESOLVED 2026-10-05 (operator) — the `.adoc` has been read.** ⚠ **Closed on the operator's word, and
  that is the right evidence here**: the question was never whether the file exists (it does, 8 of them)
  but whether a human had seen it rendered, and only the operator can answer that. No renderer is recorded
  in the repo, so this is operator-confirmed rather than first-party-verified, and the ledger says so.
- ✅ **RESOLVED 2026-10-05 — the tokens zero-floor is fixed**, by `eab509f` above, with the affected
  populations named (11 and 45 plans) rather than merely asserted. It was the third rediscovery of this
  shape; it did not need a third plan.
- ⚠ **Every plan's finding severity band is `not_measured`, and that is the mechanism working.** The Sonar
  collapse destroyed the `critical`-versus-`major` distinction at ingestion, so no historical plan can ever
  carry a band. `PLAN-PRQ-14` item 3 fixes it **forward only** — and even after it lands, bands appear only
  for plans that run through the fixed producer. ⛔ A corpus-wide `critical: 0` is therefore *never* good
  news on this corpus; it is the honest zero. — retire when PRQ-14 lands AND a plan has run through it.
- ⚠ **Lines-changed counts only the source project's PRs.** Work landing in another repository is excluded,
  so a cross-repo plan under-reports and `PLAN-PRQ-13` itself reports nothing at all, since every line it
  wrote was in the telemetry repo. ⭐ **This is `PLAN-PRQ-09`'s folded resolver recurrence reproduced in the
  new instrument** — the same out-of-repo blind spot, in the tool built to measure the tool that had it.
  Not a regression and not owned here: PRQ-09 is parked, and the new instrument inherited the limitation
  rather than introducing it. — re-check if the telemetry engine ever gains a multi-repo footprint tier.
- ⚠ **Every `quality-chain` reading of this corpus taken before `5546bde` overstated actionable chain
  debt.** All 820 `assessments.jsonl` records were counted as findings; on `PLAN-PRQ-07` that was 255 of
  255 "actionable pending" items. ⛔ **Re-derive rather than cite** any chain-debt figure from an earlier
  run — including figures quoted in this epic's own earlier landing records. — no re-check owed; a standing
  caveat on historical readings.
- ⚠ **The telemetry repo's branch protection is still unconfirmed.** `PLAN-PRQ-13` could not settle it; the
  absent `.github/` is consistent with main-only but does not establish the protection setting. Low stakes
  — the README declares the policy and the repo has no PR workflow — but it remains an asserted rather than
  observed fact. — re-check opportunistically via a `ci repo` read or the operator.
- ✅ **RESOLVED 2026-10-04 (operator) — and this Watch named the WRONG REPOSITORY, which is the part worth
  keeping.** The durable finding stands: `plan-marshall:automatic-review` `lane: off` only stops *reading*
  results and is **not a bot off-switch**, so opting out of the lane and disabling a bot are different acts.
  ⛔ **What this Watch got wrong**: it proposed disabling CodeRabbit, Sourcery and cuioss-review-bot for
  `cuioss/plan-marshall`. The operator's ruling is the opposite — *"do not change anything related in this
  repo (plan-marshall). There the bots are correct."* Disabling was only ever wanted in
  **`cuioss/plan-marshall-telemetry`**, and it is **done**: CodeRabbit via that repo's `.coderabbit.yaml`
  (`reviews.auto_review.enabled: false`, commit `b403805`), Sourcery via the operator's dashboard, and
  `cuioss-review-bot` never ran there for want of a `.github/` tree. ⚠ **Recorded as operator-confirmed,
  not independently verified** — a GitHub App's installation state is not readable through the CI
  abstraction from here; the `.coderabbit.yaml` is. ⛔ **The standing rule is untouched and still binds:
  CodeRabbit is a required reviewer in `plan-marshall` and must never be moved to `optional_bots` to clear
  a blocked merge gate.** ⇒ The lesson for this epic is about its own practice, not the bots: an owed item
  carried a target repository it had never checked, and it was restated twice — including in a resume
  anchor as "overdue" — before anyone corrected it. **Name the repository a change targets before
  proposing it.**
- ⚠ **CodeRabbit's `**Actionable comments posted: N**` summary may be counted as an actionable comment.**
  Reported by PRQ-07's `review-retrospective` as a possible defect — the leading bold markers appear to
  defeat the registry's starts-with summary pattern, so every CodeRabbit review would inflate its own
  actionable count by one. ⛔ **NOT verified by this epic** — recorded as the sender's lead, forwarded to
  `review-apparatus` with that caveat stated. If real it biases every reviewer-quality comparison, which is
  `review-apparatus`'s headline metric.
- ⚠ **`code-intelligence-substrate`'s five specs now declare a surface this repository no longer contains.**
  `PLAN-CIS-036/050/052/054/056` declare `.claude/skills/audit-archived-plan-retrospectives/**` and its test
  mirror; PRQ-07 relocated both out of this repo on 2026-10-03. Nothing collided, because nothing was in
  flight — but nothing serialized it either, so that was luck. Their own epic owns re-grounding them. This
  Watch is **kept, not retired**: it is the live residue of a disjointness gate that was overridden rather
  than passed, and it is first-party evidence for the cross-ledger blind spot this epic exists to name.
- ⚠ **The PM-MCP carry-over now carries at least one stale defect, and this epic cannot see it.**
  `plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md` extracted the whole parked corpus on
  2026-09-26. PLAN-PRQ-12's D1 was fixed in this repository on 2026-09-29 (PR #1646), so whatever the
  carry-over says about it is three days out of date — and the same exposure applies to every other carried
  row: the document is a snapshot of premises that keep moving in the repo it was extracted FROM. ⛔ **No
  checkout of `plan-marshall-mcp` exists on this machine**, so this is recorded as unverifiable rather than
  as confirmed-stale (ADR-019: a population that could not be reached is not a finding). — re-check when a
  `plan-marshall-mcp` checkout is available; at minimum the carry-over needs a re-grounding pass against
  this repo's HEAD before PM-MCP implements from it, and that pass is the natural precondition for `close`.
- **CI-wait behaviour needs an operator call, not a fold.** From the 2026-09-19 inbox drain:
  `ci_complete_precondition`'s early-negative return path (return immediately when the precondition
  cannot possibly resolve — no run started, SHA mismatch) and its ~600s poll budgets (95%+ of the harness
  ceiling) are `phase-6-finalize`/CI-behaviour changes, not post-run measurement — outside this epic's
  territory, and the standing PR/CI routing rule does not cleanly decide an owner. Neither staged nor
  forwarded; recorded here pending an operator decision on where it belongs.
- **Post-run verification is an operator option, not a precondition.** `doc/analyzis-cloud-plan/README.adoc:606`
  calls making it a precondition "the highest-value change in the set and it is not close." No plan here
  claims it yet — it is an execution-lifecycle change, not a post-run-producer change. — re-check when
  PLAN-PRQ-01 and PLAN-PRQ-02 have landed and the producers are trustworthy enough to gate on.
- **Landed claims decay and nothing re-checks them** (`README.adoc:615`, recommendation #5, explicitly
  "the one recommendation that is not about the cloud lane"). — re-check at the next corpus audit.
- **1 of 5 recorded process lessons reached the governing contract** (`test-quality.adoc:738-755`). That
  ratio is the epic's headline outcome metric for the learning half. — re-check after PLAN-PRQ-05 lands.
- **`manage-lessons list` and `get` disagree on two corpus entries.** During the 2026-09-17 lessons sweep,
  `2026-09-08-22-006` and `2026-09-08-22-007` both listed as `active` with **empty `component`/`category`**
  under `list` (and `list --status all`), but `get --lesson-id` returned `not_found` for both. ⛔ **Neither
  was touched** — `manage-lessons remove` has a recorded failure mode of destroying a lesson while
  returning `not_found`, so a retry on `not_found` risks a second destructive loss; this epic's own
  PLAN-PRQ-05 Claim Labels already carry that exact warning verbatim. Left in the corpus, unremoved,
  unarchived. — re-check as first-party evidence for PLAN-PRQ-05 D1/D2 (a corpus entry `list` can see but
  nothing else can safely read or act on is precisely a precision/provenance defect); do not attempt
  `remove` on either id outside a plan that has read `manage-lessons remove`'s failure-mode documentation
  first.
- **`plan-retrospective` reads an unclosed accumulator** (SKILL.md:133-167, "R2"), worked around by a
  `manage-metrics generate` reconcile at Step 2.5 because `record-metrics` (998) cannot move earlier. —
  re-check whether PLAN-PRQ-02's population derivation makes the workaround removable.
- **Corroborating corrections from `instrumentation-substrate`'s own re-grounding of the retired
  PLAN-09 (PLAN-PRQ-05's transfer source), 2026-09-22.** Three of the four points substantially restate
  what this epic's own A1 pass found the same day at the same HEAD (freshness/decay is a partial existing
  implementation via `arch-constraint`'s `recurrence_count`/`last_seen`/`retire-quiet`, not greenfield; the
  application-lifecycle axis is orthogonal to `status` and already noted as a PRQ-05 nuance; the
  provenance hypothesis is structurally unverifiable until D3's own field exists). ONE point is genuinely
  new and independently VERIFIED (`manage-lessons remove --help`): `remove` now requires
  `--coverage-verdict` (closed 4-value vocabulary `completely_covered`/`redundant`/`superseded`/`obsolete`)
  plus `--covering-clause`/`--covering-input` on `completely_covered`, recorded on the tombstone —
  provenance-of-retirement, worth folding into PLAN-PRQ-05 D3's design at outline. No spec edit applied
  this pass (informational, no ship semantics, PLAN-PRQ-05 not yet launched) — re-read at PLAN-PRQ-05's
  outline.
> ↪ Relocated to `settled.md` § "Cross-epic collision: PLAN-TRUTH-175/174 vs PLAN-PRQ-08/01" — settled 2026-09-26: PLAN-PRQ-01 and PLAN-PRQ-08 are parked (superseded by PM-MCP) and
> truthful-signals PLAN-TRUTH-174/-175 are parked there too, so neither side can be emitted; the overlap is moot.
