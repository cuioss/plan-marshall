# Run report — 330-retrospective-report-sections-structurally-dead (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/code-intelligence-retrospective-s9weii`    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded as the first action, per the plan's first-instruction block:

- `cloud-plan-lane` (`.claude/skills/cloud-plan-lane/SKILL.md`) — the governing contract.

Then, by bundle path (the `plan-marshall` plugin is not installed in this cloud session):

| Skill | Route | Why |
|---|---|---|
| `plan-marshall:ref-code-quality` | `marketplace/bundles/…/ref-code-quality/SKILL.md` | Always |
| `pm-plugin-development:plugin-script-architecture` | `marketplace/bundles/…/plugin-script-architecture/SKILL.md` | Always |

Its `standards/shim-marker-convention.md` was loaded on demand for D4's back-compat read path.
No skill was unobtainable by both routes.

## Deliverables

### D1 — assert the partition invariant, with the placeholder as its failing case

**Commit `6bad96f`.** Two halves, both shipped.

*Half one — written implies non-empty.* `build_document` appended the Executive Summary heading to
`written` unconditionally, including on the branch whose entire body is the literal
`_No executive summary provided._`. The placeholder branch now emits **no heading at all** — which
`references/report-structure.md` § "Conditional Rule" already forbade ("it must not emit an empty
heading") — and takes the same discriminator every other section takes: an absent or empty fragment
is a benign **omission**; a fragment that carried payload the renderer could not turn into a body is
a **drop**.

*Half two — a zero must name what it checked.* `unattributed_zero_sections()` names the written
sections reporting `findings: []` without naming their checked set, published as
`sections_unattributed_zero`. **Reported, never gating** — those sections lose nothing, so folding
them into the content-loss signal would blur an ambiguity signal with a loss signal, which is the
defect class this partition exists to surface.

The discriminating vocabulary is **derived, not invented** — each name is a field the deterministic
aspects already publish, cited at its declaration in `retro_sections.py`:

| Field / status | Declaring source |
|---|---|
| `evaluated_population` | `standards/execution-context-dispatch-audit.md` — "publishes the evaluated population beside every count so a zero is legible" |
| `population` | `references/log-analysis.md` fragment schema (`population: plan_script_execution_log`) |
| `counts` | `direct-gh-glab-usage.py`, emitted beside an empty `findings` list |
| `not_evaluated` | the token `execution-context-dispatch-audit.md` mandates in place of a bare `0` |
| `skipped` | the graceful-skip status in `references/chat-history-analysis.md` |

⛔ **The first cut of this deliverable fixed an INSTANCE, not the CLASS — caught by the verification
sub-agent, not by me.** `render_section_body(None)` returns the same literal placeholder for *any*
absent fragment, and every `conditional_trigger = None` row appended its heading to `written`
regardless. So the breach I had just closed for the Executive Summary was still open on ten other
rows. Measured either side of the correction, on an empty bundle:

| | before | after |
|---|---|---|
| sections written | 10 | **0** |
| placeholder bodies in the document | 10 | **0** |
| omitted | 6 | **17** |

A missing fragment is now an omission on **both** render paths — the static registry loop and the
generic fallback — because the invariant is a property of the partition, not of one code path. The
class-level test quantifies over `SECTION_SPEC` rather than a name list, so a row added later is
covered without an edit.

This correction is also what makes the invariant sentences in `SKILL.md` § Step 4 and
`report-structure.md` TRUE. They were **false when written** — I documented the property before the
code held it for more than one row. The fix moved the code to the spec rather than the spec to the
code.

**Verification state:** the invariant assertion was written FIRST and observed RED against pre-fix
code (`assert 'Executive Summary' not in written` → `AssertionError: … ['Executive Summary', …]`).
The zero-attribution probe was mutation-tested in both directions — forcing `_names_checked_set` to
always return `True` (guard can never fire) and forcing it to ignore attribution (guard always fires)
each turn the suite red.

**A late correction to the probe's depth.** `_names_checked_set` originally read top-level fragment
keys only, but of the three attribution fields only `counts` is published there:
`evaluated_population` lives inside `shape_violation` / `dispatch_coverage`, and `population` inside
`script_cost_rollup`. A top-level-only probe would have flagged fragments that **do** name the
population they examined — a false positive against the very producers the vocabulary was derived
from. It now reads the top level and one nesting level, bounded at one so an incidental deep key
cannot clear the flag.

### D2 — GATE: registry rows against their reachability. Mutates nothing.

**No commit — this deliverable is a derivation and it mutated nothing.**

Reachability was derived mechanically, not by hand: a row is reachable when a producer can populate
`fragments[fragment_key]` and the compiler renders it. The producer population is the union of two
independently-scanned surfaces — the Step-3 aspect table's Key column, and every literal
`--aspect <key>` command in `SKILL.md` plus each `references/`/`standards/` document it names.

**Both counts, reported separately as the plan requires:**

- **rows examined: 17**
- **dead rows: 2**

| Dead row | Registerable | Render path | Why it is dead |
|---|---|---|---|
| `_executive-summary` | **No** — `cmd_add` rejects `_`-prefixed keys by rule | Yes (the compiler uses a supplied summary verbatim) | No documented producer. No step in `SKILL.md` writes an executive-summary fragment, and `collect-fragments add` is the only documented write path into the bundle. |
| `dispatch_boundaries` | **Yes** — no `_` prefix, present in `valid_aspect_keys()` | Yes — `render_dispatch_boundaries_body` is live | No producer registers it **at top level**. `analyze-logs.py cmd_run` returns `dispatch_boundaries` as a key of **its own** fragment, so the data lands at `fragments['log-analysis']['dispatch_boundaries']` and the registry's top-level lookup never finds it. |

The remaining 15 rows have a producer. ⚠ **"Has a producer" is not the same as "renders on a
normal run", and one row must be stated precisely**: `script-failure-analysis` is produced on every
plan, but its clean-run fragment renders only when the plan actually *had* script failures — see
finding F6, which is a live false `sections_dropped` on the common path. Read the count as
**2 rows with no producer at all**, not as "15 rows behave correctly".

**The `dispatch_boundaries` diagnosis was settled by execution, not by reading.** Built against the
real producer shape, the section reports:

```
in written : False   in omitted : True   in dropped : False   rendered : False
renderer alive when registered at top level: True
```

So the row is reported as a **benign omission on every run, forever**, while the data exists and its
renderer works — a structurally-unreachable section wearing the "nothing to say" face. That is
precisely the plan's thesis, observed first-party.

**Not re-staged.** The plan's warning is conditional on D2 finding "a materially larger dead
population". It found exactly the two the plan named as a sample, so the sweep stays here.

⚠ **This run's D2 conclusion disagrees with the plan's own claim-labels table, and the
disagreement is flagged rather than quietly absorbed.** That table records *"No orchestrator
injection path exists for the headline section — **REFUTED**"*. What is refuted is the narrower
premise the re-grounding states: the **compiler** accepts an `_executive-summary` fragment and uses
it verbatim, so the section is not unrenderable. But no **producer** anywhere in the marketplace
writes one, and `collect-fragments.cmd_add` rejects `_`-prefixed keys outright, so there is no write
path into the bundle for it. Both statements hold at once; the plan's label is about the consumer and
this finding is about the producer. The independent verifier re-derived the same conclusion.

**Nothing was fixed for D2, deliberately** — the deliverable says "Mutates nothing", and remediating
the two rows is named in no deliverable. D1 addresses `_executive-summary`'s *symptom* (it no longer
counts as written). Both rows are carried in Residue.

