# PLAN-TRUTH-125: One format, several implementations that disagree, and no test compares them

epic: truthful-signals
workstream: WS-01
priority: HIGH — operator-designated 2026-09-02; PLAN-TRUTH-124 D6 depends on it

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-125-one-format-several-implementations-that-disagree-and-no-test-compares-them.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Operator question, 2026-09-02, on noticing two TOON parsers named in `PLAN-TRUTH-124`: *"Isn't that an
issue in itself? There should only one parser. Analyze."* The orchestrator's read-only analysis found
the parser is **the smaller half**, and the operator directed the result into its own spec.

Every figure below was read first-party at HEAD `30cd8aaf8`.

## Objective

**TOON is this project's inter-script contract, and it has one canonical implementation plus several
partial re-implementations that disagree with it on the same values.** Nothing compares them, so the
disagreement is invisible by construction.

### The read side — two readers, one of them dead

| Reader | Callers (tree-wide) | Tests |
|---|---|---|
| `ref-toon-format/scripts/toon_parser.py` `parse_toon` | canonical | **34** |
| `manage-solution-outline/scripts/_plan_parsing.py:719` `parse_toon_simple` | **ZERO** | none |

⭐ `parse_toon_simple` has **no caller anywhere** — not in `marketplace/`, `test/`, `.claude/` or any
document. Its only reference is its own module docstring's `Usage:` block, which **advertises it as
importable**. Structurally it cannot do the canonical's job: it `strip()`s every line (destroying
nesting), treats a table header `plans[169]{id,slug}:` as a plain list, and has no multiline handling.
⇒ **Dead code that invites a future caller into a silent divergence.**

### The write side — this is the real defect

Three behaviours for the same value, all live:

| Value | `serialize_toon` (canonical, `toon_parser.py:466+`) | `format_toon_value` (`file_ops.py:1412`) | hand-rolled f-string |
|---|---|---|---|
| `None` | `null` | `` (empty) | `None` |
| `True` | `true` | `true` | **`True`** |
| `[1,2]` | JSON, quoted | `1+2` | `[1, 2]` |
| `"a,b"` | **`"a,b"` — quoted** | `a,b` — **unquoted** | `a,b` — unquoted |

⛔⛔ **The quoting row is the sharp one.** The canonical quotes any value containing the table
separator, `,`, `:`, `\n`, `"`, a leading `#` or `- `, or one that would be misread as a number/bool/null.
`format_toon_value` does none of that. ⇒ **a value containing a comma, emitted into a table row, splits
into two columns when parsed back** — silent data corruption in the row format this project uses
everywhere.

⚠ **Stated as a construction defect, NOT as an observed corruption.** The write paths disagree by
construction; whether that has actually corrupted a stored artifact is **unverified** and is D0's first
question. ⛔ Do not write it up as a known corruption before the sweep says so.

### Why nothing caught it

**34 tests cover the canonical parser. No test asserts that any OTHER emitter produces output the
canonical parser reads correctly.** Each implementation is verified against its own expectations, so a
divergence between them is outside every suite's population. ⭐ That is the same shape as `sonar.py`'s
`_map_severity` narrowing (`PLAN-TRUTH-124` D2b) — the defect lives exactly where no test looks — and
it is why D4's round-trip property, not the individual conversions, is this plan's durable half.

## Deliverables

Six deliverables (D0, D1, D2, D2b, D3, D4). D0 is a gate.

⛔ **One question in this spec is CLOSED by operator decision and is not re-openable at outline: there is
NO FALLBACK implementation of the TOON output contract — a missing canonical serializer FAILS LOUD**
(2026-09-02). D0(c) derives the population; D2b removes them.

---

**D0 — GATE: derive the implementation population and check for real corruption, before converting
anything.**

- *(a) The population.* Enumerate every function in the marketplace that WRITES or READS TOON, and
  classify each as **canonical** / **delegating wrapper** / **independent implementation**. ⛔ **Publish
  all three counts with the population walked.** First-party floor, explicitly not the population:
  **5 files define TOON emitters without importing the canonical** — `automatic-review/review_completeness.py`
  (three emitters), `phase-5-execute/verify_failure_scope.py`, `workflow-integration-github/github_ops.py`,
  `workflow-integration-gitlab/gitlab_ops.py`, and `plugin-doctor/_analyze_workflow_doc_toon_error_field.py`.
  ⚠ A **delegating wrapper is NOT a defect** — a thin per-skill function that adds a fixed envelope and
  calls the shared serializer is correct, and converting it would be churn. The classification is what
  separates the two; do not treat every hit as a conversion target.
