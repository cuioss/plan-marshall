# PLAN-57: Planning-Lane Router Is Scale-Blind — Systematic Light-Lane False Negative

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced 2026-07-23 by a parallel plan in a CONSUMER repo (a codebase-wide BFF
> foundation, spec self-described "largest and riskiest block — expect a multi-PR split") that routed
> LIGHT/minimal and had to self-escalate via `planning-lane escalate --trigger explosion`. Operator:
> "seen this pattern many times, too often light / escalation." The router is SHARED plan-marshall
> machinery (`manage-status`), so the defect is verifiable in this repo and fixes every consumer.
> Grounded at `main` @ `110a51367`.

## Objective

The planning-lane router (`_cmd_planning_lane.py`) systematically under-routes concrete requests to
`light`, so the plan-time escalate ratchet (`explosion`/`premise`/`cross_cutting`) fires too often as
the ONLY compensator. The root is not the pointer symptom alone — it is a scale-blind heuristic whose
carve-out conflates "concrete" with "small." Make the cheap, zero-discovery router able to route deep
on SCALE, so a well-specified large change is not mislabeled a bounded surgical one.

## ⚠ Mechanism — verified at `110a51367` (four compounding defects)

1. **Scale sensor saturates at 3 paths.** `scope_estimate_from_request_pure` emits only
   `{surgical (1–3 paths), single_module (everything else)}` and NEVER `multi_module`/`broad` (those
   come only from deep-lane refine Step 9). So 4 paths and 48 paths both → `single_module`, which is
   NOT in `_DEEP_SCOPE_ESTIMATES`. The pre-route heuristic is structurally incapable of routing deep on
   scale; the S2 deep path needs a band it cannot produce (circular — the band comes only from being
   already-deep).
2. **Concreteness↔scale conflation (carve-out defect) — THE core defect, proven cleanly by PLAN-47.**
   `narrow_and_concrete = scope ∈ {surgical, single_module} AND request_concrete`. Since `single_module`
   is the ">3 paths" catch-all (i.e. large), a large-but-concrete request is judged narrow-and-concrete,
   which SUPPRESSES S3 (feature) and S4 (breaking). Escalation signals are disabled for exactly the
   concrete-and-large case. **PLAN-47 (this epic, 2026-07-23) is the decisive proof: it named FOUR
   explicit paths (not a pointer) — schema + `_cmd_effort.py` + 3+ workflow/standard docs + steward +
   tests + docs — carries a D1 design gate, and must coordinate its schema with PLAN-48, yet routed
   `light`/`minimal` and had to self-escalate.** Four paths → `single_module` → narrow+concrete →
   S3/S4 suppressed → light. This shows the defect is NOT the pointer shape (PLAN-41's domain) but the
   `single_module`-is-narrow catch-all: ANY concrete request touching >3 files is mislabeled narrow.
3. **Pointer collapse.** `implement {spec}` → 1 path → `surgical` → narrow+concrete → `light`/`minimal`,
   counting the pointer's own path as the work. Lesson `2026-07-21-17-003` (distinct_paths=1, real
   footprint 48 files/5 bundles) is the same defect; this consumer-repo report is the 3rd corroboration.
4. **Risk-prose blindness.** The request/spec explicitly says "largest and riskiest block — expect a
   multi-PR split," but the router regexes only path-count + concreteness anchors (fence/CLI/notation).
   The author's explicit scale warning is invisible.
5. **The safety net misses it.** `_cmd_classification_validate.run_classification_validation` flags only
   `feature_as_bug_fix` and `affected_files_without_scope` — neither detects scale-blind light routing.
   So the plan-time escalate ratchet is the SOLE compensator, which is why it fires "too often."

**PLAN-41 is necessary but NOT sufficient.** PLAN-41 folds spec content into request.md so the router
SEES the paths; Defects 1+2 then map many paths → `single_module` → narrow → still `light`.

## ⛔ SPLIT 2026-07-28 — the READ/COUNT seam moved to PLAN-101