### D3 — the documentation that instructs a registration supplies the exact argument

**Commit `8d60be8`.** The Step-3 aspect table gains a **Key** column carrying each row's canonical
registry key.

The asserted absence was **re-derived rather than quoted**, as the plan's claim-label table demands,
and it holds with a refinement worth recording: the canonical keys do appear in the document as
*reference-document basenames*, but **never as registration keys**, and the two obvious guesses both
fail. Re-derived at the moment of this claim: **three** of fifteen rows have a key differing from
their reference basename —

| Key | Reference basename |
|---|---|
| `invariant-summary` | `invariant-check-summary` |
| `manifest-decisions` | `manifest-crosscheck` |
| `routing-decisions` | `routing-decision-verification` |

**On ⛔ "derive the key from the registry, never restate it".** The column *is* a restatement, and the
plan's own "Done when" requires one ("each row carries its canonical key"). The constraint is
honoured in the sense that decides whether the archetype recurs: `retro_sections.SECTION_SPEC`
remains the declaring source, the document points at it by name, and a new guard fails when the two
disagree — so the restatement **cannot drift**, which is what the count-prose archetype does. This
is a judgement call and is flagged as such for the reviewer.

The guard reads the Key cell **by column position** and asserts the table header verbatim first: a
positional read without a header anchor keeps passing against the wrong column after a reorder.
Mutation-tested both ways — replacing a key with its reference basename (the natural wrong guess),
and reordering the columns — each turns the guard red.

