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
- **Declared on ONE step — `project:finalize-step-era-stamp-fill`.** Two earlier candidates were
  declared and then withdrawn on evidence; see the D1 addendum.

**The fail-toward-re-running direction is structural, not advisory.** `preserved` is reachable only
past a resolution gate — the step doc resolved AND the step declares `head_dependent: true` — and past
that gate on exactly two paths, each of which *proves* the recorded tree is still in force: the SHAs
are equal (byte-identical trees, decided without consulting any declaration), or a non-empty
declaration's globs match no path in the tree difference. Every other path returns `invalidated` with
a `reason` naming the uncertainty: absent declaration on a genuinely advanced HEAD, unresolvable step
doc, unavailable discovery machinery, absent recorded SHA, unresolvable live HEAD, or a tree diff git
could not compute. Each branch is pinned by its own test, individually — an aggregate "it usually
re-fires" assertion could pass while one branch leaked a skip.

**D1 addendum — two candidate surfaces were declared and then withdrawn on evidence, and that is the
most useful finding in this deliverable.** The plan labels the premise D1 rests on as *GENUINELY
OPEN*: "A HEAD advance can be classified invalidating-or-not with acceptable accuracy." Two
independent verification rounds tested it against the actual gates, and the answer is sharper than
either "yes" or "no":

- **`default:pre-push-quality-gate` — withdrawn.** It looked like the biggest prize: the most
  expensive head-dependent gate, and inline, so its cost is invisible to the dispatch-boundary ledger.
  But its module-tests arm executes this repository's own pytest suite, and that suite asserts over
  the *real* tree — retired-token sweeps over `doc/**`, an `.adoc` governed-population contract that
  also reads root `CLAUDE.md`, and branch-prefix / merge-trigger contracts asserted against the live
  `.github/workflows/python-verify.yml`. Its whole-tree `quality-gate` arm additionally runs
  plugin-doctor's build-failing agentfile analyzers over the repository root.
- **`project:finalize-step-plugin-doctor` — withdrawn.** The near-miss, and the one that took two
  rounds to see. Its `--paths` scope really is two skill roots, which makes `marketplace/*` plus
  `.claude/*` read like the whole story. It is not: its roster's `broken-relative-link` rule resolves
  every relative link *target* against the repository root and stats it on disk, and marketplace docs
  link into `doc/**`, `test/**`, and root files in bulk. The target set cannot be captured by a static
  glob at all, because any file can become a link target.
