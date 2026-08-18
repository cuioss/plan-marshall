# Verification — 120-review-barrier-deadlocks-on-a-refusing-bot

**Landed as:** PR #1241, squash commit `9e9e9880`
**Verdict:** verified-with-gaps

The plan's three deliverables are all present in the tree and are real, not relabelling. The
classification change, the cap extraction, the measured-diff-size pairing, the barrier's structural
carve-out, the dispatcher hook's disjoint branch table and the 81-test suite all exist and pass. Four
gaps survive, one of them load-bearing: the leaf's own refusal-recovery Branch 0 — the branch the
report names as the closure of non-option pairing #2 — reads a `cause` discriminator that **neither of
the two producers that feed it emits**, so it can never fire from the data the section names.

## Method

Read in full: `plan.md`, `report-01.md` (both pages, 672 lines).

Ground truth is `HEAD` = `61a43e53` on `claude/review-apparatus-analysis-mcf8md`.

- `git show --stat 9e9e9880` (19 files), `git show 9e9e9880 -- <path>` for the test file,
  `git diff --stat 9e9e9880 HEAD -- <path>` to establish what moved after the landing.
- `git log --oneline 9e9e9880..HEAD -- <paths>` → only `ee78fd91` (#1235) touched
  `branch-cleanup.md` since; its diff was inspected and touches **no** structural-refusal line.
  `review_completeness.py` and `test_structural_refusal.py` are byte-identical to the landing.
- Read in the current tree: `review_completeness.py` (constants, `_refusal_state`,
  `recover_causes_from_caps`, `classify_bot`, `check_completeness`, `check_deficit`, emitters,
  `declared_size_caps`, the whole argparse block), `bot_registry.py` (`refusal_size_patterns`,
  `refusal_size_cap_patterns`, `has_structural_size_cap`), `_github_pr.py`
  (`refusal_cause`, `refusal_size_cap`, `measure_diff_size`, `_extract_rate_limit_eta`,
  `_detect_rate_limited_bots`), `github_pr.py` (the refusal loop, the emit block, the
  `fetch_findings` field contract), `github_re_review.py` (`_refusal_record`), `sourcery.md`,
  `coderabbit.md`, `pr-agent.md`, `bot-participation-contract.md`, `automatic-review/SKILL.md`
  §§ recovery / predicate / canonical invocations, `phase-6-finalize/SKILL.md` item 7a,
  `branch-cleanup.md` §§ 808–1150, `create-pr.md` § advance disclosure,
  `pr-review-operations.md`, `api-contract.md`, `automated-review-lifecycle.md`,
  `test_structural_refusal.py` (all 1306 lines), `test_refusal_recovery_arming.py`,
  `test_pre_merge_barrier.py`, `test_bot_participation_contract.py` (header + guards),
  `.claude/skills/cloud-plan-lane/SKILL.md` §§ Step 7/8.
- Searches run (all over the repo unless scoped): `STATE_|REFUSAL_CAUSE|_UNPROVEN_STATES|
  refusal_size_cap|measured_diff_size|refused_structural`, `{cap}` (whole `skills/` tree),
  `three refusal|four refusal|refusal members|ten members|advisory`, `refused_hard`,
  `150000|150,000` (bundles + test), `rate_limited_bots`, `four escalation|five escalation`,
  `run_gh(`, `list flags`, `participation_complete:`, `Advance disclosure`,
  `record its OBSERVED text in` (via `git log -S`).
- Ran: `uv run python -m pytest test/plan-marshall/automatic-review/test_structural_refusal.py
  -o addopts="" -q` → **81 passed**.
- Ran the advance-disclosure surface for real (`declared_size_caps()` + `_emit_size_caps_toon`) →
  `coderabbit,false,false` / `pr-agent,false,false` / `sourcery,true,true`.
- Derived the terminal-state population in a live interpreter → **11** `STATE_` constants,
  `len(_UNPROVEN_STATES) == 9`.
- **Re-ran four of the report's nine mutations** as pytest plugins loaded from the scratchpad (no
  repository file was modified): A (disable cause-dominance in `_refusal_state`), D (drop
  `refused_structural` from `_UNPROVEN_STATES`), E (fold the structural summary bucket into
  `refused`), I (strip `refusal_size_caps` from `check_deficit`).

