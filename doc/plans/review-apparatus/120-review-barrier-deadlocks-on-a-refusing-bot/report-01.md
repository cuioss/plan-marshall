# Run report — 120-review-barrier-deadlocks-on-a-refusing-bot (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/review-barrier-deadlocks-6b5sao`    **PR:** [#1241](https://github.com/cuioss/plan-marshall/pull/1241)    **Outcome:** completed — auto-merge armed, landing delegated to the merge queue

**Per-deliverable outcome:** D0 ✅ (gate did not halt) · D1 ✅ (all three conjuncts) · D2 ✅ (4 cases,
9 mutations). The merge commit is read from the PR merge event and reported to the operator, not
embedded here — it does not exist when this report is committed.

⚠ **The slug does not describe the work.** The file name is kept because a cloud session is bound to
its path, but the real subject is: **the refusal taxonomy had no STRUCTURAL member, so a size-capped
reviewer was offered a non-option.** The plan's original deadlock premise is REFUTED and two of its
three original deliverables were already shipped; neither was re-implemented.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) — loaded first, before reading the plan |
| `plan-marshall:ref-code-quality` | bundle path (`marketplace/bundles/.../SKILL.md`) |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `pm-dev-python:python-core` | bundle path — Python production code on the surface |
| `pm-dev-python:pytest-testing` | bundle path — Python tests on the surface |

The `plan-marshall` plugin was not consulted via `Skill:` notation for the bundle skills; the bundle
path route was used directly, which is the route the contract says always works in a fresh clone. No
skill was unobtainable.

## D0 — the barrier's terminal-state population (GATE, mutates nothing)

**The gate did not halt.** The plan halts D0 if the taxonomy members cannot be enumerated from the
contract and the classifier. They can, from both, and the two agree — the pre-existing derivation
guard in `test_bot_participation_contract.py` already asserts that agreement in both directions.

**Derivation method** (published here as the plan's Verification section requires):

- **Source 1 — the classifier.** A `vars()` sweep of `review_completeness.py` for `STATE_`-prefixed
  string constants. Not a hand-list: a literal is complete only until the next member is added.
- **Source 2 — the contract.** The `## Failure taxonomy` table in `bot-participation-contract.md`,
  parsed by row. Normative, and the owner of the closure claim.

**Population size: 11 terminal states** — 10 closed non-participation members plus `participated`,
their complement. (It was 10 before this change; `refused_structural` is the eleventh.)

Each member classified on two axes. `passable` = can a plan exit by an action of its OWN, read
against the SHIPPED branches rather than what is imaginable. `await can succeed` = could waiting, in
principle, ever produce the review — this is the axis on which a remedy is a *non-option* rather than
merely a slow option.

| Member | Blocks? | Passable by plan action | Await can ever succeed | Remedy the shipped contract names |
|---|---|---|---|---|
| `participated` | no | ✅ (not a block) | ❌ (nothing to wait for) | none needed |
| `participated_but_empty` | no | ✅ (not a block) | ❌ (nothing to wait for) | none needed (accounted-for) |
| `in_progress` | yes | ✅ | ✅ | let the run finish |
| `not_triggered` | yes | ✅ | ❌ | generate the trigger event |
| `participated_stale` | yes | ✅ | ❌ | re-trigger a re-review |
| `absent` | yes | ✅ | ✅ | loop back / escalate the silent bot |
| `refused_awaitable` | yes | ✅ | ✅ | claim the window and await the reset |
| `refused_unknown` | yes | ❌ (recovery escalates) | ✅ (declared ignorance — not refuted) | operator ruling |
| `refused_hard` | yes | ❌ | ❌ | accept the gap / required-vs-optional |
| `declined` | yes | ❌ | ❌ | accept the decline |
| `refused_structural` ⭐ | yes | ❌ | ❌ | **split / accept / disable-for-this-PR** |

### Deadlocks: none. The finding is the NON-OPTION, exactly as the plan predicted

No member is a deadlock in the plan's sense (*"a state a plan cannot exit by acting"* being
unexitable). The four `passable: ❌` members all exit through the shipped, HEAD-bound,
gap-class-bound, fail-closed merge-authorization surface — the override **is** the exit, so the
plan's instruction not to re-litigate the deadlock framing is confirmed against merged `main`.

### The barrier's OWN dispositions — the second axis, and its honest limitation

D0 asks for *"every state in which the barrier can end"*, which is two populations, not one. The
per-bot member axis above is derived in code and guarded in both directions. The **barrier-disposition
axis is classified here in prose only**, and that limitation is stated rather than papered over: it is
a document's branch structure, not a code enumeration, so no `vars()` sweep reaches it.

| Barrier disposition | Passable by plan action | Exit |
|---|---|---|
| `clean` (both predicates pass) | — | merges |
| `authorized bypass` (`any_admissible: true`) | — | merges under a recorded, HEAD-bound, gap-class-matched ruling |
| `blocked / pending findings` | ✅ | loop back → triage → re-enter |
| `blocked / participation incomplete` (non-structural) | ✅ | loop back → re-await → re-enter |
| ⭐ `blocked / participation incomplete — STRUCTURAL` | ❌ | **added by this run.** No automatic exit: operator ruling, re-scope, or reclassification. `fail_into_loopback` records the sibling `loop_back` to `6-finalize` — re-entry re-runs the authorization check, which an operator remedy clears — and logs three copy-runnable remedies; `ask` renders split / accept / disable. ⚠ This row asserted "defers via Branch C" until round 5 caught it: the disposition changed and its own D0 classification did not move with it |
| `UNKNOWN` (re-fetch failed) | ✅ | never authorizable, but exitable — make the failed read succeed |
| `UNKNOWN` (predicate failed) | ✅ | same |

⚠ **This table was incomplete when first written, and a reviewer caught it.** The structural
disposition is one this run itself introduced, so the D0 classification had to be re-derived *after*
the implementation rather than only before it — the gate's population is not static across a change
that adds to it. Recorded because the reverse mistake (deriving once, up front, and never revisiting)
is the one that leaves a plan reporting a complete classification over a population it has since
grown.

### The non-option pairings — a remedy offered that cannot work

⭐ **1. SHIPPED AND LIVE. `refused_hard` + cause `size` → `escalate_ask{reason:
rate_window_not_awaitable}`, whose `prompt_options[0]` was `"Wait another
{review_rate_window_timeout_seconds}s"`.** Sourcery's registry doc states in as many words that "the
same PR is over the limit a minute later and an hour later alike, so nothing reopens by waiting" — and
the operator's *first* offered option was to wait. **This is the defect D1 fixes.**

⭐ **2. LATENT AND UNGUARDED. `refused_awaitable` + cause `size` → Branch 2 `claim_and_await`.** The
recovery arming read `rate_limit_class` ALONE
(`_RECOVERY_BY_CLASS[bot_registry.rate_limit_class(bot_kind)]`, pinned by
`test_refusal_recovery_arming.py`) and was blind to the cause. Any `awaitable_window` bot that refuses
on size would get the full claim-await-generate recovery, burning the whole
`review_rate_window_timeout_seconds` budget on a ceiling that waiting does not move, then re-triggering
a bot whose answer cannot change. No live instance today (no `awaitable_window` bot declared a size
pattern), but nothing prevented one.

**3. `refused_hard`'s own interpretation text conflated the two causes** — "a per-PR size/diff ceiling
**or** a plan-level quota" — one member, two disjoint remedy sets, so a consumer rendering the member
alone named neither remedy correctly.

