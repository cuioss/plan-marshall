# PLAN-PRQ-06: A lane override that cannot take effect is accepted, stored, and reported `set`

epic: post-run-quality
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Observed independently by the operator and by this orchestrator on 2026-09-17, then analyzed against the
archived plan `2026-09-17-truth-166-architecture-refresh-migration-churn` and the lane implementation.
⛔ **The analysis REFUTED both of the readings the observation first suggested** — see `## Claim Labels`.
This spec replaces the half of `PLAN-PRQ-04` D0/D2 that carried the refuted framing; PRQ-04 keeps the
owed-obligation work and points here.

## Operator rulings binding on this plan

Both were given on 2026-09-17 and are recorded here because a spec that re-opens a settled decision wastes
the decision:

1. **`lessons-capture` must be off when configured off.** The immunity that currently neutralizes that
   override is correct for genuine floor elements; the classification of this element is what changes.
2. **The mechanism is reclassification off the floor class** — chosen over a per-element immunity opt-out
   (which would have needed an `ext-point-lane-element` contract change) and over reclassify-plus-pinned-tier
   (which would have kept today's minimal-profile behaviour at the cost of a class that no longer means
   what it says). ⚠ The operator accepted the side effect this carries; D3 names it.

## Objective

**`.plan/marshal.json` has carried `steps["default:lessons-capture"].lane = "off"` since 2026-09-14, and
the step ran on every plan anyway — correctly, by a documented rule — while every operator-facing surface
continued to report the override as set.** The machinery did exactly what its contract says: an `off` on a
`core` or `derived-state` floor element is **immune** — ignored, kept at its class-default tier, with an
informational warning. The defect is not the immunity; it is that **nothing tells the operator their
instruction is inert**, at any point where they could act on it.

The one place the neutralization IS stated is a compose-time decision-log line inside the plan directory,
which is archived when the plan finishes. So the operator's intent fails silently, per plan, forever — and
the only way to discover it is to read an archived plan's log, which is how it was found.

⭐ **Why this epic owns it.** `lessons-capture` is the post-run learning step: an operator who turns it off
and keeps getting lessons has no way to tell whether the corpus is growing because the step is wanted or
because the knob is a decoration. A post-run quality signal whose ON/OFF state is unknowable is the epic's
theme aimed at its own control surface.

## Deliverables

Five deliverables. D0 is a gate; D3 is an escalation, not an implementation.

**D0 — GATE: derive the inert-override population, both channels, all phases.** Enumerate every
`(step, lane)` override persisted in `marshal.json`'s `plan.phase-6-finalize.steps` AND in the plan-local
`status.metadata.finalize_step_overrides` channel, join each to its element's declared `lane.class`, and
report every pair whose override cannot take effect. ⛔ Publish the population and its size before fixing
anything — **one instance found by accident is not a population**, and the same immunity applies to every
`core` / `derived-state` element, of which the finalize order has several (`push`, `create-pr`,
`branch-cleanup` are all `core`).

**D1 — The write surface refuses an override that cannot bind.** Both writers — `finalize-steps set-lane`
and the generic `plan phase-6-finalize step set --param lane` — resolve the target element's declared
`lane.class` before persisting, and refuse (or persist with a named, RETURNED warning) an `off` on an
immune class. The rejection names why and what the operator can do instead. Today both validate the VALUE
SPACE only and never read the element, which is why an inert value is indistinguishable from a live one at
write time.

