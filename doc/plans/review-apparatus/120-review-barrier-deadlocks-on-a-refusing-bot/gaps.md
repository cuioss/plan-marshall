# Gaps — 120-review-barrier-deadlocks-on-a-refusing-bot

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Emit the refusal CAUSE and CAP on the two producers the recovery sequence reads, so Branch 0 can fire

- **Severity:** major
- **Kind:** incomplete (a fix that landed only in prose)
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:404-408`
    — `_detect_rate_limited_bots` appends `{'bot_kind', 'rate_limit_class', 'eta'}` and nothing else
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py:330-336`
    — `_refusal_record` returns `{'source', 'bot_kind', 'layer', 'eta', 'body'}`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:360-362` — the false claim
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:376-398` — Branch 0, whose
    guard and whose `{cap}` interpolation both depend on the missing fields
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:912-920` — the
    `refusal_structural` envelope's `cap:` / `measured_diff_size:` / `refusal_cause:` fields
  - field contracts to move with it:
    `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md:147`
    and `:163`, `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md:394-398`,
    `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md:225-237`
- **Evidence:** `automatic-review/SKILL.md:360-362` states *"Both carry the same discriminators, so
  this section treats them uniformly: `{bot_kind}`, its `rate_limit_class` …, the refusal's `cause`
  (`size` / `quota`, from the `refused_causes[]` overlay), plus the stated `eta` … and the stated
  `cap` when its `refusal_size_cap_patterns` matched."* Reading both producers shows neither record
  carries a `cause` or a `cap`. `refused_causes[]` / `refused_size_caps[]` exist only on the
  `fetch_findings` return, produced in § "Producer: FIND" (`SKILL.md:589`), which the same section
  says runs **after** it ("skip this entire subsection and proceed directly to 'Producer: FIND'
  below", `:365`). `pr-review-operations.md:257-258` independently confirms the asymmetry:
  `refused_structural` is fed by `fetch_findings` alone, while `rate_limited_bots[]` feeds only the
  three temporal members. Confirmed by reading all five files at `HEAD` = `61a43e53`.
- **Impact:** Branch 0 (`cause: size` → `escalate_ask{reason: refusal_structural}`) has no input and
  cannot fire, so on the opt-in path an `awaitable_window` bot that refuses on size still falls into
  Branch 2 `claim_and_await` — the "LATENT AND UNGUARDED" non-option pairing the run reports as
  closed. It burns the whole `review_rate_window_timeout_seconds` budget on a ceiling waiting cannot
  move, then re-triggers a bot whose answer cannot change. The `refusal_structural` envelope's two
  audit figures are likewise unbindable, so item 7a would render them unresolved. Latent only because
  `review_rate_window_await` defaults to `false` and no `awaitable_window` bot currently declares a
  size pattern — both of which are configuration, not structure.
- **Task:** Add `cause` (via `_github_pr.refusal_cause`) and `cap` (via `_github_pr.refusal_size_cap`)
  to both refusal records — `_detect_rate_limited_bots` has the body in hand at `_github_pr.py:401`,
  and `_refusal_record` at `github_re_review.py:324`. Update the three field contracts and the two
  worked TOON examples to the new shapes. Then either keep `SKILL.md:360-362` (now true) or, if the
  producers are deliberately left thin, rewrite Branch 0 to name the field it really reads and state
  that the branch is unreachable from `rate_limited_bots[]`. Extend
  `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py` with a case that
  feeds a size notice from an `awaitable_window` bot and asserts the record carries `cause: size`.
- **Done when:** both producer records carry `cause` and `cap`; a test asserts that a size refusal
  from an `awaitable_window` bot yields a record whose `cause == 'size'`; and a test asserts that the
  recovery arms `escalate_immediately` (not `claim_and_await`) for that record.
- **Suggested grouping:** automatic-review / refusal-recovery producer seam

## G2 — Bind `{cap}` at the pre-merge barrier, or stop interpolating it

- **Severity:** major
- **Kind:** bug (unbound placeholder in normative prose)
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1089`
    (headless decision-log), `:1113` (`ask` prompt body), `:1149`, `:1150`
    (pending-findings obligations)
  - the binding site that omits it: `branch-cleanup.md:814` (binds `{refusal_size_caps}` as a
    `{bot_kind}:{cap}` **pair list** and `{measured_diff_size}` as a scalar) and `:860` (the read
    instruction, which names only `participation_complete`, `unproven_bots`, `bot_states` — never
    `refusal_causes[]`)
  - the test that pins the unbound placeholder:
    `test/plan-marshall/automatic-review/test_structural_refusal.py:759`