No repository file was modified other than this file and `gaps.md`. No commits, no pushes.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | "every terminal state is classified with its remedy set, and each non-option pairing is named" | Gate did not halt; 11 terminal states derived from two sources; two-axis classification; four non-option pairings named | 11 `STATE_` constants confirmed by live derivation; both classification maps in `test_structural_refusal.py:98-138` are total in **both** directions and guarded (`test_every_derived_state_is_classified`); the report's table matches the code mirror row for row | **met** |
| D1 | "a size-capped refusal resolves to the structural member, carries the cap, and is never offered an await — proven by a test per branch" | All three conjuncts met | Conjunct 1 **met** (`_refusal_state` consults the cause first, `review_completeness.py:461`). Conjunct 2 **met** (`refusal_size_cap` + `measured_diff_size`, both reported, unknown never defaulted). Conjunct 3 **met at the two rendering surfaces** (barrier + item 7a) but **prose-only at the leaf recovery**, whose discriminator is not produced — see G1 | **met with a gap** |
| D1 ⭐ | "Surface each bot's declared size limits where a plan can consult them" | `size-caps` + routed from `create-pr.md` | The surface exists, is routed, and runs — but reports two **booleans**, never a limit. No plan can learn a cap value before a refusal exists | **partially met** |
| D2 | four cases, each verified to fail pre-fix | 4 cases, 9 mutations, each failing exactly its intended case(s) | 81 tests pass; four mutations re-run — D, E and I reproduce the reported counts exactly; **A produces 9 failures, not the reported 7**, and one of them is in case (c), which the row does not mention | **met**; the report's row A is inaccurate |

### D0 — the terminal-state population

**CONFIRMED.** `test_structural_refusal.py:80-84` derives `_TERMINAL_STATES` by a `vars()` sweep for
the `STATE_` prefix — not a hand-list — and `test_the_derived_population_is_non_empty` (`:143`) is
asserted first, exactly as D2(d) requires:

> `assert _TERMINAL_STATES, ('zero terminal states were derived from review_completeness — the sweep is vacuous …')`

Both classification maps are asserted **equal** to the derived set (`:172`), so neither a new nor a
retired member can sit outside an arm. A live derivation returns 11 members, matching the report's
"Population size: 11 terminal states". The contract's own `## Failure taxonomy`
(`bot-participation-contract.md:49-68`) carries exactly ten rows plus the stated complement, and
`test_the_contract_documents_every_blocking_member` (`:176`) holds the doc/code closure.

The report's per-member table matches the code mirror on every row, including the two rows F77
corrected (`participated` / `participated_but_empty` render booleans, not `—`).

### D1 conjunct 1 — a size refusal resolves structurally

**CONFIRMED.** `review_completeness.py:459-466`:

```python
if cause == CAUSE_SIZE:
    return STATE_REFUSED_STRUCTURAL
```

evaluated before the class branches. `recover_causes_from_caps` (`:466-500`) is the fail-closed
recovery for a cap that arrives without its cause, is `setdefault`-based (never overrides an observed
`quota`), is one-directional, and is called by **both** `check_completeness` (`:827`) and
`check_deficit` (`:988`) — so the cross-command disagreement F27 found is closed at the shared seam.
`--refused-causes` and `--refusal-size-caps` are both in `_add_bot_observation_flags`
(`:1415`, `:1434`), which both subcommands call (`:1487`, `:1525`).

Mutation A (disabling cause-dominance) turns 9 tests red, including both parametrisations of
`test_check_and_deficit_agree_on_the_member` — the classification is discriminating.

### D1 conjunct 2 — the cap and the measurement travel