This plan grew to seven defects across **two independent seams**. Defects 3 (pointer collapse), 5
(the router scores a body that is not the request — **confirmed**, `## Original Input` is empty for
every orchestrated plan) and 6 (target-vs-citation counting) are now **PLAN-101**. **Read PLAN-101;
its content is not duplicated here.**

**This plan keeps the CLASSIFY/ROUTE seam:** defects 1 (band saturation), 2 (the
`single_module`-is-narrow carve-out — THE core defect), 4 (risk-prose blindness), the safety-net gap,
defect 7 (no operator-facing surface), and the `auto`→`standard` rename.

⛔ **PLAN-101 and this plan edit the SAME FILE (`_cmd_planning_lane.py`). Sequence, NEVER pair.** The
split buys **landability, not throughput** — two plans in one serialization class cannot run
concurrently, and a future session must not read the split as creating a parallel slot.

⭐ **The seams are genuinely independent, and PLAN-99 proves it.** Its `scope_estimate` was
`single_module` — **the CORRECT value** for a body with 16 paths and a glob — and it **still routed
light**, because `single_module` sits in `_NARROW_SCOPE_ESTIMATES` and `narrow_and_concrete` held.
**A pure defect-2 case: right estimate, wrong lane.** Fixing the read seam alone would not have
changed that plan's lane, which is exactly why this half must ship on its own merits.

⚠ **Recommended order: PLAN-101 first**, so this plan's tests are written against inputs the router
actually scores. The reverse works but forces a re-verify here afterwards.

## ⛔ DEFECT 7 — there is NO operator-facing lane surface at all (orchestrator-verified 2026-07-28)

**Operator data-point:** the four plans launched 2026-07-28 (PLAN-92/93/86/88) were **not asked for
the lane**, while the plan in the n=4 report above *was*. The obvious reading — "the prompt is
conditional and its predicate under-fires" — is **WRONG**, and the correct reading is worse.

**OBSERVED (first-party, `phase-1-init/SKILL.md`):**

- **Step 8b `planning-lane route` (`:824-837`) has no operator prompt of any kind.** It resolves
  `planning_lane ∈ {light, deep}`, persists it to `status.metadata.planning_lane`, emits its own
  decision-log line, and returns. There is no `AskUserQuestion` at the step, and no override input.
- **The lane is not among the init prompts.** `SKILL.md:42` / `:150` and
  `plan-marshall/workflow/planning.md:162` enumerate the inline init dialogues exhaustively —
  plan-existence, obsolescence, recipe-match, domain, sibling-collision, posture. **Six. The lane is
  not one of them.**
- **The one gate that could catch a bad classification is declared non-blocking.** The
  classification-validation pass inside `route` is **"flag-not-block — it never changes the resolved
  lane and never halts initialization"** (`:835`), and it flags only `feature_as_bug_fix` and
  `non_empty_affected_files_with_null_scope`. Neither class is scale-blind light routing (documented
  defect 5 in this spec's original mechanism list says the same about
  `run_classification_validation`).

**Therefore the four un-prompted plans were CONTRACT-CORRECT, and the prompted one was the
anomaly** — that session improvised an operator escalation the workflow does not document, against
the standing "workflow steps: no improvisation" rule. The improvisation caught a real defect, which
is precisely why it must not be mistaken for the system working.

⛔ **The consequence for this plan: the lane verdict has no reliable operator-facing compensator.**
The full set is (a) the DQ3 escalation ratchet *inside* the light-lane envelope — which only fires
after the light lane has already been entered and is the mechanism the epic already records as
firing "too often"; (b) a non-blocking flag gate that cannot see this failure class; and (c) an agent
happening to improvise a prompt. **(c) is not a mechanism.** A user-visible under-route is therefore
invisible by construction unless the ratchet catches it or a human notices, which is this epic's
flagship archetype at the routing layer: a confident deterministic verdict with no surfaced caveat
and no override seam.