### D4 — the retrospective stops destroying its own primary input

**Commit `498f21d`.**

**The claim-label instruction was followed exactly**: the machine-local run records were *not* looked
for; the defect was settled from the capture's write target in this clone. `session capture` called
`manage-status metadata --set --field session_id` — a **scalar**. The defect is therefore
**structural**, as the claim label said it would be if that held.

The root cause is the one the plan names: a plan legitimately spans multiple sessions (any resume, and
any observing process capturing against the plan it measures), so the field was *a scalar modelling a
list* — which is why a second writer overwrote rather than appended. There was one slot and nowhere
else to put the value.

**The list subsumes the clobber rather than sitting beside it**, exactly as the plan requires: with
`status.metadata.session_ids` there is no single slot to overwrite, and the observer's identity
becomes an append — what it was always trying to express. ⛔ **No guard was shipped**: an assertion
that the stored value never changes would fail a legitimate multi-session resume, which is the
opposite error.

Supporting change: `manage-status metadata` gains `--append` as a modifier for `--set`. Absent field
→ `[value]`; existing list → appended unless already present (so a repeated capture is idempotent);
a field already holding a **non-list** → `metadata_field_not_a_list` and **nothing is written** —
silently coercing a caller's scalar into a container is a type change made on a guess. The
read-modify-write runs inside the same `rmw_json` O_EXCL critical section every other `status.json`
writer commits through, so a concurrent append cannot be lost through a check-then-act window.

The read path returns the **last** entry — the newest session to capture against the plan, which is
the transcript `enrich` must open — with a `SHIM(B)`-marked fallback to the retired scalar for a
`status.json` written before the list (owner, floor, and removal trigger all recorded at the
definition site per the shim-marker convention).

Four documentation surfaces that instruct this read were updated in lock-step: `phase-6-finalize`
SKILL.md, the orchestrator's resolver in `plan-marshall/workflow/execution.md`, the
`persona-plan-marshall-agent` tool-usage-patterns resolver note, and the `manage-status` verb
reference (both the prose block and the Canonical-invocations entry).

Mutation-tested: reverting the capture to an overwriting `--set`, and reading the first entry instead
of the last, each turn the suite red.

### D5 — tests, RE-BASELINED

**Commit `9107964`,** plus labels on every test added by the other commits.

Every test added by this run is labelled below. "Regression" means it was **observed** to fail against
pre-fix code (either directly, or via a mutation that reinstates the exact defect); "characterization"
means it pins shipped behaviour and cannot witness anything this plan fixed.