**CONFIRMED.** `_github_pr.refusal_size_cap` (`:221-283`) reads the ceiling from the notice through
`refusal_size_cap_patterns`, handles the F2 crash (`match.groups()` truthy on a one-tuple holding
`None`) and the F28 regression (a declared group capturing nothing yields UNKNOWN, never
`group(0)`'s prose). `measure_diff_size` (`:287-320`) returns `''` on every unusable read — never a
zero. `github_pr.py:1174-1175` gates the measurement on the **cause**, not on a successfully-extracted
cap, which is F3's fix:

```python
saw_size_refusal = any(cause == REFUSAL_CAUSE_SIZE for cause in refused_causes.values())
measured_diff_size = measure_diff_size(args.pr_number) if saw_size_refusal else ''
```

`check_completeness` emits `refusal_causes[]{bot_kind,cause,cap}` derived per-record from the
classifier rather than from a second hand-maintained state set (`:884-897`), and the CLI renders an
unstated cap as the literal `unknown` (`:1053`).

### D1 conjunct 3 — never an await

**Met at the two surfaces that render a prompt; prose-only at the leaf.**

- The barrier (`branch-cleanup.md:1045-1142`) — the surface that fires on the default configuration —
  derives `{structural_bots}` from `bot_states`, states the precedence against the pending-findings
  path, separates the *re-triage remedy* from the *`loop_back` record*, forbids Branch C by name,
  names the destructive fall-through, and renders an option list containing split / accept / disable
  and no wait and no re-triage. `test_the_barriers_own_prompt_does_not_offer_a_retriage_remedy`
  (`test_structural_refusal.py:731`) asserts over the `options:` list only.
- Item 7a (`phase-6-finalize/SKILL.md:1361-1394`) carries its own disjoint branch table, renders
  `prompt_options[]` as returned, mints the `barrier-ask-override` grant, and names the required-bot
  scoping its settling claim depends on.
- **The leaf's Branch 0 (`automatic-review/SKILL.md:376-398`) cannot fire from the data the section
  names.** See G1 in `gaps.md` and § Correctness review below.

### D1 ⭐ — advance disclosure

**Partially met.** `declared_size_caps()` (`review_completeness.py:1076-1101`) reports
`{bot_kind, structural_cap, cap_extractable}` — two booleans. Running it yields
`sourcery,true,true`. There is no cap **value** anywhere in the registry (by the deliberate
"the cap is READ, never declared" decision), so a plan can learn *that* a reviewer has a ceiling but
never *what* it is, and therefore cannot answer "will my diff exceed it?" in advance. The contract
nonetheless asserts (`bot-participation-contract.md:411-412`) that

> "a diff's size is measurable at PR creation, so the exclusion is knowable in advance."

which the surface does not deliver. `create-pr.md:213-216` repeats it.

### D2 — tests

**CONFIRMED present and non-vacuous.** `test/plan-marshall/automatic-review/test_structural_refusal.py`
exists (1306 lines, 81 tests, all passing). Every named test in the report exists:
`test_the_structural_recovery_branch_neither_awaits_nor_generates` (`:608`, F7's three separate
negations), `test_the_barriers_own_prompt_offers_the_structural_remedies` (`:716`),
`test_the_default_paths_remedies_are_complete_invocations` (`:850`, F53),
`test_the_structural_prompt_discloses_every_unproven_bot` (`:870`, F48),
`test_a_cap_arriving_without_its_cause_still_resolves_structural` (`:1016`, F4),
`test_a_declared_group_that_captures_nothing_yields_unknown` (`:1228`, F28),
`test_a_non_participating_group_does_not_crash_the_producer` (`:1206`, F2).
The document-slicing helpers are anchored on headings/fences rather than character windows
(`:585-620`), which is the right shape.

`_WAIT_OFFER` (`:558-568`) covers "wait another/for/until", "await the window/reset/limit",
"retry later/in/after", "try again", "back off" — F6's widening is present.

## Report-claim audit

| Claim | Verdict | Evidence |
|---|---|---|
| "Population size: 11 terminal states — 10 closed non-participation members plus `participated`" | **ACCURATE** | Live `vars()` derivation returns 11; contract table has 10 rows |
| D0 two-axis table (11 rows, passable / await-can-succeed) | **ACCURATE** | Row-for-row identical to `_PASSABLE_BY_PLAN_ACTION` / `_AWAIT_CAN_EVER_SUCCEED` (`test_structural_refusal.py:98-138`) |
| "the pre-existing derivation guard in `test_bot_participation_contract.py` already asserts that agreement in both directions" | **ACCURATE** | `test_bot_participation_contract.py:18-46, 120, 152-165` |
| Non-option pairing 1 (`refused_hard` + `size` → `escalate_ask{rate_window_not_awaitable}` leading with a wait) — "This is the defect D1 fixes" | **ACCURATE** | The four temporal reasons still lead with `"Wait another {timeout_seconds}s"` (`phase-6-finalize/SKILL.md:1345`); `refusal_structural` is routed away from that branch (`:1361`) |
| Non-option pairing 2 (`refused_awaitable` + `size` → Branch 2 claim-and-await) — closed by "Recovery gains **Branch 0**" | **OVERSTATED — the fix is prose-only** | Branch 0 exists in `SKILL.md:376`, but `rate_limited_bots[]` is `{bot_kind, rate_limit_class, eta}` (`_github_pr.py:404-408`, and the authoritative contract `api-contract.md:147`) and `refusals[]` is `{source, bot_kind, layer, eta, body}` (`github_re_review.py:330-336`). Neither carries a `cause`. See G1 |
| "Both carry the same discriminators … the refusal's `cause` … plus … the stated `cap`" (`automatic-review/SKILL.md:360-362`) | **FALSE** | Neither producer record contains either field; `refused_causes[]` / `refused_size_caps[]` come from `fetch_findings`, produced in § "Producer: FIND" (`SKILL.md:589`) — **after** the recovery section (`:350`) |
| F1 fixed — item 7a carries the fifth reason with its own disjoint branch table | **ACCURATE** | `phase-6-finalize/SKILL.md:1315-1394`; four tests read that file directly (`test_structural_refusal.py:634-688`) |
| F2 / F28 fixed — cap extraction cannot crash and cannot return prose | **ACCURATE** | `_github_pr.py:270-278`, pinned by `:1206`, `:1228`, `:1243`, `:1251` |
| F3 fixed — measurement gated on the cause | **ACCURATE** | `github_pr.py:1174` |
| F4 fixed — fail-closed one-directional cap→cause recovery | **ACCURATE** | `review_completeness.py:466-500`; `test_a_cause_without_a_cap_is_never_inferred_backwards` (`:1038`) |
| F5 fixed — `_patch_provider` stubs `run_gh` | **ACCURATE** | `test_github_pr.py:99-109` |
| F6 fixed — `_WAIT_OFFER` widened past the literal "wait" | **ACCURATE** | `test_structural_refusal.py:558-568` |
| F7 fixed — all three negations asserted separately | **ACCURATE** | `test_structural_refusal.py:614-621` |
| F8–F20 "ALL FIXED" (thirteen stale statements) | **ACCURATE for every instance checked** | `workflow-integration-github/SKILL.md:137` now says "STATE-DETERMINING, not advisory"; `bot-participation-contract.md:451` now says the size overlay "selects the `refused_structural` member"; `--refused-bots` help text (`review_completeness.py:1366-1372`) names the cause-first rule; the `fetch_findings` docstring enumerates `refused_size_caps` (`github_pr.py:829-836`) |
| F21 fixed — a workflow step routes a plan to the disclosure | **ACCURATE** | `create-pr.md:213-231` |
| F22 rejected — a cloud run neither performs nor owes a `/sync-plugin-cache` | **ACCURATE** | `CLAUDE.md` § Standalone Plan Lane states it in as many words |
| F25 fixed — the barrier's own prompt, mutation-verified | **ACCURATE** | `branch-cleanup.md:1096-1137`; `test_the_barriers_own_prompt_does_not_offer_a_retriage_remedy` + `…_offers_the_structural_remedies` |
| F26 fixed — recovery scoped to required bots | **ACCURATE** | `automatic-review/SKILL.md:369`; named in item 7a's settling claim (`phase-6-finalize/SKILL.md:1392`) |
| F27 fixed — `--refusal-size-caps` on the shared flag block | **ACCURATE** | `review_completeness.py:1434` inside `_add_bot_observation_flags`; mutation I reproduces "exactly the cap-only case, and nothing else" (measured: 1 failure, `[cap-only-…]`) |
| F29 deferred — "latent-only (**no registered bot declares `rate_limit_eta_patterns`**)" | **FALSE** | `coderabbit.md:57-60` declares three. The bug at `_github_pr.py:347` is still live, and still latent — but for a different reason I had to derive myself (all three declared patterns carry exactly one *mandatory* group). See G4 |
| F29 deferred — "fixing it would widen the diff into a sibling function this plan does not own" | **OVERSTATED** | The plan wrote `refusal_size_cap` in the same file ~100 lines above (`_github_pr.py:221` vs `:326`), and edited that file by 110 lines |
| F37 / F49 — two `./pw verify` runs exited 0 while failing | **UNVERIFIABLE** | A property of runs, not of the tree. The two fixes they name are present |
| F43 fixed — the `deficit` canonical block documents `--refusal-size-caps` | **ACCURATE for `SKILL.md`, INCOMPLETE in the tree** | `automatic-review/SKILL.md:1003` carries it; the module's own usage synopsis (`review_completeness.py:116`) still omits it. See G5 |
| F48 fixed — the prompt renders the full `{unproven_bots}` set | **ACCURATE** | `branch-cleanup.md:1116`, `:1121-1125`; pinned at `test_structural_refusal.py:870` |
| F51–F57 fixed | **ACCURATE** | Split option points at the loop-back (`branch-cleanup.md:1139`); no `--outcome done` in the structural commands (pinned `:813`); remedies complete (pinned `:850`); mutex re-acquire named on the disable arm (`:1142`); pending-findings section carries both obligations inline (`:1147-1150`); `_add_bot_observation_flags` says "nine list flags" and nine are declared (counted) |
| F58–F63 fixed | **ACCURATE** | The two senses of "loop-back" separated (`branch-cleanup.md:1059`); the knob description rewritten (`:50`); "never re-**PROMPTS**" (`phase-6-finalize/SKILL.md:1365`); "return control to the finalize dispatcher" + the destructive-fall-through warning (`branch-cleanup.md:1092`) |
| F70 deferred — the default-configuration console text names nothing | **ACCURATE, and still open** | `plan-marshall/workflow/execution.md:609-612` renders a target-named prompt carrying no bot, cap, size or remedy |
| Build gate: "8 files", enumerated | **ACCURATE** | `git show --stat 9e9e9880` lists exactly those eight `*.py` paths |
| Build gate: "ran **ten times**" against a ten-row table | **ACCURATE** | Ten rows counted |
| Mutation table: nine rows A–I, heading "nine mutations" | **ACCURATE** as a count | Nine rows |
| Mutation row A: "7, all in case (a) + the summary and both-commands checks" | **INACCURATE** | Re-run: **9** failures, including `TestTheCapIsRecorded::test_a_cap_arriving_without_its_cause_still_resolves_structural`, which is case (c). Discrimination is *stronger* than claimed, but the row is wrong in both count and composition — the fifth instance of the stale-count defect the report itself keeps recording |
| Mutation rows D (3), E (1), I (1, cap-only) | **ACCURATE** | Re-run reproduces each exactly |
| "⛔ **No test pins the real provider figure** … every cap assertion uses a synthetic notice" | **ACCURATE in substance** | The literal `150000` does appear in this landing's own test fixtures (`test_github_pr.py:2599`, and asserted at `:2671`, `:2845`), but only as a value extracted from a **synthetic** body defined in the test — a provider budget change cannot fail it. The claim's meaning holds; the literal's presence is worth knowing |
| "One row per INSTANCE, never bundled" | **FALSE as applied** | F8–F20 (13), F30–F36 (7), F44–F47 (4) and F65–F69 (5) are each one bundled row. The report violates its own stated discipline four times in the section that states it |
| Reviewer-participation rows, the dropped `opened` dispatch, the `/review` recovery, run ids, timings | **UNVERIFIABLE from the tree** | PR-runtime facts; not checked against the provider |
| Contract check Step 8 "Bridge: `git diff --name-only origin/main...HEAD -- doc/plans/` returns exactly this plan's `plan.md` and `report-01.md`" | **ACCURATE** | `git show --stat -M 9e9e9880 -- doc/plans` shows exactly a `plan.md` rename (0 changes) and `report-01.md` |

## Survivor audit

| Survivor | Stated (a)-proof / (b)-bound | Holds? |
|---|---|---|
| **F29** — `_extract_rate_limit_eta` carries the identical `group(1) is None` crash under the identical false docstring promise | (a) "latent-only (no registered bot declares `rate_limit_eta_patterns`)"; (b) "out of this plan's declared surface … a sibling function this plan does not own" | **(a) does not hold as stated** — `coderabbit.md:57-60` declares three ETA patterns. The bug is nonetheless still latent, by a fact the report never states: all three declared patterns carry exactly one *mandatory* capturing group, so `group(1)` cannot be `None` for them. I verified this by reading the three patterns. **(b) is weak** — the twin function the plan *did* fix lives in the same file 105 lines above. The survivor is real, still open at `_github_pr.py:347`, and its recorded justification is wrong |
| **F70** — on the default configuration the operator's console text names nothing | (b) "the Display is the finalize dispatcher's, shared by every loop-back in the phase; re-shaping it is a dispatcher-wide change well outside this plan's declared surface" | **Holds.** `plan-marshall/workflow/execution.md:609-612` is the shared loop-back continuation prompt, branching only on `loop_back_target` and naming no barrier detail. Re-shaping it would indeed be dispatcher-wide. Still open |

## Correctness review

**C1 — the leaf recovery's cause discriminator is not produced (major).**
`automatic-review/SKILL.md:360-362` promises both refusal producers carry the cause and the cap:

> "Both carry the same discriminators, so this section treats them uniformly: `{bot_kind}`, its
> `rate_limit_class` …, the refusal's `cause` (`size` / `quota`, from the `refused_causes[]`
> overlay), plus the stated `eta` … and the stated `cap` when its `refusal_size_cap_patterns`
> matched."