**Deliverable consequence (D1 owns the choice, both arms are legitimate):**

1. **Surface the verdict** — the router reports its lane, the signals that produced it, and its own
   confidence/inapplicability, at a site the operator actually sees. Cheapest, and it composes with
   the defect-6 precision fix.
2. **Add a real override seam** — a documented `lane=` input and/or a conditional prompt when the
   sensor is out of its competence band. More invasive, and a prompt on every plan is a tax the
   deterministic-router design deliberately avoided.

⚠ **Do NOT satisfy this by documenting the improvised prompt as a step.** That converts an
undocumented behaviour into a mandatory per-plan operator interrupt without fixing the sensor, and
the epic already carries `feedback: infra steps must be opt-in`. The sensor being wrong is the
defect; the missing surface is what makes it *silent*.

## Corpus location for D1's threshold choice (relocated 2026-07-26)

D1 must name **exact thresholds** for the path-count bands. The non-arbitrary way to pick them is the
real path-count distribution across the shipped-plan corpus — the same substrate that produced this
plan's decisive PLAN-47 proof.

**That corpus was dormated on 2026-07-26 and is NOT gone — it MOVED.** `.plan/local/archived-plans/`
is now empty; all 115 plans live at **`.plan/temp/dormated-plans/{plan_id}/`**. Read them there.

⚠ Two consequences for the executing plan: (a) any tooling that globs `.plan/local/archived-plans/`
— including `audit-archived-plan-retrospectives` — will now find an EMPTY corpus and may report a
clean/zero result rather than "corpus missing", so treat a zero-finding corpus run as unverified
until the path is confirmed; (b) the destination is the project's temp area, so re-confirm the
directory still exists before relying on it, and if the thresholds matter, extract the distribution
into this plan's own artifacts rather than leaving the evidence in temp.

## Corpus-scale evidence + one audit self-correction (2026-07-26 full-corpus audit)

The first full-corpus sweep (115 plans; the prior recorded run covered 8) supplies the scale evidence
D1's threshold choice needs, plus a correction the executing plan MUST NOT re-derive wrongly.

- **4 named UNDER-TRACKED plans** — routed lighter than the counterfactual correct track. These are
  the positive instances; read them from the report and the dormated tree (see the corpus-location
  section above) and use their path counts to anchor D1's band thresholds.
- ⚠ **The 45 OVER-TRACKED rows are NOT counter-evidence.** The audit's own first read treated them as
  contradicting this plan and then **retracted that read**: every one carries `era: #875:carve_out`,
  which `checks/track-selection-accuracy.md` defines as **era-relative and explicitly not a routing
  miss**. Do not cite them as "the router also over-routes" — that reading is already refuted, and
  re-deriving it would manufacture a false mirror-defect for D2's no-over-escalation requirement.
- **Direction of the evidence is therefore one-sided at corpus scale**: under-tracking is real and
  counted, over-tracking is an era artefact. D2's mirror-false-positive guard ("surgical genuinely-small
  fixes still route light") remains a design requirement, but it is NOT motivated by observed
  over-escalation — no corpus instance supports it. Keep the guard; drop any claim that data demands it.
  ⚠ **Superseded in part — see the candidate mirror instance below (2026-07-26). One post-corpus
  observation now bears on the over-route direction; it is a candidate, not a counted instance, and it
  does not disturb the era-artefact retraction above.**

## ⚠ Candidate mirror instance — over-route, CANDIDATE not OBSERVED (cross-epic, 2026-07-26)

Reported by the operator from PR #1012 (test-suite-quality epic), a **residue-closing tech-debt plan**
whose five deliverables were two recorded decisions, two small code changes, and one gate change.

- OBSERVED (operator-reported measurement) — phases 1–4 consumed **1.43 M tokens** against **331 K**
  for phase 5-execute, a **4.3 : 1 planning-to-execution ratio**. The operator attributes it to a
  `cross_cutting` deep-lane escalation.