| Test | Label | Evidence |
|---|---|---|
| `test_placeholder_executive_summary_is_not_listed_as_written` | **Regression** | Observed RED against pre-fix code before the fix existed |
| `test_missing_executive_summary_emits_no_section` | **Regression** (restated) | Replaces `…_uses_placeholder`, which pinned the defect; the new assertions are the negation of pre-fix behaviour |
| `test_payload_bearing_executive_summary_without_a_body_is_dropped` | **Regression** | Pre-fix this fragment was counted as *written* |
| `test_no_section_is_written_from_an_empty_bundle` | **Regression** | The class-level case; pre-fix an empty bundle wrote 10 placeholder sections |
| `test_an_always_emit_row_with_no_fragment_is_omitted_not_written` (10 cases, one per `trigger=None` row) | **Regression** | Each row is a separate pre-fix instance of the same breach |
| `test_a_row_with_a_real_fragment_is_still_written` | **Characterization of new behaviour** | Guards the fix against over-reach ("no fragment ⇒ not written", never "write less") |
| `test_a_fallback_aspect_mapped_to_none_is_omitted_not_written` | **Regression** | Pre-fix the fallback path wrote a placeholder too |
| `TestZeroReportingSectionNamesItsCheckedSet` (14 cases) | **Characterization of new behaviour**, mutation-proven | The probed function did not exist pre-fix, so no pre-fix red is possible; non-vacuity established by mutations instead |
| `TestAspectTableKeysMatchTheRegistry` (5 cases) | **Characterization of new structure**, mutation-proven | The Key column did not exist pre-fix; three mutations (wrong key, reordered column, neutered corruption) turn it red |
| `test_metadata_append_preserves_the_earlier_value` | **Regression** | The multi-session case the scalar destroyed |
| `test_store_appends_to_the_session_ids_list` | **Regression** | Mutation reinstating the overwriting `--set` turns it red |
| `test_read_returns_the_most_recent_entry` | **Regression** | Mutation returning the first entry turns it red |
| `test_a_resume_on_a_pre_list_plan_does_not_fail` | **Regression** | The plan's own D4 verification case; fails against a scalar field |
| `test_should_refuse_append_and_write_nothing` (orchestrator store) | **Regression** | Pre-fix the flag was silently ignored and the earlier value clobbered, reporting success |
| `test_metadata_set_without_append_still_replaces` | **Characterization of PRE-EXISTING behaviour** | Passes on `origin/main` — it pins the unchanged default `--set` path, not anything this run added |
| remaining `--append` cases and session-read cases | **Characterization of new behaviour** | New verb / new read path; no pre-fix behaviour to regress from |
| `TestSkippedFragmentPartitionCharacterization` (2 cases) | **Characterization** | Re-run against the pre-plan tree: identical results, so neither can witness anything this plan fixed |

**The two previously-planned assertions the plan told me to re-baseline were NOT shipped as
regression proofs.** Re-run against `origin/main`'s `compile-report.py`:

```
PRE-PLAN | bare skipped        -> omitted
PRE-PLAN | skipped+skip_reason -> dropped
```

Identical to the current tree. They are shipped as **characterization**, with the class docstring
saying so explicitly, and are retained rather than dropped because the second one makes a live
anomaly visible (see Findings F1).

Test functions added, re-derived at the moment of this claim (`git diff origin/main...HEAD` counting
added `def test_` lines): 10 (manage-status metadata) + 1 (orchestrator store) + 23 (compile-report
behaviour) + 5 (render guard) + 8 (claude_runtime) = **47 test functions**. That is a count of test
*functions*; parametrized cases collect higher, and a reader running the suite sees the collected
number, not this one.

⚠ **The verifier's D5 audit was performed against an earlier HEAD and its label table cites figures
that have since moved** (it read 39 functions). Both readings were correct when taken; this one is
re-derived at HEAD.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **13 files**, re-derived at HEAD. Python
changed, so the full gate applies. (24 files changed overall, across 13 commits.)

- Per-commit `./pw quality-gate` before each `*.py`-touching commit: `ruff … All checks passed!`,
  `mypy … Success: no issues found in 412 source files`, `SPDX-header check passed`.
