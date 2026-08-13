# Run report — 440-the-merge-currency-treadmill (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/merge-currency-treadmill-ecq37n` (harness-assigned)    **PR:** _pending_    **Outcome:** _pending_

## Skills loaded

Loaded by reading the bundle source path directly — the `plan-marshall` plugin is not installed in
this cloud session, so `Skill: {bundle}:{skill}` notation would not resolve.

| Skill | Why |
|---|---|
| `plan-marshall:cloud-plan-lane` (project-local `.claude/skills/`) | The working contract, loaded as the run's first action |
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `plan-marshall:ref-workflow-architecture` | The plan's surface is the finalize dispatch pipeline |
| `plan-marshall:persona-implementer` | Production code |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |
| `pm-plugin-development:plugin-architecture` | `SKILL.md` / bundle structure |

Every skill named above resolved by path. None was unobtainable.

## Deliverables

### D0 — GATE: enumerate what re-stales, and what each re-stale costs — **DONE**

Commit `032e3e7`. The enumeration is published as
`phase-6-finalize/standards/verdict-currency.md`, which owns the model: the HEAD-advance trigger set
(derived from declared frontmatter facts, not hand-listed), what one re-fire costs per step, the
classification rule, the D2 ruling, and how the count is obtained.

**The trigger set — what advances HEAD inside finalize.** Derived from frontmatter, so a step added
later is covered by its own declaration:

| Trigger | Declared by |
|---|---|
| A settle-band step's edits being committed by the dispatcher's item-5f instrumentation | `mutates_source: true`, `order < 11` |
| A post-push pre-merge step's edits being committed (plus the item-5f post-PR re-push) | `mutates_source: true`, `11 < order < 70` |
| A rebase replaying commits | `advances_main_via_rebase: true` |
| A loop-back fix commit | the unified wait-region triage opening a fix task |

**The head-dependent population as it stands** (read from `head_dependent: true` frontmatter — a
verification-time snapshot of a derived set, not a hand-maintained list):
`project:finalize-step-lessons-housekeeping` (4), `default:pre-push-quality-gate` (5),
`project:finalize-step-plugin-doctor` (6), `default:pre-submission-self-review` (7),
`default:finalize-step-simplify` (8), `default:finalize-step-security-audit` (9),
`project:finalize-step-era-stamp-fill` (21), `default:ci-verify` (22),
`plan-marshall:automatic-review` (30), `default:sonar-roundtrip` (40),
`project:finalize-step-review-retrospective` (990).

**Why the observed 5× / 7× / 7× falls where it does.** The three steps the plan names —
housekeeping, structural lint, self-review — are the three EARLIEST head-dependent steps in the
pipeline (`order` 4, 6, 7). Every trigger above them re-stales them; a step at `order: 40` is
re-staled only by what follows it. The re-fire distribution is a function of position, and the
plan's reported counts are consistent with that ordering.

**What a re-fire costs.** The whole step body, not a delta of it — the re-entry check re-dispatches
as a fresh run. Two properties make it worse than it looks: a dispatched step pays a full envelope
per re-fire (target resolution, agent spawn, skill loads) that delta-scoping cannot shrink; and
`pre-push-quality-gate`'s whole-tree `quality-gate`, whole-tree `test-compile`, and module-tests
arms are unconditional by design, so they are paid in full every time and are not delta-scopable at
all. That is why not-re-running is the only lever available on the most expensive gate.

### D1 — Distinguish an invalidating HEAD advance from a non-invalidating one — **DONE**

Commit `032e3e7`.

- New frontmatter fact `verdict_inputs` on `ext-point-finalize-step` — the fnmatch globs naming the
  tracked paths whose content a step's verdict reads. **Absence is the fail-closed default**, so a
  step declaring nothing keeps the pre-existing unconditional re-fire and adoption is opt-in.
- New seam `phase-6-finalize/scripts/verdict_currency.py` — `classify` returns `preserved` when the
  **tree difference** between the recorded SHA and the live HEAD touches none of the declared paths,
  and `invalidated` otherwise.
