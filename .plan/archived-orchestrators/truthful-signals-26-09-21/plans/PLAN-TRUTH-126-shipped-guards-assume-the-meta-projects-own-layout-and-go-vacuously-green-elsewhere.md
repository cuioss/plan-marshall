# PLAN-TRUTH-126: Shipped guards assume the meta-project's own layout, and go vacuously green everywhere else

epic: truthful-signals
workstream: WS-01
priority: HIGH — operator-designated 2026-09-02; a merge-gating guard is silently inert in every consumer project

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-126-shipped-guards-assume-the-meta-projects-own-layout-and-go-vacuously-green-elsewhere.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Operator observation from a **consumer project** (`cuioss/TokenSheriff`, a Maven/Java repo), 2026-09-02,
while running `default:pre-push-quality-gate`. The orchestrator was directed to verify it first-party
and, if confirmed, spec it with a full sweep of the shipped bundle.

**Verified at HEAD `30cd8aaf8`. CONFIRMED — and the primary instance is worse than reported.** ⛔ The
TokenSheriff-side observations (the `build_map` java/javascript globs, the `verify -Ppre-commit`
resolution, `exceeds_bash_ceiling: true`) are **foreign-repo and were NOT corroborated here**; they are
carried as leads. Everything asserted below about the plan-marshall tree was read from it.

## Objective

**The `plan-marshall` bundle SHIPS to consumer projects, but parts of it are written for the
meta-project's own repository layout.** Where a step reaches its target through the architecture API it
survives the trip; where it hardcodes `marketplace/bundles`, `pyproject`, `./pw` or `plugin-doctor` it
does not — and the failure mode is not an error. **It is a guard whose population is empty by
construction, iterating zero times and reporting success.**

⛔⛔ **That is this epic's most-recorded archetype — the vacuous guard, n ≥ 6 — and this instance is
merge-gating.** `pre-push-quality-gate` is `order: 5`, the second finalize step, and its own doc calls it
*"the deterministic last-line guard against type/lint AND cross-module test regressions reaching remote
CI"*. In a consumer project that last line is a no-op that reports green.

### ⛔ Instance 1 — `derive_gate_bundles` drops the consumer shape SILENTLY

`derive_gate_bundles.py` hardcodes `_BUNDLES_SUBPATH = 'marketplace/bundles'` and anchors on the
**worktree** (`--marketplace-root "<repo/worktree root containing marketplace/bundles/>"`). Its four
derivation rules, read verbatim from the module docstring:

| Rule | Shape | Outcome |
|:-:|---|---|
| 1 | matches no `build_map` glob | skipped |
| 2 | `marketplace/bundles/<b>/…` | → bundle `<b>` |
| 3 | `test/<b>/…` where `marketplace/bundles/<b>/` is real | → bundle `<b>`; otherwise → **`unresolved[]`** |
| 4 | **any other shape** | **"dropped silently — neither a bundle nor a diagnosable-unresolvable"** |

⛔⛔ **A consumer footprint hits rule 4, not rule 3.** A path like `token-sheriff-client/src/main/java/X.java`
matches a `build_map` glob and is neither `marketplace/bundles/…` nor `test/<b>/…` ⇒ it is dropped
**silently**, because `unresolved[]` is reserved for the `test/<b>/` shape alone. ⇒ The seam returns
`bundles: []` **and** `unresolved: []`, the per-bundle loop iterates zero times, the doc's
`unresolved`-WARNING branch never fires, and the step reports success.

⭐ **This is sharper than "the arm is vacuous": it is INVISIBLY vacuous.** The one diagnostic path the
seam has is closed to exactly the shape every consumer project produces. An empty result is
indistinguishable from *"nothing in this footprint needed gating"* — the *which-zero-is-this* defect,
in a merge gate.

### ⛔ Instance 2 — the whole-tree arm resolves tool-agnostically, then invokes a hardcoded Python tool

The arm probes correctly and this half is genuinely portable:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command quality-gate --audit-plan-id {plan_id}
```

⛔ **But on `status: success` the doc's very next invocation is hardcoded:**

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build \
  run --command-args "quality-gate" --plan-id {plan_id}
```

