# Run report — 290-auditor-detector-integrity (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/auditor-detector-integrity-in4tkx`    **PR:** _pending_    **Outcome:** completed

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) — loaded as the run's first action |
| `plan-marshall:ref-code-quality` | bundle path (`marketplace/bundles/.../ref-code-quality/SKILL.md`) |
| `plan-marshall:ref-code-quality` → `standards/error-handling.md` | bundle path — loaded because every deliverable here is a classifier or gate that must fail closed rather than emit an unsubstantiated clean verdict, which that standard governs |

The `plan-marshall` plugin was not exercised; every skill was read by bundle path, the route that works in a fresh clone.

**Skills deliberately not loaded**, with reasons, since loading unused skills is pure context cost:

- `pm-plugin-development:plugin-script-architecture` and `:plugin-architecture` — the diff adds no new executor entry point and no new skill; `_decision_line_shapes.py` is a private helper module beside its existing siblings (`_manifest_decide.py`, `_manifest_rules.py`, `_manifest_lanes.py`) and follows their established shape.
- `pm-dev-python:python-core` / `:pytest-testing` — the work is edits within existing modules and their existing test suites, matching the surrounding idiom.
- `plan-marshall:persona-security-expert`, `pm-documents:ref-asciidoc`, `plan-marshall:ref-workflow-architecture` — no security surface, no `.adoc`, no dispatch-topology change.

## Serialization note

The plan's Notes section requires this plan to sequence **behind** the plan fixing the same file's working-directory resolution (`310-main-sha-records-the-pinned-cwd.md`), and states the two must never run concurrently.

**Checked, not assumed:** plan 310 is still a bare `.md` at the epic root (never executed — an executed plan becomes a directory), and `list_pull_requests` showed no open PR touching it. So there was **no concurrent run**. The ordering preference was not honoured — 310 has not run at all — and this is recorded rather than silently resolved: 310 will now rebase onto a changed `audit.py`. The hard constraint (never concurrent) held.

## Deliverables

### D1 — the verification gate (mutates nothing)

The plan forbids fixing from the report text and requires each claim be confirmed or refuted **at its site** and classified, because the remedies differ. Every claim below was settled from source in this clone.

| # | Claim | Verdict | Mode | Evidence |
|---|---|---|---|---|
| C1 | A routing key is populated from one metadata field and never read from metadata | **CONFIRMED** | **A** | `audit.py::collect_inputs` read only `metadata.get("plan_source")`; `metadata.get("recipe_key")` had zero hits in the file. Producer exists: `manage-lessons/_cmd_auto_suggest.py` documents phase-1-init Step 5c writing `status.metadata.recipe_key`. Sibling live reader `_manifest_decide._read_recipe_source` iterates **both** fields |
| C2 | The scanned marker has zero production emitters; all occurrences are tests | **CONFIRMED as a defect — REFUTED as to cause** | **A**, not D | A literal sweep for `merge:acquired` and siblings does return three files, all tests — but only because production interpolates: `_locks_core.log_lock_event` emits `f'[LOCK] ({lock}:{event}) {lock_id}'`. The emitter is real and tested. The actual defect is a **path** mismatch: `_resolve_lock_log_path` writes `.plan/logs/`, the scan read `.plan/local/logs/` |
| C3 | The removal-cause pattern cannot match the emitter's contracted shape | **CONFIRMED** | **A** | `check-routing-decisions.py` `posture_cutoff` expected `execution_profile=…, dropped … (tier above posture cutoff)`; the emitter produces `[STATUS] lane_resolution — dropped {step} from phase_6.steps (execution_profile=…): {reason}`. Field order and trailing clause both differ, exactly as claimed |
| C3b | The other three patterns (re-derivation the plan demanded) | **RE-DERIVED — all three MATCH** | — | `unresolved_ask_provider_drop`, `simplify_inactive`, `ceremony_finalize_never` each checked against their own emitter. Variable segments verified too: `_log_prefilter_omitted` is called with the literal `'finalize-step-simplify'`, and the four ceremony gate names (`qgate`/`self_review`/`simplify`/`security_audit`) are all `\w+`-safe |
| C3c | **New, surfaced BY the re-derivation:** `decision_matrix` is an unenumerated removal mechanism | **CONFIRMED** | **A** | Rules 1 (`early_terminate_analysis`) and 6 (`verification_no_files`) narrow `phase_6` to `_ANALYSIS_MINIMUM = {lessons-capture, adr-propose, archive-plan}`, dropping **both** prunable steps with cause `decision_matrix` — which no pattern read |
| C4 | A guard whose precondition is its own subject | **CONFIRMED** | **A at the extreme value** | `check_input_integrity`: `execute_blind` tested `phase_tokens.get('5-execute', None) == 0`, false for an absent phase. Precondition = presence of the record whose absence it detects. Consequence is an **inverted severity**, not merely a miss |
| C5 | A drift warning that fires at every boundary | **NOT LOCATED** | — | See below |
| C6 | A pending count that cannot reach zero | **CONFIRMED** | **B** | `_qc_resolution` buckets `none`/empty/unrecognised to `pending`, and `add_finding` seeds **every** record `resolution: 'pending'`. `_qc_finding_genuine` counted all of them |

