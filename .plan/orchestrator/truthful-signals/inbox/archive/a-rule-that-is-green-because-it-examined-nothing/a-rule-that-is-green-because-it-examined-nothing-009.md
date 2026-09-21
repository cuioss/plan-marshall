envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=landing
created=2026-08-08T18:50:10Z

## What landed

**PR #1115** — `fix(arch-gate): require negative-control fixtures for ArchUnit rules` — merged via merge queue.

Plan: `a-rule-that-is-green-because-it-examined-nothing` (title: *An arch rule that is green because it examined nothing*). Change type `enhancement`, planning lane `deep`, execution profile `standard`, confidence 100%. Documentation-only footprint (5 files, no production code).

### Substance

The plan closes a vacuous-green class in architecture fitness functions: an ArchUnit rule whose selector matches zero classes passes, and that pass is indistinguishable from a rule that examined a real population and found it compliant. Four deliverables shipped:

1. **The gate** — re-asserted the zero-arch-rule population as an execution-time gate rather than a claim in prose (`architecture search --content --literal --pattern ArchCondition` over the live tree; the repository has no ArchUnit rules today, which is exactly why the obligation had to be written before the first one is authored).
2. **The obligation** — authored the negative-control requirement centrally in `manage-architecture/standards/arch-gate-fitness-functions.md`: every arch rule ships one deliberately non-compliant fixture proving the rule can go red.
3. **The polarity trap** — documented in `pm-dev-java/skills/arch-gate-java/SKILL.md` the ArchUnit-specific way a hand-written `ArchCondition` goes vacuous, scoped (after review) to the violated-only event shape, with a pairing requirement that asserts concrete event polarity and not merely pass/fail.
4. **Marker scope** — authored the marker-suppression scope and the non-idempotent-rewrite property across the two OpenRewrite signals in `pm-dev-java-cui/skills/search-markers/standards/marker-detection.md`.

### Why it belongs to `truthful-signals`

The plan is a first-class instance of the epic's theme: **a confident green that hides the fact that nothing was examined.** It is worth recording that the theme recurred *inside the plan's own execution* at least four times — the outline asserted a gate ordering that nothing enforced (`depends=none`), a central standard asserted a binding that held in 1 of the 3 skills it named, an ADR was cited as accepted while its recorded status is Proposed, and the plan's own pairing test as first written could not distinguish "reported no events" from "reported correctly-polarised events". Every one of those was caught, but each was green until something looked.

### Shape of the run

- 6 tasks (4 planned + 2 allocated from PR review), 1 loop-back iteration to `5-execute`.
- 7 Q-Gate findings across `2-refine` / `3-outline` / `6-finalize`; all resolved in-run (5 fixed / taken into account, 1 accepted with rationale, 1 examined-and-cleared).
- 7 PR-review comments triaged (coderabbit + pr-agent), 3 FIX → TASK-005 / TASK-006, 2 taken into account, 2 accepted. Pre-merge review barrier clean.
- 3 pre-submission self-review iterations (ceiling reached), 18-19 candidates examined per iteration.
- 6 distinct script notations failed during the run.

### Residue the epic should track

1. **An under-specification was accepted rather than fixed because it surfaced at the self-review iteration ceiling** (Q-Gate `52ed98`). Negative-control fixture *placement* is explained only inside the narrower hand-written-condition section; an author of an ordinary `@ArchTest` rule gets no placement guidance. Deliberately left open — fixing it would have shipped prose no review round examined. A follow-up is owed.
2. **The negative-control obligation binds in only one of the three per-domain arch-gate skills.** `arch-gate-python` (import-linter) and `arch-gate-js` (dependency-cruiser) carry no tool-specific vacuity note. The central claim was narrowed to match reality rather than the two skills being brought up; authoring those two notes is genuine new work in untouched skills and belongs in its own plan.
3. **`scoped plugin-doctor cannot detect cross-skill divergence`** was logged as a WARNING three times in this run. Cross-skill rules whose counterpart lives outside `--paths` were never evaluated; a broken cross-skill invariant would surface first at whole-tree CI.
4. **A CodeRabbit re-review of the rebased HEAD returned `matched=true` with `head_sha_verified=false`** — the match was a "does not re-review already reviewed commits" reply, not a fresh review. Participation for that HEAD was never established by the match. Recorded here because a `matched=true` that does not mean "a bot looked" is the epic's theme at the review boundary.
5. **16 candidate-lesson messages accompany this landing** (sequences following the 8 the retrospective already sent): 7 from Q-Gate findings, 3 from remediated PR-review findings, 6 from script-failure clusters. Four of the six script clusters are the same archetype — an invented `manage-*` subcommand or flag — which recurred four times in one plan despite the prohibition sitting on the always-loaded agent floor.