- *(b) Has it actually bitten?* Sweep stored `.toon` artifacts for rows whose column count disagrees with
  their declared header arity, and for values that should have been quoted. **Publish the count and the
  population swept.** ⭐ A clean result is a genuine finding and must be reported as one — it means the
  defect is latent, which changes D2's urgency but not its correctness. ⛔ A zero here is only meaningful
  with its population beside it.
- *(c) ENUMERATE the fallback implementations — the DISPOSITION IS ALREADY SETTLED.* ⛔⛔ **OPERATOR
  DECISION, 2026-09-02: *"it must fail loud, no fallback."* This is NOT a per-site judgement call and
  MUST NOT be re-opened as one.** D0(c)'s only job is to derive HOW MANY sites there are; what happens
  to each is fixed by D2b below.

  The shape being removed: `tools-marketplace-inventory/resolve-dependencies.py:61`
  `serialize_toon_simple`, documented as *"Simple TOON serialization for when toon_parser is not
  available"* behind a `try: from toon_parser import serialize_toon`. ⇒ **when the canonical is
  unavailable the script silently emits a DIFFERENT FORMAT, and everything reports success.** A caller
  cannot tell a canonical emission from a lookalike, which is strictly worse than an error.

  ⚠ **Scope the enumeration narrowly — the population is fallback IMPLEMENTATIONS OF THE OUTPUT
  CONTRACT, not every `ImportError` guard.** 14 files pair an `ImportError` guard with TOON handling and
  **9 of them guard the canonical module specifically**, but they are NOT all this shape and lumping them
  together would be the archetype-stretching this epic records as a staging error. Three distinct shapes
  were observed first-party:

  | Shape | Example | In scope? |
  |---|---|---|
  | **Substitutes a lookalike implementation** | `resolve-dependencies.py:61` `serialize_toon_simple` | ⛔ **YES — this is the target** |
  | **Degrades and NAMES the degradation** | `phase-6-finalize/verdict_currency.py:276` returns `REASON_DISCOVERY_UNAVAILABLE` | ✅ **No — this is already correct** |
  | **Degrades a value silently** | `_architecture_core.py:326` returns `None`; `ci_base.py:724` falls back to legacy flag handling | ⚠ **No — different subject, RECORD and leave** |

⛔ **Do not convert a single emitter until (a)'s three-way classification is recorded.** Converting a
correct delegating wrapper is churn that hides the real conversions in the diff.

---

**D1 — delete the dead reader.** Remove `parse_toon_simple` and its `Usage:` advertisement from
`_plan_parsing.py`. It has zero callers, zero tests, and cannot parse the table form this project emits.
⭐ **This is the whole read-side fix**, and it is deletion, not migration. ⚠ Confirm the zero-caller
finding at the plan's own HEAD before deleting — it was true at `30cd8aaf8` and a spec is not a
substitute for re-checking a deletion premise.

---

**D2 — one authoritative serializer, and a recorded decision for `format_toon_value`.**

`serialize_toon` is the authority: it is the only implementation that quotes, and quoting is what makes
the format round-trip. The question D2 settles is what happens to `file_ops.format_toon_value` and its
`print_toon_kv` / `print_toon_list` / `print_toon_table` family — **retire them onto the canonical, or
keep them and make them agree.** ⚠ They are widely used, so this is the deliverable with the blast
radius; D0(a)'s counts decide it, and the decision is recorded either way.

⛔ **Whichever path: the `None` / `bool` / `list` / quoting rows above must produce ONE rendering each.**
A "mostly agrees" serializer is the current state.

**D2b — remove every fallback implementation of the output contract; the canonical import FAILS LOUD.**
⛔⛔ Operator decision, 2026-09-02: *"it must fail loud, no fallback."* Delete `serialize_toon_simple` and
every site D0(c) enumerates as the same shape, and let the `ImportError` propagate as a stated error.