- OBSERVED (first-party, this repo) — `cross_cutting` is one of the escalate-ratchet triggers in
  **this plan's own file**, `_cmd_planning_lane.py` (`:576`), and the ratchet is **one-way**
  (`:572-576`, "Monotonic light→deep. Refuses any attempt to set a lane back to `light`"). So once a
  mid-flight escalation fires, deep-lane cost is incurred for the remainder of the plan **even if the
  scope subsequently resolves narrow**. There is no de-escalation path.
- **HYPOTHESIS (verify-at-outline) — this is the mirror false-positive the corpus lacked.** Whether
  the escalation was *wrong* is a judgment the ratio alone does not settle: five deliverables spanning
  docs, code, and a gate is defensibly cross-cutting. **Confirm/refute against PR #1012's own
  `planning-lane` decision record** — read which trigger fired, at what point in the plan, and against
  what scope was then known. If the trigger fired on a scope that was already bounded, this is a
  counted over-route instance and D2's mirror guard acquires the empirical motivation the corpus
  section says it lacks.
- **Scope note — this does NOT add a deliverable.** D2 already requires the mirror guard and D5
  already tests both directions. What changes is the *evidence status* of that requirement, plus one
  question D1 should now answer explicitly: **is a one-way ratchet with no de-escalation the right
  shape at all**, given that its cost is unbounded once fired and its only corrective is the operator
  noticing a token ratio after the fact. Answer it in D1's design record; implement only if the answer
  is cheap and lands inside D2.
- Orchestrator boundary note: PR #1012's plan artifacts belong to another epic and were not read. The
  ratio and the trigger name are the operator's report; the ratchet mechanics are first-party.
- Source: `.plan/local/audit-reports/20260726T202149Z.toon` (603 KB, all 22 check blocks). The
  `track-selection-accuracy` block carries the per-plan rows.

## Deliverables

1. **D1 (design gate) — pick the scale-truthful fix (mutates nothing).** Settle: (a) extend the
   pre-route vocabulary so a path-count above a higher threshold emits a broad band (or a new
   "many-paths" band) that biases deep — zero-discovery, a count threshold only; (b) narrow the
   carve-out so `narrow_and_concrete` requires ACTUAL narrowness (surgical, or ≤N paths), not the
   `single_module` >3 catch-all — so escalation is suppressed only for genuinely-few-path requests; and
   the truthful-negative rule below. Name every artifact each choice edits, and the exact thresholds.
2. **D2 — scale resolution + carve-out fix.** Implement the chosen shape: the heuristic distinguishes
   "few" from "many" above the surgical bound (currently everything >3 collapses to `single_module`),
   and the carve-out stops treating "many, concrete" as narrow. Preserve: unset/borderline cases resolve
   at least as conservatively as today; surgical genuinely-small fixes still route light (no over-
   escalation of real surgical work — the mirror false-positive).
3. **D3 — a cheap scale/risk-prose signal.** Add a zero-discovery regex signal for explicit author
   scale warnings ("multi-PR", "codebase-wide", "largest/riskiest", "expect a split", "foundation",
   epic/campaign language) that biases deep. Catches the human-authored warning the router ignores today.
4. **D4 — truthful negative: unknown scale must not read as "small."** When the heuristic cannot bound
   the upper scale (many paths, no clear ceiling), it MUST NOT collapse to narrow/light — surface the
   uncertainty and fail toward deep (or at minimum stop suppressing escalation), the same fail-closed
   principle as PLAN-43 (architecture-find) and PLAN-54 (retro checkers). "I can't tell how big" ≠
   "it's small."
5. **D5 — tests + defense-in-depth flag.** Tests: a many-path concrete request routes deep (not light);
   a genuine surgical fix still routes light (no over-escalation); a pointer-shaped request folded with
   spec content (PLAN-41 shape) routes deep; a risk-prose warning biases deep; unknown-scale fails
   toward deep. Consider adding a scale-mismatch class to `classification-validate` (flag-not-block) so
   the miscalibration is observable even where routing already fired — decide at D1.