**D2 — An already-stored inert override is visible without composing a plan.** A read surface reports
declared-versus-effective per step with the neutralization reason — the same fact the composer already
computes, surfaced where an operator looks (`manage-config` read path and/or `lanes-preview`, and the
steward's configuration view). ⛔ The existing compose-time warning STAYS; it is the per-run record. This
deliverable is about the surface that answers *"is my configuration in force?"* without running a plan.

**D3 — SETTLED BY THE OPERATOR: reclassify `default:lessons-capture` off the floor so `off` binds.**
⛔ **This is a decision, not a question — do not re-escalate it.** Operator ruling, 2026-09-17:
*"lessons capture should be off if configured off."* Asked which mechanism, the operator chose
**reclassification off the floor class** over a per-element immunity opt-out and over a
reclassify-plus-pinned-tier hybrid.

The element moves from `core` to a non-immune class (`prunable` is the natural fit — it is the class its
sibling `plan-marshall:plan-retrospective` already carries, and the two are the post-run pair). No change
to `ext-point-lane-element`'s immunity rule, which stays correct for the genuine floor elements.

⚠ **The accepted side effect, recorded so it is never discovered as a surprise.** A non-immune class
defaults to tier `standard`, so after this change `lessons-capture` **also stops running under an
`execution_profile: minimal` plan** even where no `off` override is set — a behaviour change every
consumer inherits on upgrade. The operator accepted it when choosing this mechanism. ⛔ The plan must
therefore: state the change in the step's own doc, and give D4 a control that PINS the new minimal-profile
behaviour, so the side effect is asserted rather than assumed.

**D3a — Answer the knob at the source, not only at the element.** Once `off` binds, the stored
`lane: "off"` in this repository's `.plan/marshal.json` takes effect on the next composed plan and
`lessons-capture` stops running here. That is the operator's intent; the plan states it in the PR body so
the behaviour change is visible at review rather than at the first run that files no lesson.

**D2a — The composed manifest records the EFFECTIVE lane, not the requested one.** ⭐ Folded 2026-09-17
from corpus lesson `2026-09-13-06-001` (preserved in this epic), which reported this exact defect on
2026-09-13 and was never actioned. `phase_6.step_params` persists `lessons-capture: {lane: off}` while
`phase_6.steps[]` still contains the step — the manifest simultaneously says the step runs and that its
lane is off, and only the decision log records that the `off` was refused. ⛔ **The harm is observed, not
hypothetical**: that run's own retrospective dispatch prompt asserted *"`lessons-capture` is lane: off in
this plan's manifest, so lessons you seed are the run's durable output"* — a conclusion drawn from the
persisted value, and wrong. The lesson's preferred remedy is to write the resolved lane into `step_params`
and keep the requested value beside it under a distinct key (`lane_requested`), because *"what lane is this
step on?"* is the read every consumer actually performs. ⚠ A step present in `steps[]` must never carry a
bare `lane: off` in `step_params`. This survives D3: after reclassification the refusal no longer happens
for `lessons-capture`, but it still happens for every genuine floor element.

**D4 — Controls, including the negative one that does not exist today and the one D3 creates.** An inert
override is refused at write; a LIVE override on a non-immune element still writes and still binds (the
matched positive control); a legacy stored inert value still produces the compose-time neutralization
warning; a test asserts that a **genuine floor element** (`push` / `create-pr` / `branch-cleanup`) still
survives an `off`, which is the behaviour the immunity rule promises and nothing currently pins; and — new
with D3 — a test asserts that `lessons-capture` is now **dropped** both by an explicit `off` AND by an
`execution_profile: minimal` plan with no override at all. The second half is the accepted side effect: it
is pinned so a future reader sees it as intended rather than as a regression.

## Claim Labels

⛔ **Two REFUTED readings, retained with their refuting evidence** (this project keeps a refutation rather
than silently correcting it):

- ⛔ REFUTED: *"lane resolution fails to drop a non-ceremony step at `off`."* It does not fail — an `off`
  on a `core` element is immune BY CONTRACT.
  Evidence: `manage-execution-manifest/scripts/_manifest_lanes.py:171-172` (`if override == 'off' and
  lane.get('class') not in _IMMUNE_TO_OFF_CLASSES`), `:37` (`_IMMUNE_TO_OFF_CLASSES = ('core',
  'derived-state')`), `:186-209` (`_lane_keep_decision` keeps it and emits the warning), and
  `extension-api/standards/ext-point-lane-element.md:50-51, 70, 90`, which documents the rule in prose.
- ⛔ REFUTED: *"the landing's `steps=` list is not derived from the composed manifest."* The step genuinely
  ran. Evidence: the archived plan's `execution.toon` carries `lessons-capture` in the composed
  `phase_6` step list (lines 33, 84, 118) and records it `executed` at `2026-09-17T02:37:33Z` (line 158);
  `status.json` carries its `phase_steps` entry. The landing told the truth.

OBSERVED claims, all read first-party on 2026-09-17:

- OBSERVED: `.plan/marshal.json` sets `default:lessons-capture` to `lane: "off"`, and `git log` shows the
  file unchanged since 2026-09-14 — so the override was in force for the whole run.
- OBSERVED: the neutralization WAS recorded, exactly once, in the plan's own decision log:
  `logs/decision.log` entry `4a5900` — *"lane_resolution warning — lessons-capture: override 'off' ignored
  for core floor element — immune, cannot be weakened"* — in a plan directory that is now archived.
- OBSERVED: `default:lessons-capture` declares `lane.class: core`, `order: 991`, `post_run_review: true`
  (`phase-6-finalize/workflow/lessons-capture.md` frontmatter), and `push` / `create-pr` /
  `branch-cleanup` declare the same class, while `plan-marshall:plan-retrospective` declares `prunable`.
- OBSERVED: both config writers validate the lane VALUE SPACE only and never read the element's class —
  `manage-config/scripts/_cmd_finalize_steps.py:64-110` (`_RESOLVED_ASK_LANE_VALUES`,
  `_READER_LANE_VALUES`, `_reject_lane_value`), with no `lane.class` read anywhere in the writer path.
- ⚠ HYPOTHESIS: `lessons-capture` is the only currently-stored inert override in this repository —
  ⛔ asserted by nobody; D0 owns the derivation, and an asserted absence is the higher-risk half
  (verify-at-outline).
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Derived, not sampled: .plan/marshal.json plan.phase-6-finalize.steps has 26 entries; exactly 2 carry lane:off (adr-propose, lessons-capture). adr-propose declares class:prunable (non-immune, off binds -- a live override); lessons-capture declares class:core (immune, inert). No other entry carries off. Scope caveat: plan-local status.metadata.finalize_step_overrides across live plans not swept.
- OBSERVED: a non-immune class defaults to tier `standard` (`_manifest_lanes.py:26-30`,
  `_CLASS_DEFAULT_TIER`), while `core` defaults to `minimal` — which is why D3's reclassification also
  changes the no-override behaviour under an `execution_profile: minimal` plan. Read first-party,
  2026-09-17; re-verify at outline before choosing the target class.
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Line-exact at HEAD: _manifest_lanes.py:26-31 _CLASS_DEFAULT_TIER = {derived-state:minimal, core:minimal, adversarial:standard, prunable:standard}; :37 _IMMUNE_TO_OFF_CLASSES=(core,derived-state); :171,:186,:203 unchanged. D3's accepted side effect is real: reclassifying core->prunable moves the no-override default tier from minimal to standard.
- ⚠ HYPOTHESIS: `prunable` is the right target class rather than `adversarial` — both are non-immune and
  both default to `standard`, so the choice is about what the classification MEANS, not about behaviour.
  `plan-retrospective` (the post-run sibling) carries `prunable`. Confirm at outline (verify-at-outline).
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Content sweep for '  class: prunable' returns 5 files including plan-retrospective/SKILL.md (the post-run sibling, as claimed). Both adversarial and prunable default to standard tier, so the choice is about meaning, not behaviour.
- ⚠ HYPOTHESIS: the composer already computes everything D2's read surface needs, so D2 is a surfacing
  change rather than a second resolver — confirm/refute at `manage-execution-manifest` `lanes-preview`
  (verify-at-outline). ⛔ If refuted, D2 must NOT grow a second lane resolver; re-scope to reuse the one
  authority.
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: manage-execution-manifest.py:1727 cmd_lanes_preview, registered at :3448/:3621. At :1770 it calls _apply_lane_resolution and discards the warning channel: kept,_dropped,_warnings=... The neutralization reason D2 needs is already computed and thrown away, not missing. D2 is a plumbing change on an existing return value; no second resolver warranted.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_finalize_steps.py` — the `set-lane` writer (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` — the generic per-element `step set --param lane` writer (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` — the documented write contract and its refusal codes (D1) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_lanes.py` — the single immunity authority D1/D2 read (never re-implement)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — `lanes-preview` as D2's surfacing seam (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md` — the `lane.class` declaration D3 reclassifies, and the doc text stating the new minimal-profile behaviour (D3, D3a)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/` — the configuration view D2 surfaces through (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-config/` — D4's write-side controls
- OBSERVED: `test/plan-marshall/manage-execution-manifest/` — D4's immunity control, the one that does not exist today

## Dependencies and Sequencing

- Depends on: none. D3's escalation can be raised as soon as D0 publishes the population.
- ⛔ Shares `manage-execution-manifest/**` and `phase-6-finalize/**` with `PLAN-PRQ-04` — and with
  `truthful-signals` `-145`, `-147`, `-158`, which is **cross-epic and invisible to both gates**. Check
  `manage-status list` and that epic's queue before launching.
- ⚠ `truthful-signals` PLAN-TRUTH-168 (`sync-defaults` reverts a deliberate `remove-step`) is the SAME
  archetype on a different field: an operator instruction that routine machinery undoes. Different
  component, different mechanism, not merged — but whichever lands second should read the first's fix
  before designing its own refusal shape.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-06-a-lane-override-that-cannot-take-effect-is-accepted-and-reported-set.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