⭐ **The correct pattern already exists first-party in this tree and should be copied rather than
designed**: `phase-6-finalize/verdict_currency.py:276` catches its `ImportError` and returns
`REASON_DISCOVERY_UNAVAILABLE` — it **names the degradation instead of substituting a lookalike**. The
principle: a missing canonical serializer means the script's OUTPUT CONTRACT cannot be honoured, so it
must say so, not emit something shaped like the contract.

⚠ **Why the fallback existed, and why that reason does not survive.** `toon_parser` is a marketplace
sibling reached through the executor's path assembly, so the guard was protecting against a PACKAGING
failure. ⇒ **A packaging failure that silently changes the output format is precisely the failure that
must be loud** — it is invisible at the moment it happens and misattributed later. ⛔ Do not reinstate a
fallback on the grounds that the import "should never fail"; if it never fails, the guard costs nothing
to remove, and if it can fail, the silence is the defect.

---

**D3 — convert the independent emitters D0(a) identified.** The hand-rolled `print(f'key: {value}')`
sites route through the authoritative path. ⚠ **Convert only what D0(a) classified as independent** —
delegating wrappers stay.

---

**D4 — the round-trip property test, and it is the deliverable that outlives the other four.**

⛔ **Population-derived, per this epic's standing rule.** Derive the emitter list **from the tree** — not
a hand-typed roster — and assert, for every one: *what it emits, the canonical parser reads back
unchanged.* Publish the population size so a suite that degenerates to zero emitters cannot report green.

Matched controls are the whole test:

1. **Positive** — a payload containing a comma, a colon, a newline, a `None`, a `True` and a list
   round-trips through every enumerated emitter unchanged.
1b. **The canonical import failing is LOUD, not silent** (D2b). Simulate an unavailable `toon_parser` and
   assert the script ERRORS rather than emitting anything. ⛔ The matched negative control is the whole
   point: a test that only ever runs with the module present cannot see a fallback, which is exactly why
   `serialize_toon_simple` survived unnoticed.
2. **Negative** — a deliberately hand-rolled emitter is DETECTED. ⛔ Without this the suite passes on a
   population it never actually checked, which is the failure `test_inject_project_dir.py` is this
   epic's recorded precedent for.
3. **The sixth-emitter guard** — adding a new TOON emitter that bypasses the canonical must FAIL the
   suite. That is what makes this durable rather than a one-off cleanup: without it the population
   regrows and the next audit re-derives this same finding.

## Claim Labels

Corroborated first-party at HEAD `30cd8aaf8` on 2026-09-02 unless marked otherwise; re-ground at the
plan's own HEAD before relying on any one of them.

- **OBSERVED** — `parse_toon_simple` (`_plan_parsing.py:719`) has **zero references tree-wide** outside
  its own module docstring `Usage:` block; searched `marketplace/`, `test/`, `.claude/` and all tracked
  documents.
- **OBSERVED** — `serialize_toon` (`toon_parser.py:466+`) quotes on separator / `,` / `:` / `\n` / `"` /
  leading `#` / leading `- ` / number-or-bool-lookalike, and renders `None`→`null`, `bool`→`true|false`,
  `list`→quoted JSON.
- **OBSERVED** — `format_toon_value` (`file_ops.py:1412`) renders `None`→`''`, `bool`→`true|false`,
  `list`→`'+'`-joined, and **performs no quoting or escaping at all**.
- **OBSERVED** — `review_completeness.py:1236` `_emit_toon` is hand-rolled `print(f'key: {value}')` with
  no shared value formatting; the same file carries `_emit_deficit_toon` and `_emit_size_caps_toon`.
- **OBSERVED** — 5 files define TOON functions without importing the canonical module (enumerated in
  D0a). ⚠ A **grep-derived FLOOR** over one import spelling, explicitly not the population.
- **OBSERVED** — `resolve-dependencies.py:61` `serialize_toon_simple` is a documented silent fallback
  *"for when toon_parser is not available"*, guarded by an `ImportError` try. **14 files** pair an
  `ImportError` guard with TOON handling, and **9 of those guard the canonical `toon_parser` module
  specifically**. ⚠ Both figures are grep floors; how many are the lookalike-substitution shape is
  D0(c)'s to derive.