- **Evidence:** a repo-wide search for `{cap}` finds five uses inside the structural section and no
  derivation anywhere in `branch-cleanup.md`, in contrast to `{structural_bots}`, which the same
  section derives explicitly in a fenced `text` block at `:1050`. The document's own standard makes
  this a defect: `:901-904` says `{count}` and `{unproven_bots}` being *"structurally unbound"* means
  *"a prompt body or a `--granted-over` string built from them would report a fiction"*.
  `test_the_barriers_own_prompt_quantifies_the_gap` asserts only `'{cap}' in block`, so it pins the
  placeholder's presence and cannot detect that nothing binds it.
- **Impact:** on the `ask` path the operator is shown `**Declared cap**: {cap}` verbatim, or a value an
  executor improvised — which the workflow-discipline rule forbids. On the default
  `fail_into_loopback` path the same unbound token lands in the decision-log message that the barrier
  itself calls *"the ONLY operator-facing surface on the default configuration"*, and inside the
  `--granted-over` string of a copy-runnable grant. The plan's own D1 obligation — "carries the cap,
  so the gap is auditable" — is therefore satisfied in the payload and lost at the render.
- **Task:** Add a derivation next to `{structural_bots}` at `branch-cleanup.md:1050`, e.g.
  `{cap} = the cap from refusal_causes[] for each bot in {structural_bots}, rendered as
  bot_kind:cap pairs; the literal unknown for a bot whose notice stated no figure` — and extend the
  read instruction at `:860` to name `refusal_causes[]` among the fields read from the
  `review_completeness check` return. Decide the multi-bot rendering explicitly (a pair list, like
  `{refusal_size_caps}`) rather than leaving a scalar for a per-bot value. Strengthen
  `test_the_barriers_own_prompt_quantifies_the_gap` to also assert that every placeholder the prompt
  interpolates is bound somewhere in the document.
- **Done when:** `{cap}` has a stated derivation in `branch-cleanup.md`, that derivation names the
  payload field it reads, and a test asserts the derivation block exists rather than only that the
  placeholder appears.
- **Suggested grouping:** phase-6-finalize / pre-merge barrier

## G3 — Re-model `test_refusal_recovery_arming.py` on the cause-first rule

- **Severity:** major
- **Kind:** missing-test / stale test fixture
- **Where:** `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py:49-58`
  (`_RECOVERY_BY_CLASS`, `_arms`), `:150-152` (class name and docstring), `:60-73` (`_refusal_body`),
  `:176-186` (`test_a_hard_quota_escalates_immediately` docstring)
- **Evidence:** the file models the arming rule as `_RECOVERY_BY_CLASS[bot_registry.rate_limit_class(bot_kind)]`
  with no cause axis, under a class named `TestRecoveryArmingFollowsTheRegistryClass` whose docstring
  reads *"The recovery is chosen by the refusing bot's own declared class"* — the rule this plan
  replaced with "the CAUSE branch first, then the `rate_limit_class` branches"
  (`automatic-review/SKILL.md:367`). `_refusal_body` builds each bot's notice from
  `refusal_patterns[0]`, and for `sourcery` that entry **is** its size pattern
  (`sourcery.md:43`), so the suite already exercises a size refusal and asserts the class-only
  outcome for it. Additionally `test_a_hard_quota_escalates_immediately`'s docstring calls
  `hard_quota` *"A per-PR ceiling"* — the size/quota conflation the plan removed from every other
  consumer. The landing never touched this file (`git show --stat 9e9e9880`).
- **Impact:** the suite passes today only because no `awaitable_window` bot declares a size pattern.
  The moment one does — the exact scenario the structural member exists for — this test asserts
  `claim_and_await`, so the defect would be *blessed by a green test* rather than caught. It is also
  the last surviving restatement of the pre-fix rule in an executable file.