**4. `review_state_summary` bucketed every refusal under one `refused` label,** so `display_detail`
could not distinguish a size refusal from a quota one — the same collapse the summary was introduced
to undo for reviewed-vs-nobody-reviewed.

## Deliverables

| # | Deliverable | Commit | Verification state |
|---|---|---|---|
| D0 | Derive the barrier's terminal-state population | `55ba299` (report) + `eadae3b` (its code mirror) | ✅ Published above with its derivation method and size. Mirrored in code as two total classifications in `test_structural_refusal.py`, each asserted equal to the derived set in BOTH directions. Gate did not halt. |
| D1 | Structural refusal as its own taxonomy member | `eadae3b`, `b7a7057`, `3131bdc` | ✅ All three "done when" conjuncts met — see below |
| D2 | Tests, each verified discriminating | `eadae3b`, `b7a7057`, `3131bdc` | ✅ 4 cases, 9 mutations |

### D1's "done when" — the three conjuncts, checked independently

| Conjunct | State |
|---|---|
| a size-capped refusal **resolves to the structural member** | ✅ `_refusal_state(class, cause)` consults the cause first. Proven per branch: `hard_quota` (sourcery), `awaitable_window` (coderabbit — the load-bearing case), plus a registry-wide sweep with a non-empty-population guard |
| it **carries the cap** | ✅ `refusal_size_cap()` reads the ceiling off the bot's own notice; reported in `refusal_causes[]{bot_kind,cause,cap}`. An unstated cap renders the literal `unknown`, never a default. Joined by `measured_diff_size` so the gap is auditable rather than asserted |
| it is **never offered an await** | ✅ …**and this is where round 1 found the fix incomplete** — see Findings F1. Now closed at both layers: the leaf's envelope carries no wait and no `timeout_seconds`, and `phase-6-finalize` item 7a — the hook that actually renders the prompt — has its own disjoint branch table |

### Sub-claims

- **Advance disclosure** ✅ `review_completeness size-caps` reports per registered reviewer whether it
  declares a ceiling (derived from `refusal_size_patterns`, so it cannot disagree with the
  classification) and, separately, whether the ceiling's *value* is recoverable. Round 1 correctly
  noted the surface existed but nothing routed a plan to it; `create-pr.md` now does, at the step
  where a diff's size first becomes measurable, framed as a disclosure and explicitly not a gate.
- **Never `await` on the structural branch** ✅ Recovery gains **Branch 0**, evaluated before the
  class branches, returning `escalate_ask{reason: refusal_structural}`.

### ⭐ The cold read — the plan's own verification item, answered verbatim

The plan requires a fresh reader, given no framing about the change, to be asked what options the
workflow offers a size-refused reviewer, and the answer reported **verbatim** — because *"if 'wait'
appears among the options for the structural case, the fix has reproduced the non-option it was
written to remove."* Rounds 3 and 4 both reported the cold read clean, but the tree moved three
commits after round 6, so it was re-run at `601abf1` — the tree the PR merges from. The reader was
told only to read the current working tree and was given no history, diff, or framing.

**Its answer to the structural case, quoted:**

> None of the three labels — "Split the PR into diffs under the cap", "Accept the coverage gap (record
> reason)", "Disable this reviewer for this PR" — is a wait; the first defers the merge pending an
> operator-performed split ("Defer this merge; land the change as smaller PRs the reviewer will read",
> `branch-cleanup.md:1105`), not a re-review of the same diff.

It found waiting excluded at **both** surfaces, quoting the leaf — *"⛔ **Its `prompt_options[]` MUST
NOT offer a wait.**"* (`automatic-review/SKILL.md:385`) — and the barrier — *"This ceiling does not
reopen — the same PR is over it an hour from now. Re-running the review cannot change the answer, so
re-triage is not offered."* (`branch-cleanup.md:1093-1095`). Its verdict on question 3 was
**"Size-ceiling case — no."**

**Its answer to the temporal case, quoted:** **"Quota case — yes."** The first option there is
literally `- "Wait another {review_rate_window_timeout_seconds}s"` (`automatic-review/SKILL.md:902`).
That is the correct answer for that branch, and the two answers together are the whole point of the
change: **the same reader, reading the same documents, is offered a wait on the branch where waiting
works and is not offered one on the branch where it cannot.**

⭐ The reader also reconstructed, unprompted, the distinction round 5 was spent making explicit —
that the futile thing is the *re-triage remedy*, not the `loop_back` control-flow record, quoting
`branch-cleanup.md:1035` and `:1042` for it. That distinction was invisible in the pre-round-5 text;
a cold reader recovering it from the documents alone is the evidence that the repair landed in the
normative prose rather than in an aside.

### Deliberate design decisions worth recording

- **The cap is READ, never declared.** A declared constant goes stale silently the moment the
  provider changes its budget, and it cannot be reconciled against the diff that was actually
  refused. `refusal_size_cap_patterns` mirrors the shipped `rate_limit_eta_patterns` exactly, one
  axis over: an awaitable refusal states *when* it reopens, a structural one *how big* the diff was
  allowed to be. ⛔ **No test pins the real provider figure** — the plan labels it a lead, not a
  fact, so every cap assertion uses a synthetic notice and pins the extraction MECHANISM.
- **The cause DOMINATES the awaitability axis for `size`.** `rate_limit_class` is declared per BOT
  while a cause is observed per REFUSAL, and one bot refuses for both causes at one class (Sourcery's
  size ceiling and weekly quota are both `hard_quota`), so the per-bot field cannot separate them
  even in principle. Reading the class first is what would send an `awaitable_window` bot's size
  refusal into claim-and-await.
- **`measured_diff_size` carries its unit inside the value, and it is NOT the reviewer's unit.**
  Counting the reviewer's own unit exactly means downloading the whole patch — most expensive
  precisely on the oversized PRs where this fires. The pair is an order-of-magnitude comparison; the
  embedded unit is what stops a reader treating it as an exact reconciliation.
- **`--refused-causes` moved to the shared flag block** so `check` and `deficit` cannot name
  different members for one refusal. `deficit` publishes a per-reviewer `state` column, and two
  commands disagreeing on it would be unadjudicable from the output.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty — 8 files**, so the full gate
applied: `bot_registry.py`, `review_completeness.py`, `_github_pr.py`, `github_pr.py`,
`test_bot_participation_contract.py`, `test_review_completeness.py`, `test_structural_refusal.py`,
`test_github_pr.py`. ⚠ This said "5 Python files" beside an enumeration of seven until round 5
re-derived it — a count written from memory rather than from the command quoted next to it, which
is the exact failure mode this report's own findings keep recording.

`./pw verify` ran **ten times** — counted off the rows below, not from memory. ⛔ **Two of those runs
exited 0 while FAILING** — F37 and F49 — so every outcome below is read from the streamed output,
never the exit code:

| At | Result |
|---|---|
| `b7a7057` | SUCCESS — 19702 passed, 14 skipped |
| `3131bdc` | SUCCESS — 19731 passed, 14 skipped, 0 failed (11m27s) |
| `7adf802` | ⛔ **FAILED** — `verify: test-compile failed`, 2 mypy errors, **exit code 0** |
| `97f7493` | SUCCESS — 19740 passed, 14 skipped, 0 failed (10m00s) |
| `6f31a5d` | ⛔ **FAILED** — `verify: module-tests failed`, 1 test, **exit code 0** |
| `1b1b867` | SUCCESS — 19743 passed, 14 skipped, zero `FAILED` lines, zero sub-step failure lines (9m15s) |
| `3ac175d` | SUCCESS — 19746 passed, 14 skipped, zero `FAILED`/`ERROR` lines, zero sub-step failure lines (6m27s) |
| `902a5d9` | SUCCESS — 19746 passed, 14 skipped, zero `FAILED`/`ERROR` lines, zero sub-step failure lines (6m27s) |
| `a751c9a` | SUCCESS — 19746 passed, 14 skipped, zero `FAILED`/`ERROR` lines, zero sub-step failure lines (6m31s). This is the tree the PR opened from. Round 5 refused a gate recorded two commits behind HEAD, correctly: `test-compile` is exactly what F37 proved the targeted suites cannot see, so a green targeted run at a later commit is not a substitute |
| **`601abf1`** | **SUCCESS — 19876 passed, 14 skipped, zero `FAILED`/`ERROR` lines, zero sub-step failure lines (6m41s). This is the MERGED tree the PR merges from** — `origin/main` merged in after the PR opened, so the pass count rises above `a751c9a`'s by `main`'s own new tests, not by anything this branch adds |

⛔ **`./pw verify` exited 0 while FAILING on TWO of its ten runs.** Both were caught only by
reading the streamed output. Had the exit code been trusted at any of those points, this run would
have opened a PR on a red gate and reported it green — which is precisely why the lane contract makes
"read the output, not the exit code" a rule rather than a suggestion. The two distinct failures were a
test-only type error (invisible to the quality gate, which type-checks production only) and a
derivation-guard failure in a suite my targeted runs had not covered.