- Full `./pw verify` over the branch diff, re-run after the round-1 fixes: **`=== verify: SUCCESS ===`**,
  `20704 passed, 14 skipped` in 377 s — all three sub-steps (quality-gate, test-compile, module-tests).
- One gate rejection was fixed rather than worked around: plugin-doctor's
  `no-historical-prose-in-skills` fired on new wording in `phase-6-finalize/SKILL.md`; the sentence
  was reworded and the gate re-run clean.
- `git status --porcelain` clean before each diff read; no `uv.lock` churn reached any commit (paths
  staged explicitly, never `git add -A`).

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | First-party re-check (D5) | The plan's Out-of-scope asserts the skipped-fragment case "Already shipped — verified first-party". **Refuted for the skip-reason-bearing shape**: a `status: skipped` fragment carrying a `skip_reason` is classified as a **drop** (raising the run status to `warning`), because `skip_reason` is a non-empty non-envelope value and `_fragment_has_payload` reports payload for it. A *bare* skipped fragment is correctly an omission, so the boundary is the presence of the reason. This is the second half of the plan's own Problem statement ("dropped listed … a harmless zero-result aspect whose fragment explicitly declared itself skipped"). | **Rejected — out of scope by explicit plan instruction** ("⛔ Already shipped … Do not re-scope it"). Not fixed. Pinned as characterization so the next reader inherits a measured fact, and escalated to Residue. |
| F2 | Beyond-diff sweep (D1) | `retro_sections.py`'s module docstring claimed the module declares "the registry and a derived key-set helper, **nothing else**" — made false by the two new vocabulary constants. | **Fixed** in `6bad96f`, same commit as the change that falsified it. |
| F3 | Self-check while writing the D3 guard | The comment on `_KEY_CELL_INDEX` asserted a cell layout (`0='' 1=Order 2=Aspect 3=Key`) that was **wrong** — `_ASPECT_TABLE_ROW_RE` already consumes the Order cell, so the Key index is 2. An invented rationale about code I had not run. | **Fixed** — index corrected and the comment rewritten to record that the split was *run* against the live table rather than inferred. |
| F4 | Gate (plugin-doctor) | `no-historical-prose-in-skills` fired on new `phase-6-finalize/SKILL.md` wording ("not a correction of the earlier one"). | **Fixed** — reworded to a present-tense rule. |
| F5 | Pre-existing, observed while editing (D3) | `plan-retrospective/SKILL.md` § Enforcement says "dispatch the **14** aspect references"; § Dispatch shape says "**9** aspects iterate inside one envelope" and "The **8** in-context analytical aspects". The Step-3 table has **15** rows. At least one of these enumeration lead-ins disagrees with the table. | **Rejected — pre-existing and NOT made false by this change.** Not fixed: the intended denominator for "14" cannot be re-derived from the tree with confidence, and replacing one wrong number with another is worse than reporting it. Escalated to Residue with the "prefer naming to counting" remedy. |

### Verification round 1 (independent sub-agent)

