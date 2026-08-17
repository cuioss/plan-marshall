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

**Verification state:** the invariant assertion was written FIRST and observed RED against pre-fix
code (`assert 'Executive Summary' not in written` → `AssertionError: … ['Executive Summary', …]`).
The zero-attribution probe was mutation-tested in both directions — forcing `_names_checked_set` to
always return `True` (guard can never fire) and forcing it to ignore attribution (guard always fires)
each turn the suite red.

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

The remaining 15 rows are reachable.

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
| `TestZeroReportingSectionNamesItsCheckedSet` (8 cases) | **Characterization of new behaviour**, mutation-proven | The probed function did not exist pre-fix, so no pre-fix red is possible; non-vacuity established by two mutations instead |
| `TestAspectTableKeysMatchTheRegistry` (5 cases) | **Characterization of new structure**, mutation-proven | The Key column did not exist pre-fix; two mutations (wrong key, reordered column) turn it red |
| `test_metadata_append_preserves_the_earlier_value` | **Regression** | The multi-session case the scalar destroyed |
| `test_store_appends_to_the_session_ids_list` | **Regression** | Mutation reinstating the overwriting `--set` turns it red |
| `test_read_returns_the_most_recent_entry` | **Regression** | Mutation returning the first entry turns it red |
| remaining `--append` cases (7) and session-read cases (5) | **Characterization of new behaviour** | New verb / new read path; no pre-fix behaviour to regress from |
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

Test functions added: 9 (manage-status metadata) + 13 (compile-report behaviour) + 5 (render guard)
+ 8 (claude_runtime) = **35 test functions**; the four touched files collect **368 cases** in total.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **9 files** (5 production, 4 test). Python
changed, so the full gate applies.

- Per-commit `./pw quality-gate` before each `*.py`-touching commit: `ruff … All checks passed!`,
  `mypy … Success: no issues found in 412 source files`, `SPDX-header check passed`.
- Full `./pw verify` over the branch diff: **`=== verify: SUCCESS ===`**, `20683 passed, 14 skipped`
  — all three sub-steps (quality-gate, test-compile, module-tests).
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

_The verification sub-agent's findings are appended below when its round completes._

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

1. **`dispatch_boundaries` is a dead registry row** (D2). Registerable and renderable, but no producer
   registers it at top level — `analyze-logs` nests it inside the `log-analysis` fragment. The section
   is reported as a benign omission on every run. Two candidate remedies: register it as its own
   aspect, or delete the row and render the data from within Log Analysis. Neither is in this plan's
   deliverable set.
2. **`_executive-summary` has no producer** (D2). D1 removed the false *written* signal, so the
   headline section is now honestly omitted — but it is still never produced. The report currently
   ships with no Executive Summary at all. A follow-up should either add the documented orchestrator
   injection step or remove the row.
3. **F1 — a self-declared skip that names its reason is classified as a drop**, raising the run status
   to `warning` on a benign outcome. Explicitly out of scope here; the plan's premise that this
   shipped is refuted for that shape.
4. **F5 — the aspect-count lead-ins in `plan-retrospective/SKILL.md`** ("14 aspect references",
   "9 aspects", "8 in-context analytical aspects") disagree with the 15-row table. Recommended remedy
   is the standing one: prefer naming to counting, and drop the figures that carry no information the
   names do not.