Final run's (`601abf1`, the merged tree) coverage line, read back verbatim: `coverage: COMPLETE over
the dimensions below — checked over full scope: mypy(production) [402 files, cache disabled], ruff
[marketplace/bundles, test, .claude], SPDX headers [marketplace/bundles, test, .claude,
marketplace/targets, build.py], plugin-doctor [marketplace-wide], mypy(test) [743 files, cache
disabled], module-tests [whole-tree pytest]`, terminating in `=== verify: SUCCESS ===`. The file
counts rise above the earlier runs' 399/737 because `origin/main` was merged in, not because this
branch adds source. `./pw quality-gate` additionally ran before every commit touching `*.py`, each
reporting `Success: no issues found in 399 source files`, `All checks passed!`, and `SPDX-header check
passed`.

⚠ **The quality gate cannot substitute for the full verify here, and this run proved it.** The gate
type-checks *production* only; the defect at `7adf802` was a test-only type error, visible to
`test-compile`'s `mypy` over the 737-file test tree and to nothing else — not to the gate, and not to
pytest, which ran the offending helpers without complaint.

`git status --porcelain` was empty after every `verify` run — **no `uv.lock` churn** reached a commit,
and every commit staged explicit deliverable paths rather than `git add -A`.

## Findings

One row per INSTANCE, never bundled.

### From the pre-PR verification sub-agent — round 1

| # | Finding | Disposition |
|---|---|---|
| F1 | ⭐ **The fix stopped one hop short of the operator.** `phase-6-finalize/SKILL.md` item 7a — the hook that actually fires the `AskUserQuestion` — enumerated exactly four escalation reasons, hard-coded "the same three options" for all of them, and led with `"Wait another {timeout_seconds}s"`. A `refusal_structural` envelope arrived as an unknown fifth reason whose three real remedies mapped to no branch, and whose deliberately-absent `timeout_seconds` would have interpolated an unresolved placeholder into the non-option. **The defect was still live at the only place a human sees it.** | **FIXED** (`3131bdc`). Item 7a now carries the fifth reason with its own disjoint branch table, renders `prompt_options[]` as returned rather than a fixed list, resolves the `head_at_completion` SHA for it, and names both audit figures. Four new tests read that file directly |
| F2 | ⭐ **`refusal_size_cap` could CRASH the producer.** `match.groups()` is truthy for a one-tuple holding `None`, so a pattern whose first group sits in an unmatched branch yielded `None.strip()` → `AttributeError` out of `cmd_fetch_findings`. The `re.error` guard covers compile failures only — so the function's own docstring promise that a bad registry edit cannot break the return path was FALSE | **FIXED** (`3131bdc`) — fall back to the whole match, treat an empty capture as no figure. Pinned by two new tests |
| F3 | `measured_diff_size` was gated on `refused_size_caps` (a successfully-extracted cap) rather than on the size CAUSE. These come apart exactly where it matters: a size refusal stating no figure yielded NEITHER number — an unquantified gap in the one case the feature exists to prevent | **FIXED** (`3131bdc`) — guard is now `any(cause == REFUSAL_CAUSE_SIZE …)`. Pinned by a producer-level test |
| F4 | A cap arriving without its cause was silently dropped, so the bot fell back to a TEMPORAL member and was offered a wait. The two cross as separate CLI flags and the barrier's contract lets either default to empty independently | **FIXED** (`3131bdc`) — fail-closed recovery, one-directional (a cause never infers a cap) |
| F5 | `test_github_pr.py::_patch_provider` stubbed three named provider helpers but not `run_gh`, so once the measurement landed these fixtures would shell out to a real `gh pr view` and silently take its failure path — passing for the wrong reason. The exact synthetic-double shape the lane contract warns about | **FIXED** (`3131bdc`) |
| F6 | `_WAIT_OFFER` matched only the literal "wait"/"await"; a remedy set swapping in "Retry later" or "Back off" would reproduce the non-option and the sweep would report clean | **FIXED** (`3131bdc`) — widened to the plan's own equivalents |
| F7 | `test_the_structural_recovery_branch_neither_awaits_nor_generates` self-weakened with `or 'Do NOT' in branch`, which matches any `Do NOT` sentence at all, and never asserted the "generates no event" half its name claims | **FIXED** (`3131bdc`) — all three negations asserted separately |
| F8–F20 | **Thirteen stale beyond-diff statements**, by consumer kind: "the cause is advisory / never changes which member" (`workflow-integration-github/SKILL.md:137`, `review_completeness.py:885`), "it only *labels* a refusal's cause" (the OWNING contract, `:451`), five "three refusal members" enumerations, the `--refused-bots` **operator-visible `--help` text**, three producer-side member enumerations, two CLI flag counts ("seven"/"six"), and the `fetch_findings` output-field enumeration missing `refused_size_caps[]` | **ALL FIXED** (four in `b7a7057`, the rest in `3131bdc`) |
| F21 | Advance disclosure was **PARTIAL**: `size-caps` existed, was tested and documented, but **no workflow step routed a plan to it** — "where a plan can consult them" was satisfied only in the sense that a command existed | **FIXED** (`3131bdc`) — routed from `create-pr.md`, where a diff's size first becomes measurable |
| F22 | A local `/sync-plugin-cache` is owed and must be recorded | **REJECTED.** The agent read `CLAUDE.md` without the lane carve-out. `cloud-plan-lane` § "Scope and precedence" states a cloud run **neither performs nor owes** a sync: it is a machine-local build step reading the git-ignored `target/` and writing `~/.claude/`, neither of which this run has or may touch |

### From the pre-PR verification sub-agent — round 2

⭐ **Round 2's headline finding is more serious than round 1's, and it is the same defect one layer
further out.** This is the archetype the plan itself names as the epic's most frequent recurrence — *a
fix for a defect that reproduces the defect's family* — and it recurred twice inside this single run.

| # | Finding | Disposition |
|---|---|---|
| F25 | ⭐⭐ **The non-option survived at the DEFAULT surface.** `review_rate_window_await` defaults to `false`, so on the default configuration the leaf's Branch 0 never fires and the dispatcher's structural branch table is **unreachable code**. The prompt an operator actually gets is the **pre-merge barrier's** — untouched by rounds 0–1 — which offered **"Re-triage now → loop back into automatic-review triage"** as option 1, and whose own default mode (`fail_into_loopback`) takes that action **automatically with no prompt at all**. For a size-capped bot a loop-back re-reviews a diff of the same size, the bot re-refuses, and the barrier re-reaches the identical verdict. It escaped every check because it is spelled *"re-triage"*, not *"wait"* — my `_WAIT_OFFER` regex, already widened once for exactly this class of miss, returns `False` on both "re-triage" and "loop back" | **FIXED** (`7adf802`). The barrier derives `{structural_bots}` from `bot_states` it already reads; the loop-back arm is UNAVAILABLE under **both** modes — `ask` gets its own prompt (split / accept / disable, no re-triage, both audit figures named), and `fail_into_loopback` does not prompt but logs the remedies. ⚠ Its disposition was rewritten twice after this — see F39, F52 — and now records the sibling `loop_back`. **Mutation-verified**: reintroducing the re-triage option fails exactly the two barrier tests |
| F26 | ⭐ **A remedy I added looped forever.** My "Disable this reviewer for this PR" branch asserted the re-dispatch settles. It does not: the recovery arms on ANY registered bot with no `required_bots` filter and fires before the participation guard, so the operator choosing the one remedy that resolves the block lands back on the identical prompt | **FIXED** (`7adf802`) — recovery scoped to required bots, which is independently correct: an optional bot's silence cannot block, so escalating it asks a question nobody needs. The dispatcher branch now names the scoping its settling claim depends on, and a test asserts both halves |
| F27 | ⭐ **My round-1 cap-recovery broke a documented invariant.** It lived only on `check`, so `check` reported `refused_structural` and `deficit` reported `refused_hard` in exactly the scenario the recovery exists for — the cross-command disagreement three documents forbid in as many words. My own agreement test structurally could not see it: it handed both commands the cause directly | **FIXED** (`7adf802`) — hoisted to `recover_causes_from_caps`, shared by both; `--refusal-size-caps` moved to the shared flag block. The test now parametrizes the **cap-only** case, the only one that can observe it. **Mutation-verified**: removing `deficit`'s recovery fails exactly that case and nothing else |
| F28 | **My round-1 crash fix introduced a smaller defect.** Falling back to `group(0)` on an empty declared capture returned the prose `"review limit of"` as a cap — comma-free, so it survives the CLI transport and renders beside a real `measured_diff_size`, making an unaudited gap look audited | **FIXED** (`7adf802`) — a declared group that captured nothing yields UNKNOWN; the no-group convention still uses the whole match, pinned separately |
| F29 | `_extract_rate_limit_eta` carries the identical `group(1) is None` bug under the identical false docstring promise | **DEFERRED — recorded, not fixed.** Out of this plan's declared surface, latent-only (no registered bot declares `rate_limit_eta_patterns`), and fixing it would widen the diff into a sibling function this plan does not own. Named here so it is a known debt rather than an unnoticed one |
| F30–F36 | **Seven further stale statements**, including two that instructed the defect: the `review_rate_window_await` **`configurable:` knob description** (machine-read, plugin-doctor-linted) still described the pre-fix class-first order with no cause branch, and a field-contract line said item 7a *"can route them identically"* — the exact folding the structural member exists to prevent. Plus "four distinct escalations", "a fourth shape", two literal `'size'` comparisons, item 7a's recording-branch preamble, and an ambiguous "all three" in `pr-review-operations.md` | **ALL FIXED** (`7adf802`) |

### From the build gate

| # | Finding | Disposition |
|---|---|---|
| F37 | ⛔ **`./pw verify` exited 0 while reporting `verify: test-compile failed`.** Two of my new doc-slicing helpers declared `-> str` but returned `Any` — `get_script_path` is untyped, so the `Path` and its `read_text()` propagate as `Any` through the slice. **Nothing else catches this**: the quality gate type-checks production only, and pytest runs the helpers happily. This is precisely the failure mode the lane contract documents, and the reason it requires reading the output rather than the exit code — reading the exit code would have shipped a red gate as green | **FIXED** (`97f7493`) |

### From the pre-PR verification sub-agent — round 3

Round 3 confirmed **every** round-2 finding fixed and reported the cold read clean of futile options
at all three surfaces — the plan's actual goal, verified against rendered option lists rather than
prose. It then found ten more, four of them introduced by the round-2 fix itself.

| # | Finding | Disposition |
|---|---|---|
| F38 | ⭐ **The two blocked paths mandated OPPOSITE actions with no precedence** (mine). A PR with a structural refusal AND an unhandled comment satisfies both: one forbids the loop-back, the other mandates it. Harmless before the structural member existed (the paths were behaviourally identical); a live contradiction after | **FIXED** — pending findings take precedence, because triage is actionable and makes progress; the structural gap is disposed of LAST precisely because nothing automatic clears it. Disposing of it first would ask the operator to accept a gap while a remedy for the other half was still available |
| F39 | ⭐ **My structural defer invented a THIRD defer semantic** (mine). Leaving the step record absent re-arms the resumable re-entry check to re-fire the barrier into the identical verdict — a slow loop, inside the branch written to stop a loop | ⚠ **Fixed, then re-fixed.** My first fix reached for Branch C — the *wrong* existing semantic ("declined by user"), which settles and lets the plan archive with the PR unmerged. Round 4 caught it (F52). The disposition is now the sibling `loop_back` to `6-finalize`: no invention, no archive, and the remedies it names have a pass that actually runs |
| F40 | ⭐ **"Accept the coverage gap (record reason)" recorded nothing** (mine). The dispatcher branch stamped a step record and claimed the ruling was "recorded there"; nothing carried it, and on the DEFAULT barrier mode the barrier never re-asks. An option whose label promises an outcome it does not deliver — a different failure from a non-option, the same disservice | **FIXED** — mints `barrier-ask-override` over `review-barrier-gap` at the stamped HEAD, carrying both audit figures |
| F41 | **The headless decision-log named remedies an operator could not execute.** No `--kind`, no HEAD-binding hazard, and "move the bot to `optional_bots`" written where a reader reaches for `marshal.json` — which the barrier does not read | **FIXED** — each remedy names its verb and its hazard. This is the only operator-facing surface on the default configuration |
| F42 | **`pre_merge_comment_barrier`'s own `configurable:` description was stale on both arms** — the same machine-read consumer kind the round-2 fix corrected one skill over and missed in the file it was editing | **FIXED** |
| F43 | **The `deficit` canonical block omitted `--refusal-size-caps`**, so a caller following the docs passes the cap to `check` and not `deficit` — making the cap-only recovery unreachable from documented usage, which is the one scenario it exists for. plugin-doctor validates docs-against-parser, never parser-against-docs, so it stayed green | **FIXED** |
| F44–F47 | Mutex-invariant enumeration missing the terminating-defer class; a forward reference where every sibling carries an inline release; the roster row naming one grant site of three; the 5d carve-out's reason enumeration stale for the second time | **ALL FIXED** — the 5d enumeration was **removed** rather than re-counted: it had gone stale at four and again at five, so the carve-out now names none and defers to item 7a |
| F48 | A mixed gap (structural + `absent`) suppresses a loop-back that would still have fetched the absent bot's review | ⛔ **I recorded this RESOLVED and it was not — corrected in round 4.** My claim was that F38's precedence rule means "the absent bot is still awaited on the earlier pass". There need be **no earlier pass**: the first barrier entry can have `{count} == 0` with both bots unproven, and the structural gate is `{structural_bots}` non-empty AND `{count} == 0` — it says nothing about other unproven bots. **NOW FIXED** by disclosure rather than by suppression: the prompt renders the full `{unproven_bots}` set and states in as many words that accepting the gap authorizes past every one of them, and the grant's `--granted-over` carries the whole set like its sibling. The RE-TRIAGE OPTION is suppressed in `ask` mode — correctly, since re-requesting the review cannot clear the structural half — while the default `fail_into_loopback` still records a loop-back, so a merely-`absent` bot IS re-observed on the next pass there. ⚠ I first wrote "the loop-back is still suppressed" flatly, which is false for the default mode; round 5 caught it |

### From the pre-PR verification sub-agent — round 4

Round 4 confirmed R2/R3/R8/R9 cleanly fixed, D0/D1/D2 all met, and the cold read free of any wait or
re-triage at **all four** surfaces. It then returned **NOT READY** with five blockers — four of them
introduced by the round-3 fix. ⭐ **The round-3 fix repeated the pattern round 3 itself had named.**

| # | Finding | Disposition |
|---|---|---|
| F51 | ⭐ **A live contradiction three lines from the text it was meant to reconcile** (mine). The "Split" option pointed at the `fail_into_loopback` path *"(leave the step record absent, HALT)"* — the semantics I had just rewritten to Branch C. I changed the target and left the pointer | **FIXED** |
| F52 | ⭐⭐ **My Branch C fix archived the plan unmerged and foreclosed its own remedies** (mine). Branch C is the "declined by user" settle: the FOR loop continues to `archive-plan`, archiving with the PR unmerged, worktree unremoved, branch undeleted. Worse, an already-`done` `branch-cleanup` is SKIPPED on re-entry — so the message's own remedies ("grant at the HEAD the next pass will see", "reclassify then re-enter") named a pass that would never run | **FIXED** — the disposition is now the **sibling `loop_back` to `6-finalize`**, used verbatim. ⭐ The root error was inventing a disposition twice (absent+HALT, then the wrong existing one) when the document already carried a fitting one |
| F53 | **The remedies still were not executable** (mine). The grant omitted `--plan-id`, `--granted-over`, `--reason` and the executor prefix; the reclassify omitted `--plan-id`, `--param`, `--value` and is two calls. Copying either verbatim is an argparse rejection — against the fix's own stated standard, *"a remedy an operator cannot execute from the text is no remedy"* | **FIXED** — both are complete, copy-runnable invocations, pinned by a test that reads the fenced command blocks |
| F54 | **The structural `ask` merged outside the merge mutex** (mine). The arm releases the lock before the prompt and named a re-acquire for only one of its three options; "Disable this reviewer" continues to the clean path and thence to **Merge PR** with nothing re-acquiring | **FIXED** — re-acquire and re-validate named on that arm |
| F55 | **R1's precedence rule had no landing site.** It obliged the pending-findings path to carry structural context in its message, but that message is a fixed literal in a section that never mentions the rule — executing it required improvising, which the workflow-discipline rule forbids | **FIXED** — the pending-findings section now carries both obligations inline, including making its `ask` prompt name the structural gap so an operator cannot "Merge anyway" past a reviewer they were never shown |
| F56 | `_add_bot_observation_flags` docstring said "eight list flags"; the helper declares nine. The branch **incremented** the count rather than re-deriving it, preserving a pre-existing off-by-one | **FIXED** |
| F57 | The widened mutex invariant dropped a conjunction, leaving a run-on in a normative sentence | **FIXED** |

### From the pre-PR verification sub-agent — round 5

Round 5 confirmed **all five** round-4 blockers fixed, verified the remedies against the **live
argparse** rather than the prose, and — asked to challenge the new loop-back on its own terms —
confirmed it is genuinely clearable (the authorization check runs *before* the disposition on
re-entry) rather than a return to round 2's futile loop. It then returned NOT READY with seven
blockers, and named the meta-pattern this run keeps reproducing:

> ⭐ **"The fix lands, the sentences *about* the fix do not move with it."**

Four of the seven were round-3 text describing a disposition round 4 replaced — in a knob
description, a cross-skill reference, a normative prohibition, and the report's own D0 table.

| # | Finding | Disposition |
|---|---|---|
| F58 | ⭐⭐ **A flat MUST-NOT/DO-IT contradiction four lines apart, in the section round 4 rewrote** (mine). The heading said *"the loop-back arm is UNAVAILABLE"* and the framing *"a loop-back … MUST NOT be taken"*, while the branch below **takes a `loop_back`**. The reconciling distinction existed only in an explanatory note, never in the normative sentence | **FIXED** — the two senses of "loop-back" are now separated explicitly: the **re-triage remedy** is what is unavailable; the **`loop_back` control-flow record** is what the branch emits. Heading, framing, and the `{barrier_mode} == ask` bullet all re-worded; the cross-reference and the test anchor moved with them |
| F59 | ⛔ **The `configurable:` knob description still described the discarded Branch-C semantics** — *"defers with an actionable decision-log instead of looping"*. **The THIRD stale `configurable:` block in this branch**, and the SECOND on this very field | **FIXED** |
| F60 | The dispatcher asserted *"the barrier never re-asks — it defers and settles"*, load-bearing as the justification for minting the grant at the hook, and false once the barrier began looping back | **FIXED** — it never re-*prompts*, which is the true and relevant claim |
| F61 | ⛔ **The structural loop-back never said "return control to the finalize dispatcher", and the fall-through is DESTRUCTIVE.** The sections after **Merge PR** are not merge-gated: § "Remove Worktree" fires on `{worktree_path}` alone and § "Switch to Base Branch … Delete Local Branch" is uniform across `open` and `merged`. A literal executor honouring only *"Do NOT proceed to Merge PR"* would remove the worktree and delete the branch of an **unmerged** PR — then re-enter the loop-back it just recorded with no worktree | **FIXED** |
| F62 | The report's **D0 table** still published *"`fail_into_loopback` defers via Branch C"* — the gate deliverable's own classification, asserting the disposition it had replaced | **FIXED** |
| F63 | The report's F48 disposition claimed *"the loop-back is still suppressed"*, false for the default mode, where it is taken | **FIXED** — the RE-TRIAGE OPTION is suppressed in `ask`; the default still loops back |
| F64 | ⛔ **The report's build-gate section carried four mutually inconsistent counts** — "5 Python files" beside an enumeration of seven (actual: **8**), "ran four times" against a six-row table, "THREE of six" failures against two marked rows — **and recorded no gate at the tree the PR would open from** | **FIXED** — counts re-derived from `git diff --name-only`, not memory; the `3ac175d` run recorded; and the final gate re-run at the true HEAD |
| F65–F69 | An option label under-promising what it authorizes (it grants past *every* unproven bot, not one); the Branch C condemnation reading as condemning its legitimate sibling uses; a pointer naming a note title that does not exist; two stale reason enumerations (`escalate_ask` guard, and "**The** `loop_back` call site", now three) | ⚠ **I recorded "ALL FIXED" when two had not landed** — round 6 caught it. The first three were fixed in that round; the two enumerations were fixed in the next. The overstatement is the finding worth keeping: a disposition column is a claim about the tree, and this one was written from intent rather than from a re-read |
| F70 | **On the DEFAULT configuration the operator's CONSOLE text names nothing** — the dispatcher's generic loop-back Display carries no bot, cap, size, or remedy, and instructs a replay that cannot clear the block. The three copy-runnable remedies are in `decision.log`, which nothing on that surface points at | ⚠ **DEFERRED — recorded, not fixed.** The Display is the finalize dispatcher's, shared by every loop-back in the phase; re-shaping it is a dispatcher-wide change well outside this plan's declared surface, and doing it here would repeat the scope drift that produced F51–F57. Named as residue so it is known debt rather than an unnoticed gap |

### From the pre-PR verification sub-agent — round 6

Round 6 confirmed **all seven** round-5 blockers closed against the tree, verified the copy-runnable
remedies against the **live argparse**, re-checked **all 14** `configurable:` keys across both skills,
ran the documented advance-disclosure invocation for real, and confirmed plugin-doctor marketplace-wide
`total_issues: 0`. Verdict: **READY TO OPEN THE PR**, with the explicit note that it was *not*
manufacturing a further blocker list to justify the round.

Its remaining items were bookkeeping and latent cross-references. All were fixed rather than carried,
except the two already-deferred ones:

| # | Finding | Disposition |
|---|---|---|
| F71 | ⛔ **I marked F65–F69 "ALL FIXED" when two had not landed** — the `escalate_ask` guard enumeration and the "The `loop_back` call site" singular. **The second consecutive round in which a disposition column overstated the tree** | **FIXED**, and the overstatement recorded above rather than quietly amended |
| F72 | The build-gate run count said "six" against a seven-row table — **the same sentence round 5 flagged (F64), whose disposition claimed it had been re-derived** | **FIXED** — re-derived from the table itself; the count is now eight, including the final gate |
| F73 | The `{final}` gate row was still an unexpanded placeholder while F64's disposition asserted the gate had been re-run at HEAD | **FIXED** — `902a5d9` recorded, and the row now says the final gate records the tree the PR opens from |
| F74 | ⭐ **`automated-review-lifecycle.md` still described the PRE-FIX class-first recovery order** — *"for an `awaitable_window` bot it claims the bot's rate window…"* — in a file **this branch already edited**, ~17 lines from its own hunks. The same stale-consumer class, in the same file, missed by the sweep that touched it | **FIXED** rather than carried: it is a one-line prose correction of exactly the pattern this run keeps reproducing |
| F75 | **My own test docstring re-taught the conflation the fix spent a round removing** — *"'Re-triage now' IS the loop-back"* and *"the loop-back under a friendlier name"*, verbatim the wording deleted from `branch-cleanup.md` that round | **FIXED** — the docstring and both assertion messages now name the remedy/record distinction they exist to protect |
| F76 | No forward pointer from "Branch on `{barrier_mode}` using the SAME two branches" to the structural carve-out nine lines below | **FIXED** |
| F77 | The D0 table rendered `—` for `participated` / `participated_but_empty` where the code mirror asserts booleans | **FIXED** |

### From the build gate — second and third occurrences

| # | Finding | Disposition |
|---|---|---|
| F49 | ⛔ **`./pw verify` exited 0 while reporting `verify: module-tests failed`.** Widening the roster row added a markdown link — and that row's `site:` claim is **machine-resolved from its first markdown link**, so the cross-reference silently re-pointed the derivation guard at a different document, which correctly reported no matching grant there | **FIXED** — the further sites are named in plain text, with the reason recorded inline so the next editor does not re-add a link. The roster enumerates authorization *mechanisms*, one row per `{kind}`, not one row per call site |
| F50 | ⛔ **Process failure, mine.** F49 escaped my pre-commit checks because I ran the `automatic-review` suite and the quality gate while editing `phase-6-finalize` documents — the suite that OWNS those documents was never run. Targeted suites are chosen by where the *tests* live, not by where the *edits* land | **CORRECTED** — the full affected set (`phase-6-finalize`, `automatic-review`, `tools-integration-ci`, `pm-plugin-development`, 3659 tests) now runs before each commit touching these documents |

### From my own independent sweep (found before round 1 returned)

| # | Finding | Disposition |
|---|---|---|
| F23 | D2(c) asks the finding to carry the cap **and the measured diff size**; only the cap was implemented, leaving the gap half-audited | **FIXED** (`b7a7057`) — found by re-reading the plan's own acceptance text against the diff, not by any reviewer |
| F24 | `workflow-integration-github/SKILL.md:137`'s "the cause is advisory … never changes which member" (same instance round 1 later reported as its item 1) | **FIXED** (`b7a7057`), independently and before the report arrived |

### From mutation testing (my own, nine mutations — counted off the rows below)

Not defects — evidence that each D2 case DISCRIMINATES. Each mutation failed exactly the intended
case(s) and nothing else:

| Mutation | Cases that went red |
|---|---|
| A — disable cause-dominance in `_refusal_state` | 7, all in case (a) + the summary and both-commands checks |
| B — reintroduce a wait option in the structural shape | 1, case (b)'s shape test |
| C — default an unstated cap to a number | 3, all in case (c) |
| D — drop the structural member from `_UNPROVEN_STATES` | 3, the blocking-member checks |
| E — fold the structural bucket into `refused` | 1, the summary-distinguishes check |
| F — stop `deficit` reading the cause | 1, the two-commands-agree check |
| G — decouple the disclosure from the registry | 1, the disclosure-derivation check |
| H — reintroduce the barrier's "Re-triage now" option | 2, both barrier-prompt checks |
| I — remove `deficit`'s cap-recovery | 1, and only the **cap-only** agreement case — the parametrization added precisely because the `cause` case cannot observe it |

### From my own closing sweep — the stale-count defect, third and fourth occurrences

| # | Finding | Disposition |
|---|---|---|
| F79 | ⛔ **The mutation-testing heading read "seven mutations" against a NINE-row table, and the D2 deliverable row read "7 mutations" — the FOURTH instance, in a second table.** Found only because F78 prompted a sweep for the same shape elsewhere; the two earlier fixes had each treated it as a one-off in the build-gate sentence rather than as a pattern | **FIXED** in both places — re-derived by counting rows A–I. ⚠ The PR body already said "nine mutations", so the report and the PR contradicted each other and the report was the wrong one |
| F78 | ⛔ **The build-gate run count read "eight" against a NINE-row table — the third instance of one defect** (F64 said "six" against seven rows; F72 said the count "is now eight", re-derived). Each fix restated a literal that the next two rows invalidated, so the count was correct only until the table grew again. The recurring cause is that the sentence carries a number the table already contains | **FIXED** — re-derived by counting the rows at this moment: **ten**, including the merged-tree gate added in this same edit. ⚠ The fix is the same shape as the two that failed, so it will go stale the same way if a row is ever added without re-counting. The durable repair is not to state a count beside a table at all; that is a documentation-standards change beyond this plan's scope and is not made here |

### From the operator

| # | Finding | Disposition |
|---|---|---|
| F80 | ⛔ **I reported `cuioss-review-bot`'s silence as PR-Agent-specific with "cause not determined", on one query and no control.** The operator asked whether that was really the case. It was — but the framing was wrong: a positive control proved the query honest, and a second workflow proved the absence belonged to the **event**, not the bot. **A single negative query, uncontrolled, was presented as a diagnosis** | **FIXED** — participation row rewritten with the controlled evidence; the `silent` verdict was recoverable rather than terminal, and the documented `/review` trigger was posted. ⚠ The contract's own participation rule says the verdict comes from the bodies; it says nothing about deriving the *reason*, which is what decided whether a remedy existed. That gap is Proposal 3 below |

### From CI

**None.** Read back from the PR's own check runs at head `601abf1`: `verify / gate`,
`dependency-review / dependency-review` and `generate-check` all concluded `success`;
`verify / verify` was still `in_progress` at the merge gate (see Contract check below); `auto-merge`
and `Sourcery review` concluded `skipped`. No check reported a failure, so there is no CI finding to
disposition.

### From PR review

**None — and the reason is itself the finding.** No reviewer published a finding against this diff.
Both reviewers that engaged published a refusal notice instead, and the third produced nothing. The
per-reviewer evidence is in **Reviewer participation** below; the section is empty of findings
because there were no reviews, not because reviews were clean.

## Reviewer participation

**Population, derived from configuration.** Read from the `author_login` of each registry doc under
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` — `coderabbit.md`,
`sourcery.md`, `pr-agent.md`. **M = 3.** No list was transcribed; the set is whatever those docs
declare.