⇒ The step **resolves the executable and then does not run it.** In a Maven project the probe succeeds
(the operator reports it returning `verify -Ppre-commit` at `token-sheriff-parent`) and the gate then
invokes the *Python* build wrapper anyway.

⭐⭐ **This directly contradicts the project's own hard rule**, stated in `CLAUDE.md` § Workflow
Discipline: *"Build commands: resolve via abstraction layer — Never hard-code `./pw`, `mvn`, `npm`, or
`gradle`. Always resolve via `architecture resolve` first, **then run the returned `executable`**."* The
doc performs the resolve and discards its answer. ⚠ The probe also returns `execution_tier` and
`bash_timeout_seconds` (the operator reports `orchestrator` and `953` with `exceeds_bash_ceiling: true`),
which the hardcoded invocation likewise ignores — so even where the tool happens to match, the tier
handling does not.

### ⛔⛔ Instance 4 — `pre-submission-self-review` reports a clean pass over a surface it cannot classify

Folded 2026-09-03 from a consumer-project data-point (`cui-http` / a Java repo). ⭐ **Every mechanism
claim re-verified first-party at HEAD `30cd8aaf8`;** the consumer-run figures are the reporter's.

`default:pre-submission-self-review` (`order: 7`, **`default_on: true`**) has two halves: a deterministic
surfacer producing candidate defect sites, and an LLM cognitive review **over those candidates only**.
⇒ **Zero candidates means the LLM half never runs at all.**

The surfacer is pluggable via `ext-point-self-review-surfacing`, and **exactly one implementor exists in
the entire marketplace**: `pm-plugin-development:ext-self-review-plan-marshall`. Its classifier
partitions every changed file into six classes —

```python
CONTENT_CLASSES = ('python', 'skill_doc', 'standards_doc',
                   'markdown_other', 'structured_config', 'other')
```

— and the string `java` does not appear anywhere in `_self_review_detectors.py` (0 occurrences). **A
`.java` file is classified into `other` and then analysed by nothing.**

⛔⛔ **The result is a `done` outcome with zero findings, which is indistinguishable from "I reviewed
your changes and found nothing wrong."** The reporter's contrast is the tell: a sibling plan on the same
project recorded **3 candidates examined** — because it touched `.adoc` and `.md`, which the surfacer
*does* classify. ⇒ **The step looks like it works, because on documentation changes it genuinely does.**

#### ⭐⭐⭐ The sharper diagnosis — the report blames the wrong path, and it matters for the fix

The step doc names a **zero-generator fallback**: *"When NO implementor resolves in the current executor,
Step 1 takes the zero-generator fallback — an empty candidate set, no LLM dispatch, and a clean `done`
outcome."* ⚠ **That path is not the one that bit here, and fixing only it would leave the defect
standing.** There are TWO routes to the same silent green, and they need different remedies:

| Route | When | Today |
|---|---|---|
| **No implementor resolves** (the documented fallback) | consumer installs no bundle carrying a surfacer | clean `done`, by design |
| ⛔ **A WRONG-DOMAIN implementor resolves** | consumer also installs `pm-plugin-development` | the surfacer runs, classifies Java as `other`, returns zero — **and nothing distinguishes it from a real clean pass** |

⇒ **The second route is worse and is undocumented.** The fallback at least contemplates the absence of a
surfacer; here a surfacer answers *confidently* about a domain it does not cover. **An implementor that
resolves is treated as an implementor that applies, and nothing checks the difference.**

#### What this adds to the plan — and what it does NOT

- **D2's "degrade to a named unknown" disposition now has its highest-value instance**, and **D4 is
  exactly fix-half-1**: emit the **matched vs unmatched share of the changed surface**, so zero coverage
  over a non-empty changed set is a loud outcome — a finding, or an explicit `skipped` with the reason —
  **never a silent `done`**.
- ⛔ **Writing an `ext-self-review-java` implementor is NOT this plan's work.** That is building a domain
  capability in `pm-dev-java`, not making a guard truthful, and folding it here would turn a
  truthfulness plan into a feature plan. **It is recorded as a separate unowned item** — see the epic's
  Open Defects. ⭐ The two are independent by construction: coverage reporting is correct and valuable
  **even with no Java implementor ever written**, because "0% of the changed surface was analysable" is a
  true and useful answer.