Neither does:

- `_github_pr._detect_rate_limited_bots` appends `{'bot_kind', 'rate_limit_class', 'eta'}`
  (`_github_pr.py:404-408`), and its docstring says so (`:369`). The authoritative field contract
  agrees: `rate_limited_bots[N]{bot_kind,rate_limit_class,eta}`
  (`tools-integration-ci/standards/api-contract.md:147`, restated
  `workflow-integration-github/SKILL.md:398`).
- `github_re_review._refusal_record` returns `{'source', 'bot_kind', 'layer', 'eta', 'body'}`
  (`github_re_review.py:330-336`).

`refused_causes[]` and `refused_size_caps[]` exist only on the `fetch_findings` return, produced in
§ "Producer: FIND" (`automatic-review/SKILL.md:589`) — **after** § "Rate-limit refusal recovery"
(`:350`), which the SKILL itself confirms ("skip this entire subsection and proceed directly to
'Producer: FIND' below"). `pr-review-operations.md:257-258` states the same asymmetry honestly:
`refused_structural` is fed by `fetch_findings` alone, while `rate_limited_bots[]` feeds only the
three temporal members.

Consequences, all confirmed by reading:

1. Branch 0's guard (`cause: size`) has no input on the recovery path, so an `awaitable_window` bot
   refusing on size still falls to Branch 2 `claim_and_await` — precisely non-option pairing #2,
   which the report records as closed.
2. The `refusal_structural` envelope's `cap:` and `measured_diff_size:` fields
   (`automatic-review/SKILL.md:918-920`) have no source at emit time, so item 7a's two audit figures
   would render unbound.
3. Because `review_rate_window_await` defaults to `false`, none of this fires on a default install —
   which is exactly the reasoning F25 used, and exactly why it survived six review rounds.

**C2 — `{cap}` is an unbound placeholder at the barrier (major).** It is interpolated at
`branch-cleanup.md:1089` (the headless decision-log), `:1113` (the `ask` prompt body), `:1149` and
`:1150` (the pending-findings obligations). The barrier binds `{refusal_size_caps}` — *a list of
`{bot_kind}:{cap}` pairs* — and the scalar `{measured_diff_size}` at `:814`, and explicitly derives
`{structural_bots}` at `:1050`; it never derives `{cap}`. Its read instruction at `:860` names only
`participation_complete`, `unproven_bots` and `bot_states` — not `refusal_causes[]`, the field that
actually carries the cap. The document's own standard makes this a defect rather than a nit
(`:901-904`):

> "**Nothing can describe the gap.** `{count}` and `{unproven_bots}` are structurally unbound on an
> UNKNOWN path … so a prompt body or a `--granted-over` string built from them would report a fiction"

`{cap}` is additionally per-bot while the placeholder is scalar, so with two structural bots there is
no single correct value. `test_the_barriers_own_prompt_quantifies_the_gap`
(`test_structural_refusal.py:759`) asserts `'{cap}' in block` — it pins the *presence of the unbound
placeholder*, so it cannot catch this.

**C3 — the printed grant remedy carries a HEAD that its own caveat says may be wrong (minor).**
`branch-cleanup.md:1089` interpolates `--head {sha}` (bound at `:999`, the authorization check) into
a "complete as written" copy-runnable remedy, then adds "this barrier re-resolves HEAD after an
unconditional rebase, so grant against the HEAD the next pass resolves". When the base advanced, an
operator copying the printed command verbatim mints a grant that the next pass reports lapsed. The
hazard is disclosed; the command is still the wrong one to copy.

**C4 — no fail-open, no non-idempotence, no unreachable predicate found in the Python.** I checked:
`refusal_causes_out`'s re-derivation (`review_completeness.py:884-897`) correctly excludes a bot
carrying a cause whose classified state is not the refusal state that pair maps to (a participant, an
`absent` bot, a cap for a bot that never refused); `recover_causes_from_caps` cannot invent a cap from
a cause; `measure_diff_size` returns `''` on every failure path and never `0`; `refusal_size_cap`
strips only commas, which is required by the comma-separated CLI transport, and a colon-bearing cap
survives `parse_causes`' first-colon split (pinned at `:957`); `_refusal_state` is total and
fail-closed on an unrecognised class. `classify_bot`'s branch order puts the refusal branch after
proven participation and before `declined` / `participated_stale`, which matches every document.

**C5 — the liveness question.** The barrier cannot block forever on the structural member. On
`fail_into_loopback` it records `loop_back` to `6-finalize`; re-entry re-runs § "Authorization check"
*before* the disposition (`branch-cleanup.md:1066`), and the run is bounded by `max_iterations` and by
`loop_back_without_asking: false` halting after one pass (`:1094`). The one residual futile shape is
**not** new: if the producer's `refused_causes[]` is empty or malformed (the documented empty-fallback
at `:814`), a size refusal resolves to a temporal member, the structural carve-out never fires, and
the pre-fix loop-back is taken — bounded, but silent. `recover_causes_from_caps` closes only the
cap-survives-but-cause-lost half of that.

