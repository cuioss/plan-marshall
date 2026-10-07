# Run report — 090-harness-and-rule-gaps (run 02)

**Date (UTC):** 2026-08-18    **Branch:** `claude/harness-rule-gaps-541rjw` (run 01's harness-assigned
branch, kept)    **PR:** [#1294](https://github.com/cuioss/plan-marshall/pull/1294)
**Outcome:** completed

A **pickup run**. Run 01 reached an open PR with every deliverable landed and its verification loop
closed, then ended before the merge gate — leaving three report sections as placeholders and the
review cycle unworked. This run owns that remainder: the integration check against the `main` run 01
never saw, the review cycle, the merge gate, and the record.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | plugin (`Skill:`) — this run's first action |

The conditional domain skills were not loaded: this run planned no authoring surface, and the code it
did write (R1, R3, R4 below) is guard logic inside test modules run 01 had already established, made
under this contract's own mutation-check obligation. Recorded as a judgement rather than passed over
in silence.

## Deliverables

Run 01 delivered D1–D7. This run's own work is the findings recorded in § Findings; the ones
described here are those that changed a file — R1, R3, R4, R7 and R8 under `test/`, and R2 in the
plan's gating record. R5 and R6 are report corrections and are dispositioned in the table there.

### R1 — the D3 guard's positive control was pinned to a filename another slice owns

`main` advanced **four** commits between run 01's base (`b199d94`) and this run — 95 changed files —
among them PR #1290, which renamed `test/plan-marshall/build_test_helpers.py` to
`_build_extension_fixtures.py`. Run 01's `test_the_scan_finds_the_loader_call_sites` asserted its
positive control as

```python
assert any(site.endswith('build_test_helpers.py') for site in loaders), loaders
```

so the control reds on the merged tree while the walker it controls answers correctly. The PR read
`mergeable_state: clean` throughout — the break is semantic, not textual — and nothing on the PR's own
head could see it, because CI there verifies the base the branch was cut from.

**Fixed** by identifying the site by **role**: a shared fixture helper is a non-test module, since
pytest collects only `test_*`. That is the same correction run 01 made for `conftest`'s routing
docstring in D6, applied to a site it left pinned.

**Mutation-proven, not assumed.** With `_registered_name` forced to return `None` — a walker that
resolves nothing, the defect the control's own docstring names — the assertion reds with
`AssertionError: set()`. The mutated file was restored from a byte snapshot taken by the harness and
the restore verified by comparison, never by a git command.

Green on both trees: the PR head alone, and the PR head merged with current `main`.

### R2 — the `marketplace/bundles/**` ownership check the plan requires was not performed

The plan makes it a gating HYPOTHESIS with a stated procedure: read the **Out of scope** section of
each of `030`–`080` and confirm every one excludes `marketplace/bundles/**`. Run 01 recorded instead
that "no in-flight test-quality work exists to contend for it" — a substitute for the check, and one
contradicted four paragraphs earlier in its own report, which records plan `070` as open PR #1290.

**Fixed** by performing the check. It is **CONFIRMED**: all six plans exclude the surface, `050`
extending its exclusion to `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` as
well. The per-plan table is in `report-01.md` § Gating checks, replacing the substitute sentence.

### R3 — two guard populations were hand-kept mirrors of their sources

`REGISTERING_HELPERS` mirrored the loader helpers `conftest` defines, and `WRAPPER_SCRIPTS` mirrored
the wrappers routed through `build_main`. A helper or wrapper added later and not added by hand
contributes no call site, so the guard goes green over a population that silently shrank — the
n−1-of-n failure, committed by the guard built to prevent it.

**Fixed** by deriving each population and asserting the two agree:

* `registering_helpers_in_conftest()` walks `test/conftest.py` for every public function reaching
  `_exec_module_from_path` — the single construction both loaders funnel through, by that function's
  own contract — directly or by delegation, which is the hop `parse_ns` takes.
* `_wrappers_calling_build_main()` AST-walks the **whole** marketplace for calls to `build_main`; a
  wrapper added under another bundle is exactly the case a hand-kept list misses.

Each is an equality guard plus a non-vacuity assertion, so a derivation that stops finding anything
reds rather than passing. The declared constants keep their per-helper arity facts, which are
signature facts the tree does not state.

### R4 — the registration probe leaked `credentials` into `sys.modules`

`monkeypatch.delitem(sys.modules, PROBE_NAME, raising=False)` undoes only its own deletion, and the
key is absent when it runs, so it records nothing to restore. The load that follows registers
`credentials` and no teardown removes it — in a module whose entire subject is `sys.modules`
displacement.

**Fixed** with an autouse fixture popping the name on both sides, and the three ineffective
`monkeypatch.delitem` lines removed.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → Python files changed, so the gate applies.

`./pw verify` was run on the **merged** tree (PR head + current `origin/main` + this run's fixes)
rather than on the PR head alone, because the defect R1 fixes is invisible to a head-only build.

**SUCCESS**, twice — once after R1, once after R2–R4:

| Run | Result |
|---|---|
| after R1 | 21010 passed, 14 skipped |
| after R2–R4 | 21012 passed, 14 skipped in 459.66 s |
| after R7–R8 (shipped) | **21014 passed, 14 skipped** in 450.62 s |

Both with `ruff` "All checks passed!", `mypy` "Success: no issues found in 414 source files"
(production) and 776 (test-compile), "SPDX-header check passed", and plugin-doctor clean. `uv run
python -m pytest <file>` was used for the fast red/green and mutation checks; `./pw verify` is the
gate.

## Findings

Per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R1 | This run's integration check (PR head merged with current `main`) | The loader-scan positive control pins `build_test_helpers.py`, renamed on `main` by #1290. Red on the merged tree, invisible to the PR's own CI | **Fixed** — role-based control, mutation-proven against a walker that resolves nothing |
| R2 | This run's read of the plan against `report-01.md` | The `marketplace/bundles/**` gating check was replaced by an inference from PR state, and that inference contradicted the same section's own PR table | **Fixed** — the plan's stated check performed and recorded per plan; CONFIRMED |
| R3 | PR review (`coderabbitai`) | `REGISTERING_HELPERS` and `WRAPPER_SCRIPTS` are hand-kept mirrors; a helper or wrapper added later escapes the checks that quantify over them | **Fixed** — both populations derived from their live sources, asserted for equality and non-vacuity, both mutation-proven |
| R4 | PR review (`coderabbitai`) | `monkeypatch.delitem(..., raising=False)` restores nothing when the key is absent, so the probe leaks `credentials` into `sys.modules` for the session | **Fixed** — autouse teardown; proven by running the registering test alone in-process (CLEAN with the teardown, LEAKED without) |
| R5 | PR review (`coderabbitai`) | The report classifies verification condition 2 as satisfied while recording `plan-marshall` coverage falling 83.40 % → 83.34 % | **Fixed** — the report now states condition 2 as NOT met as literally worded, keeps the per-file result as the narrower claim it supports, and names the residue |
| R7 | PR review (`coderabbitai`, **review-summary body**) | `_exec_module_from_path` registers the module before executing it, so a body that raises leaves a half-initialised module published under its name — a later plain `import` then succeeds and returns the broken object. Its docstring also promised `ImportError` for an execution failure, which `exec_module` does not raise | **Fixed** — the entry is popped on failure (the standard importlib pattern), the `Raises:` clause corrected to say the body's own exception type propagates, and a guard added that reds when the cleanup is removed |
| R8 | PR review (`coderabbitai`, **review-summary body**) | `_PR_REFERENCE_RE` accepts `pull request #NNN` and no test covers that alternative; only `PR #NNN` and the bare form had cases | **Fixed** — a regression case for the spelled-out form. It carries no digit bound, so a regression narrowing it would be invisible to the bare-form cases, which do |
| R6 | Run 01's record | Three report sections were left as `_Filled in …_` placeholders; a landed report carrying them is an incomplete record | **Fixed** — run 01's placeholders cross-reference this report, which carries the three sections |

⚠️ **Four of run 01's own defects were caught by an external reviewer, not by its four-round loop** —
R3, R4, R7 and R8 are all in code that loop wrote, reviewed, and mutation-tested. R4 and R7 are both
`sys.modules` defects inside the change whose subject is `sys.modules` defects. That is the concrete
form of what `report-01.md` calls its residue, and it is evidence for the lane's own rule that a
stopped loop is not defect-free code.

⚠️ **R7 and R8 arrived on the review-SUMMARY surface, not as inline threads**, filed as "nitpicks"
inside the same review that opened the four threads. A run that read `get_review_comments` and
treated the resolved threads as the whole review would have shipped both — including R7, a real
`sys.modules` defect. That is exactly the three-surface rule this contract states, and here it paid
for itself on the surface easiest to skip.

### Stop record

**Which exit ended the loop.** This run ran **no** dispatch-and-fix verification loop, so neither exit
applies to it: it performed one integration check, worked one round of external review, and fixed
what both produced. Run 01's loop ended on the **verifier exit** at round 3 of a **four**-round budget
that run declared for itself (the contract has since fixed the default at five, in #1292 — after run
01 executed). No extension was asked for or granted. That record, its evidence and its survivor stand
in `report-01.md` and are not restated here.

**Were the late findings narrower?** Not applicable to a single round. Worth stating in the other
direction, though: the findings this run added were **not** narrower than run 01's — R3 and R4 are
defects in shipped test code, which is a wider class than the report-only findings run 01's round 3
was returning when it stopped.

**Survivors.** None added here. Run 01's single survivor — the two mutually-redundant arity guards,
characterised under B(a) — is unchanged and open on the same terms. No behavioural finding is
deferred.

**Residue to assume remains.** R1, R3 and R4 are each one instance of a class, and none of the three
classes is closed:

* a guard that names another slice's file breaks when that slice renames it — the tree was not swept
  for other path literals in guards;
* a declared population that mirrors a live source can fall behind it — two were derived here, and no
  sweep established that these were the only two;
* a `monkeypatch` call whose undo is conditional on prior state restores nothing — one was found by a
  reviewer, and the tree was not swept for the shape.

Read the shipped change as still carrying defects of these kinds.

## Reviewer participation

Population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | `reviewed` | — | Four inline review-thread findings on head `224fea4`, filed 13:37 UTC after the window it had quoted reopened and `@coderabbitai review` was posted. Its earlier bodies on this PR were rate-limit notices only |
| `cuioss-review-bot` | `reviewed` | — | "PR Reviewer Guide 🔍 … PR contains tests / No security concerns identified / No major issues detected", published as an issue comment |
| `sourcery-ai` | `rate-limited` | **no** | Review body: "you have reached your weekly rate limit of 500000 diff characters." A size/quota ceiling on the account's week, not a countdown — the same request does not succeed by waiting on this PR |

**Coverage: 2 of 3.** The § Step 8 shortfall disclosure is made to the operator before arming, in
these terms: *"Review coverage: 2 of 3 — `coderabbitai` reviewed (four findings, all fixed);
`cuioss-review-bot` reviewed (no major issues); `sourcery-ai` rate-limited on a weekly
diff-character ceiling, does not reopen."*

No verdict is `silent`, so no recovery check was owed. No surface was `unreadable`: all three —
`get_comments`, `get_reviews`, `get_review_comments` — returned cleanly on every read, and the PR
payload's own comment count agreed with what was read. Merge-gate condition 2 is therefore
**established**, not overridden: every comment on the PR was fixed, and each was replied to on its
thread with what was changed and the evidence.

⚠️ **What `coderabbitai` reviewed, precisely.** Its full pass is against head `224fea4` — the four
inline findings and the two review-summary nitpicks alike — and its verification of the fixes is
thread-by-thread: three confirmed against the replies, and the guard-population thread confirmed as
"Addressed in commit `9369dfb`" after that commit landed. It has performed **no fresh full review of
any later head**; its commit status on each of them reads "Review rate limited", and the fixes for the
two summary nitpicks were answered in a PR comment rather than re-reviewed. So the final head carries
a confirmed or answered disposition per finding and no new full pass, and this record says which
rather than letting `reviewed` imply the latter.

⚠️ **`coderabbitai`'s review was obtained, not merely awaited.** Its first two attempts — the PR
opening and this run's push — both returned rate-limit notices. The review exists because the window
it quoted was allowed to reopen and its registry `trigger_comment` was then posted. A run that read
only the first notice would have recorded a shortfall that was closable.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not recorded from a trusted source — the session exposes no clock the run may read.
  Reported as unavailable rather than estimated.
- **Population:** n/a for the figures above. ⛔ Had a figure been available it would count **this
  single Claude Code cloud session's usage**, which is **not** comparable to a plan-marshall
  `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under a per-task billing
  boundary this session does not share.

## Contract check (Step 9)

Covers both runs: run 01's steps as it recorded them, and this run's.

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Done.** Run 01's five are named in `report-01.md`; this run's one is named above, with the reason no domain skill was loaded |
| 2 Branch | **Done.** `claude/harness-rule-gaps-541rjw` exists on `origin` and carries every commit of both runs |
| 3 Plan directory | **Done.** `doc/plans/test-quality/090-harness-and-rule-gaps/plan.md` exists and opens with the first-instruction block |
| 4 Implement | **Done.** Every commit of both runs carries the `Co-Authored-By` trailer; deliverables addressed |
| 4 Per-commit gate | **Done.** Both of this run's Python-touching commits were preceded by a full `./pw verify` (which subsumes the quality gate), each read from the tools' own clean lines rather than from an exit code |
| 4 Pushed | **Done.** `git status -sb` reports no `ahead` at the end of the run |
| 5 Build gate | **Done.** Verdict and both build results recorded above |
| 6 Verification sub-agent | **Done by run 01** (four rounds against a four-round self-declared budget, stopped at round 3 on the verifier's answer — see `report-01.md`). **Not re-run here**: this run's own findings came from an integration check and from external review, and it discloses that rather than presenting itself as having re-verified the deliverables |
| 7 PR cycle | **Done.** PR #1294; all four review findings fixed and each replied to on its thread; the participation table above carries a verdict and a `Reopens?` value per reviewer, and no verdict is `silent` or `unreadable` |
| 8 Merge gate | Conditions 1–2 met at this commit, which **is** condition 3's last pre-merge commit; the condition-4 disclosure is stated in § Reviewer participation and made to the operator before arming. Arming follows this commit — a report committed before the merge cannot assert the merge, so the landing is read from the PR and recorded to the operator, never here |
| 8 Bridge | **Done.** No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory |
| 9 This check | **Done** — this table |
| 9 What have we learned | **Done** — proposal below, presented to the operator rather than self-approved |

**GitHub access path:** the GitHub MCP server, both runs. No `gh` CLI in the session.

**Branch form:** harness-assigned, created by run 01 and kept. ⚠️ This session was itself pre-assigned
a *different* branch, `claude/harness-rule-gaps-541rjw-rvvyp0`, sitting at `origin/main` with no
commits; it was abandoned for the branch carrying the work and the open PR, on the operator's explicit
instruction. Recorded as the departure it is: the keep-your-assigned-branch rule exists for
resumability, and resuming onto the empty branch would have lost the work that rule protects.

**Plugin cache sync:** not owed. A cloud run neither performs nor records one.

## What have we learned (Step 9)

**Proposed contract change: the merge gate has no integration condition.**

The evidence is R1. Conditions 1–3 are all satisfiable by a PR whose suite is red on the tree it will
actually land on. Condition 1 reads `mergeable_state`, which reports **textual** mergeability — `clean`
here throughout — and the PR's own `verify` runs against the base the branch was cut from. Run 01 did
everything the contract asks and still left a PR the merge queue would have rejected, because a
sibling slice renamed a fixture helper its guard names by filename. The gap is systematic for this
lane rather than incidental: a cloud session can end at any point, and the interval between "PR
opened" and "PR armed" is exactly where `main` moves.

The proposed edit, at § Step 8, as a new condition between 1 and 2:

> **A stale base is re-verified before arming.** When `origin/main` has advanced past the PR's merge
> base, merge it into the branch and re-run § Step 5's gate on the merged tree. `mergeable_state:
> clean` reports the absence of a *textual* conflict and says nothing about a semantic one — a renamed
> fixture, a moved constant, a widened rule — and the PR's own CI cannot see it, because it verifies
> the base the branch was cut from. A run that arms on a stale base hands the merge queue a build
> nobody has run.

**Presented to the operator, not self-approved, and not shipped in this PR** — per § Step 9 it belongs
on its own `chore/` branch, without `skip-bot-review`.

## Residue

| Item | Where it goes |
|---|---|
| Run 01's residue table — the 20 preambles, the 15 `parse_ns` conversions, the 12 `manage-providers` sites, the 23 pinned collisions, the 90 unresolvable call sites, the three non-zero rule counts, the 36 serial-order failures, the coverage nondeterminism, `pytest-testing`'s missing `register` note, and `credentials.py`'s 52.6 % | Unchanged; see `report-01.md` § Residue. This run neither closed nor re-derived any of it |
| **The three open classes R1, R3 and R4 each instantiate** — path literals in guards, declared populations mirroring live sources, and conditional-undo `monkeypatch` calls. Each was found by one instance, and no sweep established it was the only one | A follow-up whose deliverable is the sweep, per class; the reduction slices as they touch the modules |
| The proposed § Step 8 integration condition | Its own `chore/` PR, on the operator's decision |