**All three comment surfaces were read** before the merge gate, as three separate MCP calls:
`get_comments` (1 comment), `get_reviews` (1 review), `get_review_comments` (0 threads,
`totalCount: 0`). Each verdict below comes from a stored body, never from a check state.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `sourcery-ai` | `rate-limited` | `get_reviews`, review `4944046456`: *"Sorry @cuioss-oliver, your pull request is larger than the review limit of 150000 diff characters"*. A **structural** refusal — the ceiling is a property of the diff, so it does not reopen. ⚠ Its `Sourcery review` **check run concluded `skipped`**, which as a check state is not a verdict and would have read as "nothing to see"; the body is the evidence |
| `coderabbitai` | `rate-limited` | `get_comments`, comment `5302742537`: *"Review limit reached … you've reached your PR review limit, so we couldn't start this review. **Next review available in:** **56 minutes**"*. A **temporal** refusal, current-head-bound — the body names base `622f4484` and head `601abf11` |
| `cuioss-review-bot` | `silent`, then recovered — see below | No artifact on any of the three surfaces, and no `review / review` check. **The PR-open event dispatched no workflow at all** — see the diagnosis below. Recovered by the documented on-demand trigger |

#### `cuioss-review-bot`: the open event dispatched nothing, and only this bot could not recover

