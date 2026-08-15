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

The barrier's own dispositions were classified alongside the per-bot members: `clean` (merges),
`blocked/participation-incomplete` and `blocked/pending-findings` (both authorizable), and the two
`UNKNOWN` branches (never authorizable — but not deadlocks either: their exit is to make the failed
read succeed, which is an action).

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

`./pw verify` — **SUCCESS**, run twice: once at `b7a7057` (19702 passed, 14 skipped) and again after
the round-1 review fixes at `3131bdc` (**19731 passed, 14 skipped, 0 failed**, 11m27s). Read from the
streamed tool output, not the exit code: `coverage: COMPLETE — … mypy(production) [399 files], ruff,
SPDX headers, plugin-doctor [marketplace-wide], mypy(test) [737 files], module-tests [whole-tree
pytest]`. `./pw quality-gate` additionally ran before every commit touching `*.py`, each reporting
`Success: no issues found in 399 source files`, `All checks passed!`, and `SPDX-header check passed`.

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