## Completeness review

- **`test_refusal_recovery_arming.py` was not updated and still models arming as class-only.**
  `_RECOVERY_BY_CLASS` (`:49-53`) and `_arms` (`:56-58`) contain no cause axis; the class is named
  `TestRecoveryArmingFollowsTheRegistryClass` (`:150`) with the docstring *"The recovery is chosen by
  the refusing bot's own declared class"* — the rule this plan replaced. `_refusal_body`
  (`:60-73`) feeds each bot `refusal_patterns[0]`, which for `sourcery` **is its size pattern**, so
  the suite already exercises a size refusal and asserts the class-only outcome for it. It passes
  today only because no `awaitable_window` bot declares a size pattern. Its
  `test_a_hard_quota_escalates_immediately` docstring additionally calls `hard_quota` *"a per-PR
  ceiling"* — the size/quota conflation the plan's finding 3 removed elsewhere. This is the test-fixture
  consumer kind, and the sweep missed it.
- **The module's own usage synopsis contradicts the parser.**
  `review_completeness.py:116` documents `deficit` without `--refusal-size-caps`, while
  `_add_bot_observation_flags(deficit_parser)` (`:1525`) declares it. Same class as F43, fixed only
  in `SKILL.md`.
- **`test_pre_merge_barrier.py` was named in the plan's Expected surface and never touched.** Its
  `test_widened_member_gates_byte_identically_to_absent` (`:686`) hand-lists three widened members
  (`participated_stale`, `not_triggered`, `declined`) and omits `refused_structural` — a hand-list
  that a new blocking member must join, which is the exact staleness shape D0 rejects.