My first diagnosis of this row was **wrong in its framing**, and only got corrected because the
operator challenged it. I had recorded it as PR-Agent-specific with the cause undetermined. It is
neither.

**The claim was verified with a positive control first.** `actions_list` for `pr-agent.yml` filtered
to this branch returns `total_count: 0`; the same call against PR #1240's branch returns
`total_count: 1` (run `31887806994`, conclusion `success`), so the filter reports real absence rather
than failing silently.

**The absence is not PR-Agent's.** `python-verify.yml` also subscribes to `pull_request`, and on this
branch it has exactly two runs — `31890971355` at head `601abf1` (14:49:16Z) and `31891858490` at head
`ffde442` (15:08:09Z). Both are later pushes. **Neither is the PR-open event at 14:46:14Z**, whose head
was `d6b6d8d`. So the `opened` event dispatched **no workflow at all**.

**Only PR-Agent stayed dead, and for a documented reason.** `python-verify.yml` also listens to
`synchronize`, so the 14:49 push gave it a second chance. `pr-agent.yml` listens to `opened` /
`reopened` / `ready_for_review` / `issue_comment` and **deliberately not** `synchronize` — its own
comment block records that `synchronize` was added in #1048 and reverted the same day, because
PR-Agent's runner gates that action behind two settings that default off, producing a red check and no
review. That choice is sound; its consequence is that a missed `opened` cannot be recovered by
pushing.