Round budget declared before the first dispatch: **4 rounds**. Round 1 ran ~17 minutes, 105 tool
calls, and reported against a HEAD that moved four times during its review.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F6 | Verifier, D2 re-derivation | **`script-failure-analysis` produces a false `sections_dropped` + `warning` on every clean plan.** Its real clean-run fragment (`status: success`, `findings: []`, `lessons: []`, `total_failures: 0`, plus `log_path` / `work_log_path`) fails `should_emit` — no non-empty payload list — and then `_fragment_has_payload` sees the non-empty `log_path` string and calls it a DROP. Executed: `should_emit: False`, `_fragment_has_payload: True`, `dropped: ['Script Failure Analysis']`, run status `warning`. This is the plan's own Problem statement live on the **most common** path, and a **different route** from the `status: skipped` case of F1. | **Rejected — not fixed.** See the reasoning note below the table. Escalated to Residue as the highest-value follow-up. |
| F7 | Verifier, D1 | **The invariant held for 1 of 17 rows.** The fix addressed `_executive-summary`; every other `conditional_trigger = None` row still wrote a `_No data provided._` placeholder into `sections_written`. | **Fixed** — class-level, both render paths, with a registry-quantified test. |
| F8 | Verifier, D1 (Condition A) | Two statements were **false when written**: `plan-retrospective/SKILL.md` § Step 4 and `references/report-structure.md`, both asserting *written implies non-empty*, which held for one row. | **Fixed by F7's code change** — the spec was right and the code was wrong, so the code moved. No documentation was weakened to match a defect. |
| F9 | Verifier, D4 inward sweep (Condition A + B) | **`--append` was silently ignored for `--store orchestrator`.** The flag sits on the shared `metadata` subparser; `cmd_orchestrator_metadata` had no append handling, so the call fell through to `--set`, OVERWROTE, and returned `status: success`. Executed: two appends left `{'session_ids': 'sess-B'}`. The exact clobber D4 exists to eliminate, reintroduced on the surface D4 added. | **Fixed** — refused with `append_unsupported_for_store`, writing nothing, with a regression test. |
| F10 | Verifier, D4 sweep (Condition A + live behaviour) | **`phase-1-init/SKILL.md` Step 8a still read the retired scalar.** It verifies `status.metadata.session_id` and runs `--get --field session_id`; after D4 the capture writes `session_ids`, so the check would have found an absent field and emitted its spurious `[WARNING]` on **every** plan init. A live regression my own four-surface sweep missed. | **Fixed.** |
| F11 | Verifier, D4 sweep (Condition A) | `plan-marshall/SKILL.md` § "Session ID Resolver" named the retired field and its retrieval command. | **Fixed.** |
| F12 | Verifier, D3 (Condition A) | A test comment claimed **"the two rows"** differ from both their prose name and their reference basename. Re-derived by execution: exactly **one** does (`invariant-summary`). `routing-decisions` and `manifest-decisions` differ from their basename alone — their prose slugs to their key. | **Fixed** — corrected and the distinction spelled out. |
| F13 | Verifier, D3 (vacuous guard + Condition A) | `test_guard_bites_on_a_key_that_is_not_in_the_registry` was **vacuous**: set arithmetic on a literal that never called the scanner, its second assertion a tautology given its first, under a comment claiming it exercised the correspondence check. | **Fixed** — it now runs the real parser over a deliberately corrupted table. Neutering the corruption turns it red. |
| F14 | Verifier, D1 inward sweep | The attribution probe read **top-level keys only**, but only `counts` is published there; `evaluated_population` and `population` are emitted one level down. The probe would have flagged fragments that **do** name their population. | **Fixed** — reads one nesting level, bounded, with tests for both the real dispatch-audit shape and the two-levels-down non-case. |
| F15 | Verifier, D3 | The correspondence guard is **one-directional** (`table → registry`). A new `SECTION_SPEC` row shipped with no table row is caught by nothing. | **Accepted as a stated limitation, not fixed.** The reverse assertion fails today on the two dead rows, and encoding them as exemptions would pin them in place. Recorded in the guard's own docstring with the condition for re-opening it. |
| F16 | Verifier, D2 | This run's D2 conclusion appeared to contradict the plan's claim-labels table without flagging it. | **Fixed in this report** — the contradiction is stated and resolved in the D2 section (consumer vs producer). |
| F17 | Verifier, D5 | Report figures had gone stale ("35 test functions", "session-read cases (5)"), four later tests were unlabelled, and `test_metadata_set_without_append_still_replaces` was mislabelled as characterization of *new* behaviour when it pins pre-existing behaviour. | **Fixed in this report** — figures re-derived at HEAD, all tests labelled. |