- **OBSERVED** — the guards are NOT one shape. Three were read first-party and differ in kind:
  `resolve-dependencies.py:61` substitutes a lookalike implementation; `verdict_currency.py:276` returns
  the NAMED `REASON_DISCOVERY_UNAVAILABLE`; `_architecture_core.py:326` and `ci_base.py:724` degrade a
  value silently. ⇒ only the first is this plan's target (D0c).
- **OPERATOR DECISION (2026-09-02), not a claim to re-verify** — *"it must fail loud, no fallback."*
  Recorded here so a future reader treats D2b as settled rather than as a design option.
- **OBSERVED** — `test/plan-marshall/ref-toon-format/test_toon_parser.py` carries **34** tests, and no
  test in the tree asserts cross-emitter agreement (searched for tests referencing `format_toon_value`,
  `print_toon_table` or `_emit_toon` — three files match and none compares emitters).
- **HYPOTHESIS** — that a value requiring quoting has actually reached a stored `.toon` artifact and
  corrupted a row. ⛔ **UNVERIFIED — the divergence is established by construction, the corruption is
  not.** Confirm/refute in D0(b) (verify-at-outline). A refutation makes the defect latent and changes
  D2's urgency, not its correctness.
- **HYPOTHESIS** — that `platform-runtime/runtime_base.py`'s `toon_success` / `toon_error` / `toon_noop`
  and `plugin-maintain/_maintain_shared.py`'s `output_toon` are delegating wrappers rather than
  independent implementations (each imports the canonical). Confirm/refute per site in D0(a)
  (verify-at-outline) — if they are wrappers they are correct and out of D3's scope.
- **Verify-first clause** — before D2 retires anything, confirm `format_toon_value`'s consumers do not
  depend on its DIVERGENT behaviour (notably `None`→`''` rather than `null`, and `'+'`-joined lists). A
  consumer relying on the divergence turns D2 from a retirement into a migration and is a re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py` — the
  authoritative serializer/parser (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-toon-format/SKILL.md` — the format contract
  and the single-implementation rule (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` —
  the dead reader and its `Usage:` advertisement (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` —
  `format_toon_value` and the `print_toon_*` family (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` —
  three hand-rolled emitters (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py` —
  a hand-rolled emitter (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` —
  `format_checks_toon` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py` —
  the symmetric twin; ⛔ changing one and not the other is a divergence this project has recorded before
  (D3)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/resolve-dependencies.py`
  — the silent `serialize_toon_simple` fallback (D0c)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py`
  — `serialize_inventory_toon` (D0a classification, D3 if independent)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` —
  touched only if D0(a) classifies its three emitters as independent (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/plugin-maintain/scripts/_maintain_shared.py`
  — same condition (verify-at-outline)
- OBSERVED: `test/plan-marshall/ref-toon-format/` — the D4 round-trip property and its controls
- OBSERVED: `test/plan-marshall/automatic-review/` — the converted emitters' tests (D3)

## Dependencies and Sequencing

- Depends on: none.
- ⭐⭐ **`PLAN-TRUTH-124` D6 DEPENDS ON THIS PLAN.** That deliverable promises `statistics` returns *"the
  unified data as a standardized TOON model"* — **a standardized model emitted through a divergent
  serializer is not standardized.** ⇒ This plan should land before `-124` D6 is implemented. ⚠ It is NOT
  a hard block on `-124` as a whole: D0-D5 there are vocabulary work that does not touch serialization,
  so the two can run in either order provided `-124` D6 reads this plan's outcome.
- ⛔ **The chain is now `-125` / `-124` → `-123`.** `-123` remains hard-blocked on `-124`.
- ⚠ **Surface overlap with `-124` is small but real**: both may touch
  `workflow-integration-github/scripts/` and `workflow-integration-gitlab/scripts/`, though at different
  functions (`-124` at `add_finding` fields, `-125` at `format_checks_toon`). **Re-derive from
  `corpus cross-check` at emit time** rather than trusting this note.
- ⚠ **Cross-epic:** `review-apparatus` specs touch `github_pr.py`, not `github_ops.py`; the two are
  different files and the distinction matters when reading a collision row. Re-derive rather than assume.
- Adjacent to: `PLAN-TRUTH-124` D2b (`_map_severity` narrowing) is the same archetype in a different
  format — a lossy boundary no test compares across. ⛔ Do not re-derive it here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-125-one-format-several-implementations-that-disagree-and-no-test-compares-them.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