- **Task:** Give `_arms` the cause axis (cause `size` → `escalate_structurally`, else the class map),
  rename the class to name the two-axis rule, add a case for an `awaitable_window` bot fed a
  size-shaped notice asserting it does **not** arm `claim_and_await`, and correct the
  `hard_quota` docstring to describe an account/plan-level quota rather than a per-PR ceiling.
- **Done when:** the arming model in that file consults the cause before the class, and a test would
  fail if an `awaitable_window` bot's size refusal armed `claim_and_await`.
- **Suggested grouping:** automatic-review / refusal-recovery producer seam (pairs with G1)

## G4 — Fix `_extract_rate_limit_eta`'s `group(1) is None` crash and correct the record of why it was deferred

- **Severity:** major
- **Kind:** bug + false-report-claim (unclosed survivor with a wrong proof)
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:347`
  and its docstring promise at `:344-345`; the false justification in
  `doc/plans/review-apparatus/120-review-barrier-deadlocks-on-a-refusing-bot/report-01.md` finding F29
- **Evidence:** the line is
  `return (match.group(1) if match.groups() else match.group(0)).strip()` — identical to the shape
  fixed 105 lines above in the same file (`refusal_size_cap`, `:270-278`), under the identical
  docstring promise that *"a bad registry edit must not break the poll return path"*. F29's stated
  bound is *"latent-only (no registered bot declares `rate_limit_eta_patterns`)"*, which is **false**:
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md:57-60` declares
  three. Latency does hold, but for a fact the report never states and that I had to derive: all
  three declared patterns carry exactly one *mandatory* capturing group, so `group(1)` cannot be
  `None` for them. F29's second bound — "a sibling function this plan does not own" — is also weak:
  the landing edited that file by 110 lines and wrote the twin function.
- **Impact:** any registry edit adding an ETA pattern with an alternation or an optional group (e.g.
  `resets in (?:([0-9]+) minutes|shortly)`) raises `AttributeError` out of the wait-for-comments
  return path, turning a refusal observation into a crashed poll. The recorded reason for deferring
  it would also mislead the next reader into believing the field is unused.
- **Task:** Apply `refusal_size_cap`'s resolution verbatim — a declared group that captured nothing
  yields no figure and moves to the next pattern; the no-group convention keeps `group(0)`. Add the
  two tests that pin it (a non-participating group, and a declared group capturing only whitespace),
  mirroring `test_structural_refusal.py:1206` and `:1243`. Correct the F29 row's stated reason.
- **Done when:** `_extract_rate_limit_eta` cannot raise on a compiling pattern that captures nothing,
  and a test proves it with a monkeypatched registry pattern.
- **Suggested grouping:** workflow-integration-github / refusal extraction

## G5 — Add `--refusal-size-caps` to the `deficit` usage synopsis in `review_completeness.py`

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:116`
- **Evidence:** the synopsis line reads
  `review_completeness.py deficit --plan-id <id> [... ] [--refused-causes [<csv>]] [--min-deficit <n>]`
  with no `--refusal-size-caps`, while `_add_bot_observation_flags(deficit_parser)` (`:1525`) declares
  it at `:1434`. This is the same defect F43 recorded and fixed only in
  `automatic-review/SKILL.md:1003-1010`, which now documents the flag correctly.
- **Impact:** a caller following the module's own `--help`-adjacent synopsis passes the cap to `check`
  and not to `deficit`, making the cap-only cause recovery unreachable from documented usage — the
  one scenario the shared flag exists for, and the cross-command disagreement three documents forbid.
  plugin-doctor validates docs-against-parser, never parser-against-docs, so it stays green.
- **Task:** Add `[--refusal-size-caps [<csv>]]` to the `deficit` synopsis line, in the same position
  it occupies on the `check` line.
- **Done when:** the two synopsis lines differ only by `--triage-ran` / `--measured-diff-size` (check)
  and `--min-deficit` (deficit).
- **Suggested grouping:** automatic-review / review_completeness CLI

## G6 — Stop claiming the size exclusion is "knowable in advance" while the disclosure carries no cap value

- **Severity:** minor
- **Kind:** stale-doc (overstatement) / incomplete deliverable
- **Where:**
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:409-412`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:213-218`,
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:1076-1101`
  (`declared_size_caps`)
