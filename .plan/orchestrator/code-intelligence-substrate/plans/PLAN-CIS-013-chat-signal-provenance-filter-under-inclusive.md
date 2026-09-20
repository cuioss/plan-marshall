# PLAN-CIS-013: Chat-Signal Health Verdict Is Volume-Derived — It Strengthens As Signal Degrades

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-07-26 from a cross-epic finalize report (PR #1012, test-suite-quality epic) which
> reported: *"extract-chat-signal reports healthy while feeding instruction text — the health verdict
> is volume-derived so it strengthens as signal degrades."* Companion to lesson `2026-07-26-22-005`.
> **The operator's report was a lead; the mechanism below was then verified first-party against the
> shipped source at HEAD.** This is the epic's flagship archetype in its purest observed form: a
> metric that improves precisely as the thing it measures gets worse.

## Objective

`extract-chat-signal.py` decides Tier 1 (feed the reduced transcript to the LLM) vs Tier 2 (refuse,
`transcript_too_large`) from a single flag, `no_signal`, computed as *"did the reduction keep zero
turns?"* Its `user`-turn provenance filter drops only two synthetic classes — empty turns and
skill-load injections — so every other harness-authored `user` turn survives and counts as operator
signal. Make the health verdict reflect operator-authored signal rather than surviving volume.

## ⚠ Mechanism — OBSERVED, verified first-party at HEAD

Read directly from
`marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py`:

- OBSERVED — `is_signal_bearing` (`:149-162`) keeps a `user` turn unless it is blank
  (`:157-158`) or matches `is_synthetic_skill_load` (`:159`). **Those are the only two exclusions.**
- OBSERVED — `is_synthetic_skill_load` (`:105-116`) fires only on the literal
  `_SKILL_LOAD_MARKER = 'Base directory for this skill:'` (`:101`) followed by a markdown heading.
  It recognizes **one** injection shape.
- OBSERVED — `no_signal = len(turns) == 0` (`:264`). The verdict is a pure count of survivors; it
  carries no notion of what the survivors *are*.
- OBSERVED — the docstring (`:37-41`) asserts the surviving set *"is now operator-authored content
  **by construction**"*. **The implementation does not establish that.** Harness-authored `user`
  turns that carry neither an empty body nor the skill-load marker pass the filter unchanged.
- **Therefore the failure is compounding, not merely incomplete.** Each additional class of injected
  instruction text raises the survivor count, which drives `no_signal` further from `True`, which
  reports *more* health. Signal quality and the reported verdict move in opposite directions.

### This is a recurrence of the defect the same file documents as fixed

The docstring (`:21-25`) records the original incident: filtering by role alone left the reduced
transcript *"dominated by framework boilerplate (measured: ~90% of 285 KB, fewer than 10 of 287 turns
operator-authored)"* and *"a transcript with almost no operator signal was confidently classified
Tier 1."* The fix enumerated **two** synthetic classes. The failure mode was never the two classes —
it was **enumerating** at all, against a harness that adds injection shapes over time. #1012 is the
same sentence recurring against the same file.