**C5 is reported as not located, not as refuted and not as fixed.** The plan labels it *"Rescued from a withheld proposal; re-derive"*, and the re-derivation did not find it. Sites checked: `_lane_keep_decision` (warns only when an `off` override hits an immune floor class — not 100%), `_ceremony_prefilter_warnings` (guarded: skips when the lane would have dropped the step anyway), and a sweep of every warning-shaped emission in `audit.py`. A 100%-firing warning was not found at any of them. Recording this as an open item is the honest outcome; guessing at a site and "fixing" it would be the exact defect this plan exists to close.

**The reporting contract, settled.** A check that cannot substantiate a verdict emits **`unmeasured`** and withholds its counts entirely — it does not emit `0`. The in-tree pattern this mirrors is `MetricsEndTimePresence` (`audit.py`), whose value fields are `None` on every unreadable state precisely so a caller cannot accidentally substitute a clean verdict for an absent one. Withholding rather than zeroing is load-bearing twice over: a zeroed count reads as health, and an absent `genuine_signal_count` keeps `retire-on-quiet` from recording a quiet run — so an unmeasured check cannot accumulate toward its own retirement.

**Split-guard check.** The plan's closing question — whether these members share a reporting seam, and whether the counts-noise member must be split out — resolves as: **they do not share one seam, and no split was needed**, because the deliverables were already scoped to separate surfaces. D2/D3/D4/D6 and C4 are in `audit.py`; D5 is in `check-routing-decisions.py` plus a new shared module. C6 (the counts-noise member, failure direction B) is the one whose remedy is opposite to the others' and it landed in its own commit against its own check.

### D2 — read the field live data actually carries

| | |
|---|---|
| **Commit** | `f5761fb` |
| **Change** | `collect_inputs` reads `('plan_source', 'recipe_key')` in the same precedence as the canonical live resolver `_manifest_decide._read_recipe_source`. The comment asserting the two were "equivalent for matrix purposes" is replaced by one naming the two producers and the resolver it mirrors |
| **Verification** | 7 tests. **Red-first confirmed**: the two `recipe_key` cases failed (`surgical_bug_fix` where `recipe` was expected); the five controls passed |
| **Beyond-diff** | `_read_recipe_source`'s own docstring described the audit as the one-directional surrogate it no longer is — corrected in lock-step |

### D3 — measure contention, or say unmeasured