- ⚠ **Population note:** the reporter searched every bundle and every cached version and found no
  `ext-self-review-{domain}` implementor besides the plan-marshall one. **Corroborated here across
  `marketplace/bundles/`** — the only other two hits on the ext-point name are its own contract
  (`extension-api`) and its consumer (`phase-6-finalize`). ⇒ **Every domain except plan-marshall's own is
  in this state**, so the instance is not Java-specific and D0's classification should say so.

### ✅ Instance 3 — the shape that behaves CORRECTLY, and it is the reference to copy

`finalize-step-sync-baseline`'s post-rebase executor refresh reports **`executor_drift: unknown`** with
*"Explicit marketplace anchor did not resolve to marketplace/bundles"* (the message is first-party at
`script-shared/scripts/marketplace_paths.py:771` and `:794`). ⇒ Same meta-project assumption, **but it
degrades to a NAMED unknown rather than to a green.**

⭐⭐ **D1's target shape is this one.** The fix for instances 1 and 2 is not to make them work in a
consumer project — much of what they check genuinely does not exist there — it is to make them **say
so**. A guard that cannot run must be `unknown`, never `pass`.

## ⛔⛔ The distinction that scopes this plan — read before the first grep

**Two superficially identical patterns, and only one is a defect:**

| Shape | Example | Verdict |
|---|---|---|
| **(A) Resolving plan-marshall's OWN installed bundle source** | a script locating its sibling module under the plugin cache | ✅ **Legitimate everywhere** — the installed cache has that layout by construction |
| **(B) Assuming the CONSUMER'S repository has that layout** | `derive_gate_bundles` mapping *footprint* paths to bundle names | ⛔ **The defect** |

⛔ **28 skills import `marketplace_paths`, and that count is NOT the defect population** — most are
shape A. Publishing 28 as a finding would be the under-derived-completeness error this epic records.
**D0's classification is the whole gate.**

## Deliverables

Six deliverables. D0 is a gate. **D2 is the sweep the operator asked for.**

---

**D0 — GATE: classify before fixing, and publish both partitions.**

Walk the shipped `plan-marshall` bundle (**81 skills**) for meta-project layout assumptions and classify
every hit as **(A) own-source resolution** or **(B) consumer-layout assumption**. ⛔ **Publish both
counts with the population walked**, and name the criterion that separated them.

Grep-derived FLOORS, explicitly **not** the population — each is a starting set, and the token count is
not the defect count:

| Token | Files in bundle |
|---|:-:|
| `marketplace/bundles` | 107 |
| `plugin-doctor` | 108 |
| `.claude/` | 66 |
| `pyproject` | 60 |
| `./pw` | 24 |
| `marketplace/targets` | 14 |
| `build.py` | 13 |
| `build-pyproject:pyproject_build` in a shipped doc | **7** |

⚠ **The last row is the highest-yield starting point** and spans `phase-6-finalize`, `execute-task`,
`phase-4-plan`, `persona-plan-marshall-agent`, `manage-solution-outline`, `manage-architecture` and
`script-shared`. ⛔ Some are legitimate self-reference (`build-pyproject`'s own SKILL.md must name
itself); the classification decides, not the grep.

⛔ **Do not fix a single site until the A/B partition is recorded.** Converting a shape-A site is churn
that hides the real fixes in the diff, and this epic has recorded exactly that error before.

---

**D1 — make instance 1 diagnosable: a consumer-shaped footprint must be reported, never dropped.**
Extend `derive_gate_bundles` so a path matching a `build_map` glob but resolving to no bundle under ANY
rule reaches `unresolved[]` — closing rule 4's silent-drop path for the consumer shape.

⭐ The seam's own docstring already states the correct principle for rule 3: *"never silently dropped,
never a hard failure."* **D1 extends that principle to rule 4** rather than inventing one. ⚠ Preserve
rule 4's genuine remit: a footprint path matching no glob at all is still legitimately out of scope —
the change is for paths that DID match a glob and then vanished.

