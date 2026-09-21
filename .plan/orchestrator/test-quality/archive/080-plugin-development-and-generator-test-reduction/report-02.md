# Run report — 080-plugin-development-and-generator-test-reduction (run 02)

**Date (UTC):** 2026-08-19    **Branch:** `chore/plugin-dev-generator-tests-run-02`    **PR:** [#1306](https://github.com/cuioss/plan-marshall/pull/1306)    **Outcome:** completed

> **Verification loop exit:** `verifier-clear`

A **re-entry** of a landed plan, as the epic README sanctions: a new report ordinal in the same
directory, the plan's deliverables unchanged. Run 01 (PR #1302, merge commit `6427016`) recorded its
unfinished work in `report-01.md` § Residue; this run closes the reachable part of it.

## Skills loaded

`cloud-plan-lane`, from `.claude/skills/cloud-plan-lane/SKILL.md`. The surface is `test/**` only, so the
one domain skill the work touches is `pm-dev-python:pytest-testing`, whose house rules reach this run
through `doc/plans/test-quality/README.md` § House style (**B1**–**B10**).

**Branch form: run-created**, not harness-assigned. The session's original `claude/*` branch was
consumed by run 01 and locked at enqueue, so this run cut a new one under the closed prefix set —
`chore/` for maintenance and refactoring, per `CLAUDE.md` § Branch Naming.

## Deliverables

Run 01 completed D1, D2, D4 and D5 and left D3 partial. This run addresses D3's two open halves.

| # | Deliverable | Run 01 | Run 02 |
|---|---|---|---|
| D3 **B6** — namespaces from the real parser | 184 of 211 | **211 of 211 — complete, 0 remaining** |
| D3 **B7** — one import preamble | 59 → 9 findings | **9 → 2** |
| D1 — scaffold conversion | 51 of 57 modules | **unchanged, and deliberately** — see below |
| D2, D4, D5 | Done in run 01 | not re-opened |

### D3 § B6 — complete

| Measure | Before | After |
|---|---:|---:|
| Hand-built `argparse.Namespace` in the slice | **27** | **0** |
| `parse_ns` template calls | 25 | **39** |

⚠️ **The population needs restating, because the plan's own re-derivation command over-counts.**
`grep -c 'Namespace('` also matches `types.SimpleNamespace(` — 11 in this slice, never a B6 target — and
the after-count additionally contains the `_ns` overlay helper's own body, one per converted module. The
figure above is hand-built `argparse.Namespace` **only**, which is what B6 is about.

**`profiles.py` is the concrete case for why B6 matters.** Its real parser yields a **`plan_id`**
attribute that none of the five hand-built namespaces in that module carried at all — so those tests
were passing against a namespace the CLI cannot produce, which is precisely the defect B6 exists to
remove. It was found by doing the conversion, not by arguing for it.

**Ambiguous shapes are keyed on the handler, never on the kwarg set.** `profiles.py`'s `unmatched` and
`suggest` both take only `--project-dir`; each site uses the template for the handler it actually feeds.
The verification round confirmed this independently and by a stronger method than test outcome — the
parsed namespaces carry the parser's own `func` binding, so `_REVIEW_NS.func is cmd_review` and its
siblings settle the pairing directly. `profiles.py` has no `func`; its `handlers` dict was read instead.

**Every one of the 39 `parse_ns` calls is at module scope** (column 0), so none re-executes its script
module per test — the hazard the plan names explicitly.

### D3 § B7 — 9 → 2, and the third survivor was mine, not the tree's

Skill-root `extension.py` loads now route through `conftest.load_skill_module`. Five path constants left
dead behind them were removed — **ruff does not flag an unused module-level constant**, so they would
have survived the lint that cleaned up the `importlib` imports beside them.

⛔ **The first commit of this run kept a third survivor on a false rationale, and the verification round
caught it.** That commit reported that `test/marketplace/test_extension_profiles.py` could not be
converted, because routing it through `load_skill_module` pushed the loader-collision guard to 91
unresolved call sites against a bound of 90, and the guard's own comment forbids growing that bound.
Both halves are true. **The conclusion was not.**

The walker skips any call that opts out of registration
(`test/plan-marshall/script-shared/_loader_contract_fixtures.py:220`), and the rule's own message names
the escape verbatim: *"pass a distinct `module_name` — **or `register=False`** — or they displace each
other."* Passing `register=False` converts the module, leaves the unresolved count at exactly **90**, and
is **behaviour-identical** to the preamble it replaces, which never touched `sys.modules`.

The rule this run now applies, stated once so it is reusable:

> A **literal** `module_name` where the guard can read it; **`register=False`** where the name is
> computed and the guard cannot.

**The two remaining survivors are genuinely unreachable, and the reason is structural rather than
budgetary.** `test/marketplace/targets/test_dist_manifest.py` loads `marketplace/targets/generate.py`
and `test/marketplace/test_spdx_enforcement.py` loads the repository-root `build.py`. `MARKETPLACE_ROOT`
is `marketplace/bundles`, so neither `load_skill_module` nor `get_skill_dir` can address either file.
This is not a residue a later run can close by spending more budget.

### D1 — not re-opened, and that is the finding

The dispatch brief named "the unconverted D1 modules" as run 02 scope, and the verification round
correctly flagged that no `test_analyze_*.py` appears in this diff: 51 of 57 import
`assert_analyzer_findings` at both `main` and HEAD. **That is the right outcome, not an omission.**
Run 01 characterised all six individually — a two-argument analyzer, a subset assertion the scaffold's
full-multiset comparison would change, a results-not-findings return, two modules with no analyzer call
at all, and a verifier-echo test. None became convertible between runs. The brief overstated the scope;
the deliverable did not understate it.

## Build gate

**Python-change verdict.** `git diff --name-only origin/main...HEAD -- '*.py'` returns 12 files, so the
gate applies.

**The gate that was actually run is the full one**, which is the correction run 01 owed: its C1 finding
was that `./pw quality-gate` plus targeted `pytest` had been substituted for `./pw verify`, so
`test-compile` never ran and CI rejected the branch. This run ran `./pw verify` **four times** — after
the B6 conversion, after the B7 conversion, after the revert, and after the verification fixes.

```text
21070 passed, 14 skipped
=== verify: SUCCESS ===
```

Read from the tool output rather than the exit code: `ruff … All checks passed!`,
`mypy … Success: no issues found in 415 source files` (production), `Success: no issues found in 778
source files` (test-compile), `SPDX-header check passed`, and a pytest summary with 0 failed / 0 errors.

⭐ **The full gate earned its cost twice in this run.** The B7 conversion initially failed
`test_conftest_loader_contract.py` — a failure `quality-gate` alone cannot see, because it is a test, not
a lint. And three blank-line defects the diff introduced were invisible to the gate for the opposite
reason: the project runs ruff with **preview off**, so `E301`–`E306` never fire. They were found by
running `ruff --preview` over the changed files and diffing against `origin/main` (3 on HEAD, 0 at
baseline), and fixed.

**Stale-base re-verification (§ Step 8 condition 2).** `git rev-list --count HEAD..origin/main` = **0**
at the gate — the base is current, so no merge was needed and no throwaway-branch shape was used.
Recorded as the measurement it is; the count is re-derived immediately before arming.

**A red `verify / conclusion` on the superseded head is a cancellation, not a failure.** Pushing the
report commit `ba3e19a` superseded the in-flight run on `5679efa`, and GitHub reported that run's
`verify / conclusion` as **`failure`** at 17:38. The run's own record says otherwise: workflow run
`32281870698` has `conclusion: cancelled`, and its `Run verification` step likewise `cancelled` after
8m18s — a step that was still executing, not one that failed an assertion. It is recorded here because a
later reader browsing the PR's checks will see a red mark against an obsolete SHA and should not read it
as a defect this run left behind.

## Findings

Every finding is from the pre-PR verification round unless marked otherwise. Recorded per instance.

| # | Finding | Disposition |
|---|---|---|
| V1 | `test_python_derivation_resolver.py` docstring said the module is loaded "by explicit file path … via `spec_from_file_location`"; the body now resolves by identity | **Fixed** |
| V2 | Same shape at `test_documentation_extension.py` and `test_path_attribution.py` — both said "by explicit path" | **Fixed** (2 instances) |
| V3 | **The run's own commit message asserted a false rationale** for keeping the third B7 survivor — `register=False` clears the finding and leaves the guard's count at 90 | **Fixed**: the module is converted, B7 is 9 → 2, and the correction is stated in the commit that made it and again above. The original commit message is immutable on a pushed branch, so condition A is discharged by stating the correction here |
| V4 | Six new `sys.modules` registrations where the replaced preambles registered nothing — a real behavioural delta whose bound held but was written nowhere | **Bound recorded** — see below |
| V5 | Three blank-line defects (`E305` ×2, `E302`) introduced by the template insertion and the constant removal, invisible to the gate because ruff runs with preview off | **Fixed**; verified 3 → 0 against an `origin/main` baseline of 0 |
| V6 | D1 residue untouched against the brief's stated scope | **Not a defect** — see § D1 above. Recorded so the discrepancy is explicit rather than silent |
| V7 | `report-02.md` owed; the line delta is **positive**; an already-over-budget module grew | **This report**; figures below |
| V8 | Four pre-existing items outside this run's surface | **Recorded below with owners** |

### V4 — the one behavioural delta, characterised under B(a)

Six `load_skill_module` calls take the default `register=True`, where the `spec_from_file_location`
preambles they replace never touched `sys.modules`. The new registrations are
`extension_pm_dev_frontend_cui`, `extension_pm_dev_python_resolver`, `pm_documents_extension`,
`plugin_dev_extension`, `pm_plugin_dev_extension`, `pm_plugin_development_extension_wt`.

**It cannot change what the deliverable does**, and the proof is executed rather than argued: all six
names are distinct from each other and from every other loader-registered name tree-wide; none is
imported plainly anywhere, which the loader-contract guard asserts and which is green; and the slice was
run in default **and reverse** directory order with identical results. The seventh conversion takes
`register=False` precisely because its name is computed, so it adds no registration at all.

### V8 — outside this run's surface, with owners

| # | Finding | Owner |
|---|---|---|
| R1 | `doc/plans/test-quality/README.md` § "What the executed half left open" still says "`030`–`060` have landed" and carries no `080` row. It **restates current state** — the section exists so a follow-up can be commissioned without reading six reports — so unlike a run report it is not a record and is now false | **`120`**, or the next edit to that README |
| R2 | `plugin-script-architecture/standards/testing-standards.md:356-369` still teaches the hand-rolled `spec_from_file_location` preamble as house style, contradicting the doctor rule and `conftest`'s loaders | **`090`** — `marketplace/bundles/**` is its exclusive surface |
| R3 | `plan-marshall/skills/phase-3-outline/standards/consumer-sweep.md:109,135,150,157` names `test/pm-dev-java/manage-maven-profiles/test_profiles.py`; the real path is `.../maven-profile-management/...` | **`090`** |
| R4 | Two pre-existing duplicate loader module names inside this slice — `extension_pm_dev_java` and `extension_pm_dev_python`, each pair loading the identical file. Harmless today, but the collision guard detects only load-vs-plain-import, not load-vs-load | **`090`** (loader mechanics), recorded as a guard-coverage gap rather than a live defect |

### Stop record (§ Step 6, "When the loop stops")

* **Exit: `verifier-clear`.** Budget five; the plan sets none. **One** round ran, no extension needed.
* **The verifier's own last answer**, quoted: *"**Yes — three things remain that A or B forbids leaving
  open**"* — A violated by V1/V2 (false mechanism docstrings) and by V3's rationale, B violated by V3's
  mis-characterised survivor and mildly by V4's unrecorded bound. **All five are now fixed or recorded**,
  which is what A requires: A is discharged by the repair, not by another round of verification.
* **The evidence is stronger than a read.** The round simulated the loader-collision walker on the exact
  candidate call shape (`counted_unresolved` False with `register=False`, True without), ran the doctor
  on a converted copy against an unconverted control (`1` → `0`), dumped `vars(parse_ns(...))` for all
  14 templates and compared every overlaid key per site, resolved handler pairing through the parser's
  own `func` binding, and ran the slice in both directory orders — each returning a verdict that could
  have come back otherwise.
* **Were the findings narrower?** Only one round ran, so no trend is claimed. Its composition is worth
  stating: of eight findings, **one was a false rationale in the run's own commit message**, three were
  false statements in prose the run had just written, and none was a weakened assertion or a lost test.
* **Residue to assume remains.** Read the deliverables as still carrying defects of the kind this round
  found — **prose describing a mechanism the code no longer has, and rationales asserted rather than
  executed**. A second round would most profitably re-read every sentence this run wrote about *why*.
* **No survivors.** Nothing is left open under B; V4 is characterised under (a) above.

## Reviewer participation

**The expected population is derived from configuration, not transcribed**: the `author_login` of every
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc —
`coderabbit.md` → `coderabbitai`, `pr-agent.md` → `cuioss-review-bot`, `sourcery.md` → `sourcery-ai`.
**M = 3.** Every verdict is derived from the reviewer's own stored comment body across all three surfaces
(`get_comments`, `get_reviews`, `get_review_comments`), never from a check-run state — which matters
here, since `Sourcery review` reports `skipped` as a check while the reviewer published a refusal as a
review.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `cuioss-review-bot` | `reviewed` | — | Issue comment: *"PR Reviewer Guide 🔍 — PR contains tests / No security concerns identified / No major issues detected."* A review artifact against this diff, with no actionable finding |
| `coderabbitai` | `rate-limited` | **yes** | Issue comment: *"Review limit reached … Next review available in: **41 minutes** … You've used the included review currently available."* A clock condition stated with its clearing time — **not** a property of this diff; it listed all 14 files as selected for processing before refusing. Re-issued automatically on the report-commit push and read again at 17:37: **33 minutes**. The countdown drains |
| `sourcery-ai` | `rate-limited` | **yes** | Review body: *"you have reached your **weekly** rate limit of 500000 diff characters."* A quota that resets, not a per-diff ceiling |

**Coverage: 1 of 3.** No verdict is `unreadable` — all three surfaces read cleanly, returning 2 issue
comments, 1 review summary, and **0** inline review threads (`totalCount: 0`). Merge-gate condition 3 is
therefore **established**: every comment that exists has been read and dispositioned, and neither refusal
is actionable.

**No `silent` verdict arose, so no recovery check was needed.** Both shortfalls are explicit refusals
published as comments, not absences.

⭐ **Both shortfalls are `yes` here — and in run 01 on the same PR pair, both were `no`.** That inversion
is the case the lane's `Reopens?` column exists to make visible. Run 01's refusals were size ceilings
(*"112 files, which is 12 over the limit of 100"*; *"larger than the review limit of 150000 diff
characters"*) that this 14-file diff does not trip at all. `sourcery-ai` in particular refused under
**both kinds across the two runs**, which is exactly why the skill says to take the value from the notice
body and never infer it from the reviewer's identity.

### Why `coderabbitai` was not re-requested, despite `Reopens? yes`

**Not because the window was judged unreliable — it demonstrably drains.** The notice was observed twice
on this PR: **41 minutes** at 17:29 on head `5679efa`, and, re-issued automatically when the report
commit `ba3e19a` was pushed, **33 minutes** at 17:37. Eight minutes of clock, eight minutes off the
countdown. On this PR the window behaves exactly as it reads.

⚠️ **An earlier draft of this section claimed the opposite, and the claim did not survive its own
evidence.** It reasoned from a concurrent session on PR #1305 — a notice at 16:10 saying *"57 minutes"*
and a retry at **17:16**, 66 minutes later, refused with a **new 53-minute** countdown — and concluded
that a retry *consumes an attempt and pushes the window out*. That is **one** explanation. A simpler one
fits the same two data points without any special mechanism: the allowance is per-developer over a
rolling 7 days (the notice says so), reviews landed on other PRs in that hour, and they spent it. The
41→33 observation above is inconsistent with the retry-penalty story in the form it was asserted, since a
refused attempt here cost nothing. **The claim is withdrawn rather than repaired** — it is exactly the
defect this run's § What have we learned is about, and it would be absurd to commit a fresh instance of
it in the same report.

**What the evidence does support** is the part that decides the action: the allowance is **one
per-developer pool shared across every PR in the organisation**, so a review spent here is a review not
available elsewhere. Two facts then settle it:

1. **PR #1305 explicitly requires a CodeRabbit review** — its operator made that a condition, and it does
   not merge without one. Its own retry window and this one are the same window.
2. **This PR requires no such thing.** The operator's standing decision from run 01 — **land at 1-of-3
   with the shortfall disclosed** — was taken for exactly this shape of gap, and this diff is 14 files of
   mechanical test conversion, not the 112-file diff that decision was originally made against.

So the slot is left to the PR that needs it. This also fixes the arming order: **pushing any commit
re-triggers CodeRabbit automatically** (the `ba3e19a` push did, with a new Run ID), so landing this PR
before the window clears is what *keeps* the slot for #1305, rather than spending it on an
auto-triggered review nobody asked for.

⛔ **Stated as the scheduling judgement it is, not as a claim that the review was unobtainable.** Waiting
roughly half an hour would in all likelihood have produced a CodeRabbit review of this diff. It was not
waited for, and the coverage figure below reflects that choice rather than an impossibility.

**What stands in for the missing coverage, stated so the gap is not papered over.** The verification
round's evidence was **executable rather than a re-read** — it simulated the collision walker on the
exact call shape, ran the doctor on a converted copy against an unconverted control (`1` → `0`), dumped
`vars(parse_ns(...))` for all 14 templates and compared every overlaid key per site, and ran the slice in
both directory orders. The full `./pw verify` ran four times. And the round's most valuable finding was
that **this run's own rationale was false** — a defect no lint and no CI check would have surfaced.
**None of that is a substitute for a second reader**, and the residue below should be read with 1-of-3
coverage in mind.

## Cost

* **Tokens:** not available to the agent in this session.
* **Wall-clock:** not separately instrumented; four full `./pw verify` runs (~6–7 min each) dominate.
* **Population:** this single Claude Code cloud session. ⛔ **Not comparable** to a plan-marshall
  `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a per-task billing
  boundary this session does not share.

## Measured deltas (D5, for this run)

| Measure | Before (`origin/main`) | After | Delta |
|---|---:|---:|---:|
| Slice lines | 61,818 | 61,892 | **+74** |
| Collected tests (slice) | 3,357 | 3,357 | **0** |
| Hand-built `argparse.Namespace` | 27 | **0** | −27 |
| `parse_ns` template calls | 25 | **39** | +14 |
| `test-module-preamble-boilerplate` | 9 | **2** | −7 |
| `test-module-line-budget` (slice) | 43 | 43 | 0 |

⚠️ **The line delta is POSITIVE, and that is expected rather than a failure.** A B6 conversion is
line-positive by construction — it replaces a one-line hand-built namespace with a module-scope template
plus an overlay call — and plan `100` independently records the same property for its own cluster
("line-neutral to slightly positive"). The epic's § "Why there is no line floor" governs: the delta is
**reported, not targeted**, and no assertion, rationale or comment was deleted to move it.

**One already-over-budget module grew**: `test/pm-dev-java/maven-profile-management/test_profiles.py`,
**537 → 563** lines (+26), the largest single growth in the diff. **No module newly crossed the 400-line
budget** — the slice's over-budget count is unchanged at 43 (42 this plan's, 1 plan `010`'s). Splitting
it is plan `100`'s row 6, whose stated prerequisite (`080` landed) is now met.

**Coverage (Verification condition 2) was NOT measured this run**, and is stated as unmeasured rather
than assumed: the diff changes no production code and no test count (3,357 both sides), so coverage
cannot fall, but that is an argument, not a measurement.

## Contract check (Step 9)

**GitHub access path:** the GitHub MCP server (`mcp__github__*`). No `gh` CLI is present in this session.
**Branch form:** **run-created** — `chore/plugin-dev-generator-tests-run-02`, for the reason recorded in
§ Skills loaded: the session's harness-assigned `claude/plugin-dev-generator-tests-v0zvzg` was consumed
by run 01 and locked at enqueue, so it could not carry a second run's commits. ⚠️ **This is a deviation
from the harness rule that a cloud session keeps its assigned branch**, and it is recorded as one rather
than presented as the norm. The risk that rule protects against — work stranded on a branch no remote
carries, which a VM reclaim then destroys — **does not apply here**: the branch was pushed on creation
and after every one of its three commits, so `origin` holds the run's complete history at all times.
**Arrival:** re-entry run; the branch was cut from `origin/main` at `34e7b99` and pushed before any edit.
A cloud run **never owes** a `/sync-plugin-cache`; none is recorded as owed, and this run touched no
`marketplace/bundles/` file at all.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done** | § Skills loaded, with the route used and the one domain skill the surface reaches |
| 2 Branch | **Done, with a recorded deviation** | On `origin` before the first edit and after every commit; form and reason above |
| 3 Plan directory | **Done** | `doc/plans/test-quality/080-…/plan.md` exists and opens with the first-instruction block; re-entry adds `report-02.md` beside `report-01.md` rather than moving anything |
| 4 Implement | **Done** | 3 commits (`fb326db`, `802730b`, `5679efa`), every one carrying the trailer and no "Generated with" footer; D3's two open halves addressed |
| 4 Per-commit gate | **Done** | Both `*.py`-touching commits were preceded by a **full** `./pw verify`, quoted in their own messages (`21070 passed, 14 skipped, SUCCESS`). The report commit touches no source |
| 4 Pushed | **Done** | Pushed after every commit; no unpushed commit remains |
| 5 Build gate | **Done** | § Build gate. The full `./pw verify` ran four times, not the `quality-gate` substitute that was run 01's C1 defect. It caught a test failure and, with `--preview` added, three blank-line defects |
| 6 Verification sub-agent | **Done** | One round, exit `verifier-clear`, budget 5 with no extension needed. Findings V1–V8 with dispositions; the verifier's last answer quoted; evidence executable rather than a re-read; residue-to-assume stated; no survivors, and the one behavioural delta characterised under B(a) |
| 7 PR cycle | **Done** | PR **#1306**. Every comment on the PR is dispositioned in § Reviewer participation; the table carries a verdict **and** a `Reopens?` value per reviewer |
| 8 Merge gate | **Done** | Condition 1 required contexts green (`verify / conclusion`, `verify / gate`, `review / review`, `dependency-review`); condition 2 stale base re-checked immediately before arming (§ Build gate); condition 3 established in § Reviewer participation — 0 open comments; condition 4 this report finalized and committed as the **last** pre-merge commit. The **1-of-3** coverage shortfall was disclosed to the operator in words, with each reviewer's `Reopens?` value, before arming |
| 8 Bridge | **Done** | `git diff --name-only origin/main...HEAD -- doc/` returns exactly one path, this plan's `report-02.md`. No status or bookkeeping write landed elsewhere under `doc/plans/` |
| 9 This check | **Done** | This table |
| 9 What have we learned | **Done** | Below |

**Re-verified at report time, per § Step 9.** *Tree* claims: the plan directory holds exactly `plan.md`,
`report-01.md` and `report-02.md`; `.plan/` was never written by this run and no `.plan/` path appears in
the diff. *History* claims: **this run performed no rebase**, so every SHA quoted here is reachable from
the branch under review, each re-derived from `git log` at the moment of writing.

## What have we learned (Step 9)

**The run's own worst defect was an argument standing in for an experiment, and it survived self-review
because it looked like caution.** Commit `fb326db` recorded `test_extension_profiles.py` as unconvertible
and kept its B7 finding, reasoning from two true premises: routing it through `load_skill_module` pushed
the loader-collision guard to 91 unresolved call sites against a bound of 90, and that guard's own
comment says the bound *"may not grow (that widens what the guard cannot see)"*. The conclusion was
false — the walker skips any call that opts out of registration, and the rule's own message names the
escape verbatim. One `register=False` converts the module and leaves the count at exactly 90.

⭐ **The direction of that error is the lesson.** It was *conservative*: it kept a finding rather than
removed one, preserved a guard rather than weakened it, and shrank the run's own claimed result from 9→2
to 9→3. Nothing about it triggered the suspicion a self-serving claim would. It was caught only because
the verifier **ran the walker on the exact call shape** instead of re-reading the reasoning.

**One contract change is proposed, on that evidence.** § Step 4 and the Report's § Residue both let a run
record an item as **unreachable** — a stronger claim than *deferred*, since it asserts the item can never
be done rather than that this run did not do it — and neither asks the run to demonstrate it. The
proposed clause, in § Report under Residue:

> An item recorded as **unreachable** (as opposed to deferred) must carry the **executed** evidence of
> its unreachability — the command run and what it returned — not the reasoning that predicts it. Where
> execution is genuinely impossible, name the structural fact that makes it so and say how *that fact*
> was checked. A deferred item needs no such evidence: it claims only that this run stopped, which its
> own scope statement already establishes.

This run passes the proposed clause on its remaining two B7 survivors, which is why it is worth
proposing rather than merely confessing: `test_dist_manifest.py` and `test_spdx_enforcement.py` load
`marketplace/targets/generate.py` and the repository-root `build.py`, and the structural fact — neither
path lives under `marketplace/bundles`, which is the only tree `load_skill_module` can address — was
checked **by resolving the paths**, not by predicting them.

⛔ **Deliberately not proposed: extending this to deferred items.** Requiring executed proof for every
item a run chooses not to do would tax honest scope statements — the six `test_analyze_*.py` modules are
*deferred and characterised*, not claimed impossible, and demanding an experiment per module would buy
nothing. The clause is scoped to the strong claim precisely because only the strong claim can be wrong
in the way this run's was.

⛔ **Also not proposed, though adjacent: a rule against reasoning from a comment.** The premise that
misled this run came from a code comment that was itself accurate. The defect was not trusting the
comment; it was never testing whether the comment's rule *bound this case*. A prohibition on reading
comments would be the wrong lesson from a run that read one correctly and applied it wrongly.

**Presented to the operator rather than self-approved**, per § Step 9, and **not shipped in this PR**:
the lane requires a contract amendment to be its own `chore/` branch with its own review audience, and
this run does not self-approve a change to the contract that governs it. It joins run 01's § Step 6
dispatch-checklist proposal, which is still unshipped.

## Residue

**Closed by this run:** B6 entirely (0 remaining); B7 down to its structural floor.

**Genuinely unreachable, not budget:** the 2 remaining preamble findings —
`marketplace/targets/generate.py` and the repository-root `build.py` are outside `marketplace/bundles`,
so the skill-root loader cannot address them. A future fix would need a new conftest accessor, which is
`090`'s surface.

**Left by design:** the 6 unconverted `test_analyze_*.py` modules (each characterised in `report-01.md`
§ D1); the 42 over-budget modules (**plan `100` row 6**, now unblocked).

**Handed on:** R1–R4 above.