- Wired into the dispatcher at the one branch where the SHAs already differ
  (`phase-6-finalize/SKILL.md` § "Special case — HEAD-dependent steps" table and the item-1
  pseudocode).
- **Declared on ONE step — `project:finalize-step-plugin-doctor`.** The first attempt also declared
  `default:pre-push-quality-gate`; the verification round refuted that surface and it was withdrawn.
  See § Findings F1 for the evidence and § D1 addendum below.

**The fail-toward-re-running direction is structural, not advisory.** `preserved` is reachable only
past a resolution gate — the step doc resolved AND the step declares `head_dependent: true` — and past
that gate on exactly two paths, each of which *proves* the recorded tree is still in force: the SHAs
are equal (byte-identical trees, decided without consulting any declaration), or a non-empty
declaration's globs match no path in the tree difference. Every other path returns `invalidated` with
a `reason` naming the uncertainty: absent declaration on a genuinely advanced HEAD, unresolvable step
doc, unavailable discovery machinery, absent recorded SHA, unresolvable live HEAD, or a tree diff git
could not compute. Each branch is pinned by its own test, individually — an aggregate "it usually
re-fires" assertion could pass while one branch leaked a skip.

**D1 addendum — the lever is engaged on one step, and the second withdrawal is the more interesting
result.** `pre-push-quality-gate` looked like the biggest prize: it is the most expensive
head-dependent gate and it is inline, so its cost is invisible to the dispatch-boundary ledger. Its
declared surface did not survive scrutiny. Its module-tests arm executes this repository's own pytest
suite, and that suite asserts over the *real* tree — retired-token sweeps over `doc/**`, an `.adoc`
governed-population contract that also reads root `CLAUDE.md`, and branch-prefix / merge-trigger
contracts asserted against the live `.github/workflows/python-verify.yml`; its whole-tree
`quality-gate` arm additionally runs plugin-doctor's build-failing agentfile analyzers over the
repository root. So no proper subset of the tree is a sound surface for it, and a declaration naming
the whole tree would be an inert lever wearing the shape of a real one. The refusal is recorded with
its evidence at `pre-push-quality-gate.md` § "Verdict-input surface — deliberately undeclared", and
the ext-point now states the superset bar and names both shapes that must not declare. That is the
honest outcome: **the mechanism is sound and general; its current reach is one step, not two.**

**A tree diff, not a commit walk.** `git diff --name-only {recorded} {live}` compares two trees, so
one call is correct under all three supersession mechanisms (loop-back commit, force-push, rebase)
with no per-mechanism detector. It is also strictly narrower: a change and its revert cancel out.

**A preserved skip never re-stamps `head_at_completion`.** The record keeps the SHA the verdict was
genuinely computed against — re-stamping would make it claim a currency it does not have, which is
the false-green signal this mechanism exists to remove. It also keeps the decision monotone: the
diff range only grows.

**Remote-state verdicts declare nothing.** `ci-verify`, `automatic-review`, and `sonar-roundtrip`
record verdicts about the *pushed* HEAD, so any advance that reaches the remote re-stales them
regardless of which paths moved. They are deliberately left undeclared.

Tests: `test/plan-marshall/phase-6-finalize/test_verdict_currency.py` (30 tests) — the pure
classifier, the glob convention, each fail-closed branch independently, `resolve_changed_paths`
against a real temporary git repository (including revert-cancellation and the unresolvable-SHA
case), and a declaration-conformance guard over the derived implementor population.

### D2 — Settle the unconditional pre-merge rebase — **DONE (ruling recorded and implemented)**

Commit `032e3e7`. **The ruling: its necessity is a function of `use_merge_queue`, and the operator's
deviation was correct on the path it was taken on.**

- **`use_merge_queue == true`** — the rebase and its force-push are **skipped**, with a decision-log
  line recording the skip. The queue rebases and re-tests the branch against the latest base as its
  own authoritative gate and refuses a still-red result — which `branch-cleanup.md` already relied on
  when it downgraded the pre-merge CI wait to a non-authoritative snapshot on this same path. A
  rebase here duplicates that at full price: a replaying rebase rewrites every SHA on the branch and
  re-stales every head-dependent verdict at once, the pipeline's largest single re-stale event.
