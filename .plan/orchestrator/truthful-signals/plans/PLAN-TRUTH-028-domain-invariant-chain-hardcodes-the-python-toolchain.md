> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-019`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-028: the domain-invariant chain hardcodes the Python toolchain

epic: truthful-signals
workstream: WS-01

## Objective

Domain-invariant plan-marshall surfaces — steps that run for **every plan in every project** — invoke
`plan-marshall:build-pyproject:pyproject_build` verbatim and describe their own behaviour in Python
terms (mypy, ruff, pytest). On a Maven or npm consumer repo those invocations are simply wrong. The
architecture resolver is **not** at fault and already returns the correct per-project command; the
invariant layer bypasses it.

De-bleed the invariant chain: route every domain-invariant build invocation through
`architecture resolve`, restate toolchain-specific prose in canonical terms, and add a detector so the
class cannot silently regrow.

## Provenance — a RECURRENCE, not a new finding

⛔ **This is the second report of an Open Defect already in this ledger** (`epic.md` Open Defects,
tagged *Source: API-Sheriff #8*), which recorded `pre-push-quality-gate.md` as written entirely against
`build-pyproject`. The 2026-08-01 API-Sheriff report re-reported it independently with sharper evidence
(exact call sites, and a green gate obtained only by the operator resolving the canonical by hand).
⇒ **Fold the recurrence onto the existing defect; do not file a second one.** The recurrence is itself
the signal: the defect was recorded, not allocated, and then cost a second consumer real time.

⭐ The reporter's own hypothesis — *"the same smell likely affects the sibling steps that name
`pyproject_build`"* — is **CONFIRMED and under-stated**. It reaches `execute-task` and the foundational
persona, not just sibling finalize steps.

## The diagnosis the sweep produced

A manual file-by-file read of the invariant chain (see § Sweep Result) found the bleed is **not**
uniform ignorance of other domains. Two structural facts shape the whole fix:

1. **The code layer is domain-complete; the prose layer is not.** Every Python registry that had to
   work for the product to function enumerates all four build systems and says so —
   `_build_execute_factory._TOOL_NOTATIONS` (maven/gradle/npm/python, with `routable_notations()`
   documented as "the single source of truth") and `inject_project_dir._BUCKET_B_NOTATIONS` (all four
   wrappers plus the integration tools). The hardcoding lives almost entirely in **markdown workflow
   and standards documents**, which no consumer-repo run ever exercised until API-Sheriff did.
2. **The shape is Python-as-primary-with-a-degraded-fallback, not Python-only.** Three independent
   surfaces know non-Python projects exist and handle them *only in the fallback arm* while the primary
   arm stays hardcoded: `pre-push-quality-gate.md`'s `whole_tree_available == false` branch commented
   *"(e.g. a non-Python project)"* (covers the pytest arm, not the two quality-gate arms), the same
   doc's whole-tree honest-degradation branch, and `tool-usage-patterns.md` step 2's *"a non-pyproject
   build"* fallback under a hardcoded step 1. ⇒ **A fix that only adds more fallbacks reproduces the
   defect.** The primary arm must resolve.

⛔ **The root cause of the two hardest call sites: two verbs have NO canonical.** The resolver's
command set is six — `clean, compile, quality-gate, verify, module-tests, coverage` (OBSERVED as real
resolver output quoted in `pre-push-quality-gate.md`'s recorded caveat). Neither **`test-compile`** nor
**`resolve-test-scope`** is among them. Those are exactly the two invocations that cannot be fixed by
"call `architecture resolve` instead", and exactly where the authors hardcoded.

⭐ **The existing caveat is a defending-documentation instance** (archetype n=5 in this epic).
`pre-push-quality-gate.md` argues its `test-compile` bypass "is **not** a hard-coded build command"
because the executable and `run --command-args` shape "still come from the resolver" — reasoning that
only holds for Python. On Maven there is no module-scoped `test-compile` whose module argument you can
drop. **The defence is Python-specific prose defending a Python-specific bypass.**

## Deliverables

1. **D0 — GATE (mutates nothing): derive the population.** The Sweep Result below is a **SAMPLE** — the
   orchestrator read roughly a dozen files of a much larger invariant surface. Derive the real
   population by the *defect shape*, not by one token: (a) a hardcoded build-wrapper notation in any
   domain-invariant skill, (b) toolchain-proper-noun prose (mypy / ruff / pytest / pyproject) in an
   invariant doc, (c) a primary-arm-hardcoded / fallback-aware pair. ⛔ **Do not grep for
   `pyproject_build` and call that the population** — shape (b) and (c) do not contain it.
   ⚠ D0 also decides whether D1 splits out (below).
2. **D1 — settle the two non-canonical verbs.** Decide, and record why, exactly one of:
   **(a)** register `test-compile` and a test-scope resolution as first-class canonicals across all
   four build systems (a production change to build-command discovery — `_build_commands` plus an
   `architecture discover` refresh, and the equivalent for maven/gradle/npm); or **(b)** keep them
   out-of-band but make the invariant docs degrade **honestly and symmetrically** — the non-Python path
   must be a stated, logged capability gap, never a silently-wrong invocation.
   ⛔ **(a) is a genuinely larger change than the rest of this plan combined.** If D0 confirms that,
   **split it into a sibling plan** and let this plan take (b) as the interim, with the gap logged.
   Record the split-or-proceed decision either way.
3. **D2 — de-bleed `pre-push-quality-gate.md` (the reported surface).** All six call sites route
   through `architecture resolve --command {canonical}`; the four resolvable ones
   (`quality-gate` ×2, `module-tests` ×2) can be fixed with no new canonical — **API-Sheriff proved
   `architecture resolve --command quality-gate` already returns the correct Maven form.** The
   remaining two follow D1. Restate the Python-specific rationale prose (mypy/ruff/pytest, the
   `.claude/` ruff paths, the `marketplace/targets` SPDX coverage, `build.py:cmd_verify`,
   `_pyproject_cmd_discover._build_commands`) in canonical terms, or move it to a
   meta-project-specific home. ⛔ **Retire the defending caveat** — do not update it.
4. **D3 — de-bleed `execute-task` and the foundational persona.** `execute-task/SKILL.md` is the
   per-task runner for **every** profile and domain: its hardcoded `pyproject_build resolve-test-scope`
   call and its normative Python prose (*"mypy and ruff must also pass"* as a MUST-NOT-mark-done
   condition) bind every consumer. `persona-plan-marshall-agent/standards/tool-usage-patterns.md` is
   loaded by **every agent in every domain** and makes a hardcoded pyproject `parse` call the stated
   *first choice*. ⛔ Fix the primary arm; do not settle for improving the fallback.
5. **D4 — de-bleed teaching-by-example, and justify any deliberate retention.** `phase-4-plan/SKILL.md`
   illustrates the `verification.commands` TOON quoting rule with a hardcoded pyproject command, and
   `manage-solution-outline/examples/plugin-feature.md` models four more. These do not break a
   consumer run directly — they teach plan authors to hardcode, which is how the class reproduces.
   ⚠ Some may be legitimately meta-project-scoped; **state the retention reason per site** rather than
   converting or deleting silently.
6. **D5 — a detector, and tests that fail pre-fix.** A rule that flags a build-wrapper notation in a
   domain-invariant skill. ⛔ **Population-derived from D0, not a hand-listed set** — this epic's
   standing rule, and a vacuous guard here would be occurrence 6+ of that archetype. Tests: (a) an
   invariant doc with a hardcoded notation is flagged; (b) `build-pyproject`'s own docs and the
   domain-complete registries are NOT flagged (the false-positive boundary — both directions);
   (c) D0's population derivation is asserted non-empty and contains the known members.

Six deliverables — at the presumptive split threshold. **Split evaluated and declined for D0/D2–D5**
(one archetype, one derived population, one detector); **D1 carries its own explicit split trigger.**

## Sweep Result (manual, file-by-file — a SAMPLE, see D0)

**Confirmed bleeds, by severity:**

| # | Site | Kind | Why it matters |
|---|------|------|----------------|
| 1 | `phase-6-finalize/standards/pre-push-quality-gate.md` lines 99, 112, 135, 163, 180, 189 | 6 hardcoded invocations + pervasive Python prose | `class: core`, `default_on: true` — dispatched for every plan in every project |
| 2 | `execute-task/SKILL.md:256` | hardcoded `resolve-test-scope`; plus normative prose at :37, :248, :261, :297 | the per-task runner for every profile and domain |
| 3 | `persona-plan-marshall-agent/standards/tool-usage-patterns.md:89` | hardcoded `parse` as stated *first choice*, fallback-aware at step 2 | loaded by **every agent in every domain** |
| 4 | `phase-4-plan/SKILL.md:565,573` | teaching-by-example in the `verification.commands` quoting rule | plan authors copy it into every task |
| 5 | `manage-solution-outline/examples/plugin-feature.md` ×4 | teaching-by-example in the outline template | outline authors copy it |
| 6 | `phase-5-execute/standards/canonical_verify.md` | descriptive prose only ("mypy + ruff") | otherwise the exemplary correct implementation |

**Verified CLEAN — reference implementations. ⛔ Do not "fix" these:**

- `phase-5-execute/standards/canonical_verify.md` **mechanism** — resolves every canonical via
  `architecture resolve --command {canonical}`, with an explicit unresolved-canonical skip. **This is
  the pattern D2/D3 should adopt; the correct mechanism already exists one phase earlier.**
- `phase-6-finalize/standards/ci-verify.md` — classifies build checks by architecture-resolved
  canonical names and sends divergence to `architecture` config, *"not here"*.
- `phase-6-finalize/standards/finalize-step-simplify.md` — *"Domain-agnostic by construction"*, loads
  only invariant standards.
- `script-shared/scripts/build/_build_execute_factory.py` `_TOOL_NOTATIONS` / `routable_notations()`
  and `execute-task/scripts/inject_project_dir.py` `_BUCKET_B_NOTATIONS` — domain-complete registries.
- `manage-architecture/standards/resolve-command.md` — pyproject appears as resolver **output**
  examples, which is what that document is for.

## Claim Labels

- **OBSERVED**: all six `pre-push-quality-gate.md` call sites and their line numbers, read this pass;
  the file's `class: core` / `default_on: true` frontmatter; the Python-specific prose throughout.
- **OBSERVED**: `execute-task/SKILL.md:256` hardcodes `pyproject_build resolve-test-scope`; :37 makes
  *"mypy and ruff must also pass"* a normative gate condition.
- **OBSERVED**: `tool-usage-patterns.md:89` hardcodes the pyproject `parse` call as step-1 first choice,
  with a *"non-pyproject build"* fallback at step 2.
- **OBSERVED**: the resolver's six-command set, quoted as real resolver output in
  `pre-push-quality-gate.md`'s recorded caveat — `test-compile` and test-scope are absent.
- **OBSERVED**: the two domain-complete registries named above enumerate all four build systems.
- **REPORTED (API-Sheriff, first-party to them, NOT verified by us)**: that
  `architecture resolve --command quality-gate` returned `maven run --command-args "verify -Ppre-commit"`
  on their repo, and that a strict reading of the standard would have run pyproject tooling against a
  Java repo. ⚠ We cannot run their resolver; **D2 must re-confirm the resolvable-today claim against a
  real non-Python project before relying on it.**
- **HYPOTHESIS**: the six sweep rows are the whole population — **confirm/refute at D0. They are a
  sample; the orchestrator read roughly a dozen files.**
- **HYPOTHESIS**: `manage-solution-outline/examples/plugin-feature.md` is legitimately
  meta-project-scoped and needs no conversion — **confirm/refute at D4.**
- **Verify-first clause**: D1's option (a) assumes `test-compile` and a test-scope verb are meaningful
  canonicals for Maven, Gradle and npm. That must be settled against each build system's real
  capability before any canonical is registered — a canonical that resolves for one toolchain and
  silently no-ops for three is this same defect wearing the resolver's clothes.

## Expected Surface

- **OBSERVED**: `plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
- **OBSERVED**: `plan-marshall/skills/execute-task/SKILL.md`
- **OBSERVED**: `plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md`
- **OBSERVED**: `plan-marshall/skills/phase-4-plan/SKILL.md`, `manage-solution-outline/examples/plugin-feature.md`
- **OBSERVED**: `plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` (prose only)
- **HYPOTHESIS**: further sites from D0 (verify-at-outline — the point of D0)
- **HYPOTHESIS**: `pm-plugin-development/skills/plugin-doctor/**` for D5's detector (verify-at-outline)
- **HYPOTHESIS**: `build-pyproject/scripts/_pyproject_cmd_discover.py` and the maven/gradle/npm
  equivalents, **only if D1 takes option (a)**