**Fifth instance of the vacuous-authority / defending-documentation family** (after PLAN-73, PLAN-74,
PLAN-75, and PLAN-CIS-016's `decision-rules.md:475`): a docstring asserting a property "by construction"
that the construction does not provide.

## Deliverables

### D1 — GATE: enumerate what actually survives, then choose allow-list vs deny-list (mutates nothing)

Run the reducer over real session transcripts and **classify the surviving `user` turns by
provenance**. The known-suspect classes to check for explicitly: `<system-reminder>` blocks,
`<local-command-caveat>` / `<command-name>` / `<command-message>` / `<local-command-stdout>` blocks,
injected `CLAUDE.md` / memory content, hook output, task-notification blocks, and
compaction-summary turns. Then settle the design question this plan exists to answer:

**a deny-list of synthetic shapes is structurally the wrong instrument** — it must be extended every
time the harness adds one, and its failure mode is silent over-counting. Decide whether the filter
inverts to an **allow-list** (keep only turns positively identified as operator-authored) or whether
a deny-list is retained with an explicit, tested inventory. **Record the reasoning either way** — if
D1 keeps a deny-list, it must say what makes the next unenumerated shape detectable.

### D2 — the provenance filter matches D1's chosen shape

Implement it. **Correct the `:37-41` "by construction" claim in lock-step** — either make it true or
stop asserting it. Leaving an over-claiming docstring beside a corrected filter is the exact pattern
this epic keeps finding.

### D3 — the verdict stops being purely volume-derived

`no_signal` must not be satisfiable by surviving non-operator volume. At minimum the TOON gains an
operator-authored count distinct from the raw survivor count, so a caller can tell *"kept 200 turns,
3 operator-authored"* from *"kept 200 operator turns."* **A ratio or count that can distinguish
those two states is the deliverable**; whether it also changes the Tier-1/Tier-2 threshold is D1's
call, since raising the bar trades a false-healthy for a false-refusal.

### D4 — tests

(a) A fixture transcript composed of harness-injected `user` turns (using the real block shapes, not
invented ones) is verified to be classified **healthy/Tier-1 by the current code** and correctly by
the fixed code — the assertion that fails against today's implementation. (b) A genuine
operator-authored transcript still routes Tier 1 — the **mirror false-positive guard**: this fix must
not make the reducer refuse real transcripts. (c) The D3 counts distinguish high-volume-low-signal
from high-volume-high-signal.

Four deliverables (D1 a gate) — under the split guard.

## Expected Surface

- OBSERVED: `plan-retrospective/scripts/extract-chat-signal.py` — `is_signal_bearing` (`:149-162`),
  `is_synthetic_skill_load` (`:105-116`), `_SKILL_LOAD_MARKER` (`:101`), the `no_signal` computation
  (`:264`), the `cmd_run` TOON payload (`:236-282`), and the docstring claim (`:37-41`).
- HYPOTHESIS: `plan-retrospective/references/chat-history-analysis.md` — the Aspect-14 contract doc;
  update in lock-step if the verdict vocabulary changes (verify-at-outline).
- HYPOTHESIS: the `plan-retrospective` SKILL.md Tier-1/Tier-2 description, if D3 changes the
  threshold (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/plan-retrospective/**`.
- OBSERVED: lesson `2026-07-26-22-005`, retired at finalize.

**Disjointness — ⚠ SEQUENCE AFTER PLAN-54.** PLAN-54 (currently launched) touches
`plan-retrospective/scripts/check-artifact-consistency.py`, `check-routing-decisions.py`, and
**`test/plan-marshall/plan-retrospective/**` — the same test directory this plan writes to**. The
script files are disjoint; the test tree is not. Do not pair these two concurrently. Disjoint from
PLAN-57 (`manage-status`), PLAN-75 (`manage-execution-manifest`), PLAN-62 (`manage-run-config`),
PLAN-CIS-016 (project-local auditor).

## ⛔⛔ RECONCILED 2026-08-09 — GATE STRUCK, SCOPE NARROWED, MECHANISM RE-VERIFIED

✅ **The mechanism is EXACT at HEAD — verified first-party, no re-derivation owed.**
`extract-chat-signal.py` still carries `_SKILL_LOAD_MARKER` at **`:101`**, `is_signal_bearing` at
**`:149`**, and `no_signal = len(turns) == 0` at **`:264`** — the three line numbers this spec cites
are all still correct. ⭐ **Spend the D1 budget on the marker inventory, not on re-locating the code.**

⛔ **THE GATE IS STRUCK.** ~~Gated on PLAN-54 landing (test-tree collision)~~ — `PLAN-54` belongs to
the **retired `plan-optimization` epic** and shipped long ago. It is not in this epic's queue and
nothing is in flight on that test tree. **This plan is unblocked.** (Same class as `epic.md`
§ Queue Reconciliation 2026-08-09 finding R1 — the sequencing block also names PLAN-51, PLAN-57,
PLAN-62, PLAN-75, PLAN-99, all likewise historical.)

⛔⛔ **SCOPE NARROWED — items (b) and (e) are STRUCK as duplicates of `PLAN-CIS-012`.** This spec's
§ "Three `plan-retrospective` checkers" carries the `check-artifact-consistency` **recall-0%**
defect as items (b) and (e). **That is `PLAN-CIS-012`'s entire founding subject**, where it is
supported by six independently-measured true values and a settled remedy tier. Carrying it in both
is the F0b two-writers shape.
⇒ **`PLAN-CIS-012` owns the footprint/recall defect. This plan owns `extract-chat-signal` only.**
⭐ **What survives here is sharper for the narrowing**: this plan is now about **one** instrument —
the chat-signal reducer — and its D1 design question is already **answered by evidence** (invert to
a positive predicate; see the 2026-08-03 fold). ⚠ Item (c) (`check-routing-decisions` mislabelling a
phase-6 subtotal as `actual_tokens`) is **also not this plan's** — it belongs with `PLAN-CIS-022`'s
ledger-disagreement arm; cross-noted, not folded, to avoid a third writer.

## Dependencies and Sequencing

- ✅ **Unblocked** — the former PLAN-54 gate is struck (above).
- Related but disjoint: PLAN-51 (#1009) shipped the `sections_omitted` / `sections_dropped` partition
  in `compile-report.py`. **That is the proven pattern for D3** — same skill, same "distinguish
  nothing-there from nothing-reported" shape, already landed and reviewable.
- Independent of #1003.

## Notes

- **Why this one matters disproportionately:** the chat-history aspect is an input to
  `plan-retrospective`, which is the machinery that produces this epic's findings. A confidently-healthy
  verdict over instruction text means retrospective conclusions have been drawn from a substrate whose
  quality was never measured. As with PLAN-CIS-016's auditor, *absence* of findings from this path has
  never been evidence of absence.
- The enumerate-the-synthetic-shapes approach is the same instrument class as PLAN-CIS-016's `[LOCK]`
  marker scan — a predicate over an input set that the environment silently changes. Worth noting the
  pairing in the epic vision.

## Three `plan-retrospective` checkers, one serialization class

All three are `plan-marshall:plan-retrospective` script defects observed on PR #1034, so they belong
in one plan rather than three passes over the same bundle. **All claims below are message-supplied
(`category=bug`) and are HYPOTHESIS until re-verified first-party at outline** — but each carries its
own arithmetic, so verification is cheap.

**(a) `extract-chat-signal` — the plan's own subject, now with a measured instance.** On PR #1034 it
returned `status: success`, `no_signal: false`, `over_budget: false` after
`raw_turn_count: 804 → reduced_turn_count: 1`, **dropping 803 turns (99.88%)**. The single surviving
turn is the slash-command invocation itself. **A confident success verdict over a reduction that
retained nothing** — the volume-read-as-coverage archetype in its purest observed form, and the
strongest evidence this plan has.

**(b) `check-artifact-consistency` reports 0% recall because the worktree is already gone.** It
derives the plan footprint **live from the plan's worktree** (`{base}...HEAD` union porcelain), but
`branch-cleanup` has already removed it. Reported `affected_files_recall, fail, Recall 0% below 70%
threshold`, `declared: 8`, `found: 0`. ⛔ **The declared set was exactly right** — merged commit
`89fd4d1f6` touched precisely those 8 files, so true recall was **100% with zero scope creep**. The
0% is entirely an artefact of *when* the aspect runs. **This is a false FAIL, the mirror image of the
epic's usual false PASS — and equally corrosive, because it trains readers to ignore the check.**
The fix is ordering or source (read the merged commit, not the deleted worktree), not the threshold.

**(c) `check-routing-decisions` labels a phase-6-only sum as the plan's `actual_tokens`.** It emitted
`actual_tokens: 974134`, which is the **exact sum of the phase-6 `record-step` entries alone**
(78968+47466+196865+255921+140442+70067+43815+140590). The real plan cost was ~2.7M. A field named
`actual_tokens` carrying a per-phase subtotal is a mislabelling that silently understates cost by
roughly 3×, and any adjudication reading it is wrong by that factor.

**(b) RECURRENCE, independently reported on #1037** — *"reports 0% recall when the footprint SOURCE
is gone, not 'unmeasurable'"*. Two different plans hit this on two different PRs within hours, which
settles it as systematic rather than incidental. ⭐ **The second report also names the correct fix
shape: the honest output is `unmeasurable`, not `0%`.** A checker that cannot reach its source must
**declare inapplicability**, never emit a number — the same remedy shape PLAN-67 needs for
`check_freshness`. Adopt that framing; do not merely re-order the step.

**(d) `dispatch_boundaries` is a `SECTION_SPEC` row NO PRODUCER CAN EVER FILL — and it fails into the
BENIGN bucket** (cross-epic handover from `test-suite-quality`, observed on #1036's run). Reported
`sections_omitted[1]: Phase Dispatch Boundaries`, `sections_dropped[0]` — i.e. *"the trigger fragment
was absent, so there was nothing to lose."* ⛔ **That classification is wrong: the payload exists,
`analyze-logs` produced it richly, and it is being discarded.**

⚠ **This is a partial regression of PLAN-51 / #1009**, which shipped precisely this partition
(benign `sections_omitted` vs warning `sections_dropped`). The partition is correct; **the
unfillable-row case lands on the wrong side of it**, so a real loss is reported as a non-event.
**Do not re-litigate the partition — add the third state:** a section whose producer cannot exist is
neither benign-omitted nor dropped-after-render, it is **structurally unreachable**, and that must be
its own loud verdict. Same remedy shape as (b)'s `unmeasurable`.

**(e) THIRD independent report of (b), and a second instance of (a) (#1039).** `affected_files_recall`
again reported a confident **0% / fail** from an **empty footprint** — real recall **10/10** — because
it runs after `branch-cleanup` removed the worktree. **Three independent reports in two days settles
this as systematic; stop treating it as an anecdote.** And `extract-chat-signal` again returned
Tier-1 **"signal present"** after discarding **880 of 881 turns** — the same shape as (a)'s 803-of-804,
so the survivor-count verdict is not a one-off either.

⚠ **Two independent detectors, one remedy shape:** both must **declare inapplicability**
(`unmeasurable` / `no-signal`) instead of emitting a confident number computed from nothing. Design
the remedy once and apply it to both, rather than patching each.

**(f) `metrics.md` renders the largest-token phase as UNRECORDED, under-reporting the plan by ~36%**
(#1039). A cost report that silently omits its biggest contributor is the flagship archetype in the
measurement layer. ⚠ **Coordinate with PLAN-99 and PLAN-CIS-014** — both consume these numbers, and a 36%
under-report would corrupt any anchor derived from them.

⚠ **Split guard:** this widening may push the plan past the guard — **evaluate a split at outline and
record the verdict**. (b) and (c) are independent of (a) and could ship separately.
⚠ **Sequencing unchanged:** still after PLAN-54's surface, and coordinate with **PLAN-99**, whose
exploration-share measurement reads the same cost fields (c) mislabels.

## Inherited Inbox Evidence (folded 2026-07-29 from `truthful-signals-004`)

⚠ **Leads, not facts** — re-verify before scoping.

⭐ **The sharpest instance of this plan's archetype yet observed.** `exploration-share-is-unmeasured-009`
(PLAN-99 / #1043): the chat-history aspect **reported Tier 1 full analysis after keeping 2 of 1156
turns** — a **0.17% sample reported as full coverage**.

**Volume-read-as-coverage in its most extreme observed form.** Fold as this plan's anchor example:
the detector does not merely under-include, it reports the under-inclusion as completeness.

## Second Evidence Fold (2026-07-29 — `truthful-signals-010`, API-Sheriff #14)

⭐ **THE ROOT CAUSE, not just a sharper instance.** `extract-chat-signal` reduced a **565-turn**
transcript to **2 user turns**, reporting `no_signal: false, over_budget: false` — a clean Tier 1
extraction — and concluded **zero** corrective feedback, scope changes and frustration.

**All three conclusions are literally true and jointly misleading.** The operator made **eleven**
decisions in that run — domain widening, planning-lane escalation, execution-posture change
(12 → 18 finalize steps), ADR granularity — **every one through an `AskUserQuestion` gate.** None
appear in the reduced transcript **because they arrive as TOOL RESULTS, not user turns.**

⇒ *"On a gated run the answer lives entirely in the gate answers; reducing to free-form turns measures
only the channel the operator did not use."* **This is not under-inclusion by degree — it is a whole
signal CHANNEL the filter cannot see.**

**Fix**: retain `AskUserQuestion` invocations and their selected answers as a **distinct signal
class**; report `free_form_corrections` and `gate_decisions` as **two counters**.
⭐ *"A run with 0 corrections and 11 gate decisions is well-instrumented, and the aspect should be able
to say so."*

## Evidence Fold — 2026-07-29, from `truthful-signals-012` item 3

⚠ **Lead, not fact** — re-verify at outline. ⭐ **This is a MEASURED data point from a real run, which
is what the plan was missing**: `extract-chat-signal` reported `no_signal=false` after retaining
**2 of 655 turns** — the chat aspect passed green on **0.3 % of the transcript**.

`no_signal=false` is *technically* true (signal was found) while being materially misleading about
coverage — the same volume-read-as-coverage shape this plan already targets, now with a concrete
retention ratio to calibrate against. Use it as the anchor case: whatever discriminator this plan
introduces must render a 2/655 retention as something other than an unqualified green.

## Second Evidence Fold — 2026-07-29, `truthful-signals-014` + `-016`

⚠ **Leads, not facts.** ⭐ **Three measured retention ratios now exist, and the third one changes the
thesis from "under-inclusive" to "wrong in both directions at once".**

**The measured population, all from real runs:**

| Run | Retained | Verdict reported |
|---|---|---|
| already folded above | 2 of 655 (0.3 %) | green, `no_signal=false` |
| `-014` | 3 of 1131 (0.3 %) | **clean Tier-1 verdict** |
| `-016` | reduction **dropped every operator-decision turn** | `no_signal: false` |

⛔ **The `-016` data point is qualitatively different and is the one to scope against: the filter is not
merely dropping VOLUME, it is dropping THE DECISIONS.** A 0.3 % retention that happened to keep the
operator's gate dispositions would be defensible; one that discards exactly the turns carrying operator
intent is measuring the wrong thing entirely, and reporting a clean verdict over it.

⭐ **And the filter is over-inclusive on the other side**: `extract-chat-signal` **counts harness
task-notifications as operator signal**. ⇒ **Both directions are wrong simultaneously** — it discards
real operator input while admitting harness noise, so the retained remainder is not "a small sample of
operator signal", it is *a small sample contaminated with non-signal*. A precision/recall framing of
the fix needs both halves; widening the filter alone would admit more noise.

⇒ **Success criterion this fold implies**: the aspect must be able to state *what it retained and what
it discarded, by provenance class*, and a verdict computed over a reduction that dropped all
operator-decision turns must not render as clean. Pair with the standing rule from PLAN-CIS-012's fold —
*a quantity that could not be measured must not be reported as a measured value*.

## Evidence Fold — 2026-08-03, CIS-028 drain (`…-012`) — FIRST-PARTY, and it settles D1's design question

⭐ **This is the sixth measured retention ratio and the first one where the surviving set was
enumerated turn-by-turn.** On PLAN-CIS-028's 1122-turn session `extract-chat-signal run` returned
`reduced_turn_count: 4`, `raw_turn_count: 1122`, `dropped_turn_count: 1118`, `no_signal: false`,
`over_budget: false` — the Tier-1 condition. **Retention 0.36%. All four survivors are harness
boilerplate; ZERO operator-authored turns survived:**

| role | what it actually is | operator-authored |
|---|---|:---:|
| user | `<command-message>` / `<command-name>` / `<command-args>` slash-command injection | no |
| user | `"Skill /plan-marshall:plan-marshall is already loaded above; instructions unchanged."` | no |
| assistant | one `[STATUS]` marker line | no |
| user | `<task-notification>` block (PR #1080 MERGED monitor event) | no |

⛔ The run's real operator decisions — the `blocked_user_review` escalation where the operator
dispositioned two CodeRabbit Majors FIX-HERE, **creating TASK-021 and TASK-022** — are absent from
the reduced set. The plan's most consequential operator input was invisible to the aspect that
reports on operator input.

⭐⭐ **D1's design question is now ANSWERED by evidence, not argument — invert to a positive
predicate.** The prior fix enumerated the **two** synthetic classes visible in **its** sample; this
transcript exhibits **three more** it never enumerated. That is not an incomplete list, it is the
wrong instrument:

- **A negation-list drop filter derived from a sample will always be incomplete**, and it **fails
  toward "operator"** — the direction that manufactures the false Tier-1.
- **A positive predicate fails toward "synthetic"** when the harness adds a new wrapper. Derive
  synthetic-ness from the harness's own injection markers — any `user` turn wholly enclosed in a
  harness tag block (`<command-message>`, `<command-name>`, `<command-args>`, `<task-notification>`,
  `<system-reminder>`, `<local-command-stdout>`) or a verbatim re-entry notice — and keep what is
  left. ⇒ **D1 should record "allow-list" as the settled answer and spend its budget on the marker
  inventory, not on re-litigating the choice.**

⭐ **The most instructive part, and why this fold is not just a sixth data point**: here the
**remediation itself was the thing that sampled.** This is the same archetype as lesson
`2026-08-03-06-002` (*a named site list is a detector sample*), applied to a fix rather than to a
reviewer — the second concrete instance of it inside PLAN-CIS-028 alone.

⛔ **The false claim is load-bearing and inline in the code**, which is what makes it a
vacuous-authority instance rather than a mere gap:

```python
# ``no_signal`` is computed from the SURVIVING turn count — the set that is
# operator-authored by construction after the reduction above.
```

*"By construction"* is **false on this transcript**, and it is the stated justification for the
`no_signal` verdict. Correct it in lock-step with D2, per this plan's existing D2 obligation.

**Cheap regression for D4**: a transcript with `retention_rate < 1%` and **zero** turns passing the
positive operator predicate MUST report `no_signal: true`. This one assertion fails against today's
implementation and passes against the D1 allow-list — it is the discriminating test the aspect has
never had.

## Evidence Fold — 2026-08-08, from `lessons-handling-…-003` cluster C08

**`2026-07-26-23-001` — `extract-chat-signal` SELF-REPORTS a healthy Tier 1 reduction while the reduced
transcript is dominated by skill-document bodies misclassified as user turns, plus empty turns.**

⭐ **The sender called this the sharpest member of its cluster and that assessment holds: a reduction
instrument that certifies its own health while the thing it reduced is misclassified.** It is the same
under-inclusive-provenance-filter defect this plan already owns, observed from the **output** side rather
than the predicate side — so it is a **second, independent symptom of this plan's root cause**, not a new
defect.

⛔ **Why it changes the plan's success test rather than merely supporting it.** The reduction ratio is
currently the instrument's own evidence of working. If skill-document bodies are being counted as user
turns, a *higher* reduction ratio can indicate a *worse* misclassification — the metric moves the wrong
way under the defect. ⇒ **D1's allow-list fix must NOT be validated by the reduction ratio improving.**
Validate against the classification of a known population of turns; the ratio is an output of the defect,
not a check on it.

⭐ Note the compounding with the empty-turn half: an empty turn and a misclassified document body both
inflate the same numerator, so the two cannot be told apart by the ratio either.

**Claim labels** — OBSERVED: lesson id, component, category. HYPOTHESIS (verify-at-outline): that the
misclassification still occurs and still feeds the self-reported ratio. Confirm/refute artifact: the
retrospective's `extract-chat-signal` reducer — specifically the turn-classification predicate and the
site that computes the reported reduction.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