- **`use_merge_queue == false`** (default) — the rebase stays **unconditional**. The immediate
  `pr safe-merge` path has no queue re-test, so the rebase plus the authoritative CI wait after it
  ARE what make the merged history linear and verified. Nothing else discharges those purposes here.

So the record is not "the rebase was always unnecessary" and not "the deviation was unsafe" — those
were the two readings the plan said the record could not have both of. Sites:
`phase-6-finalize/standards/branch-cleanup.md` § "Rebase Branch onto Base" (mechanics) and
`standards/verdict-currency.md` § "Ruling" (the ruling).

**Collateral tightening, disclosed:** the trigger-A re-review section immediately downstream assumed
"a rebase + force-push happened above". It now fires only when HEAD **actually advanced** (the rebase
ran AND returned `action: rebased`), and fails toward re-reviewing when that return is unavailable or
ambiguous. This narrows *when* the re-review fires and never *what it checks*; its own precondition
is an advanced HEAD, which an unadvanced HEAD does not satisfy.

### D3 — Make the re-fires visible — **DONE, and one plan claim REFUTED**

Commit `032e3e7`. New read-only verb `manage-execution-manifest refire-report --plan-id X
[--phase 6-finalize]`, reporting per step `firings`, `refires` (`max(0, firings - 1)`), `skipped`,
`errors`, and the summed token-attribution triple, worst-offender first.