**Why F6 is reported rather than fixed.** It is a real defect and I am not disputing it. But it is a
change to the **drop-side** calibration, and no deliverable in this plan authorises one: D1 is scoped
to the written-side invariant plus the zero-naming property, D2 mutates nothing, and D3–D5 are
elsewhere. The plan's Out-of-scope section removes the drop-side example its own Problem statement
raised (`⛔ Already shipped … Do not re-scope it`), which reads as the author having settled that
half. F6 is a *different route* to that same miscalibration and is therefore not literally excluded
— but fixing it means changing what `_fragment_has_payload` counts as content (here, a provenance
string like `log_path`), which ripples across every conditional row. That is a coherent piece of work
and it belongs in a plan that scopes it. **A reviewer who wants it in this PR should say so and I
will do it.**

**Condition-B survivor accepted from round 1.** A `session_ids` field holding a *scalar* is invisible
to `_manage_status_read_session`: `isinstance(values, list)` is False, so it falls through to the
legacy scalar and returns `None`. **Bound (B-(b)):** no supported writer can create that state — the
append path refuses a non-list and writes nothing, and no other writer targets the field. It is
reachable only by a hand-edited `status.json` or a deliberate plain `--set --field session_ids`. The
verifier independently classified this as a legitimate survivor.

_Round 2 findings are appended when that round completes._

## Reviewer participation

_Recorded after the PR is opened._

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a usage figure
  to the running agent, and no in-session counter was read.
- **Wall-clock:** not separately instrumented. The dominant measured component is the build: one full
  `./pw verify` at **374.92 s (6 m 15 s)** plus a second full verify and several scoped
  `./pw quality-gate` runs.
- **Population:** whatever figures appear here describe **this single Claude Code cloud session**.
  ⛔ They are **NOT comparable** to a plan-marshall `metrics.toon` total, which counts the
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a
  boundary a single interactive cloud session does not share. No parity figure is offered.

## Contract check (Step 9)

_Completed at Step 8 condition 3, before arming auto-merge._

## What have we learned (Step 9)

_Completed at Step 8 condition 3._

## Residue

1. ⭐ **`script-failure-analysis` reports a false `sections_dropped` and a `warning` status on every
   plan with no script failures** (F6). This is the highest-value follow-up: it is the plan's own
   Problem statement live on the most common path, and it is the *drop-side* calibration this plan's
   deliverables do not reach. The mechanism is precise — `should_emit` refuses the fragment (no
   non-empty payload list) and `_fragment_has_payload` then sees the non-empty `log_path` provenance
   string and calls it content. A follow-up should decide what `_fragment_has_payload` counts as
   content, since the same question governs every conditional row.
2. **`dispatch_boundaries` is a dead registry row** (D2). Registerable and renderable, but no producer
   registers it at top level — `analyze-logs` nests it inside the `log-analysis` fragment. The section
   is reported as a benign omission on every run. Two candidate remedies: register it as its own
   aspect, or delete the row and render the data from within Log Analysis. Neither is in this plan's
   deliverable set.
3. **`_executive-summary` has no producer** (D2). D1 removed the false *written* signal, so the
   headline section is now honestly omitted — but it is still never produced. The report currently
   ships with no Executive Summary at all. A follow-up should either add the documented orchestrator
   injection step or remove the row.
4. **F1 — a self-declared skip that names its reason is classified as a drop**, raising the run status
   to `warning` on a benign outcome. Explicitly out of scope here; the plan's premise that this
   shipped is refuted for that shape.
5. **F5 — the aspect-count lead-ins in `plan-retrospective/SKILL.md`** ("14 aspect references",
   "9 aspects", "8 in-context analytical aspects") disagree with the 15-row table. Recommended remedy
   is the standing one: prefer naming to counting, and drop the figures that carry no information the
   names do not.
6. **F15 — the aspect-table correspondence guard runs in one direction only.** Re-open the
   `registry → table` direction once neither dead row remains; today the reverse assertion would fail
   on them and encoding them as exemptions would pin them in place.