| | |
|---|---|
| **Commit** | `751338a` |
| **Change** | Scans both global-log roots; reports `status: unmeasured` with a reason and **no counts** when no `lock-*.log` substrate exists; publishes the summary-metric only when measured |
| **Split decision (the plan required one, not absorption)** | The auditor absorbs the **scan**; the **emission** stays with the lock skill and is reported, not changed. Reconciling the two paths is that skill's surface, and an auditor that reads only where it believes the producer *should* write is the same defect facing the other way |
| **Verification** | 12 tests. End-to-end cases drive `_locks_core.log_lock_event`, assert **where** it wrote, and match the parser against a line it produced. **Red-first confirmed** by direct reproduction: a real emission landed in `.plan/logs/lock-2026-08-16.log` and the old scan returned `rows=[]` |
| **Distinguishability** | Asserted explicitly — `test_unmeasured_block_withholds_counts_and_says_why` (no `contended_plans:` at all) against `test_lock_log_present_with_no_merge_events_is_a_measured_zero` (`contended_plans: 0`) |

### D4 — partition the structural pendings

| | |
|---|---|
| **Commit** | `cfbe68b` |
| **Change** | The pending column splits into `pending_actionable` and `pending_structural`; only the actionable half counts as genuine. Both halves published, plus a per-plan `structural_pending` column |
| **Partition source** | Mirrors the fixed actionable-vs-knowledge split already shipped at `plan-marshall/scripts/_invariants.py` — the blocking gate's own rule, and the "proven pattern" the plan pointed to |
| **The stated property** | Each half now answers "what would make this zero?": the actionable half by resolving the findings, the structural half never — which is why it is not counted |
| **Deliberately unchanged** | The corpus matrix still counts structural rows (labelled, not deleted — the matrix answers *what was filed*, the split answers *what could be cleared*). The `auto-review` leg stays genuine for knowledge findings, because what it cost to catch is the point. `build_pending_pile` needs no exclusion: its mechanism is exactly `build-error.jsonl`/`test-failure.jsonl`, both actionable |
| **Verification** | 12 tests. **Red-first confirmed**: 10 failed, the 2 passing being negative controls that hold in both readings |

### D5 — branch on the recorded removal cause

| | |
|---|---|
| **Commit** | `482fde1` |
| **Change** | New `_decision_line_shapes` module renders the subtraction-record line for the writer and parses it for the reader — the plan's **preferred** remedy, one home for the shape. The reader matches **gate-agnostically**, taking the gate name as the cause |
| **Why gate-agnostic beats fixing the regex** | It closes both instances at once and prevents the third: `posture_cutoff` (drifted) and `decision_matrix` (never enumerated) are both recognised, and a gate added to the composer later needs no edit on the reading side. Coverage becomes a property of the shape, not of a list someone must remember to extend |
| **The vacuous-authority instance** | The pattern set's comment asserted each shape was *"copied verbatim from the emitter contract"*. `standards/decision-rules.md` **is** that contract, it was correct and current, and the pattern did not match it. Nothing observed the copy |
| **Why the tests never caught it** | The fixtures were hand-transcribed from the standards document and had drifted from it, encoding the same retired shape as the pattern — both halves of a tautology agreeing while neither matched production. They now render through the writer's own formatter |
| **Verification** | 41 tests in that module. **Red-first confirmed**: 7 failures against the old reader, including the `skip` → `fail` inversion that **is** the false mis-prune |
| **Beyond-diff** | The script docstring's "every one of the four mechanisms" and the reference contract's four-item prose list both corrected |

### D6 — the class guard

| | |
|---|---|
| **Commit** | `f3f55fb` |
| **Change** | New `suspect-zero-census` meta block: one row per registered check, each zero classified `structural` / `starved` / `disciplinary` / `no_block`, or `fired` |
| **Structural vs disciplinary** | The plan's required distinction. `structural` = the check declared `unmeasured`; `starved` = the corpus supplied no plans (the "one un-stubbed sibling away from non-zero" class); `disciplinary` = a non-empty corpus was examined and nothing was genuine. `structural` outranks `starved`, since the check's own declaration is stronger evidence than the corpus size |
| **Relation to `retire-on-quiet`** | The inverse reading of the same streak, computed from one shared derivation (`quiet_streaks`) so the two cannot disagree about the streak while disagreeing about its meaning. Publishing only the retirement reading is what lets a **broken** detector be retired as redundant — strictly worse, because retiring it closes the case |
| **Scope** | Reporting only, per the plan: proposes nothing, removes nothing, blocks nothing |
| **Honest limit, recorded in SKILL.md** | A `disciplinary` zero is **not** a clean bill of health for the check. A predicate reading a field live data never carries reports `disciplinary` on every run. The census narrows where to look; it does not remove the need to read the predicate against its producer |
| **Verification** | 15 tests, including the plan's stated acceptance (a deliberately-starved detector surfaced as suspect and classified) **with a discriminating half**, so the case cannot pass on a census that calls everything structural |

