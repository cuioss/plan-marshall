# PLAN-TRUTH-112: plugin-doctor's LLM phase documents rules that emit nothing

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-25 from the PLAN-TRUTH-094 drain (PR #1343, `1169fb5bf`), inbox `-001`, findings
`7a3b32`, `74b801`, `d2785d`, `b9a23d`, `8668f3`. Held as Open Defects `D-094-a`…`D-094-e` pending the
classification decision below, which the operator has now settled.

⭐ **The gating question is ANSWERED, and the answer is what makes this plan small.** Two reviewers on
#1343 disagreed on whether the `doctor-skills.md` sections documenting emitter-less rule ids are
legitimate LLM-phase checks or documentation of rules that emit nothing. **Operator decision,
2026-08-25 (`AskUserQuestion`): plugin-doctor's LLM phase is NOT a first-class rule surface.** The
consequence is that every member below is a **deletion or a false-claim correction**, never a wiring
gap — do not re-open the classification.

## Objective

plugin-doctor advertises rule machinery that produces nothing: rule ids with no emitter, detectors
whose return value is never read, validators with no caller, and prescribed tooling that does not
exist. Each one tells a reader that a check is running when none is. Remove the advertisements, so the
gate's advertised surface and its emitting surface are the same set.

## Deliverables

Five deliverables. D0 is a population gate.

**D0 — GATE: derive the advertised-vs-emitting delta before deleting anything.** Enumerate (a) every
rule id cited anywhere in plugin-doctor's docs and (b) every rule id the deterministic phase can
actually emit, and publish **both counts and the delta as three numbers**. ⛔ **The five members below
were each found by a different accident during ONE plan's run, which is evidence the surface was never
swept** — a fix that deletes only these five and reports "done" repeats the defect this epic exists to
remove. ⭐ **The instrument now exists**: #1343 shipped `population_size` / `blind_spots` publication on
the argument-naming rule, so this enumeration is mechanically performable rather than aspirational.

**D1 — delete the rule ids with no emitter.** *(`7a3b32`, `D-094-a`)* Of 18 ids `plugin-doctor/SKILL.md`
cites, **7 exist nowhere in 426 scripts**. Remove them, and remove any `doctor-skills.md` prose that
frames LLM-phase guidance as a rule id. ⚠ The prose content may survive **as guidance**; only the
rule-id framing is deleted. Per the operator decision, the LLM phase emits no rule ids and the docs
must stop implying it does.

**D2 — delete the two detectors whose output nothing reads.** *(`7a3b32`, `D-094-a`)*
`check_explicit_script_violations` and `check_command_self_containment` execute and return under keys
`_doctor_analysis.py` never reads, so no `Finding` is ever constructed. Delete both, and their call
sites. ⛔ **Pin the deletion with a test that the returned key set is fully consumed**, so a future
detector cannot be added under an unread key without failing.

⛔⛔ **D3'S PREMISE IS REFUTED — RE-SCOPED 2026-08-26 at `31bed3e76`.** The claim that
`validate_extension` / `scan_extensions` are **callerless and sit behind an unregistered
`_validate.py`** is FALSE. Verified first-party: `validate_extension` has **three real call sites**
(`_cmd_extension.py:619`, `:938`, `:949`), and `_cmd_extension` is imported by
`doctor-marketplace.py:64` **and** `_runner.py:100` — both registered entry points. They are reachable.

⇒ **D3 is NOT a deletion.** What survives of it is narrower and must be re-derived before any edit:
whether the gate's extension entry (`validate_extension_contracts`) excludes the 11 manifests by
directory-name prefix, and if so whether those manifests are validated by anything. That is a
**coverage question about one population**, not dead code. ⚠ Deleting reachable, unit-tested,
called code on the original premise would have been a real regression. `validate_command_mappings`
(below) is separately confirmed dead and is unaffected by this refutation.

**D3 (as filed, premise refuted) — remove the unreachable extension validators and correct the coverage they imply.**
*(`74b801` / `D-094-b`, `d2785d` / `D-094-c`)* `validate_command_mappings` is dead code, leaving **3 of
10** documented `extension.py` contract requirements checked by nothing (required-profile presence,
`discover_modules()` compliance, `ExtensionBase` inheritance). Separately, `validate_extension` /
`scan_extensions` cover 7 of 10 contract bullets, **are unit-tested**, and have no caller — they sit
behind the unregistered `_validate.py` while the gate's extension entry is the *different*
`validate_extension_contracts`, whose population excludes those manifests by directory-name prefix
⇒ **11 manifests validated by nobody, with a green row printed.** ⭐ **The unit tests are the hazard,
not the dead code**: they are the evidence a reader would cite for coverage that does not exist, so
deleting the code without deleting or re-pointing the tests leaves the false signal standing.

**D4 — correct the two false enforcement claims.** *(`b9a23d` / `D-094-d`, `8668f3` / `D-094-e`)*
`_doctor_shared.py`'s docstring says every entry must have a `fix-catalog.md` row and
`rule-provenance.md` says **a regression test enforces it**; no test does, and the tree violates the
contract while green. ⛔ **The false part is the claim of enforcement, which is worse than the missing
test — it tells a reader not to look.** Either write the test or delete the enforcement claim; do not
leave a contract asserted and unchecked. Also: `verification-guide.md` prescribes `verify-fix.sh` and
`analyze-tool-coverage.sh` while plugin-doctor ships **no `.sh` files at all**, and
`safe-fixes-guide.md` sample code names `FIX_PRIORITY`, which exists nowhere.

## Expected Surface

⚠ **Declared narrowly and deliberately under-committed** — D0's sweep is expected to widen it, and the
disjointness consequences of a wrong declaration are `PLAN-TRUTH-113`'s subject. Re-declare after D0.

- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/SKILL.md`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-skills.md`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/verification-guide.md`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/safe-fixes-guide.md`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_analysis.py`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_shared.py`
- HYPOTHESIS: the `scan_manage_invocation` rule and the marketplace-root resolution it derives its
  accept-set from — added 2026-09-05 by the `-126` drain fold of messages `-001`/`-002` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/**` plugin-doctor suites — a root-parity control (verify-at-outline)

## Out of scope

- **Re-opening the LLM-phase classification.** Settled by operator decision 2026-08-25.
- **The argument-naming rule's own population/blind-spot machinery** — shipped by `-094` in #1343.
- Any gap owned by another staged plan; record an overlap and serialize rather than absorbing it.

## Claim Labels

- OBSERVED: 7 of 18 cited rule ids exist nowhere in 426 scripts — confirm/refute at `plugin-doctor/SKILL.md` § rule-id citations, against the emitter set in `_doctor_analysis.py`.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Emitter-set derivation needs an AST walk; a content-search sweep for cited-but-unemitted ids is unsound (misses docstring and comment-only rule refs)
- OBSERVED: `check_explicit_script_violations` and `check_command_self_containment` return under keys `_doctor_analysis.py` never reads — confirm/refute at `_doctor_analysis.py` § the result-key consumption sites.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _analyze_markdown.py calls both detectors assigning to workflow_explicit_script_violations and command_self_contained_violations; that key string appears nowhere outside this one file
- OBSERVED: `validate_command_mappings` is dead code — confirm/refute at `_validate.py` § `validate_command_mappings`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: validate_command_mappings has exactly 1 occurrence tree-wide -- its own def at _cmd_extension.py:307 -- zero callers
- OBSERVED: `validate_extension` / `scan_extensions` are unit-tested and callerless — confirm/refute at `_validate.py` § `validate_extension`.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED: validate_extension has 3 call sites in _cmd_extension.py (619,938,949) and is imported by doctor-marketplace.py:64 and _runner.py:104, both registered entrypoints; 23 references across 12 files. The sibling claim (validate_command_mappings, zero callers) stands. Re-scoped: D0 must derive the called set by an AST or import walk, never by content search.
- OBSERVED: `rule-provenance.md` asserts a regression test enforces the fix-catalog row rule, and none does — confirm/refute at `references/rule-provenance.md` § the enforcement sentence.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: rule-provenance.md:370 asserts a regression test enforces fix-catalog.md rows; test_rule_provenance_meta.py only checks that contract PROSE mentions the phrase, no test walks FIX_HANDLERS vs fix-catalog rows
- OBSERVED: plugin-doctor ships no `.sh` files — confirm/refute at `skills/plugin-doctor/` § the file listing.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Filesystem walk of the plugin-doctor skill tree finds zero .sh files
- HYPOTHESIS: the five members are a sample rather than the population — confirm/refute at `_doctor_analysis.py` § the emitter enumeration D0 derives (verify-at-outline).

⚠ Every claim above was filed first-party by `-094` inside its own run and re-checked at the drain,
but the checks were per-member and not exhaustive. D0 is the exhaustiveness gate.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Explicitly deferred to D0 emitter enumeration; not run

## Dependencies and Sequencing

⛔ **Generate this section's collision set with `corpus cross-check`; do not hand-author it.** R48
records four cross-epic misses out of seven from a hand-read map in this epic.

- **`PLAN-TRUTH-101`** shares the *documented-thing-that-does-not-work* theme but not the surface: `-101`
  is documented **invocations** that fail at runtime, this is documented **rules** that never emit.
  Not a duplicate; no ordering constraint identified.
- **`PLAN-TRUTH-104`** holds `ec6c97`, a plugin-doctor provenance test with a silently partial
  population. Adjacent surface (`plugin-doctor` provenance), different defect. **Check for overlap at
  outline.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-112-plugin-doctors-llm-phase-documents-rules-that-emit-nothing.md"
```

## ⭐ FOLDED 2026-09-05 — PLAN-TRUTH-126 drain (2 messages)

- **`shipped-guards-...-001` + `-002`** (finding `cb3735`) — *`scan_manage_invocation` emits confident
  false positives whose verdict depends on the marketplace ROOT it resolves through.*

  ⛔⛔ **This widens the spec's subject and the widening is deliberate.** `-112` was scoped to rules that
  advertise a check and **emit nothing**. This is the opposite failure at the same gate — a rule that
  emits **173 errors against a worktree marketplace root and 0 against main, on identical source**.
  Both are the same defect in the gate's *self-knowledge*: the advertised surface and the emitting
  surface are not the same set, in one direction or the other. **D0's advertised-vs-emitting delta must
  therefore be computed per RESOLUTION ROOT, not once.**

  ⭐ **The tell is inside the finding text and is mechanical**: the `registered` set the rule reports is
  always the small router/common set (`['audit-plan-id', 'help', 'plan-id', 'project-dir']`) rather than
  the subcommand's own flags — so the accept-set derivation is resolving the router and never walking to
  the subcommand. Every flag it names (`--total-tokens`, `--required-bots`, `--bot-kind`, `--types`,
  `--title`) was invoked successfully dozens of times in the run that filed the report.

  ⭐⭐ **`-002` is the half that matters most and it was found by RE-RUNNING, not re-reading.** The scoped
  control settles the cause — same 9 `--paths`, same 37-rule roster, only the root swapped: worktree **49**,
  main **0**. And the blast radius **grew between two runs over an unchanged marketplace tree** (iteration 4
  gated the same 9 dirs at `96cd4890a` with 0; the only commit since touches two `test/` files).
  ⛔ **The defect is NON-STATIONARY, so a single clean scoped run is not evidence the next one is clean** —
  D0 must state the root and the run, not just the count.

## ⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (1 claim contradicted)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 3 | `validate_extension` has no caller | **REFUTED** — 3 call sites in `_cmd_extension.py` (619, 938, 949), imported by `doctor-marketplace.py:64` and `_runner.py:104`, **both registered entrypoints**. Independently re-confirmed: 23 references across 12 files. |

⭐⭐ **The sibling claim SURVIVES and the contrast is the useful part.** `validate_command_mappings`
has **exactly one occurrence tree-wide — its own `def` at `_cmd_extension.py:307` — and zero callers**
(claim 2, corroborated). ⇒ **Two functions in the same file, one dead and one load-bearing, and the
spec asserted both were dead.** A member list built by inspection got one of two right.

⛔⛔ **This is the spec's OWN archetype committed inside the spec.** `-112` exists because plugin-doctor
advertises rules that emit nothing; its claim 3 advertised a dead function that is very much alive.
⇒ **D0's mandate hardens: the emitting/called set must be DERIVED by an AST or import walk, never by a
content-search sweep** — which claim 0's `unverifiable` verdict already concedes is unsound, since a
text search cannot tell a call from a docstring mention. **That concession is now load-bearing rather
than cautionary.**

⚠ The other corroborated members stand unchanged: the `_analyze_markdown.py` violation keys appear
nowhere outside that one file (claim 1), `rule-provenance.md:370` asserts a regression test that does
not exist (claim 4), and the skill tree holds zero `.sh` files (claim 5).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-153-tests-fixtures-and-detectors-that-cannot-fail-and-underived-completeness-claims.md` (PLAN-TRUTH-153)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
