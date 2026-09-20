# PLAN-CIS-015: Outline & Plan Scope-Derivation Integrity

epic: code-intelligence-substrate
workstream: WS-05

> Staged plan spec (lessons-triage 2026-07-25). Gathers the phase-3-outline / phase-4-plan family
> where scope, footprint, or a consumed field is DERIVED from narrative intent (or a stale side
> store) instead of the authoritative write-set — silently dropping a required profile, build, or
> assessment. LARGE; the D1 gate MAY split along the outline / plan / phase-5 boundary if it exceeds
> the six-deliverable presumption.

## Objective

Phase-3-outline and phase-4-plan repeatedly consume a field summarized from intent (a deliverable's
declared file-type bucket, change_type, module) or a point-in-time sweep, rather than deriving it
mechanically from the Affected-files write-set / solution outline. The result is a dropped
finalize step, a skipped build, an un-assessed late-scoped file, or an inherited foreign commit.
Make the consumed fields **derived, not asserted**, and the completeness checks **closure-based**.

## Deliverables

## ⭐ SIXTH RECURRENCE — folded 2026-07-27 from the PLAN-80 landing (#1021)

- OBSERVED (operator narrative, first-party, PR #1021): the outline declared a **"closed consumer set"
  that was not closed — and on the strength of that closure claim it told phase-5 NOT to re-check.** It
  verified `test_re_review_strategy.py` had no dict-equality assertions but never looked at
  `test_github_ops.py`, which had two. Both broke on the new `body` key and surfaced only in the
  whole-tree test run.
- **⇒ The compounding shape D1 must weigh: an asserted closure that also SUPPRESSES the check that
  would have caught it.** A merely-incomplete sweep is recoverable downstream; an incomplete sweep
  carrying the authority to disable re-verification is not. That makes "closed set" claims a
  higher-severity sub-class than the other asserted fields this plan clusters, and it argues the fix is
  not just *derive the set* but *deny the claim the power to skip re-checking* — a closure assertion
  should never be a licence, only a hint.
- **Recurrence count: SIXTH.** D1 should treat the archetype as established and spend its budget on the
  fix shape rather than on re-proving prevalence.

## ⭐ SEVENTH RECURRENCE — folded 2026-07-28 from the PLAN-94 landing (#1040), inbox messages 003 + 004

**Two Q-Gate findings from one run, same root gap, different rule.** One governs the FIX SET, the
other governs the GUARD measured against it. Operator resolution `137ac5` settled both together, and
the pairing is the point — this is the same "asserted rather than derived" archetype at the outline's
own scope boundary, so it belongs to D1's cluster (a) / (b), not to a new plan.

**Instance A — a declared-but-unrun sweep froze `affected_files` (finding `13e1ce`, severity ERROR).**
Deliverable 2 declared a survey scope explicitly including `doc/**/*.adoc` and stated that *any* hit
beyond its two named files was in scope and corrected in the same deliverable — but `affected_files`
listed only those two. **Nobody had run the declared sweep.** Running it at Q-Gate time surfaced a
real, live third restatement at `doc/concepts/orchestration.adoc:31`. That path appeared in **no**
deliverable's `affected_files`, so the retrospective's `affected_files_recall` check could never have
seen it. The outline was also internally contradictory: the request's Constraints section limited the
change to two skill docs plus a test (excluding `doc/`), while D2's survey scope committed to
correcting any `doc/` hit — both statements in the same outline.

⇒ **Rule for D1's fix shape:** a declared-but-unrun sweep is a promise no downstream verification can
check, because `affected_files` is the only handle the recall check has. So: **run the declared sweep
at outline time before freezing `affected_files`**, enumerate the result including hits outside the
request's constraints, and treat an out-of-constraint hit as a **scope contradiction to resolve
explicitly** — either widen with a recorded authorization or narrow the declared scope and record the
un-swept surface as a deliberate documented exclusion. ⛔ **Never leave the pair
`{declared scope = wide, affected_files = narrow}` unreconciled — that pair is the signature**, and
it is machine-comparable (a declared glob vs the enumerated file list).

**Instance B — the regression detector's population was narrower than the fix set's (finding `3985e9`).**
Deliverable 3 specified a "population-derived detector" enumerating `*.md` under `MARKETPLACE_ROOT`.
Deliverable 2's declared survey scope was strictly wider — marketplace `*.md` **plus** `doc/**/*.adoc`
**plus** `CLAUDE.md` — and the one live hit sat **inside the gap**. The guard was therefore
**structurally incapable of failing on the one surface where the real hit was found**, and would have
shipped green.

⇒ **Rule:** when a plan (a) sweeps a surface for a contradiction and (b) adds a regression detector for
it, assert `detector_population ⊇ fix_set_population` **explicitly at outline time**, as a normative
line in the deliverable rather than an implicit consequence of the chosen root constant. Two further
carries: extend sentence extraction to the **AsciiDoc surface forms** (a Markdown-shaped tokenizer
silently skips every `.adoc` hit, and a wider-looking glob returns you to a vacuous population); and
add a **positive-population guard** asserting each surface slice is non-empty *and* that the known-hit
file is present in the enumerated population. That last is load-bearing — **without it, widening the
glob is unverified: a glob that matches nothing looks identical to a glob that matches everything.**

⭐ **This is TWO independent vacuity axes, not one** — and it extends, rather than replaces, the
recorded "every set-guarding detector must be population-derived" rule. Population-derived is not
enough if the source set you derive from is the wrong, narrower one; derive from the set the plan
actually corrected.

| Axis | Question | Guard |
|------|----------|-------|
| Predicate | Does the detector flag the bad content? | Negative fixture carrying the pre-fix text verbatim |
| Population | Does the scanned set contain the at-risk documents? | Positive-population assertion: slice non-empty **and** contains the known hit |

The population axis is the one routinely missed, because the fixture test passing *feels* like
sufficient proof of non-vacuity.

**Both instances were caught by an LLM Q-Gate pass; both comparisons are mechanical.** A deterministic
`phase-3-outline` check comparing (i) a deliverable's declared survey scope against its produced
`affected_files`, and (ii) a sibling guard's population against the fix set's, would retire the class.
D1 should weigh that as a candidate fix shape.

### D1 — GATE: cluster the defects + decide derive-vs-assert fixes (mutates nothing); split decision
Confirm each open defect at HEAD; group into (a) footprint/bucket derivation, (b) outline
completeness/closure, (c) phase-5 pre-flight integrity. Decide whether to split by that boundary.

### D2 — derive footprint/bucket/change_type from the write-set
- `2026-07-22-20-004` + `2026-07-22-16-001`: derive a deliverable's file-type bucket + module from Affected-files, never from narrative intent; a read-only reference file must not flip the bucket.
- `2026-07-16-20-001`: compose `change_type` by modal/majority across deliverables, not the first (outlier-first drops simplify/security-audit).
- `2026-07-16-12-001`: `keyword_drift` haystack must include the solution-outline analysis prose, not only title/metadata.

### D3 — outline completeness is closure, not existence
- `2026-07-21-17-004`: pass-1 must compute referrer/projection/claim-vs-index **closure**, not only that declared paths exist.
- `2026-06-28-17-001`: make the phase-4 §2.2 CERTAIN_INCLUDE coverage check lane/baseline-aware (stop over-firing on empty-baseline outlines).
- `2026-07-07-13-001`: phase-4 Step-7b derives affected_files/track from the solution outline, not the stale/absent manage-references store.

### D4 — phase-5 pre-flight & emission integrity
- `2026-06-29-02-001`: outline `get-module-context` resolves with a main-checkout fallback pre-phase-5 (worktree not yet materialized), not exit-2.
- `2026-07-21-11-002`: worktree materialization asserts local `main == origin/main` before branching (no silent foreign-commit inheritance).
- ~~`2026-07-21-17-005`: `[ARTIFACT]` emission decoupled from a single task-completion path.~~ ⛔ **STRUCK 2026-08-08 — DUPLICATE OF `PLAN-CIS-010` D3**, which owns it as a full deliverable *(`[ARTIFACT]` emission fires for every completed task, or its scope limit is declared in the output)* **plus a test**. Two plans in two different workstreams (WS-05 here, WS-04 there) were carrying one defect. **CIS-010 owns it** — it is the finalize-dispatch-evidence plan and the defect is an emission defect, not a scope-derivation one. ⚠ The one framing worth carrying across: the detection `artifact_entries>0` **cannot see the collapse**, so the under-emission is invisible to the check that would report it — CIS-010 D3 should say so.
- `2026-07-22-14-001`: q-gate deliverable-hash segmentation terminates the final deliverable at the next top-level `## `.

### D5 — misc authoring/integrity + tests + retire
- `2026-06-21-19-001`: Q-Gate auto-fix loop skips informational triage findings the re-entry guard can't act on (no burned iteration).
- ~~`2026-07-21-15-001`: plan-efficiency calibration table gains multi_module/broad/tech_debt rows + a superset cross-check.~~ ⛔ **STRUCK 2026-08-08 — THIS HALF IS ALREADY CLOSED AND THIS SPEC WAS ABOUT TO RE-SHIP IT.** Verified first-party against the lesson body (§ "Closed sibling concern"): the calibration table is now the exact cross-product of both live axes, every pair `anchored` or explicitly `fallback`-graded, and `test/plan-marshall/plan-retrospective/test_plan_efficiency_anchors.py` re-derives both axes from their owning sources and asserts set equality **in both directions**, so a new or retired enum value cannot ship unreconciled. ⇒ **Do not scope this.** The lesson's *other*, still-open half (`seconds_per_task` computed from wall-clock, grading operator idle time as agent cost) is **NOT this plan's** — it is folded into `PLAN-CIS-022`. ⚠ **The lesson is therefore NOT retirable by this plan alone**; retirement follows CIS-022's half.
- `2026-07-21-16-001`: delete-or-revive the dead discover-modules integration tier + strengthen its weak unit assertions.
- `2026-07-22-21-002`: ref-toon block-scalar authoring prohibition + collect-fragments internal-shape validation.
- Tests pin each; finalize retires all carried lessons.

## Lessons Carried (bound 2026-07-25 · lessons-triage) — all OPEN unless noted
Carry each at phase-1-init (`convert-to-plan`); retire at finalize.

- `2026-07-22-20-004`, `2026-07-22-16-001`, `2026-07-16-20-001`, `2026-07-16-12-001` (D2)
- `2026-07-21-17-004`, `2026-06-28-17-001`, `2026-07-07-13-001` (D3)
- `2026-06-29-02-001`, `2026-07-21-11-002`, `2026-07-21-17-005`, `2026-07-22-14-001` (D4)
- `2026-06-21-19-001`, `2026-07-21-15-001`, `2026-07-21-16-001`, `2026-07-22-21-002` (D5)

## Expected Surface
- `phase-3-outline` (pass-1 closure, get-module-context fallback), `phase-4-plan` (bucket/change_type/Step-7b derivation, keyword_drift haystack)
- `manage-tasks` q-gate segmentation; `prepare_execute` main==origin assert; phase-5 ARTIFACT emission
- `plan-retrospective` calibration table; discover-modules tests; `ref-toon-format` + collect-fragments

**Disjointness:** broad across outline/plan/phase-5 — the D1 gate may split. Coordinate with PLAN-57
(lane router, `manage-status`) and PLAN-41 (landed).

## `get-module-context` refuses in phase 3 on a worktree not materialized until phase 5

Observed on PR #1034 (message-supplied; HYPOTHESIS until re-verified at outline). `get-module-context`
refuses during **phase-3-outline** because it targets a worktree that `phase-5-execute` does not
create until later — the outline phase is asked to read a directory that cannot exist yet.

It lands here because this plan already owns outline-time scope derivation: a phase-3 consumer whose
precondition is a phase-5 artifact is a **derivation-order defect**, not a missing directory. ⚠ Check
whether outline should read the *main checkout* instead, or whether the worktree creation point
should move — the second option touches `phase-5-execute` and would collide with in-flight work, so
prefer the first unless outline genuinely needs worktree state.

## Premise verification checks a spec's CITATIONS but not its ASSERTIONS

Message-supplied, HYPOTHESIS until re-verified at outline. Verification confirms that the files and
symbols a spec **cites** exist, but never tests whether the spec's **claims about behaviour** hold.

#1037 is the proof: its D4(b) premise — *"a daemon restart yields an undeterminable fate"* — was
**false** (`replay_on_restart` renders `killed`), and every citation in that premise was valid. The
premise survived verification because verification was aimed at the wrong object.

⛔ **This is the Verify-First Contract's blind spot, and it sits squarely in this plan's scope.** The
contract already requires a HYPOTHESIS to name a confirm/refute artifact — but naming a real file is
satisfied by a citation check, so **a plan can pass premise verification while its mechanism claim is
wrong.** The deliverable is verification that reads the *implementing source* for the *behaviour*,
not the existence of the path.

⚠ Note the interaction with this plan's derive-not-assert theme: an assertion that survives because
its citations are valid is *worse* than an unverified one, because it now carries a verification
stamp.

## Path-derived preconditions belong at PLAN time

A plan whose footprint touched `.github/workflows/**` reached **finalize**, then failed to push
because the OAuth token lacked the `workflow` scope — **discovered at the most expensive possible
moment.**

**The rule, and it is this plan's own theme:** treat *"the change footprint includes
`.github/workflows/**`"* as a **plan-level precondition**.

1. When the solution outline or task plan names any path under `.github/workflows/`, flag the plan
   as requiring the `workflow` OAuth scope **up front**.
2. Verify the scope **before Phase 5 starts** — the authenticated token's scopes are queryable — and
   escalate to the operator then, when the cost is a token refresh rather than a stalled finalize.
3. If the scope cannot be granted, that is a **PLANNING INPUT**: the workflow-file change must be
   split out or handled by the operator, and **the plan should know before it writes the change.**

⭐ **Generalize rather than special-casing this path.** The durable rule is: *any precondition that
is a pure function of the footprint should be evaluated as soon as the footprint is known.* The
`workflow` scope is one instance; D1 should ask what else is footprint-derived and currently
discovered late. **A fix that only checks `.github/workflows/**` has learned the example, not the
lesson.**

## Second Evidence Fold (2026-07-29 — `truthful-signals-010`, API-Sheriff #2 — THIRD OBSERVATION)

`manage-status get-worktree-path` publishes a **tri-state** (`disabled` / `pending` / concrete path),
where `pending` is returned as `status: success`. `resolve_project_dir.py:228-237` reads only
`use_worktree` and `worktree_path` — **never the `worktree_state` discriminator** — and raises
`worktree_resolution_failed`. ⇒ **The exact bytes the producer calls a successful `pending` are
re-read by the consumer as a hard error.**

⚠ **BLAST RADIUS IS THE REASON THIS MATTERS MORE THAN ITS SIZE SUGGESTS**: this is the *shared*
routing helper, so **every script pairing `--plan-id` with `--project-dir` is unusable with
`--plan-id` for the ENTIRE pre-phase-5 window** — phases 1-4, exactly where outline and planning work
live. Observed consequence: `get-module-context` failed at phase 3 and the outline's
`## Architecture Hints` section was **omitted silently**, because the section is *defined* to be
omitted when its hint lists are empty — **an errored lookup is indistinguishable from a genuinely
empty one.**

⭐ **GENERALIZABLE RULE WORTH ADOPTING BUNDLE-WIDE, and the most reusable line in this fold**:
*"When a producer publishes an explicit discriminator for an n-state contract, consumers MUST branch
on THAT discriminator, not re-derive the state from primitive fields. Re-derivation is where 'success'
silently collapses into 'error'."*

## Evidence Fold — 2026-07-29, from `truthful-signals-012` item 1 and the PLAN-01 landing (#1056)

⚠ **Leads, not facts** — re-verify at outline.

**(a) A declared affected-file path that has NEVER existed, counted by three consumers, stat'd by
none.** The outline for `orchestrated-plan-detection-fails-silently` declared
`test/plan-marshall/marshall-orchestrator/test_finalize_orchestration_routing.py`. That path has never
existed — the real file is under `phase-6-finalize/`. The phantom path **propagated unchecked into the
scope estimate and the execution manifest**; three consumers counted it and not one performed an
existence check. ⭐ Corroborated from an unrelated source: CodeRabbit's rate-limit refusal comment on
#1057 enumerates the 5 files it would have reviewed and names the real `phase-6-finalize/` location —
confirming the true path without relying on the plan's own account. **This is the plan's core thesis
in its purest form: an estimate computed over a set that was never validated to exist.**

**(b) `inventory-blind-spot-003` — the same integrity failure one level up, at RULE-AUTHORING time.**
The request named **3** invisible sub-directory kinds; the measured population was **6 kinds / 138
markdown files (+4 non-markdown)**. An allowlist of the 3 named kinds would have left 8 files
invisible and re-broken on the seventh. ⭐ **The subtler half is the one worth carrying**: the first
outline correctly reasoned its way out of a *directory-name* allowlist, then specified the residual
rule as "any remaining **`.md`**" — name-free over directories but **enumerated over extensions**. The
blind spot simply moved axes. Worse, the plan's own population-derived regression test narrowed its
collection to `.md`, so **the test structurally could not detect the extension gap it existed to
prevent**.

⇒ **The recurrence signature this plan should be able to detect**, stated as the fold's takeaway: *a
rationale paragraph that correctly rejects an allowlist on one axis, immediately followed by a rule
that is an allowlist on a different axis* — and *a guard test whose collection step carries a filter
the rule it guards does not*. Both are derivable from the outline text plus the rule, which is this
plan's surface.

## Second Evidence Fold — 2026-07-29, from the PLAN-10 landing (#1059), `end-phase-...-012`

⚠ **Lead, not fact** — re-verify at outline. ⭐ **This is the plan's "derived, not asserted" thesis at
the EARLIEST point in the lifecycle — 1-init — and it is the instance with the clearest counterfactual
cost.**

Three `decision.log` lines from 1-init:

```text
[11:51:17Z] Request aspect classified: implementation (confidence=0.043)
[11:52:18Z] Classified scope_estimate=single_module (distinct_paths=1, glob=True, scope_resolved=True)
[11:52:55Z] Routed planning_lane=light (predicate=signal_set, fired=none, ...)
```

**Two independent signal-quality defects:**

1. **A near-zero confidence recorded as a settled classification.** `confidence=0.043` is 4.3 % — the
   classifier effectively abstained. The line records it in the same declarative form a 95 % result
   would get, and `request_aspect: implementation` is persisted to `status.metadata` **with no
   confidence qualifier**. ⛔ Downstream consumers read a fact; the classifier produced a coin-flip, and
   the routing predicate **cannot distinguish "classified implementation" from "guessed implementation
   at 4.3 %"**.
2. ⭐ **`distinct_paths=1` counted the POINTER, not the target.** The plan was launched with
   `task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-10-….md"`. The one
   distinct path the heuristic found was **the epic spec file** — the address of the instructions, not
   any file the plan would touch. **`scope_resolved=True` asserted the scope was resolved when what was
   resolved was where to read the brief.** The real footprint was 6 files across a widely-consumed CLI
   surface plus three test modules.

**The counterfactual cost is measured, not hypothetical.** The light route was wrong and the correction
was human (operator escalation on `trigger=premise`). Deep-lane discovery then found that
`_resolve_token_field` returns either a per-close delta **or** an already-cumulative value — so the
spec's implied blanket `+=` would have introduced a **new double-counting bug**. A light-lane outline
would plausibly have shipped it. ⛔ **And no automated check flagged the mis-route**:
`check-routing-decisions` reported `passed: 1, failed: 0` because it audits *which steps were pruned*,
not *whether the lane itself was right*.

**Remedy shape — note the third item, it is nearly free:**

1. Persist `request_aspect_confidence` alongside the classification and have `planning-lane` treat a
   sub-threshold aspect as an **unset signal**, not a value.
2. Teach `scope-estimate-heuristic` to recognise a **pointer-shaped request**: when the only distinct
   path is a `.plan/local/orchestrator/**/plans/PLAN-*.md` spec (or any `.plan/` artifact), scope is
   **unresolved** — emit `scope_resolved=False` and let the router route on absence. ⭐ **The
   `orchestrator inbox detect` verb already classifies exactly this pointer shape and is the seam to
   reuse** — do not write a second detector.
3. Log routing inputs **with their provenance**, so `distinct_paths=1` records *which* path. A
   pointer-derived route would then be visible in the log without an operator noticing it by eye.

⚠ **Orchestrator note on scope**: items 1–2 are `phase-1-init` / `manage-status` surfaces, not
`phase-3-outline`. They belong here because the *defect class* is this plan's — a scope figure computed
over an unvalidated set — but the split guard applies: if absorbing 1-init widens this plan past six
deliverables, split the init-side arm out and record the verdict.

## Evidence Fold — 2026-07-30, from `audit-report-path-ignores-plan-dir-002` (PR #1063, NOT yet merged)

⭐ **A reported defect LOCATION is a sample, not the defect** — a live, measured instance of this
plan's own thesis, contributed by a plan whose PR is still open.

**What happened.** The spec for `audit-report-path-ignores-plan-dir` named `write_persisted_report` as
the function that ignored the plan directory by calling `Path.cwd()`. Outline scoped its D1 to that
function. **The hypothesis was refuted on contact**: `write_persisted_report` never calls `Path.cwd()`
at all — it receives `repo_root` as a parameter. The single cwd-dependent site was its transitive
caller, `audit.py` `main()`:7065, and that one resolved value threads into **six** consumers.

⛔ **The blast radius was 6× the reported one, and the fix belonged to a different function than the
one named.** An outline that had trusted the spec's function name would have produced a deliverable
aimed at a site that does not exhibit the defect.

**Why it belongs to THIS plan and not to a lessons file.** It is the same archetype as "a reviewer's
list of call sites is a SAMPLE, not an enumeration", generalised one step: whoever reports a defect
reports **where they observed it** — a symptom site. The defect lives where the bad value is
*produced*, and the impact set is every consumer of that value. That is exactly this plan's
derived-not-asserted thesis, applied to the *inbound* premise rather than to the outline's own output.

**The rule the fold contributes to D3 (outline completeness is closure, not existence):**

1. **Verify the named site actually exhibits the reported behaviour** — read it; a spec's function name
   is not an established fact.
2. **Walk to the producer.** If the named site *consumes* a value rather than producing it, the defect
   is upstream.
3. **Enumerate the producer's consumers and state the count in the outline.** That count — not the
   reported site — is the deliverable's scope.

⚠ **Corroborating, not new.** This is the same family as the epic's standing rule 4 and the plan's
existing "Premise verification checks a spec's CITATIONS but not its ASSERTIONS" section — which is
precisely the gap this instance fell through. Treat it as a *second observation* of that named section
rather than as a new deliverable; the split guard above still binds.

✅ **Provenance caveat RESOLVED 2026-07-30 — the fold is now first-party corroborated.** When this
section was written PR #1063 was still open and the narrative was flagged as an unverified lead. It has
since merged as `d0da6742d`, and the orchestrator verified the substance against the merged diff:
`_resolve_repo_root()` is defined at `audit.py:667` and consumed at `:7259` (i.e. in `main()`, not in
`write_persisted_report`). ⚠ **The "six consumers" count is still the sending plan's** — corroborate it
yourself before making it the deliverable's scope, per rule 3 above.

## ⛔ Evidence Fold — 2026-07-30, from the PLAN-02 landing (#1067), `resolver-ext-point-seam-002`

⛔ **READ THIS BEFORE SCOPING D3. It falsifies the remedy this plan is most likely to reach for.**

⭐ **THREE instances of the archetype fired inside ONE plan — and that plan's own Overview explicitly
flagged the trap.** All three were caught, none reached main, and the reusable content is not the
archetype (already known at n≥8 here) but the **falsification of "warn about it in the plan text"** as a
control.

| # | Set claim | Stated | Real | Caught by |
|---|---|---|---|---|
| 1 | the spec's cited coordinate-join site | 1 | **2** (`_cmd_client_query.py` inline join + `_build_internal_deps_map`) | outline discovery — because it reads the tree, not the spec |
| 2 | `_build_internal_deps_map`'s callers | 3 | **5, plus an unenumerated 6th** derivation consumer (`render_module_markdown`, `_cmd_client_render.py:230`) | Q-Gate |
| 3 | deliverable 4's characterization fixture corpus | 2 of 5 poms | **5** | Q-Gate |

⛔ **Instance 3 is the sharpest thing in this fold, and it is a NEW failure mode for this plan's
thesis.** The omitted fixture (`legacy/auth-service/pom.xml`) carries the deliberately-duplicated
`com.example:auth-service` coordinate — precisely the input that meets the last-write-wins join. Because
a characterization test's job is to pin *current* behaviour, **the under-enumerated corpus would have
faithfully pinned the silent module-drop as EXPECTED behaviour**, converting a latent defect into a
green test that certifies it.

⇒ **Under-enumeration in a characterization corpus is not incomplete coverage — it is an active,
self-perpetuating endorsement of the bug.** Instances 1 and 2 fail loudly-ish (a missed call site
eventually breaks a consumer); instance 3 fails silently and permanently.

**The rule this contributes to D3 — a mechanical enumeration step, owned by whichever phase produces the
set:**

1. **Never carry a count forward from a spec, an outline, or a reviewer's list.** Re-derive it from the
   live tree at the moment of consumption.
2. **Derive call-site sets from the population** (`architecture find --pattern`, or a symbol query) and
   use the query output as the set. Never hand-transcribe a subset.
3. ⭐ **A characterization fixture corpus MUST be population-derived from the live corpus directory** —
   enumerate every fixture, then justify each **exclusion** explicitly. **Opt-out with a stated reason,
   never opt-in by selection.** An unstated exclusion is indistinguishable from an endorsement of the
   behaviour on the excluded case.
4. ⛔ **Prose warnings are not a control.** A plan that identifies an enumeration risk in its Overview
   must discharge it with a concrete enumeration step in a deliverable. This plan is the proof: it did
   warn, and it recurred three times anyway.

⚠ **Split-guard note.** This fold adds a *rule* to D3, not a deliverable. If D3 grows a fourth arm for
the characterization-corpus case, **split it out** rather than absorbing it silently.

⭐ **Companion recurrence, same landing (`-010`, staged separately as PLAN-CIS-021):** the same plan
reproduced the *invariant* it was written to eliminate, one abstraction layer up, in a document that
states the general rule three sections earlier. Together the two messages generalise this plan's thesis
from **enumeration** to **invariants**: *a stated invariant is not a checked invariant.*

## Evidence Fold — 2026-08-08, from `lessons-handling-26-08-08-01-005` (cluster C12, 17 instances)

⛔⛔ **THE SPLIT IS NOW MANDATORY, NOT A D1 OPTION — and this fold is what settles it.** The sender
handed C12 over undivided, flagging it as the second-largest cluster in the corpus and almost certainly
too large to fold whole, and deferred the cut to us because it depends on this plan's shape. **Decided:
this plan splits.** The § Overview's *"the D1 gate MAY split"* is superseded — **D1 splits, and records
the cut; it does not re-litigate whether to.**

The reason is not the instance count. It is that this spec already carries **five deliverables, a
Lessons-Carried list of fifteen, and ten evidence folds**, and C12 adds a further seventeen instances
across three distinct sub-groups. **Ten folds against five deliverables is the tell**: the folds have
been doing the work of deliverables without ever being counted against the guard.

### ⚠ SUBSTANTIAL OVERLAP — C12 is largely a re-enumeration of what this spec already binds

**Already carried, do NOT re-scope on them**: `2026-07-22-20-004` and `2026-07-22-16-001` (D2),
`2026-07-21-17-004` (D3), `2026-06-29-02-001` (D4, and again in § "`get-module-context` refuses in
phase 3"). `2026-07-26-16-001` is the same `get-module-context` worktree-state surface as
`2026-06-29-02-001` — **the sender flagged them as near-duplicates and they are: treat as ONE item**,
and note this spec's § "Second Evidence Fold (2026-07-29 — `truthful-signals-010`)" already names the
exact mechanism (`resolve_project_dir.py:228-237` reads `use_worktree`/`worktree_path` and never the
`worktree_state` discriminator).

⛔ **`2026-07-21-15-001` was ALSO in this cluster's sibling C08 and it produced a real correction** —
see the struck D5 line above. Its calibration half is **closed**; its `seconds_per_task` half belongs to
`PLAN-CIS-022`. **This spec was carrying a deliverable for finished work**, which is the exact
inverse of the defect this plan exists to fix.

### The cut — split along the sender's axis, which matches this spec's own D-boundary

| Arm | Sub-groups | Existing deliverables |
|-----|-----------|----------------------|
| **A — the derived SET is incomplete** (the sweep did not see everything) | C12 sub-group A (7) + sub-group C (4) | D3, and the closure/enumeration rules the folds contribute |
| **B — the derived BUCKET or classification is wrong** | C12 sub-group B (6) | D2, D4 |

⭐ **The axis is real and not merely convenient**: arm A is about **coverage** of a derived set and its
failures are *silent omissions*; arm B is about **classification** of an already-derived set and its
failures are *wrong routing* (a dropped profile, a skipped build, a mis-bucketed footprint). They have
different tests and different failure signatures. ⚠ **Whichever arm does not take the 1-init material**
(§ "Second Evidence Fold — 2026-07-29, PLAN-10 #1059" — pointer-shaped requests, `confidence=0.043`
recorded as settled) **must say so explicitly**; that material was already flagged as split-liable and
must not fall between the two arms.

### ⭐ The C12 members that add something genuinely new

- **`2026-07-29-19-001` — a staged spec premise EXPIRES; re-measure at outline, never inherit it.**
  ⛔ This is the sharpest member for *this epic specifically*, because our specs are long-lived and
  heavily folded — this very spec has folds dating back six weeks. It is also a Verify-First Contract
  concern, so `truthful-signals` has a claim on it; **the sender offered it either way and we take it
  here**, because the consuming action (re-measure at outline) is this plan's surface.
- **`2026-06-21-02-001` — outline mandated an edit to a symbol a prior shipped plan had already
  REMOVED.** The staleness archetype with a concrete failure, and the natural test for the item above.
- **`2026-07-28-19-004` — the planning-lane router's pre-override input is OVERWRITTEN by its output**,
  so an operator lane escalation leaves no auditable record of what the router got wrong. ⭐ Pairs
  directly with the #1059 fold's finding that `check-routing-decisions` audits *which steps were pruned*
  and never *whether the lane was right* — **the evidence needed to audit the router is destroyed by the
  router.**
- **`2026-07-25-19-001` — corroborating outputs of one extractor must share ONE input population**;
  retaining the wider input behind a no-op docstring keeps the false-fact channel open.
- **`2026-07-27-08-003` — a success criterion resting on PRE-EXISTING test coverage must locate that
  coverage at authoring time**, or the change ships unsubstantiated.
- **`2026-07-29-18-009` / `2026-08-03-06-004`** — a plan can reproduce its own target defect in its own
  run, and a plan whose deliverable the lifecycle consumes at an already-passed phase is not
  self-exercising. Both are **already recorded epic-level rules**; carry as corroboration only.

**Claim labels** — OBSERVED: lesson ids, categories, sub-group membership; the already-carried overlap
and the struck D5 line (both verified by reading this spec and the lesson body first-party); the
five-deliverables / ten-folds count. HYPOTHESIS (verify-at-outline): that each remaining derivation gap
is still open. Confirm/refute artifacts: the `phase-3-outline` discovery-sweep pass, and
`manage-solution-outline`'s `get-module-context` worktree-state branch.

## Write-Boundary
Repository source + tests only; NO `.plan/local/orchestrator/` writes. See orchestration-model.md § Ledger Write-Boundary.