Five deliverables (D1 a gate) — under the split guard.

## Claim Labels

- OBSERVED: the scale-vocabulary ceiling — read at `_cmd_planning_lane.py`:214-241
  (`scope_estimate_from_request_pure`, emits only `surgical`/`single_module`) and :80
  (`_DEEP_SCOPE_ESTIMATES = {multi_module, broad, none}`, excludes `single_module`).
- OBSERVED: the carve-out conflation — read at :308 / :272 (`narrow_and_concrete = scope ∈
  {surgical, single_module} AND request_concrete`) with `_NARROW_SCOPE_ESTIMATES` at :76 including
  `single_module`, and the S3/S4 suppression at :319/:322.
- OBSERVED: the pointer-collapse trace — a 1-path body → `surgical` (:239) → narrow+concrete →
  no signal fires → `light` (:340), posture `minimal` (:273).
- OBSERVED: the safety net's two classes — read at `_cmd_classification_validate.py`:11-24; neither is
  scale.
- OBSERVED (n=4 corroboration): lesson `2026-07-21-17-003` (pointer, 1 path) + the PLAN-23 #986 retro
  cross-link + the 2026-07-23 consumer-repo BFF report + **PLAN-47 (2026-07-23, 4 explicit paths — the
  non-pointer proof)**. The four span the full range: 1-path pointer through 4-path explicit through
  48-path folded — all routed light. The invariant across them is `single_module`-is-narrow, not the
  pointer shape.
- HYPOTHESIS: PLAN-41's spec-fold alone leaves the light verdict unchanged for a 48-path request —
  confirm/refute at outline by running the router over a spec-folded request.md fixture (verify-at-
  outline; PLAN-41 must land first for the real fixture).
- Verify-first clause: before D2 raises a threshold, confirm the mirror false-positive is not created —
  a genuinely surgical concrete fix must STILL route light; over-escalating real surgical work trades
  one false signal for the opposite one, which the vacuous-guard/PLAN-54 polarity note warns against.

## Expected Surface

- OBSERVED: `manage-status/scripts/_cmd_planning_lane.py` — `scope_estimate_from_request_pure`,
  `_NARROW_SCOPE_ESTIMATES` / `_DEEP_SCOPE_ESTIMATES`, `evaluate_signals_pure` carve-out, the new
  risk-prose signal, `project_profile_pure`.
- HYPOTHESIS: `manage-status/scripts/_cmd_classification_validate.py` — only if D5 adds the
  scale-mismatch flag (verify-at-outline).
- OBSERVED: the planning-lanes solution-outline / `ext-point-lane-element.md` doc where the signal set
  (DQ1) is specified — update the S2/S5 + carve-out contract in lock-step.
- OBSERVED: tests under `test/plan-marshall/manage-status/**` (the lane-router suite).

Re-verify at outline against HEAD: PLAN-50 renames the lane TIER value `auto`→`standard` (touches the
lane system) and PLAN-41 changes request.md content — coordinate both.

## Dependencies and Sequencing

- **Coordinate with PLAN-41** (in flight) — complementary, disjoint files (router script vs
  phase-1-init SKILL): PLAN-41 makes the router SEE the paths, this makes it COUNT them. Ideally
  sequence AFTER PLAN-41 lands so D5's pointer-fixture tests the real spec-folded request.md; they can
  run concurrently on file-disjointness but the semantics interlock — do not validate this plan against
  a pre-PLAN-41 request.md.
- **Coordinate with PLAN-50** (lane-tier rename `auto`→`standard`) — both touch the lane system;
  whichever lands first, the other re-grounds. Distinct concern (tier vocabulary vs scale signal).
- Disjoint from the other in-flight plans (PLAN-27 java-markers, PLAN-45 routed-verdict, PLAN-46 title,
  PLAN-47/48 orchestrator-config).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-57-lane-router-scale-blind-false-negative.md"