## Dependencies and Sequencing

- **Depends on**: none.
- ⛔ **EXCLUSIVE-COLLIDES with PLAN-TRUTH-002** — that spec declares itself exclusive against anything
  touching dispatched workflow docs, and this plan edits several. **Cannot run concurrently.**
- ⛔ **SERIALIZATION PAIR with PLAN-TRUTH-026** — 026 makes `--plan-id` mandatory on build operations
  and touches the same build-invocation call sites this plan rewrites. **Whichever lands second
  re-grounds.** ⭐ Strong argument for **026 first**: rewriting a call site to resolve via architecture
  and *then* changing its argument contract touches the same lines twice.
- ⚠ **PLAN-TRUTH-019** (`build-gate-coverage-parity`) concerns the local gate vs CI parity and names
  `pre-push-quality-gate.md` as a surface it may move — **check for overlap at outline; name the PR to
  `review-apparatus` if that file moves** (TRUTH-019's own recorded constraint).
- ⚠ **PLAN-TRUTH-012** (`canonical-block-diverges-from-argparse-choices`) shares the plugin-doctor
  analyzer surface D5 targets.
- **Adjacent to**: `PLAN-TRUTH-010` — its "what is genuinely build-class" question informs D0's shape
  (b) classification, but the two do not touch the same files.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-028-domain-invariant-chain-hardcodes-the-python-toolchain.md"
```

## ⭐ FOLDED 2026-08-02 — THIRD-PARTY RECURRENCE, and it converts a hypothesis into an observation

Round-7 item 8 of a consuming project's bundle findings (bundle 0.1.1276), **checked first-party by the
filer**:

> `pre-push-quality-gate` names `pyproject_build` unconditionally, so it **resolves the wrong build
> system on a Maven project**. Observed in `plan-35-bearer-proxied-benchmark-regression`, an
> **all-Java/Maven repository**.

⛔ **Recurrence, NOT a new item — do not re-file it.** Its value is evidential, not informational:

⭐ **This plan's core claim was that the PROSE layer is Python-primary while the CODE layer
(`_TOOL_NOTATIONS`, `_BUCKET_B_NOTATIONS`) is domain-complete. That claim was derived from a manual
sweep of our own tree — i.e. it predicted a failure nobody had yet observed. It has now been observed,
in a real all-Maven consumer, on the exact file this plan names first.**

⇒ **D0's population must no longer be justified as a precaution.** It is confirmed live. ⚠ And the
consuming project reached it *through a landing*, meaning the hardcode is not merely latent — it fires
in normal use on a non-Python repo.

⚠ **Bundle 0.1.1276 predates our tree — re-ground the line references at D0**, but the call-site count
in § Sweep Result remains a SAMPLE either way.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