The root cause of the dropped dispatch is **not determined** — the workflow file is present on the
branch, Actions demonstrably works on the branch, no documented skip rule applies, and a job-level
`if:` skip would have produced a run with conclusion `skipped` rather than no run at all. It reads as
a provider-side dispatch miss.

⭐ **A guard-skip and a non-dispatch are different facts that look identical from the comment
surfaces.** Both leave a reviewer `silent`; only the second is recoverable. Distinguishing them needed
the Actions API, which the participation rule does not mention — the verdict came from the bodies as
required, but the *reason* did not, and the reason is what decided the remedy.

**Recovery.** `pr-agent.md` declares `trigger_comment: "/review"`, and the workflow subscribes to
`issue_comment: [created]`. Because this bot was never rate-limited — it simply never got the event —
the trigger was posted rather than the gap accepted.

**Coverage: 0 of 3 at the time of the disclosure**, with `cuioss-review-bot` recovered by on-demand
trigger afterwards. Sourcery stays structurally refused whatever happens; CodeRabbit's window reopens
~15:45Z.

**The § Step 8 condition-4 shortfall disclosure is made here, and restated to the operator in words at
the merge gate, before auto-merge is armed.** It states: coverage **0 of 3**; `sourcery-ai`
rate-limited on a **structural** size ceiling of 150000 diff characters, which waiting does not clear;
`coderabbitai` rate-limited on a **temporal** window reopening in 56 minutes; `cuioss-review-bot`
silent with no workflow run and no cause determined. Per the contract this is a **disclosure and not
a block** — the shortfall changes what the run says, never whether it merges.

⭐ **This PR is a live instance of the defect it fixes, and of the fix's own distinction.** Two
reviewers refused the same diff at the same moment under the two causes this change separates, with
**opposite correct remedies**: sourcery's ceiling is unmoved by waiting, coderabbit's window clears in
56 minutes. Under the pre-change taxonomy both would have resolved by `rate_limit_class` alone and
been offered the same option pair — and sourcery's, at `hard_quota`, would have led with a wait. The
implementation was run against both real notices as first-party evidence:

| Bot | `is_refusal` | cause is `size` | `rate_limit_class` | cap extracted |
|---|---|---|---|---|
| `sourcery-ai` | `True` | `True` | `hard_quota` | `150000 diff characters` |
| `coderabbitai` | `True` | `False` | `awaitable_window` | — |

This also confirms with first-party evidence the cap figure the plan labelled a HYPOTHESIS. ⛔ **No
test was pinned to it** — the plan calls the figure a lead, and the confirmation does not change that.

## Cost

- **Tokens:** **not available to the agent in this session.** The harness exposes no token counter to
  the running agent, and no figure is inferred.
- **Wall-clock:** ~4h40m — first commit on the branch `1481ac1` at `2026-08-15T10:26:05Z` to the
  merge gate at `2026-08-15T15:04Z` (source: `git log --date=iso-strict` and `date -u`). This excludes
  the pre-commit portion of the run (skill loading, plan read, D0 derivation), which produced no
  timestamped artifact.
- **Population:** one Claude Code cloud session's wall-clock, as its own git history records it.
  ⛔ **NOT comparable to a plan-marshall `metrics.toon` total**, which counts an orchestrator-plus-agent
  dispatch tree under plan-marshall's per-task billing boundary. This run has no such tree: it is a
  single interactive session that dispatched six verification rounds and one closing cold read as
  sub-agents inside its own context. The figures cannot be made comparable, so no parity is claimed.

## Contract check (Step 9)