**It consumes the existing emitters rather than duplicating them**, as the plan required: `record-step`
(item 5e) already appends one `execution_log[]` row per firing, and the sibling instrumentation plan's
per-firing `[DISPATCH]` emission (#1200, `1da26b1`, confirmed an ancestor of this branch) already
covers the dispatch side. No new emitter was added.

Two coverage boundaries the payload **names rather than hides**: a `skipped` row is never folded into
`firings` (a skip is precisely what a preserved verdict produces, so folding it in would blind the
instrument to the thing it measures), and `total_tokens` is a **floor** — `record-step` receives the
`<usage>` triple only for dispatched steps and inline steps record zeros by contract — with a
`token_population` field stating which rows the figure was summed over.

Tests: `test/plan-marshall/manage-execution-manifest/test_refire_report.py` (14 tests).

### D4 — A before/after measurement on a real finalize — **NOT DONE**

**Not performable in this lane, and reported as not done rather than narrated as complete.** A
before/after measurement requires running a real plan-marshall finalize twice. This lane executes in a
Claude Code cloud session that clones the repository fresh: `.plan/` is git-ignored, so there is no
plan state, no execution manifest, no generated executor, and no plan-marshall runtime of any kind
here. There is no finalize to measure, before or after.

What this run delivered toward it, and what remains owed:

- **Delivered:** the instrument (D3's `refire-report`) that makes the per-step re-fire count
  obtainable, and the denominator definition the measurement must publish — `refires` per step,
  against the `token_population` the payload names.
- **Owed:** the measurement itself, taken on a local plan-marshall run — one finalize on `origin/main`
  as the *before*, one on this change as the *after*, both reporting `refire-report --phase 6-finalize`
  and the billing-weighted cost with its population.

**The known downward bias, stated plainly rather than reported as a clean number.** The plan's
Verification section requires this disclosure if the sibling instrumentation has not landed. It HAS
landed (#1200 is an ancestor), so the dispatch side is per-firing. The residual bias is different and
still real: the dispatch-boundary ledger fires only for steps dispatched as Task agents (item 5c gates
on the same condition as 5b), so **every inline step's cost is absent from it by design** —
`pre-push-quality-gate`, `ci-verify`, and `era-stamp-fill` are inline AND head-dependent, so the
single most expensive re-firing gate contributes zero tokens to any ledger-derived finalize figure.
Any cost figure taken from that ledger is therefore a floor, and this report does not quote one.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` — **non-empty** (two production files, two test
files), so the full path was taken. Working tree confirmed clean before the diff was read.

`./pw verify` (run with `UV_HTTP_TIMEOUT=600`) — **clean, read from the tool output, not the exit
code**:

- `mypy --no-incremental marketplace/bundles .claude` — `Success: no issues found in 398 source files`
- `ruff check marketplace/bundles test .claude` — `All checks passed!`
- `SPDX-header check passed`
- plugin-doctor marketplace-wide static analysis — `status: pass`, `total_issues: 0`, 36 rules run
- `mypy test` (test-compile) — `Success: no issues found in 733 source files`
- `pytest test` — `19612 passed, 14 skipped in 377.63s`
- `coverage: COMPLETE — checked over full scope`
- `=== verify: SUCCESS ===`

The first `verify` attempt failed `test-compile` on one unused `type: ignore` in the new test file
(`Found 1 error in 1 file`). Fixed in `2ebc266` and re-run to the clean result above. Worth recording:
that error was caught by the whole-tree `test-compile` arm — the exact gap that arm exists to close,
and an arm this change deliberately keeps inside `pre-push-quality-gate`'s declared verdict surface.

No `uv.lock` churn appeared; `git status` was checked before each commit and deliverable paths were
staged explicitly.

## Findings

### From the claim-label re-derivation (the plan's own table, re-derived first-party)

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | The delta-scoping change is an ancestor of both observed runs | **CONFIRMED, with a stated limit** | `94bcddf` (#1189, "self-review surfacing integrity", which introduced the `--since-ref` delta anchor in `pre-submission-self-review.md`) landed 2026-08-12 19:23:10 UTC and `git merge-base --is-ancestor 94bcddf HEAD` succeeds; 26 commits have landed on `main` since. So it is an ancestor of every landing after that instant. **The limit:** the two specific runs cannot be identified from this clone — run records live under git-ignored `.plan/`, and the plan forbids going there — so "both observed runs" is confirmed only insofar as they post-date that instant, which the plan asserts and this clone cannot contradict. |
| 2 | A single finalize re-ran three steps 5× / 7× / 7× | **NOT RE-DERIVED** | The counts live in run reports under `.plan/`. Not re-derived, so no target in this change is pinned to them. What IS first-party: the three named steps are the three earliest head-dependent steps by `order` (4, 6, 7), which is exactly where the highest re-fire counts must fall. |
| 3 | Landing costs of 109M / 134.4M billing-weighted, finalize at 70% | **NOT RE-DERIVED, and not quoted** | Same `.plan/` provenance; one figure is self-labelled a FLOOR. Neither is used as a measured total anywhere in this change. |
| 4 | An unconditional pre-merge rebase re-stales every recorded verdict | **PARTIALLY REFUTED — true only of a replaying rebase** | `git-workflow.py::cmd_worktree_rebase_to` reads HEAD immediately before and after the rebase and returns `action: noop` with HEAD **unchanged** when the branch already contained the base; the `state == 'clean'` arm returns `noop` without running a rebase at all. So the call is unconditional but the re-stale is not — it happens on `action: rebased` only. Recorded in `verdict-currency.md` so the discriminator (the step's own returned `action`, evidenced by `pre_sha`/`post_sha`) is written down rather than assumed. |
| 5 | The re-fires emit no step bracket, so neither ledger counts them | **REFUTED as stated; a narrower true claim survives** | Item 2 emits `[STEP] Executing step:` and item 7 emits `[STEP] Completed step:` on **every** firing — only a SKIP is exempt. Item 5e's `record-step` appends an `execution_log[]` row per firing for **every** step, dispatched and inline. So re-fires ARE recorded and the count IS derivable (`firings - 1`). What survives: **no ledger marks a firing AS a re-fire** — every row looks like a first firing, so the count had to be derived by counting duplicate rows and no verb exposed it (D3 now does); and the **dispatch-boundary** ledger genuinely omits inline steps by design (item 5c gates on the dispatched condition), so a cost figure taken from THAT ledger does understate finalize — but that is an inline-vs-dispatched gap, not a re-fire gap. |
| 6 | A HEAD advance can be classified invalidating-or-not with acceptable accuracy | **CONFIRMED for the declared shape, by construction** | Not by estimation: a step's verdict is a function of its declared inputs' content, so byte-identical content on that surface recomputes the same verdict. Confirmed against the two steps that declare one — each glob traced to a named arm or read in the step's own doc. Steps whose surface could not be substantiated are left undeclared and unchanged. |
| 7 | Any re-fire ever produced a DIFFERENT verdict from its predecessor | **NOT ESTABLISHED, and the design does not depend on it** | Deliberately unaddressed: the classification never asks whether re-fires *usually* agree. It skips only where a differing verdict is impossible (unchanged inputs), so the "mostly" exceptions the plan warns about are preserved by construction — an advance touching the surface always re-fires. |

### From the build gate

| # | Source | Description | Disposition |
|---|---|---|---|
| 8 | `./pw test-compile` | Unused `type: ignore[arg-type]` in `test_refire_report.py:222` | **Fixed** in `2ebc266` |

### From the verification sub-agent (round 1)

One finding per instance, never bundled. All were accepted; none was rejected. Every fix landed in
`176cee2`, after which the sub-agent was re-dispatched — a verification pass that found a defect has
not finished.

| # | Finding | Disposition |
|---|---|---|
| F1 | `pre-push-quality-gate`'s `verdict_inputs` missed `CLAUDE.md` / `AGENTS.md`, which its whole-tree arm's plugin-doctor agentfile analyzers lint from the repository root — a build-failing rule the gate would have skipped | **Fixed** — declaration withdrawn entirely (see the D1 addendum) |
| F2 | The same surface missed `doc/**`, which its pytest arm reads: three real test modules assert over the live `doc/` tree, so a `doc/`-only commit can turn the gate red | **Fixed** — same withdrawal; this is the finding that made the withdrawal the right answer rather than a wider glob list |
| F3 | The same surface missed `.github/**` (two test modules assert against the live workflow file) and `uv.lock` (pins every arm's tool versions) | **Fixed** — same withdrawal |
| F4 | `preserved` was claimed reachable on "exactly ONE path" in four places while the code had two (the equal-SHA short-circuit) | **Fixed** — all four sites corrected; the equal-SHA check also moved BEFORE the declaration check, so an undeclared step whose HEAD never moved no longer answers `invalidated` against the dispatcher's own steady-state row |
| F5 | `resolve_verdict_inputs` called `_read_frontmatter_fields` outside any `try`; its call-time import could escape as a traceback, breaking the documented always-exit-0 contract | **Fixed** — guarded, returning `discovery_unavailable` |
| F6 | Every `classify_step` test patched `resolve_verdict_inputs`, so the real discovery + `canonicalize_step_key` bridge had no coverage | **Fixed** — three tests now drive the unpatched seam against the live population |
| F7 | The new `## Verdict-input surface` H2 split `## Mark Step Complete`'s Branch A from Branch B, leaving an execution branch under an unrelated heading | **Fixed** — section moved above `## Mark Step Complete` |
| F8 | Branch F is reached only on `use_merge_queue == true` — the path that now never rebases — yet mandated `--fact action=` and `--fact upstream_commit_count=`, which have no value there | **Fixed** — both facts dropped from Branch F and bracketed as conditional on Branch A and Branch E |
| F9 | Branch A's rebase-clause table had no row for a skipped rebase, and its stated 71-char worst case assumed a now-unreachable clause pairing | **Fixed** — clause added; worst case re-derived to 70 by measuring, with the `use_merge_queue` coupling that makes the 71 pairing unreachable recorded |
| F10 | The amended trigger-A paragraph opened with the advanced-HEAD condition and still closed with "load and execute it here when `state == open`" | **Fixed** — the paragraph was split and the entry condition stated once |
| F11 | `branch-cleanup-rereview.md` was untouched and still asserted "a rebase + force-push happened above", including a sentence directly negating the new skip | **Fixed** — the sub-standard now defers its entry condition to its caller instead of restating one |
| F12 | The operator merge prompt asserted "CI passed on the rebased branch" on a path where neither the rebase nor an authoritative CI wait happened | **Fixed** — prompt wording routed by `use_merge_queue`, with an explicit pre-merge-rebase line |
| F13 | The merge-mutex section, its heading, its acquire rationale, and invariant 1's re-rebase clause all justified themselves by a force-push the queue path no longer performs | **Fixed** — rationale restated as "the first staleness-creating operation", which the routing then names per path |
| F14 | The pre-rebase confirmation gate still asked the operator to authorize a rebase and force-push that would not run | **Fixed** — action list and question routed by `use_merge_queue` |
| F15 | The new `use_merge_queue` consumption site carried no `**Observability (mandatory)**` block, and `test_every_use_merge_queue_consumption_site_is_observable` reported green because its derivation regex could not see the site's phrasing | **Fixed** — the site adopted the canonical `read \`use_merge_queue\` off` phrasing so the guard counts it, and carries the mandatory block. Fixed by making the site conform, not by loosening the guard |
| F16 | Two section references introduced by the change pointed at headings that do not exist (`§ "CI wait"`, `§ "Rebase onto base"`) | **Fixed** |
| F17 | `phase-5-execute/standards/sync-with-main.md` still cross-referenced the rebase as "unconditional" | **Fixed** |
| F18 | `doc/user/parallelism-and-locking.adoc` did not record that `use_merge_queue` now also skips the pre-merge rebase and force-push — a user-visible behaviour change | **Fixed** |
| F19 | `refires` was attributed wholly to the HEAD-advance re-entry check, though `loop_back`, a retry after `failed`, and the `push` barrier's parity re-fire also produce extra `executed` rows | **Fixed** — corrected in both the SKILL.md and the script docstring; the column now states it counts extra firings, not re-stales |
| F20 | The `skipped` column's stated purpose was unverifiable from the pseudocode — whether a preserved SKIP reaches item 5e was not resolvable | **Fixed** — item 1 now states the obligation explicitly at the SKIP branches; without that row the saving would appear only as an absence |
| F21 | `refire-report` was absent from both the § Scripts table and § Canonical invocations in its own SKILL.md | **Fixed** |

### From the verification sub-agent (round 2)

_Pending — recorded at Step 8 condition 3._

### From CI and PR review

_Pending — recorded at Step 8 condition 3._

## Reviewer participation

_Pending — recorded at Step 8 condition 3, derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc._

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no usage counter to
  the running agent, so no figure is reported rather than an estimated one.
- **Wall-clock:** first commit `1a59f09` at 2026-08-13 19:04:06 UTC; measured to the last pre-merge
  commit. Source: git committer timestamps on this branch.
- **Population:** these figures cover this single Claude Code cloud session. ⛔ **NOT comparable to a
  plan-marshall `metrics.toon` total**, which counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary — a boundary an interactive cloud session does not
  share. No conversion is offered, because none would be sound.

## Contract check (Step 9)

_Pending — recorded at Step 8 condition 3._

## What have we learned (Step 9)

_Pending — recorded at Step 8 condition 3._

## Residue

- **D4's measurement is owed** and is the plan's only unmet deliverable — see D4 above for the exact
  before/after procedure and the instrument to take it with. It needs a local plan-marshall run; it
  cannot be taken in this lane.
- **Ten of the eleven head-dependent steps declare no `verdict_inputs` surface** and therefore keep
  the unconditional re-fire. Three are remote-state verdicts and correctly stay that way. One —
  `pre-push-quality-gate` — is a **recorded refusal on evidence**, not an unwritten obligation: no
  proper subset of the tree is sound for it (§ D1 addendum). The remaining six —
  `lessons-housekeeping`, `pre-submission-self-review`, `finalize-step-simplify`,
  `finalize-step-security-audit`, `era-stamp-fill`, `review-retrospective` — were left undeclared
  because this run could not substantiate their surfaces arm-by-arm from their own docs, which is the
  admissibility bar the ext-point sets. Each is a candidate for a later, evidence-led declaration, and
  `pre-submission-self-review` (7× in the observed runs) is the highest-value one.
- **Decomposing `pre-push-quality-gate` is the unblocking condition for its own declaration.** Its
  per-bundle `quality-gate` sweep has a bounded surface even though its module-tests arm does not, so
  separating the arms would make a sound declaration possible on the bounded half. That is a
  decomposition of the step rather than a declaration on it, and it is deliberately out of scope here;
  the condition is recorded in the step's own doc for whoever revisits it.