- **Evidence:** the contract says *"a diff's size is measurable at PR creation, so the exclusion is
  knowable in advance"*. Running the surface returns only booleans:
  `size_capped_reviewers[3]{bot_kind,structural_cap,cap_extractable}` →
  `coderabbit,false,false` / `pr-agent,false,false` / `sourcery,true,true`. `cap_extractable: true`
  means only that a pattern exists to read a figure **out of a future notice** — the figure itself
  exists nowhere until a refusal happens. The plan's D1 ⭐ asked to "surface each bot's declared size
  **limits**".
- **Impact:** a plan consulting the disclosure at PR creation learns "some reviewer has a ceiling" and
  cannot decide whether its own diff exceeds it, which is the decision the disclosure is framed as
  supporting. The prose promises a comparison the data cannot support.
- **Task:** Either (a) re-word both prose sites to promise what the surface delivers — *which*
  reviewers carry a ceiling, not whether this diff exceeds one — or (b) add an optional
  `declared_cap` registry field (accepting that a declared figure goes stale, which the design note
  at `_github_pr.py:229-237` deliberately rejected) and report it alongside. Option (a) is consistent
  with the shipped design; pick it unless the advance comparison is wanted enough to accept a
  declared constant.
- **Done when:** no shipped document claims the exclusion is decidable in advance unless the
  disclosure emits a comparable figure.
- **Suggested grouping:** automatic-review / advance disclosure

## G7 — Include `refused_structural` in the barrier's widened-member parity sweep

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py:666-686`
  (`test_widened_member_gates_byte_identically_to_absent` and its `pytest.mark.parametrize` list)
- **Evidence:** the parametrisation hand-lists three members — `STATE_PARTICIPATED_STALE`,
  `STATE_NOT_TRIGGERED`, `STATE_DECLINED` — and omits `STATE_REFUSED_STRUCTURAL`. The landing did not
  touch this file, though the plan's Expected surface named it.
- **Impact:** the property "a widened member's merge verdict equals `absent`'s" is unproven for the
  member this plan added, at the barrier — the surface where the member actually matters. The hand-list
  is also the staleness shape D0 rejects: a new blocking member does not join it automatically.
- **Task:** Add a fourth `pytest.param` for `refused_structural` with the observation
  `{'refused_bots': ['pr-agent'], 'refused_causes': {'pr-agent': 'size'}}`; better, derive the
  parametrisation from `_UNPROVEN_STATES` minus the members the scenario cannot produce, so the next
  member joins it without an edit.
- **Done when:** the parity sweep covers `refused_structural`, and adding a blocking member to
  `_UNPROVEN_STATES` either covers it automatically or fails a totality assertion.
- **Suggested grouping:** phase-6-finalize / pre-merge barrier

## G8 — Correct the report's mutation-table row A

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/120-review-barrier-deadlocks-on-a-refusing-bot/report-01.md`
  § "From mutation testing", row A
- **Evidence:** the row reads *"A — disable cause-dominance in `_refusal_state` | 7, all in case (a) +
  the summary and both-commands checks"*. Re-running that mutation against the unchanged tree
  (`test_structural_refusal.py` and `review_completeness.py` are byte-identical to the landing) yields
  **9** failures, and one of them —
  `TestTheCapIsRecorded::test_a_cap_arriving_without_its_cause_still_resolves_structural` — is in case
  (c), which the row's composition does not mention. Rows D (3), E (1) and I (1, cap-only) reproduce
  exactly.
- **Impact:** the discrimination is *stronger* than reported, so nothing is unsafe — but the row is a
  count written beside a result rather than from it, which is the fifth instance of the exact defect
  F64 / F72 / F78 / F79 record. A later reader re-deriving the mutation set from this row will
  under-expect.
- **Task:** Re-run mutation A and restate the row from the observed failure list, naming the case-(c)
  test explicitly.
- **Done when:** the row's count and composition match a re-run.
- **Suggested grouping:** report hygiene / stale-count defect

## G9 — Reconcile the report's finding tables with its own "one row per INSTANCE" rule

- **Severity:** minor
- **Kind:** false-report-claim (self-inconsistency)
- **Where:** `report-01.md` § "Findings" preamble (*"One row per INSTANCE, never bundled."*) against
  rows `F8–F20` (13 instances), `F30–F36` (7), `F44–F47` (4) and `F65–F69` (5)