- **`project:finalize-step-era-stamp-fill` — declared, and sound by construction.** Its verdict is a
  property of exactly two files named by full path in its own doc: that neither
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` nor
  `test/plan-marshall/audit-archived-plan-retrospectives/test_audit.py` carries an unresolved
  `PR-PENDING` sentinel. It reads nothing else to compute that, and stages exactly that pair. The
  surface is a superset by construction rather than by survey — which is precisely what the other two
  could not offer.

**The generalizable result: a gate whose body executes something open-ended over the repository has no
sound static surface, and a gate whose verdict is a property of named files has a trivially sound
one.** That is now the ext-point's admissibility bar, stated as a superset obligation with both
disqualifying shapes named and both refusals recorded in the refusing steps' own docs. The honest
bottom line for this deliverable: **the mechanism is sound, general, fail-closed, and tested; its
current reach in this repository is one step, and the two it does not reach are documented refusals
rather than unwritten obligations.**

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
and one of the arms whose unbounded reach is why `pre-push-quality-gate` ends up declaring no verdict
surface at all (§ D1 addendum).

The gate was re-run to a clean `verify: SUCCESS` after each verification round's fixes as well —
three clean whole-tree runs in total, the last at `19616 passed, 14 skipped`.

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
| 6 | A HEAD advance can be classified invalidating-or-not with acceptable accuracy | **SPLIT — confirmed for one gate shape, REFUTED for the other** | Not answerable as a single yes/no, which is why the plan was right to label it open. Where a gate's verdict is a property of *named files*, the classification is exact by construction, not estimated (`era-stamp-fill`). Where a gate's body executes something open-ended over the repository — a pytest suite that asserts against the real tree, a link-target resolver anchored at the repo root, a whole-repo walk — **no proper subset of the tree is a sound surface at all**, and the classification is not merely inaccurate but unavailable. Both halves were established first-party against the real analyzer sources and test modules across two verification rounds; see § D1 addendum. |
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
| F4 | `preserved` was claimed reachable on "exactly ONE path" in four places while the code had two (the equal-SHA short-circuit) | **Fixed in two passes.** Round 1 corrected four sites and this row originally claimed completeness; round 2 found the claim false — `phase-6-finalize/SKILL.md`'s dispatcher consumption site and a summary sentence in `verdict-currency.md` still carried it. Both corrected in `d12be01`. The equal-SHA check also moved BEFORE the declaration check, so an undeclared step whose HEAD never moved no longer answers `invalidated` against the dispatcher's own steady-state row |
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
| F19 | `refires` was attributed wholly to the HEAD-advance re-entry check, though `loop_back`, a retry after `failed`, and the `push` barrier's parity re-fire also produce extra `executed` rows | **Not fixed in round 1 — fixed in round 2.** This row originally claimed both named sites were corrected. They were not: only `verdict-currency.md` carried the correction, while `manage-execution-manifest/SKILL.md` and the `summarize_refires` docstring — the two sites the finding actually named — still asserted the single cause. Both corrected in `d12be01` |
| F20 | The `skipped` column's stated purpose was unverifiable from the pseudocode — whether a preserved SKIP reaches item 5e was not resolvable | **Fixed** — item 1 now states the obligation explicitly at the SKIP branches; without that row the saving would appear only as an absence |
| F21 | `refire-report` was absent from both the § Scripts table and § Canonical invocations in its own SKILL.md | **Fixed** |

### From the verification sub-agent (round 2)

Round 2 verified round 1's claims independently rather than taking them. **It refuted three of my own
recorded dispositions**, which is the strongest argument in this report for re-dispatching rather than
declaring done after a round of fixes. All fixes landed in `d12be01`.

| # | Finding | Disposition |
|---|---|---|
| G1 | `finalize-step-plugin-doctor`'s surface was STILL not a superset. Its roster's `broken-relative-link` rule resolves each relative link target found in a marketplace doc **against the repository root** and stats it on disk; marketplace docs link into `doc/**`, `test/**`, and root files in bulk, so renaming a link *target* turns the gate red without touching either declared root. After round 1's withdrawal this was the only declaration left in the tree, so the feature's entire live surface was the unsound one | **Fixed** — declaration withdrawn, refusal recorded with both disqualifying rules named (see the D1 addendum) |
| G2 | The ext-point rule round 1 wrote — a step performing "a whole-repo walk" MUST NOT declare — disqualified `finalize-step-plugin-doctor` by its own words (its agentfile analyzers walk the repo root), and nothing reconciled the tension | **Fixed** — resolved by G1's withdrawal; the rule and the roster now agree |
| G3 | `phase-6-finalize/SKILL.md`'s dispatcher consumption site still asserted `preserved` "on exactly one path" — the most-read statement of the classifier's contract, and false about the code | **Fixed** (see F4) |
| G4 | `verdict-currency.md` carried a one-path summary 19 lines above its own corrected two-path paragraph | **Fixed** — the summary now defers to the single authoritative statement below it |
| G5 | The `refires` mis-attribution was corrected in `verdict-currency.md` only; both sites the finding named were untouched | **Fixed** (see F19) |
| G6 | Branch A's lede still read "PR was rebased onto base … carries all four facts", contradicting the conditional fact block and the rebase-skipped clause twelve lines below it | **Fixed** — lede restated per path |
| G7 | A WARNING the merge-queue path actually emits said "CI red snapshot **after rebase** (merge-queue path)" — a log line asserting a rebase on the one path that never rebases | **Fixed** |
| G8 | Four further prose sites assumed a rebase or force-push happened: the CI-gate lede ("After the force-push"), "red on the rebased HEAD" inside the `true` branch, the mutex re-acquire rationale, and the pre-rebase gate's own framing sentence | **Fixed** — one row per site, all four corrected; the CI gate also gained its own heading, since it is now reached from two routes |
| G9 | `upstream_commit_count` is bound from two sources — the rebase payload (fact table) and the classifier re-run (operator prompt, both paths) — so Branch F's "structurally cannot have it" held only under the first binding, and an executor could reasonably have recorded the other | **Fixed** — the two bindings disambiguated at the fact site, with an explicit prohibition on substituting the classifier-sourced value |
| G10 | The `[--fact …]` argparse-bracket notation introduced in round 1 was a second convention in a document that uses `{… (if …)}` everywhere else, and one guard test skips any block containing `[` | **Fixed** — converted to the document's own conditional form |
| G11 | `pre-push-quality-gate.md` said "See § … **below**" for a section round 1 had moved **above** it | **Fixed** |
| G12 | `finalize-step-plugin-doctor` said its surface "covers three things" above two bullets | **Fixed** — resolved by G1's withdrawal |
| G13 | `phase-2-refine/standards/refine-workflow-detail.md` still described branch-cleanup as "unconditionally rebases" — the same class as F17, in a file the round-1 sweep did not reach | **Fixed** |
| G14 | `doc/user/parallelism-and-locking.adoc`'s narrative § "Platform merge queue" — the section a user actually reads for this feature — never mentioned the skipped rebase and force-push, though round 1 had fixed the two table rows | **Fixed** |
| G15 | Two stale test docstrings: the merge-queue routing guard said "adding a **fifth** consumption site" (there are now five), and the new real-resolver test claimed to cover the `default:`-prefixed bridge when the sole declarer is `project:`-prefixed | **Fixed** — the first now states why it pins no cardinality literal at all; the second names which bridge each test actually covers |

**Rejected: none.** Every finding in both rounds was accepted. Round 2 additionally re-derived the
70-character worst case character by character and confirmed both the arithmetic and the coupling
argument, and re-traced the reordered `classify_step` end to end confirming no new unsafe path — those
are recorded here as confirmations rather than findings.

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
  the unconditional re-fire. Three are remote-state verdicts and correctly stay that way. Two —
  `pre-push-quality-gate` and `finalize-step-plugin-doctor` — are **recorded refusals on evidence**,
  not unwritten obligations: no proper subset of the tree is sound for either (§ D1 addendum). The
  remaining five — `lessons-housekeeping`, `pre-submission-self-review`, `finalize-step-simplify`,
  `finalize-step-security-audit`, `review-retrospective` — were left undeclared because this run could
  not substantiate their surfaces arm-by-arm from their own docs, which is the admissibility bar the
  ext-point sets. Each is a candidate for a later, evidence-led declaration, and
  `pre-submission-self-review` (7× in the observed runs) is the highest-value one — though the same
  open-endedness that disqualified the other two may well disqualify it, since its subject is the
  plan's whole diff.
- **Decomposing `pre-push-quality-gate` is the unblocking condition for its own declaration.** Its
  per-bundle `quality-gate` sweep has a bounded surface even though its module-tests arm does not, so
  separating the arms would make a sound declaration possible on the bounded half. That is a
  decomposition of the step rather than a declaration on it, and it is deliberately out of scope here;
  the condition is recorded in the step's own doc for whoever revisits it.
- **The surface vocabulary is static globs, and that is what excludes the link-target case.**
  `broken-relative-link`'s inputs are derivable — they are exactly the link targets its own scan
  finds — but they are not expressible as a glob written ahead of time. A future `verdict_inputs`
  that admitted a *derived* surface (a command whose output is the path set) would make
  `finalize-step-plugin-doctor` declarable. That is a change to the ext-point's vocabulary, not a
  declaration under it, and it is not attempted here.