```

## Notes

- Theme fit: flagship confident-signal-hides-a-caveat — the router reports `light` while its scale
  sensor is blind above 3 paths and its carve-out suppresses escalation for concrete requests; plus
  vacuous-guard-adjacent (the "narrow-and-concrete" guard mis-fires for large requests; the escalate
  net firing "too often" is the tell).
- Polarity guard (from PLAN-54): the fix must not create the mirror false-positive — over-escalating
  genuine surgical work. D2/D5 pin both directions.

## Same enum — rename the lane tier `auto` → `standard`

This plan rewrites the lane router; the tier value that router routes on is renamed here too, because
two passes over one enum is waste.

**Deliverables for this half:**
- **GATE (mutates nothing)** — precise enumeration of every `auto` occurrence in the tier sense, plus
  the migration decision for existing values.
- **Rename in the contract and the implementations** — the lane enum and `_manifest_lanes.py`.
- **Project `marshal.json` and docs.**
- **Tests plus an acceptance check.**

**Two carried constraints — both load-bearing:**
- ⚠ **`auto` is overloaded — NEVER touch `deep_lane`.** The rename targets the tier value only.
- ⚠ **`standard` was chosen deliberately over `default`**, because `default:` is the built-in
  step-id namespace prefix and `default` would collide. Recorded as an epic decision 2026-07-22 —
  **do not re-litigate the name.**
- ⚠ `manage-execution-manifest` was flagged as overlapping a then-running plan; **re-ground
  `_manifest_lanes.py` against HEAD** before scoping, since that overlap may be stale.

⛔ **This fold does NOT relieve the split pressure — it adds to it.** This plan already grew from
five documented defects to **seven** on 2026-07-28 (defect 6: the path counter cannot distinguish a
target from a citation; defect 7: there is no operator-facing lane surface at all). **It is now the
largest staged plan in the epic and is a SPLIT candidate.** The rename is mechanical and belongs with
the router work, but **D1 must evaluate splitting the router work itself and record the verdict.**
Diff-scoped-sweep-misses-the-tree applies to any rename — sweep the tree, not the diff.

## ⭐ PLAN-99 ISOLATES DEFECT 2 FROM DEFECT 5 — the sensor was RIGHT and the router still under-routed

Measured 2026-07-28 on the live `exploration-share-is-unmeasured` plan (at `1-init`), using this
file's own regexes:

| Scored region | bytes | paths | glob | rule says |
|---|---|---|---|---|
| header (pre-`## Original Input`) | 473 | 1 | no | `surgical` |
| `## Original Input` section | **0** | 0 | no | `single_module` |
| whole `request.md` | 12291 | **16** | **yes** | `single_module` |

**Persisted `scope_estimate: single_module`.**

⭐ **`single_module` is the CORRECT classification for this body** — 16 paths and a glob both force it.
**The sensor was right, and the plan still routed `light`.** That happens because `single_module` sits
in `_NARROW_SCOPE_ESTIMATES` (`:76`), so `narrow_and_concrete` holds and S3/S4 stay suppressed.

⛔ **This is the cleanest available isolation of documented defect 2 from defect 5.** PLAN-94 was a
defect-5 case (truncated read → wrong estimate). PLAN-99 is a **pure defect-2 case: correct estimate,
wrong lane.** They are independent, and **fixing the read seam alone would not have changed this
plan's lane.** D1 must fix both or state plainly which it is deferring.

⚠ **Unexplained and NOT to be papered over:** PLAN-94 and PLAN-99 have structurally identical
requests (both have an empty `## Original Input`, both have a 1-path header) yet persisted
**different** values — `surgical` vs `single_module`. The pure function cannot produce both from the
same structure, so **something other than `scope_estimate_from_request_pure` is writing this field, or
the scored input differs in a way not visible in the file.** D1 owes an explanation; do not assume the
pure function is the only writer.