- **Evidence:** four rows each carry a range of finding ids and a prose enumeration in a single cell,
  directly under the sentence forbidding it. F71 records that one of those bundled rows overstated its
  disposition ("I marked F65–F69 'ALL FIXED' when two had not landed"), which is the failure mode
  bundling produces.
- **Impact:** a bundled row's disposition column is one verdict over many instances, so a partial fix
  reads as complete — the defect F71 caught once and that nothing prevents recurring. It also makes
  the finding count unauditable.
- **Task:** Either split the four ranges into one row per instance, or amend the preamble to state the
  actual rule (one row per instance except for enumerated same-shape sweeps, which carry their member
  list and a per-member disposition).
- **Done when:** the stated discipline and the tables agree.
- **Suggested grouping:** report hygiene

## G10 — Correct two stale statements in `pr-agent.md`

- **Severity:** minor
- **Kind:** stale-doc (first) / bug (second, pre-existing)
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:252-256`
- **Evidence:**
  1. `:253` states unconditionally *"The recovery sequence therefore escalates immediately for this
     class (`escalate_ask{reason: rate_window_not_awaitable}`)"*. Branch 1 is now conditional —
     *"`hard_quota` or `unknown` **(and `cause` is not `size`)**"*
     (`automatic-review/SKILL.md:400`) — so an `unknown`-class bot refusing on size escalates with
     `refusal_structural`, not `rate_window_not_awaitable`. Same stale-consumer class as F30–F36 and
     F74, in a registry doc the plan's Expected surface named.
  2. `:255` instructs *"record its OBSERVED text in `ignore_patterns`"* for a refusal.
     `sourcery.md:111` says the opposite in as many words — a refusal *"is **not** a noise drop and
     lives in the separate `refusal_patterns` list, not in `ignore_patterns`"* — and
     `bot-participation-contract.md:457` defines `ignore_patterns` as an **unconditional drop**.
     `git log -S "record its OBSERVED text in"` dates this to #1041, so it is pre-existing and this
     plan inherited no obligation for it.
- **Impact:** (1) a reader of the PR-Agent registry doc learns the pre-fix escalation rule. (2) an
  editor following `:255` after observing a PR-Agent refusal would file the refusal phrasing as a
  noise pattern, causing the refusal to be dropped rather than branched — the exact failure the
  contract calls out as letting *"a PR whose every required reviewer refused report a clean, complete
  review"*.
- **Task:** Qualify `:253` with "(and the cause is not `size`)" and cross-reference Branch 0; change
  `:255` to `refusal_patterns`, and add the size overlay note (`refusal_size_patterns`) so a future
  observed size refusal is filed on both lists.
- **Done when:** neither sentence contradicts `automatic-review/SKILL.md` § "Rate-limit refusal
  recovery" or `bot-participation-contract.md` § "The three per-bot marker lists".
- **Suggested grouping:** automatic-review / per-bot registry docs

## G11 — Give the default-configuration loop-back console text something to act on (F70, still open)

- **Severity:** minor
- **Kind:** unclosed-survivor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:609-612`
- **Evidence:** the ELSE branch of the loop-back continuation displays a target-named prompt only —
  *"`loop_back_target == "6-finalize"` (inline replay): prompt the user to run `/plan-marshall
  action=finalize` to replay the finalize step."* It carries no bot, cap, measured size, or remedy,
  and it instructs a replay that for a structural refusal reaches the identical verdict. The three
  copy-runnable remedies live in `decision.log` (`branch-cleanup.md:1089`), which nothing on this
  surface points at. Recorded as deferred residue by the run (F70); confirmed still open at `HEAD`.
- **Impact:** on the default configuration (`pre_merge_comment_barrier: fail_into_loopback`,
  `loop_back_without_asking: false`) this prompt is what the operator actually sees when a structural
  refusal blocks the merge, and it tells them to do the one thing that cannot clear it.
- **Task:** Either let a loop-back-emitting step supply a short operator hint that the continuation
  prompt renders (a `display_detail`-derived line plus "see `decision.log` for the remedies"), or add
  a pointer to `decision.log` to the generic prompt. Keep it dispatcher-wide rather than
  barrier-specific, which is why the run correctly declined to do it inline.
- **Done when:** the default-path prompt for a barrier loop-back names where the remedies are, or
  carries them.
- **Suggested grouping:** plan-marshall / finalize dispatcher loop-back continuation