### C4 — the guard whose precondition is its own subject

| | |
|---|---|
| **Commit** | `04b7b0f` |
| **Change** | `execute_blind` now treats an **absent** `5-execute` phase as blind, not merely partial |
| **Why it matters more than a miss** | The severity was **inverted**: a plan recording `5-execute` at zero graded `blind`, while a plan with no `5-execute` section at all — strictly less recorded — graded only `partial`. The plans most blind to their own cost were the ones the confidence read-out was least worried about |
| **Deliberately preserved** | The marker-explained carve-out. A phase the recorder knows was never closed stays `partial`, so the widened guard does not trade a false-clean verdict for a false-alarm one |
| **Verification** | 5 tests. **Red-first confirmed** most directly by the ordering test: `assert 1 >= 2` — absence at `partial` against a recorded zero at `blind`, which is the inversion itself |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (5 Python files: `audit.py`, `_decision_line_shapes.py`, `_manifest_decide.py`, `manage-execution-manifest.py`, `check-routing-decisions.py`, plus 8 test modules), so the full gate ran.

`./pw verify` → **`=== verify: SUCCESS ===`**, **20,510 passed, 14 skipped, 0 failed** (444 s). All three sub-steps clean: quality-gate (`ruff` all checks passed, `mypy` success over 411 production files, SPDX passed), test-compile (`mypy` over 761 test files), module-tests.

A per-commit `./pw quality-gate` ran before every commit touching `*.py`. Two caught real defects before they landed: an `F402` where a loop variable shadowed the `dataclasses.field` import, and a `mypy` narrowing conflict where a rebound name collided (which also surfaced a parameter shadowing the new `quiet_streaks` function).

No lockfile churn reached any commit — `git status` was checked before each, and every commit staged its deliverable paths explicitly rather than by `git add -A`.

**Working-tree claim, re-verified after the build:** `git status --porcelain` is empty at the time of writing, after `./pw verify` ran.

## Findings