---

**D2 — the sweep, and it is what the operator asked for.** For every shape-B site D0 found, decide and
apply one of exactly three dispositions, recorded per site:

1. **Route through the abstraction** — the site can be made portable (instance 2: run the `executable`
   the resolve returned, honouring its `execution_tier` / `bash_timeout_seconds`).
2. **Degrade to a named unknown** — the check genuinely cannot exist off the meta-project, so it reports
   `unknown` with the dimension named (instance 3's shape).
3. **Declare it meta-project-only** — the surface is legitimately not shipped behaviour, and says so.

⛔⛔ **"Leave it reporting green" is NOT a disposition.** Every shape-B site ends in one of the three.

---

**D3 — fix instance 2: run what the resolve returned.** Replace the hardcoded `pyproject_build`
invocation in the whole-tree arm with the resolved `executable`, and honour the returned
`execution_tier` / `bash_timeout_seconds` (an `execution_tier: orchestrator` result is an orchestrator
hand-off, not a Bash call to make anyway).

⚠ **Check the sibling arms in the same document before editing one of them** — the per-bundle loop
(§ "Derive unique bundle set") and the `test-compile` gate both invoke `pyproject_build` too. Fixing the
whole-tree arm alone would leave one document with two conventions, which is worse than one wrong one.

---

**D4 — a guard that cannot run must be visible in the step's own verdict, not only in a log line.**
Instance 3 degrades honestly but into a WARNING; instance 1 degrades into nothing at all. ⇒ The
finalize step's recorded outcome must carry which dimensions were **gated** and which were **un-gated**,
so a reader of the plan record — and `PLAN-TRUTH-123`'s scorer — can tell a checked pass from an
un-runnable one.

⭐⭐ **This is the seam to `PLAN-TRUTH-123`/`-124` and it must not be built twice.** `-123` D2 resolves
three presence states from `execution.toon`; `-124` D1 settles the shared verdict vocabulary. **D4
EMITS into that vocabulary — it does not define a fourth one.** ⚠ If `-124` has not landed, D4 records
the requirement and defers the vocabulary choice rather than coining one.

---

**D5 — the tests, and they are what stop the class from regrowing.** ⛔ Population-derived per this
epic's standing rule; publish the population size.

1. **A consumer-shaped footprint produces a DIAGNOSABLE result, not an empty one.** Feed
   `derive_gate_bundles` a Java-shaped footprint against java-shaped `build_map` globs and assert the
   paths land in `unresolved[]`. ⛔ **The matched negative control is a meta-project footprint that
   still resolves to real bundles** — without it the test passes on a seam that reports everything as
   unresolved.
2. **The whole-tree arm runs the resolved executable.** Assert the invocation is derived from the
   resolve's return, not a literal — a test asserting the literal `pyproject_build` would pin the defect,
   which is `test_inject_project_dir.py`'s recorded failure mode.
3. **A changed surface nothing classified is DISTINGUISHABLE from a clean review** (instance 4). Two
   fixtures — a changed set the surfacer classifies and one it cannot — assert two different outcomes.
   ⛔ **The matched negative control is the classifiable set**; without it the test passes on a step that
   reports "no coverage" for everything. ⚠ Cover BOTH routes to the silent green: no implementor
   resolving, and a wrong-domain implementor resolving and returning zero.
4. **No shipped doc hardcodes a build tool.** Derive the doc set from the tree and assert none names a
   `build-*` notation in an invocation position, with the legitimate self-references enumerated as an
   explicit allow-list **derived from D0's classification**, never hand-typed.

## Claim Labels

Corroborated first-party at HEAD `30cd8aaf8` on 2026-09-02 unless marked otherwise; re-ground at the
plan's own HEAD before relying on any one of them.

- **OBSERVED** — `pre-push-quality-gate.md:7` declares `order: 5`; `:20` describes the three guards and
  the per-bundle derivation; `:26-28` name the three whole-tree-only dimensions (marketplace-wide
  plugin-doctor pass, `.claude/` + `marketplace/targets` ruff, `marketplace/targets` SPDX); `:54-55`
  anchor the parity argument to `./pw verify` / `build.py:cmd_verify` / *"the one shared
  `pyproject.toml`"*.
- **OBSERVED** — `derive_gate_bundles.py:65` `_BUNDLES_SUBPATH = 'marketplace/bundles'`; its CLI takes
  `--marketplace-root` documented as the *worktree* root; and its rule 4 states any other shape is
  **"dropped silently — neither a bundle nor a diagnosable-unresolvable"**, while `unresolved[]` is
  populated only by rule 3's `test/<b>/` shape. ⇒ instance 1 is invisibly vacuous, not merely vacuous.
- **OBSERVED** — the whole-tree arm probes via `architecture resolve --command quality-gate` and then
  invokes `plan-marshall:build-pyproject:pyproject_build` (`pre-push-quality-gate.md` § "Whole-tree
  quality-gate arm"). ⇒ instance 2 resolves and discards.
- **OBSERVED** — `CLAUDE.md` § Workflow Discipline requires resolving via architecture and **running the
  returned `executable`**. ⇒ instance 2 contradicts a stated project hard rule.
- **OBSERVED** — *"Explicit marketplace anchor did not resolve to marketplace/bundles"* exists at
  `script-shared/scripts/marketplace_paths.py:771` and `:794`; `MARKETPLACE_BUNDLES_PATH` is the literal
  `'marketplace/bundles'` at `:98`; **28 skills** import that module.
- **OBSERVED** — token floors across the 81-skill bundle, as tabled in D0. ⚠ Every one is a
  **grep-derived FLOOR over one spelling**, not a defect count and not a population.
- **REPORTED, NOT CORROBORATED** — every TokenSheriff-side figure: the `build_map` java (7 globs) /
  javascript (4 globs) entries, `verify -Ppre-commit` at `token-sheriff-parent`,
  `execution_tier: orchestrator`, `bash_timeout_seconds: 953`, `exceeds_bash_ceiling: true`, and the
  `executor_drift: unknown` observation. ⛔ **Foreign repo — the orchestrator did NOT read it.** The
  plan-marshall-side mechanism stands without them; they are what make it concrete. Re-establish
  first-party at outline (a non-Python fixture project is sufficient and is preferable to depending on a
  consumer repo) or drop them from the brief.
- **HYPOTHESIS** — that instances 1 and 2 are the *only* two vacuous-in-consumer guards in
  `pre-push-quality-gate`. ⛔ **Unswept — the document is 442 lines and three arms were read.** The
  `test-compile` gate ("mypy over `test/`") and the module-tests divergence gate carry their own
  assumptions. Confirm/refute per arm in D0 (verify-at-outline).
- **HYPOTHESIS** — that the `finalize-step-sync-baseline` degradation is genuinely honest end-to-end (the
  message exists first-party; the *caller's* handling was not read). Confirm/refute at
  `phase-6-finalize/standards/finalize-step-sync-baseline.md` before adopting it as D1's reference shape
  (verify-at-outline).
- **Verify-first clause** — before D2 disposes of any site, confirm whether consumer projects are
  EXPECTED to carry a `plugin-doctor` equivalent. `CLAUDE.md` states the sync-plugin-cache surface is
  *"meta-project-only — consumer projects of plan-marshall do not get it"*, which suggests some
  dimensions are legitimately meta-project-only and belong in disposition 3 rather than 1. A refutation
  moves sites between dispositions and is a re-scope, not a detail.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
  — instances 1 and 2, and the arms D0 must sweep (D1, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/derive_gate_bundles.py` —
  the silent-drop rule 4 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md`
  — instance 3, D1's reference shape (read-only unless D0 reclassifies it)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` — the
  `marketplace/bundles` anchor and its 28 consumers (D0 classification)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — the shipped finalize step docs
  the D2 sweep dispositions
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/` — a shipped doc hardcoding
  `pyproject_build` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/` — same (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/` — same (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/` — same (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/` — same (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
  — instance 4's step contract: the zero-generator fallback and the coverage reporting D4 adds
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`
  — the ext-point Output Schema a coverage figure must be declared in (instance 4, D4)
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/` — the sole
  implementor; touched only if D0 finds the coverage figure must be EMITTED by the implementor rather
  than derived by the step from its returned candidate set (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — the D5 seam and arm tests
- OBSERVED: `test/plan-marshall/script-shared/` — the D5 doc-sweep test
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/` — D0's sweep may reach further shipped skills
  than the six named above; declared at bundle scope so a widened sweep is not an under-declaration
  (verify-at-outline). ⛔ **Narrow this to the classified set once D0 publishes it** — leaving it at
  bundle scope past D0 would serialize every sibling behind this plan.

- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/**` — the absent `ext-self-review-java` implementor, added 2026-09-03 by the drain fold of `deployment-and-refresh-gaps-018` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **D4 depends on `PLAN-TRUTH-124` D1's vocabulary** if it has landed; if not, D4 records the
  requirement and defers rather than coining a fourth verdict vocabulary. ⛔ **Do not build a second
  gated/un-gated vocabulary here** — that is the defect `-124` exists to end.
- ⚠ **`PLAN-TRUTH-123` D2 is the consumer of D4's output** (the three presence states). Recorded as a
  seam, not a transfer: `-126` emits, `-123` scores.
- ⛔ **Surface overlap is broad and MUST be re-derived at emit** — this plan reaches into
  `phase-6-finalize`, which several staged specs touch (`-097`, `-104`, `-106`, `-108`). Its declared
  surface is deliberately wide until D0 narrows it, so it will collide with more siblings than it
  ultimately needs to. **Re-run `corpus cross-check` at emit time; do not trust this note.**
- Adjacent to: `PLAN-TRUTH-104` (*a clear verdict over an empty population is reported as a checked
  negative*) is the same archetype swept tree-wide. ⛔ **This plan is one instance family, not that
  sweep** — if `-104`'s population reaches these guards, it records and defers here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-126-shipped-guards-assume-the-meta-projects-own-layout-and-go-vacuously-green-elsewhere.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`deployment-and-refresh-gaps-018.md`** (relayed from Token-Sheriff, plan `outbound-hostname-verification-quarkus`, PR #694) — *no Java-domain implementor for `ext-self-review-{domain}`, so a Java project gets a green self-review that proves nothing.*

  ⭐⭐ **This is this spec’s thesis observed from OUTSIDE the meta-project, which is the evidence class the spec was staged to obtain.** `pre-submission-self-review` ran against a 15-file diff (Java production + test sources plus AsciiDoc) and surfaced **zero candidates across all 21 detector lists**. ⛔ **Not because the diff was clean:** the only registered implementor of `ext-self-review-{domain}` is `ext-self-review-plan-marshall`, whose detectors target **Python scripts and markdown skill bodies**. Against a Java/AsciiDoc diff every one of its detector lists is **vacuously empty**.

  ⛔ **The failure mode, in the sender’s words:** the step reported *“a clean pass carrying no mechanical structural coverage at all”*, and the pass is indistinguishable from its return payload from a genuine zero-finding review of a fully-covered diff. **“This is worse than an absent step: an absent step is visible, a green step over an empty detector set is not.”**

  **Two arms, and the sender ranks them:**
  1. **Implement `ext-self-review-java`** — the real fix. Java-domain analogues of the plan-marshall detectors: symmetric-pair methods, flag-guard pairs, contract sources (interfaces/annotations), schema-bearing files, producer-consumer pairs, same-document normative Javadoc directives, stale count-prose, near-identical hunks, ordinal references. ⚠ **An extension-point implementor is a `pm-dev-java` bundle deliverable**, which is why this fold widens the Expected Surface into that bundle.
  2. **Make the coverage gap visible in the interim** — have the step report **the domain implementors it resolved** and **the detector-list population it actually ran**, so a zero over an empty population is reported as `indeterminate` rather than as a checked pass. ⭐ *“This is the cheap change and it closes the silent half of the defect even before (1) lands.”*

  ⭐ Arm 2 is the one that belongs to THIS spec’s vacuously-green thesis; arm 1 is a genuine new capability and D0 should decide whether it splits out rather than absorbing it by default.