⛔ **REFUTED AGAIN — "the spec writes its paths in backticks, so the heuristic saw almost none of the
real surface."** Now asserted twice by two different sessions. `_PATH_RE` contains no backtick in its
character class; **16 paths matched in this very spec, all of them in backticked prose.** Backticks
are a non-issue. **Recorded twice because a plausible-and-wrong mechanism that keeps being
re-proposed will eventually be "fixed".**

## ⛔⛔ SEVERITY ESCALATION — defect 2 also drops the SECURITY GATES, by design

**OBSERVED first-party at HEAD, `project_profile_pure` (`:244-282`):**

```python
narrow_and_concrete = scope_estimate in _NARROW_SCOPE_ESTIMATES and request_concrete
if narrow_and_concrete:
    return MINIMAL
```

**The posture resolver uses the SAME predicate as the lane resolver**, and its own docstring states
the dominance rule outright: *"the same narrow-and-concrete predicate the lane verdict's S3/S4
carve-out uses, so a bounded surgical fix stays `minimal` even when its `change_type` reads
generative or its `compatibility` reads breaking — **the narrow, concrete bound dominates**."*

⛔ **So ONE wrong `scope_estimate` corrupts TWO independent decisions**: the planning lane *and* the
execution posture. And `minimal` **drops `sonar-roundtrip`, `automatic-review`, and the security
audit.**

**The live instance (API-Sheriff, cross-repo, 2026-07-28):** a plan whose **core fix is a
session-confusion vulnerability**, in an epic whose standing conventions mandate a green Sonar gate
and full review-comment triage, routed `light`/`minimal` — **dropping the security audit on a
security fix.**

⛔ **This is not a posture bug.** The dominance is deliberate and documented; the resolver is doing
exactly what it says. **The defect is entirely upstream: a wrong narrow verdict.** That is why
defect 2 cannot be deferred as a cost optimisation — **it is a security-gate suppression path.**

⚠ **Two consequences D1 must carry:**

1. **Escalating the LANE does not fix the POSTURE.** They are separate outputs of the same predicate,
   so an operator who overrides only the lane still runs `minimal` and still loses the security
   steps. Whatever D1 fixes must correct both, and any operator-facing surface (defect 7) must
   surface **both** verdicts, not just the lane.
2. ⚠ **`change_type` and `compatibility` cannot rescue it.** The narrow bound dominates
   `feature_breaking` and `breaking` by design — so the signals that *should* force ceremony are
   explicitly overridden by the one signal we know is wrong.

⭐ **Cross-repo: the instance count now spans repositories.** This one is from API-Sheriff, a consumer.
The router is shared `manage-status` machinery, so the fix lands for every consumer — and the defect
is currently suppressing security gates in at least one downstream repo.

⛔ **REFUTED A THIRD TIME — the backticks explanation.** Proposed again by this report. `_PATH_RE`
contains no backtick in its character class; 16 paths matched in a spec where all were backticked.
**Three independent sessions have now proposed it and it has been refuted three times.** D1 must not
spend budget here.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests — it creates and edits
NO file under `.plan/local/orchestrator/` during execution, and reports its outcome through its PR
alone. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Lessons Carried (bound 2026-07-25 · lessons-triage)

The plan lifecycle MUST carry the lessons below so each lives/moves with the plan and leaves the
global corpus when the fix lands: at phase-1-init run
`manage-lessons convert-to-plan --lesson-id {id} --plan-id {plan_marshall_plan_id}` per lesson; the
finalize `lessons-housekeeping` step then retires them (provenance to the tombstone `--reason`).

- `2026-07-21-17-003` — scope-estimate-heuristic counts concrete paths only, under-reading
  glob-scoped requests (Defect 3 / pointer collapse — the same `single_module`-is-narrow root).
- `2026-07-21-11-001` — architecture-resolved build-duration estimates run ~5× stale and converge
  too slowly to be a trustworthy `execution_tier` routing input (the stale-learned-value half of the
  scale-blind routing surface; coordinate with the D-notes on learned-value truthfulness).