- **`pr-agent.md:253` restates the recovery unconditionally**: "The recovery sequence therefore
  escalates immediately for this class (`escalate_ask{reason: rate_window_not_awaitable}`)". Branch 1
  is now conditional — "`hard_quota` or `unknown` **(and `cause` is not `size`)**"
  (`automatic-review/SKILL.md:400`). Same stale-consumer class as F30–F36 and F74, in a registry doc
  the plan's Expected surface named.
- **Pre-existing, adjacent, and worth a later plan:** `pr-agent.md:255` instructs *"record its
  OBSERVED text in `ignore_patterns`"* for a refusal. `sourcery.md:111` states the opposite in as many
  words — a refusal "lives in the separate `refusal_patterns` list, **not** in `ignore_patterns`" —
  and `ignore_patterns` is an unconditional noise **drop** (`bot-participation-contract.md:457`).
  `git log -S` dates it to #1041, so this landing neither caused nor inherited an obligation for it.
- **Everything else in the F8–F20 / F30–F36 sweep that I re-checked is genuinely fixed** —
  `workflow-integration-github/SKILL.md:137`, `bot-participation-contract.md:451`,
  `pr-review-operations.md:276`, `automated-review-lifecycle.md:32` (F74),
  the `review_rate_window_await` and `pre_merge_comment_barrier` `configurable:` descriptions,
  the 5d carve-out's removed enumeration (`phase-6-finalize/SKILL.md:1120`), the `escalate_ask` guard
  invariant (`:1560`), and the merge-authorization roster row's deliberately link-free secondary
  sites (`branch-cleanup.md:121`).