Per instance, not bundled.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | D1 gate | `recipe_key` never read from metadata — Row 2 structurally unreachable for auto-suggest-routed plans | **Fixed** (`f5761fb`) |
| F2 | D1 gate | The `[LOCK]` scan root is one directory above the emitter's write path | **Fixed** on the auditor side (`751338a`); emission left to the lock skill by explicit split decision |
| F3 | D1 gate | The claim "zero production emitters" is **wrong about the cause** — production emits by interpolation | **Recorded as a refutation.** The defect is real, the diagnosis was not; fixing the predicate (Mode D's remedy) would have achieved nothing here |
| F4 | D1 gate | `posture_cutoff` pattern cannot match its emitter | **Fixed** (`482fde1`) |
| F5 | D1 re-derivation | `decision_matrix` is an unenumerated removal mechanism dropping **both** prunable steps | **Fixed** (`482fde1`) — surfaced only because the plan demanded the other members be re-derived |
| F6 | D1 gate | `execute_blind`'s precondition is the presence of the record whose absence it detects; severity inverted | **Fixed** (`04b7b0f`) |
| F7 | D1 gate | Quality-chain `pending` mixes actionable debt with pending-by-construction knowledge findings | **Fixed** (`cfbe68b`) |
| F8 | D1 gate | The "warning that fires at every boundary" could not be located at any site checked | **Open — reported, not guessed at.** See D1's C5 row for the sites examined |
| F9 | D5 | The routing-decisions test fixtures were hand-transcribed from the standards doc and had drifted from it, so the suite certified a reader that matched nothing production emits | **Fixed** (`482fde1`) — fixtures now render through the writer's own formatter |
| F10 | Build gate | `F402`: loop variable `field` shadowed the `dataclasses.field` import in the D2 change | **Fixed** before commit |
| F11 | Build gate | `mypy` assignment-narrowing conflict in `suspect_zero_census`; the same read surfaced a parameter shadowing the `quiet_streaks` function | **Fixed** before commit |
| F12 | Beyond-diff sweep | `_read_recipe_source`'s docstring described the audit as a one-directional surrogate it no longer is | **Fixed** (`f5761fb`) |
| F13 | Beyond-diff sweep | Two era/registration tests asserted `status: success` for *every* check block, which the `unmeasured` state makes false | **Fixed** (`751338a`) — the era test now pins its real contract (the stamp follows `status:`, whatever its value) |
| F14 | Beyond-diff sweep | `merge-window-accounting.md` stated the lock lines live in `.plan/local/logs/` and share a corpus with `global-log-analysis` — both false | **Fixed** (`751338a`) |
| F15 | Beyond-diff sweep | The routing-decisions script docstring and reference contract both carried a stale "four mechanisms" enumeration | **Fixed** (`482fde1`) |
| F16 | Serialization | Plan 310, which the plan requires to run first, has not run; it will now rebase onto a changed `audit.py` | **Reported, not resolved** — the hard constraint (never concurrent) held; the ordering preference did not |

### Verification sub-agent, round 1

The round returned **twelve** findings against the change. The severe one is recorded first because it is the plan's own subject matter committed by the plan's own deliverable.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| V1 | **HIGH** | **D4 published a false zero.** `_qc_structural_pending` re-read the record's `resolution` while `_qc_resolution` short-circuits `promoted` → `lesson`. Numerator and denominator came from two derivations of the same population, so `actionable = pending − structural` underflowed: a promoted `tip` alone gave `pending_actionable: -1`, and a promoted tip beside a genuinely pending `build-error` gave `pending_actionable: 0` — real chain debt published as none | **Fixed.** The predicate takes the computed bucket as a parameter, so containment holds by construction. Five cases added for the boundary the exhaustiveness assertion never staged |
| V2 | MEDIUM | The retired `.plan/local/logs/` claim survived in the merge-window section comment, fifteen lines above the constant documenting that it is false | **Fixed** |
| V3 | MEDIUM | The census classified `quality-chain` `disciplinary` on a **defaulted** count — that block emits `plan_genuine_signal_count`/`finding_genuine_signal_count` and no bare one, so no count was ever read | **Fixed.** An unread count is `None`, with its own `no_count` class |
| V4 | MEDIUM | `_classify_zero` used the whole corpus size while the nine delivery-cost checks run over the shipping partition, so a check that examined nothing was called `disciplinary` | **Fixed.** `_examined_population` reads the `plans_excluded_non_shipping` the block already carries |
| V5 | MEDIUM | The `merge_window_ci_rerun` synthesis coupling rendered `contended_plans=0` on an unmeasured run, re-manufacturing the false zero downstream | **Fixed** |
| V6 | MEDIUM | `recompose_divergence` counts lines, not composes — the same emitter change that broke `posture_cutoff`, reaching a second consumer in the same file | **Claim fixed, count left as-is** (reconstructing composes needs a per-compose delimiter the emitter does not provide; that belongs with the composer). Corrected at all three sites |
| V7 | LOW | The `_invariants.py` mirror is one-directional — exact for the knowledge half, not the actionable half, which leaves `bug`/`anti-pattern`/`triage` in neither set | **Fixed.** The comment now claims only the half that holds |
| V8 | LOW | The shared-shape gate enumeration omitted `terminal_emission_orchestration_gate` — wrong on its first read, having just replaced an enumeration that was wrong | **Fixed** by de-enumerating and pointing at the live call sites |
| V9 | LOW | The D2 comment named the wrong producer: Step 5c-LESSON writes **both** fields, so it was never the gap | **Fixed.** Now names Step 5c-recipe-match's auto-route and operator-selection legs, which write `recipe_key` alone |
| V10 | LOW | `build_pending_pile`'s rationale was an unearned absolute | **Fixed** (caught independently mid-run and already corrected before the round reported) |
| V11 | LOW | D6 had no end-to-end assertion joining the real emitter to the real classification — the "suite synthesises its own marker" shape the plan names for D3 | **Fixed.** The new test earned itself immediately: it caught `no_count` masking `structural` on a real sweep, a precedence defect introduced by the very commit that added it |
| V12 | LOW | The census does not census itself — `suspect-zero-census` and `retire-on-quiet` are not in `CHECK_NAMES`, so the class guard's own permanent zero is the one class it cannot report | **Documented, not resolved.** Recorded in SKILL.md as mode E standing unresolved in the instrument built to surface it; an instrument whose blind spot is undocumented is read as having none |

### Verification sub-agent, round 2

Round 2 ran `./pw verify` itself (round 1 had not), confirmed **all twelve** round-1 fixes real and complete — re-deriving V1's arithmetic exhaustively over 3,300 type × resolution × `promoted` × filename combinations, with containment holding by construction and zero violations — and reproduced both pre-fix defects in-process, so the round-1 tests are genuinely red-first.

It then found **fourteen** more. None was a behavioural regression; the two severe ones are the same defect class as the round-1 fixes, one step further out.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| W1 | MEDIUM-HIGH | **The census reported a FIRING detector as suspect, on every run.** `quality-chain` publishes per-tier genuine counts and no bare one, so the count was never read, the class was always `no_count`, and `suspect: true` was published on every full sweep — including runs where the check produced signals. D6's charter is to surface a detector that produced *zero* positives; this one had not | **Fixed.** The reader recognises and sums the per-tier spelling. Round 1's fix had moved the defect from a false `disciplinary` to a false `suspect` rather than making the count readable |
| W2 | MEDIUM-HIGH | **The examined population covered one narrowing axis of two.** `exploration-share` and `billing-composition` narrow on a second, independent axis and both read `disciplinary` over a population of zero — publishing verbatim the sentence `_examined_population`'s own docstring says it exists to prevent | **Fixed.** `plans_in_corpus` — the check's own statement of what it examined — is read first, so a check growing a third axis needs no edit here |
| W3 | MEDIUM | **The shared formatter had a second writer.** `_log_pre_push_quality_gate_omitted` hand-wrote the identical shape, so the reader matched it by coincidence of copied text — the arrangement the module exists to end, surviving inside the change that introduced it. Its "one home" claim was also broader than the module's actual scope | **Fixed.** Routed through the formatter; the scope clause names the four gates that render their own untagged lines |
| W4 | MEDIUM | Two "every check reports a `genuine_signal_count`" statements, both falsified by the round-1 fixes and left standing | **Fixed** |
| W5 | MEDIUM | `checks/quality-chain.md` still asserted the `_invariants.py` mirror is bidirectional, contradicting the code comment the same round had corrected | **Fixed** — one claim had been corrected in one of its two statements |
| W6 | MEDIUM | `routing-decision-verification.md` over-claimed that no mechanism can become invisible; a gate rendering its own line still can, and `frozen_manifest_stale` (the `reconcile` verb) already does | **Claim fixed; the gap recorded.** The live counter-example is named in the doc and carried to Residue |
| W7 | LOW | `_parse_step_tokens` described a list-repr form no live emitter produces, and partitioned a mechanism set that had gained a fourth family | **Fixed** — and the retired form is retained deliberately, for archived logs written under the old emitter |
| W8 | LOW | SKILL.md said "eight" delivery-cost checks; `DELIVERY_COST_CHECKS` holds nine, and SKILL.md's own table marks nine rows | **Fixed** |
| W9 | LOW | The resolution-bucket table omitted `rejected` and understated `pending` (which is also the catch-all for any unrecognised disposition) | **Fixed** |
| W10 | LOW | My own W-round enumeration missed `arch-constraint` and `pr-comment-overflow`, and misattributed why they leave the pending column (`arch-constraint` is documented non-promotable) | **Fixed** — the conclusion held; the stated grounds did not |
| W11 | LOW | `_examined_population` had no end-to-end test; its correctness rested on an unpinned call order that a three-line move would silently regress | **Fixed.** A test drives the real `run_checks` |
| W12 | LOW | The SKILL.md merge-window row lacked the `unmeasured` state that two other sites had gained | **Fixed** |
| W13 | LOW | The re-derivation obligation pointed at `decision-rules.md`, which does not enumerate every gate | **Fixed** — repointed at the emitters themselves, so a doc-only re-derivation cannot miss a live mechanism |
| W14 | LOW | `report-01.md`'s build-gate figure predates the fixes it reports as landed | **Fixed** at the end of the run — see § Build gate, which now records the final re-verify |

**What round 2 could not verify**, recorded rather than assumed: the historical claim that the retired aggregate emission wrote one `lane_resolution` line per compose (repo history is effectively squashed, so it is plausible and harmless but unverified from this clone); the audit corpus, which the plan declares unreachable and forbids looking for; and C5, the unlocated 100%-firing warning, which it did not re-derive and on which it has no evidence either way.

**What round 1 verified clean** — so the list above is distinguishable from a pass that examined nothing: the D5 shape contract against all five live `_log_dropped_records` call sites and against `decision-rules.md`'s canonical renderings; the three surviving removal-cause patterns against their own emitters; that no unrecognised mechanism can remove a `_PRUNABLE_PREDICATES` member; the `_read_recipe_source` mirror; both `[LOCK]` path derivations; the retire-on-quiet streak mechanism; the absent-phase reproduction against the pre-change detector; that `add_finding` seeds every record `pending`; that an omitted summary-metric renders as `""` and never `0`; a retired-token sweep (no surviving `posture_cutoff`, no surviving "four mechanisms", no fixture encoding the retired line shape); the `status: success` sweep; the cross-skill import against `plugin-script-architecture`'s standard; and TOON quoting of the census `reading` column.

## Reviewer participation

_To be completed after the PR is opened and the reviewers report._

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a token counter to the running agent, so no figure is stated rather than an estimated one.
- **Wall-clock:** not separately instrumented. The one measured component is the full `./pw verify` at **444 s**; the per-commit `./pw quality-gate` calls and the targeted `uv run pytest` calls (order-of-seconds each) are not individually timed.
- **Population:** what little is measured above covers **this single Claude Code cloud session's build invocations only**. ⛔ It is **NOT** comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a boundary a single interactive cloud session does not share. The figures cannot be made comparable, so no comparison is offered.

## Contract check (Step 9)

_To be completed as the run's final pre-merge commit._

## What have we learned (Step 9)

_To be completed._

## Residue

- **F8 — the unlocated warning (C5).** The plan's "drift warning that fires at every boundary" was not found at any site examined. It should go to whoever holds the withheld proposal it was rescued from, since the re-derivation this run performed was not sufficient to locate it.
- **F2's emission half.** `_locks_core._resolve_lock_log_path` writes the lock timeline to `.plan/logs/` while every other global log lives in `.plan/local/logs/`. This run scanned both rather than changing the emitter, per the plan's explicit exclusion. Whether the two roots should be reconciled belongs to a `manage-locks` plan; the auditor is correct either way now.
- **F16 — plan 310.** It now rebases onto a changed `audit.py`. The overlap is small (its subject is working-directory resolution; this run touched `collect_inputs`, the merge-window scan, the quality-chain partition, `check_input_integrity`, and added a census block), but it is not zero.
