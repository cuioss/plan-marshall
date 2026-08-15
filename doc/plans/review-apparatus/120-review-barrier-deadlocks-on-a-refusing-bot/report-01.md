# Run report — 120-review-barrier-deadlocks-on-a-refusing-bot (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/review-barrier-deadlocks-6b5sao`    **PR:** _pending_    **Outcome:** _in progress_

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
| `participated` | no | — | — | none needed |
| `participated_but_empty` | no | — | — | none needed (accounted-for) |
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
| ⭐ `blocked / participation incomplete — STRUCTURAL` | ❌ | **added by this run.** No automatic exit: operator ruling, re-scope, or reclassification. `fail_into_loopback` defers via Branch C; `ask` renders split / accept / disable |
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
| D2 | Tests, each verified discriminating | `eadae3b`, `b7a7057`, `3131bdc` | ✅ 4 cases, 7 mutations |

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

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (5 Python files: the classifier,
the registry, the two producer modules, and three test modules), so the full gate applied.

`./pw verify` ran four times. ⛔ **One of those runs exited 0 while FAILING** — see F37 — so the
outcome below is read from the streamed output, never the exit code:

| At | Result |
|---|---|
| `b7a7057` | SUCCESS — 19702 passed, 14 skipped |
| `3131bdc` | SUCCESS — 19731 passed, 14 skipped, 0 failed (11m27s) |
| `7adf802` | ⛔ **FAILED** — `verify: test-compile failed`, 2 mypy errors, **exit code 0** |
| `97f7493` | SUCCESS — 19740 passed, 14 skipped, 0 failed (10m00s) |
| `6f31a5d` | ⛔ **FAILED** — `verify: module-tests failed`, 1 test, **exit code 0** |
| `1b1b867` | SUCCESS — **19743 passed, 14 skipped**, zero `FAILED` lines, zero sub-step failure lines (9m15s) |

⛔ **`./pw verify` exited 0 while FAILING on THREE of its six runs.** Every one was caught only by
reading the streamed output. Had the exit code been trusted at any of those points, this run would
have opened a PR on a red gate and reported it green — which is precisely why the lane contract makes
"read the output, not the exit code" a rule rather than a suggestion. The two distinct failures were a
test-only type error (invisible to the quality gate, which type-checks production only) and a
derivation-guard failure in a suite my targeted runs had not covered.

Final run's coverage line: `COMPLETE — … mypy(production) [399 files], ruff [marketplace/bundles,
test, .claude], SPDX headers, plugin-doctor [marketplace-wide], mypy(test) [737 files], module-tests
[whole-tree pytest]`. `./pw quality-gate` additionally ran before every commit touching `*.py`, each
reporting `Success: no issues found in 399 source files`, `All checks passed!`, and `SPDX-header check
passed`.

⚠ **The quality gate cannot substitute for the full verify here, and this run proved it.** The gate
type-checks *production* only; the defect at `7adf802` was a test-only type error, visible to
`test-compile`'s `mypy` over the 737-file test tree and to nothing else — not to the gate, and not to
pytest, which ran the offending helpers without complaint.

`git status --porcelain` was empty after both `verify` runs — **no `uv.lock` churn** reached a commit,
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
| F25 | ⭐⭐ **The non-option survived at the DEFAULT surface.** `review_rate_window_await` defaults to `false`, so on the default configuration the leaf's Branch 0 never fires and the dispatcher's structural branch table is **unreachable code**. The prompt an operator actually gets is the **pre-merge barrier's** — untouched by rounds 0–1 — which offered **"Re-triage now → loop back into automatic-review triage"** as option 1, and whose own default mode (`fail_into_loopback`) takes that action **automatically with no prompt at all**. For a size-capped bot a loop-back re-reviews a diff of the same size, the bot re-refuses, and the barrier re-reaches the identical verdict. It escaped every check because it is spelled *"re-triage"*, not *"wait"* — my `_WAIT_OFFER` regex, already widened once for exactly this class of miss, returns `False` on both "re-triage" and "loop back" | **FIXED** (`7adf802`). The barrier derives `{structural_bots}` from `bot_states` it already reads; the loop-back arm is UNAVAILABLE under **both** modes — `ask` gets its own prompt (split / accept / disable, no re-triage, both audit figures named), and `fail_into_loopback` neither loops nor prompts but logs the remedies and defers. **Mutation-verified**: reintroducing the re-triage option fails exactly the two barrier tests |
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
| F48 | A mixed gap (structural + `absent`) suppresses a loop-back that would still have fetched the absent bot's review | ⛔ **I recorded this RESOLVED and it was not — corrected in round 4.** My claim was that F38's precedence rule means "the absent bot is still awaited on the earlier pass". There need be **no earlier pass**: the first barrier entry can have `{count} == 0` with both bots unproven, and the structural gate is `{structural_bots}` non-empty AND `{count} == 0` — it says nothing about other unproven bots. **NOW FIXED** by disclosure rather than by suppression: the prompt renders the full `{unproven_bots}` set and states in as many words that accepting the gap authorizes past every one of them, and the grant's `--granted-over` carries the whole set like its sibling. The loop-back is still suppressed — correctly, since it cannot clear the structural half — but the operator is no longer asked to accept a bot they were never shown |

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

### From mutation testing (my own, seven mutations)

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

### From CI

None yet — the PR is not open at the time this section was written. Any CI or PR-review finding is
recorded in the run's closing update.

## Reviewer participation

_(completed below)_

## Cost

_(completed below)_

## Contract check (Step 9)

_(completed below)_

## What have we learned (Step 9)

_(completed below)_

## Residue

_(completed below)_