## Out-of-scope compliance

**Compliant.** Checked each of the plan's five out-of-scope items against the diff and the tree:

- *Re-implementing the refused-versus-unproven split* — untouched; `_refusal_state`'s class arms are
  the shipped ones.
- *Building a coverage-gap acceptance mechanism* — none built. The landing adds two **call sites** of
  the already-shipped `barrier-ask-override` / `review-barrier-gap` grant
  (`branch-cleanup.md:1140`, `phase-6-finalize/SKILL.md:1368-1372`) and widens the roster row that
  enumerates them (`branch-cleanup.md:121`). Using a shipped mechanism at a new site is not building
  one, and D1's "accept" remedy requires exactly this.
- *Re-litigating the deadlock framing* — the report explicitly confirms the refutation instead.
- *Splitting large PRs as the remedy* — offered as an operator option only; the workflow says in as
  many words that it "never performs the split itself" (`phase-6-finalize/SKILL.md:1362`).
- *Making the barrier block on a coverage gap* — no new gate. `_UNPROVEN_STATES` gains the member, so
  a structural refusal blocks exactly as its siblings do (pinned at `test_structural_refusal.py:234`);
  what changed is which remedy is offered.

The landing did touch files beyond the plan's "Expected surface" (`bot_registry.py`, `_github_pr.py`,
`github_pr.py`, `phase-6-finalize/SKILL.md`, `create-pr.md`, `pr-review-operations.md`,
`workflow-integration-github/SKILL.md`, `automated-review-lifecycle.md`). "Expected surface" is a
scoping hint rather than a prohibition, and each of those edits is a consumer of the changed contract,
so this is not a scope violation.