**GitHub access path:** the GitHub MCP server throughout. No `gh` CLI exists in this session, and
Bash cannot reach `api.github.com`. **Branch form:** harness-assigned `claude/review-barrier-deadlocks-6b5sao`,
kept as-is per § Step 2 — this run created no branch, so the closed prefix set did not apply.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | ✅ done | Named in **Skills loaded** above. Every bundle skill loaded by path; none was unobtainable |
| 2 Branch | ✅ done | `claude/review-barrier-deadlocks-6b5sao` exists on `origin`; `git status -sb` reports no divergence. ⚠ Whether the *initial* push preceded the first commit is **not reconstructible** from the artifacts now — it is asserted by neither. What is verified is that nothing is unpushed |
| 3 Plan directory | ✅ done | `doc/plans/review-apparatus/120-review-barrier-deadlocks-on-a-refusing-bot/plan.md` exists, moved with `git mv` in `1481ac1`, numeric prefix preserved, and re-checked at this step to still open with the first-instruction block (verbatim, line 1) |
| 4 Implement | ✅ done | 18 commits; all three deliverables addressed. **17 of 18 carry the trailer** — `601abf1` is a `git merge` commit, which takes no trailer |
| 4 Per-commit gate | ✅ done | Every commit touching `*.py` was preceded by a direct `./pw quality-gate` reporting `ruff`/`mypy`/SPDX clean. ⚠ **F50 records a real gap in how I chose the targeted suite**, not in the gate itself — see Findings |
| 4 Pushed | ✅ done | `git status -sb` reports no `ahead` |
| 5 Build gate | ✅ done | Python-change verdict and ten `./pw verify` runs recorded in **Build gate** above, two of which exited 0 while failing |
| 6 Verification sub-agent | ✅ done | Six rounds plus a closing cold read; findings F1–F79 recorded per instance with dispositions. Ranges, not a total, precisely because a restated count is what F78/F79 record going stale |
| 7 PR cycle | ✅ done | PR **#1241**. All three comment surfaces read as three separate calls. Both stored bodies are refusal notices carrying no finding to fix, so each is dispositioned as a participation verdict rather than a comment; no open, unaddressed comment remains |
| 8 Merge gate | ✅ conditions 1–3 met, armed | Condition 1: `mergeable_state: blocked` at the gate with `verify / verify` **`in_progress`** on head `601abf1` — armed anyway per § Step 8's no-self-wake carve-out, deferring the required-green gate to the merge queue. Condition 2: no open comment. Condition 3: this report is the last pre-merge commit. Condition 4 disclosure made — see **Reviewer participation** |
| 8 Bridge | ✅ done | `git diff --name-only origin/main...HEAD -- doc/plans/` returns exactly this plan's `plan.md` and `report-01.md`. No ledger, no status file, no other plan's directory |
| 9 This check | ✅ done | This table |

**No step is reported as not done.** No `/sync-plugin-cache` is owed: a cloud run neither performs
nor records one (§ Scope and precedence), even though this branch edits `marketplace/bundles/`.

## What have we learned (Step 9)

**Three contract changes are proposed, all from evidence this run produced. None is applied** — the
contract forbids self-approving a change to the contract that governs the run. Each would ship as a
separate `chore/` PR on operator approval, never in this plan's diff.

⭐ Proposal 3 is the one that changed this run's own outcome, and it was found only because the
operator challenged a row I had already written and committed.

### Proposal 1 — the `rate-limited` verdict cannot say whether the shortfall clears

**Evidence from this run.** § Step 7's verdict vocabulary is `reviewed` / `rate-limited` / `silent`.
This PR recorded **two** reviewers as `rate-limited` at the same moment under refusals with **opposite**
properties: `sourcery-ai` hit a 150000-diff-character ceiling that never clears for this diff, while
`coderabbitai` hit a window reopening in 56 minutes. The participation table renders them identically.

That matters because the contract elsewhere assumes the shortfall may clear — § Step 7 instructs
"when its window permits, re-request its review", and condition 4's own example prose distinguishes
"window reopens" from "weekly quota" in *free text* while the vocabulary does not carry it. A reader
of the table alone cannot tell whether a re-trigger is worth attempting. This is precisely the
distinction this plan's deliverable makes machine-readable in `review_completeness`; the lane's own
record does not yet carry it.

**Proposed edit.** Add a required column to the participation table — `Reopens? yes / no / unknown` —
or split `rate-limited` into `rate-limited-temporal` / `rate-limited-structural`. The column form is
the smaller change and keeps the three verdicts stable.

### Proposal 2 — § Step 7 says "both surfaces" where it means three

**Evidence from this run.** Step 7 item 2 reads "Read the actual comment bodies, from **both**
surfaces", and the participation rule repeats "(both surfaces above)" — while the table immediately
between them enumerates **three**, and the paragraph after it states "All THREE surfaces MUST be read"
and names skipping one as the exact false-clean failure the lane exists to prevent. Executing the step
required reconciling "both" against a three-row table to know how many calls to make.

**Proposed edit.** Change both "both" occurrences to "all three". Purely a consistency repair — the
normative rule is already correct and unambiguous three lines away.

### Proposal 3 — a `silent` verdict is treated as terminal, but one kind of silence is recoverable

**Evidence from this run.** § Step 7 defines `silent` as "published **nothing at all**", instructs
that the reason be stated "when one is known", and says an unexplained silence "is recorded as such".
It then routes every non-`reviewed` verdict into the same condition-4 disclosure. That treats all
silence as equivalent — and this run shows it is not.

`cuioss-review-bot` was silent because its **`opened` event dispatched no workflow**. That is
recoverable in one comment: the registry declares `trigger_comment: "/review"` and the workflow
subscribes to `issue_comment`. Had this run followed the contract literally — record the verdict from
the bodies, disclose the shortfall, arm — it would have merged at 0-of-3 with a reviewer that was
available the whole time. It did not merge that way only because the operator questioned the row.

The gap is precise: the verdict is correctly derived from the bodies, but the **reason** cannot be —
the bodies are empty, which is what `silent` means. Distinguishing a rate limit (not recoverable) from
a guard-skip (not recoverable) from a non-dispatch (**recoverable**) needs the Actions API, which the
contract never mentions.

**Proposed edit.** On a `silent` verdict, require one Actions-API check for a workflow run on the head
branch, and split the outcome: **no run at all** → post the registry's `trigger_comment` and re-read
before disclosing; **a run that concluded `skipped` or failed** → record it and disclose. Keep the
disclose-not-block rule unchanged — this adds a cheap recovery attempt before the disclosure, never a
gate.

### What was examined and found sound

The three-surface rule earned itself on this PR: `get_reviews` carried the sourcery refusal,
`get_comments` carried the coderabbit one, and `get_review_comments` was empty. A run reading any one
surface would have recorded the wrong population verdicts. The exit-code warning at both § Step 4 and
§ Step 5 also earned itself three times (F26, F49, and the round-6 gate). Neither needs changing.

## Residue

| Item | Where it should go next |
|---|---|
| **Contract Proposals 1, 2 and 3 above** | Awaiting operator decision. On approval, one `chore/cloud-plan-lane` PR touching only the skill |
| **The dropped `opened` dispatch** | Diagnosed as far as this run can reach: the event fired no workflow, and only `pr-agent.yml` could not recover because it alone declines `synchronize`. The provider-side cause is unreachable from here. Worth watching whether it recurs — if it does, the cheap mitigation is that a lane run posts the documented `/review` trigger whenever a reviewer is `silent` with no workflow run, since that case is recoverable and a rate limit is not |
| **`coderabbitai`'s window reopens ~15:45Z** | A `@coderabbitai review` comment could obtain the review this PR never got. Not attempted: arming auto-merge locks the branch and the queue is expected to land the PR before the window opens. If the operator wants review coverage on this change, the reachable route is a follow-up read of the merged commit, not this PR |
| **Two findings deferred out-of-scope** | Recorded with reasons in **Findings**; both are pre-existing and neither is touched by this diff |
| **Local `/sync-plugin-cache`** | ⛔ **Not owed by this run.** Noted only because this branch edits `marketplace/bundles/`: a developer working locally after the merge syncs their own cache, which is a machine-local concern and not a debt this run tracks |
