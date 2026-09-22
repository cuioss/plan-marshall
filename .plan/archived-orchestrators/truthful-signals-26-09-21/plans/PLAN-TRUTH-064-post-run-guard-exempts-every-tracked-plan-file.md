# PLAN-TRUTH-064: The post-run source guard exempts every tracked file under `.plan/`

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.

## Objective


`post_run_source_guard` exists to catch tracked source a finalize step left dirty with no
push path. It filters out everything under `.plan/` on the assumption that `.plan/` is plan
state and therefore never tracked. That assumption is false for 14 files, including
`.plan/marshal.json` and every `project-architecture/*/enriched.json`. The guard therefore
reports `clean: true` over precisely the paths where an unpushable tracked edit is most
likely — architecture-enrich writes at the end of finalize. This plan makes the predicate
depend on trackedness rather than on a path prefix, so the guard's clean verdict means what
it says. This is the #990 defect class re-entering through the guard built to close it.

## Deliverables

1. Replace the unconditional `.plan/` prefix exemption with a predicate that exempts a
   `.plan/` path only when it is NOT git-tracked, so tracked `.plan/` files are reported as
   offenders like any other tracked source.
2. Publish the guard's examined population in its own output (paths considered, paths
   exempted, and why) so a `clean: true` is distinguishable from a *looked-at-nothing* pass —
   the epic's standing rule that a zero must carry its population.
3. Tests: a positive control (a dirty tracked `.plan/` file IS reported) and a matched
   negative control (a dirty UNtracked `.plan/` file is NOT reported); the guard must fail
   today against the positive control.
4. Decide and document the disposition path for a legitimately-dirty tracked `.plan/` file at
   finalize (architecture-enrich hints are the recurring instance) — the guard reporting it is
   the goal, but the run needs a stated remedy rather than a new recurring block.

Four deliverables — under the ~6 split guard, no split. Rationale recorded at staging.

## Claim Labels