## Residue status

| Residue item | Status |
|---|---|
| Contract Proposals 1, 2 and 3 (awaiting operator decision) | **CLOSED by later work.** `.claude/skills/cloud-plan-lane/SKILL.md` now carries the `Reopens? yes / no / unknown` column (`:1241-1249`, `:1742`), reads "all three surfaces above" (`:1201`), and carries the silent-recovery rule with the `⛔ Query by event, never by head branch` prohibition (`:1260-1280`) |
| The dropped `opened` dispatch | **Open by nature** — a provider-side observation with no in-tree artifact |
| `coderabbitai`'s window reopens ~15:46Z | **Moot** — the PR merged |
| Two findings deferred out-of-scope (F29, F70) | **Both still open.** F29 at `_github_pr.py:347`; F70 at `plan-marshall/workflow/execution.md:609-612` |
| Local `/sync-plugin-cache` — "not owed by this run" | **Correct** per `CLAUDE.md` § Standalone Plan Lane |

## Summary

**Gaps by severity: 1 blocker-adjacent major that changes behaviour (G1), 3 further major (G2–G4),
7 minor (G5–G11). No refuted deliverable.**

The plan landed real work. `refused_structural` is a first-class member decided by an observed cause
that dominates the per-bot class, the cap is read from the notice rather than declared and is paired
with a measured diff size, and the pre-merge barrier — the surface that actually fires on a default
install — renders split / accept / disable with no wait and no re-triage, backed by an 81-test suite
whose discrimination I re-verified on four of the nine reported mutations. The three claimed
non-option surfaces were each reached, and the report is unusually honest about its own six rounds of
self-inflicted regressions. What survives is one structural incompleteness and a cluster of
placeholder/consumer misses: the leaf's Branch 0 branches on a `cause` that **neither producer feeding
it emits** and that is not produced until a later stage, so the "no await ever" property is real at
the two prompt-rendering surfaces and prose-only at the opt-in leaf; `{cap}` is interpolated five
times at the barrier and bound nowhere, with a test that pins its unbound presence; the recovery-arming
test still asserts the class-only rule this plan replaced; and the survivor F29's recorded proof is
factually wrong even though its conclusion happens to hold.