- OBSERVED: the guard filters on a bare path prefix, unconditionally — read at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py`
  § `_PLAN_STATE_PREFIX` (`'.plan/'`) and § `filter_tracked_source` (returns
  `{p for p in paths if not p.startswith(_PLAN_STATE_PREFIX)}`).
- OBSERVED: the filter runs AFTER the porcelain observation has already restricted to tracked
  paths, so every path it drops is known-tracked — read at the same file § `check_tracked_source`.
- OBSERVED: 14 files under `.plan/` are git-tracked, including `.plan/marshal.json` and 13
  `project-architecture/*/enriched.json` — derived from `git ls-files .plan/` at this analysis
  (count re-derived at the moment of the claim, n=14).
- OBSERVED: the live instance — `.plan/project-architecture/{default,plan-marshall}/enriched.json`
  dirty on main after PR #1115's finalize, 4 architecture hints added, guard reported clean.
- HYPOTHESIS: the guard's docstring rationale ("Every finalize step legitimately writes plan
  state under `.plan/`") is the origin of the assumption and is the right place to correct the
  contract — confirm/refute at the same file § module docstring lines 37–42 (verify-at-outline).
- Verify-first clause: re-derive the tracked-file set with `git ls-files .plan/` against HEAD
  before scoping. If that set is empty at outline time, the premise is refuted and the plan
  re-scopes — the defect is only live while tracked files exist under `.plan/`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py`
  — `_PLAN_STATE_PREFIX`, `filter_tracked_source`, `check_tracked_source`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the 6
  `post_run_source_guard` references (contract prose)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_post_run_review_ordering.py` — 3
  references; new controls land here or in a sibling module
- HYPOTHESIS: no second consumer re-implements the prefix filter — confirm/refute by a
  content search for `_PLAN_STATE_PREFIX` and `.plan/` prefix filtering across
  `phase-6-finalize/scripts/` (verify-at-outline)

## FOLDED IN 2026-08-08 — the plan that produced the dirty files also filed the owed call

`a-rule-that-is-green-because-it-examined-nothing-026` and `-027` both report an **owed
`architecture enrich` call** — the two messages are the producing side of the same event this
spec's live instance describes from the guard side. ⇒ The dirty `enriched.json` pair is not a
stray edit: it is an enrich write the run knew it owed. **Two messages, one event** — counted as
one instance, not two.

⭐ **This sharpens D4.** The remedy question is not *"what do we do with an unexpected dirty
file"* but *"a finalize step legitimately produces a tracked `.plan/` write, and there is no
push path for it."* D4 must answer that, not merely surface it — otherwise the fixed guard
converts a silent hole into a recurring block on every plan that enriches.

## ⭐⭐ POPULATION DERIVED 2026-08-08 — THIS IS NOT ONE SITE, AND THE SPEC SAID IT WAS

The Objective above describes `post_run_source_guard` as *the* guard with this hole. **Swept at HEAD:
six non-test production files carry a literal `.plan/` path exemption**, and at least two implement
the same *tracked-file-invisible* logic:

| Site | `.plan/` refs | Status |
|------|--------------:|--------|
| `phase-6-finalize/scripts/post_run_source_guard.py` | 11 | ⛔ **CONFIRMED same defect** — `_PLAN_STATE_PREFIX` / `filter_tracked_source` |
| `plan-marshall/scripts/_invariants.py` | 9 | ⛔ **CONFIRMED same defect** — `_filter_main_dirty_paths` (`:445`) drops every `.plan/`-prefixed path from the layer-D main-dirty invariant, on the same "normal bookkeeping" rationale. Found via `PLAN-TRUTH-046`'s surface correction. |
| `extension-api/scripts/_path_attribution_merge.py` | 6 | ⚠ **UNCLASSIFIED — check at D0** |
| `plan-retrospective/scripts/check-manifest-consistency.py` | 2 | ⚠ **UNCLASSIFIED — check at D0** |
| `plan-retrospective/scripts/check-routing-decisions.py` | 1 | ⚠ **UNCLASSIFIED — check at D0** |
| `marshall-steward/scripts/gitignore_setup.py` | 21 | ✅ **EXPECTED — not a defect.** This file's job *is* `.plan/` gitignoring; it is the matched negative control. |

⭐ **The two confirmed sites fail identically and independently**: each drops a path on a *prefix*
rather than on a *property of the file*, so each is blind to the same 14 tracked `.plan/` files. A fix
to one leaves the other live. ⛔ **This is why D1 must be stated as a shared predicate, not as an edit
to one function** — otherwise this plan fixes the guard that was noticed and leaves the invariant that
was not.

⚠ **The three UNCLASSIFIED rows are a floor, not a verdict.** They were found by a literal-string sweep
and have not been read. **D0 classifies each as same-defect / different-purpose / negative-control and
publishes the classification** — a count of six with three unexamined is exactly the *volume-read-as-
coverage* failure this epic tracks.

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none currently running. **PLAN-TRUTH-045** (dispatch audit) and
  **PLAN-TRUTH-054/058** (`_cmd_baseline_reconcile.py`) are different files in the same
  finalize surface — no file overlap.
- Adjacent to: the architecture-enrich writer that produces the dirty hints. This plan does
  NOT change what enrich writes or when; it changes only whether the guard can see it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-064-post-run-guard-exempts-every-tracked-plan-file.md"
```

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -057

**Component:** `phase-6-finalize (footprint truthfulness)` · **Deliverables after merge: 8** (raised cap is 12).

Both plans are the same defect at two ends: **a finalize step acting on a file set that is not the
file set it actually touched.**

- **`-064`** — the footprint the guard is allowed to *see*. Two confirmed sites drop paths on a `.plan/`
  prefix rather than on a property of the file, so 14 tracked files are invisible to both.
- **`-057`** — the footprint a step is *told about*. `affected_files` is absent on 17 of 246 corpus
  files and, more importantly, **under-recorded when present** (the 19-vs-37 finding): a plan whose
  scope moves during execute keeps the narrower list.

⭐ **Why they must ship together**: fixing the guard while the declared footprint stays narrow just
moves the blind spot — the guard now sees correctly and is handed a wrong list. Both are "the set of
files this step believes it is responsible for", and they share consumers.

⛔ **`-057`'s premise was REFUTED as stated** (the key is present on 229 of 246) and re-scoped to
inconsistent-writing + under-recording. **Do not implement the absent-key remedy** — it fixes 6.9% and
leaves the silent half.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count deliverables at outline.** The figure above is the sum of the pre-merge counts; overlapping deliverables should COLLAPSE rather than concatenate, and a merged plan that still reads as two plans stapled together has not been merged.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}`
message — the orchestrator owns every other ledger write — and reports its outcome through
its PR and its inbox message.


---

## ⭐ FOLDED FROM THE 2026-08-09 INBOX DRAIN — 2 messages, and one of them is this spec's own D0 answered from outside

**`daemon-...-015` (candidate-lesson).** *The post-run-band dirty-tree guard excludes `.plan/`, but
`.plan/project-architecture/**` is **TRACKED**.* ⇒ **Independent confirmation of this spec's core
claim, from a different plan.** The guard's blanket `.plan/` exemption is not a safe over-approximation:
it exempts tracked files, so a tracked, modified, unpushable path is invisible to the very guard that
exists to catch it. ⭐ **This spec's population of confirmed sites stands at 3** (`post_run_source_guard.py`,
`_invariants.py:_filter_main_dirty_paths`, and the tracked-path case named here), with
`gitignore_setup.py` as the legitimate negative control.

⚠ **And it is LIVE on main right now**: two `.plan/project-architecture/*` descriptors are dirty and
unpushable as of 2026-08-09, with the operator's land-or-discard decision open. **The defect is not
hypothetical while this spec is staged.**

## ⭐ ABSORBED SPEC POINTER — `affected_files` (PLAN-TRUTH-057 merged here 2026-08-08)

**`provider-...-008` (L8, and the sender labelled it RECURRENCE itself).** *`references.affected_files`
is **frozen at outline time**, so every derived finalize gate under-scopes.* ⇒ this names the
**mechanism** behind the instances this epic has been collecting:

1. PLAN-CIS-001 — a 19-vs-37 gap;
2. #1123 — **701 approved-but-undeclared lines** absent from every deliverable's `affected_files`;
3. this message — the general form: **frozen at outline, so any scope movement during execute is lost.**

⛔ **The three are one defect and the fix is at the freeze point, not at the consumers.** Patching each
derived gate to re-derive its own scope would multiply the source of truth — the field must be updated
when scope moves, or every consumer must be taught it is a *declaration*, never a *record*.
⭐ **Approval is not recording**: #1123's widening was legitimate and still never reached the manifest,
so a fix keyed on "unsanctioned scope" would miss the confirmed instance.
