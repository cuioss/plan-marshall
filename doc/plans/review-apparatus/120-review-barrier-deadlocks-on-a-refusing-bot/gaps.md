# Gaps — 120-review-barrier-deadlocks-on-a-refusing-bot

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis. **Eleven entries: 2 major (G1–G2), 9 minor (G3–G11).**

## G1 — Emit the refusal CAUSE and CAP on the two producers the recovery sequence reads, so Branch 0 can fire

- **Severity:** major
- **Kind:** incomplete (a fix that landed only in prose)
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:403-409`
    — `_detect_rate_limited_bots` appends `{'bot_kind', 'rate_limit_class', 'eta'}` and nothing else
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py:331-337`
    — `_refusal_record` returns `{'source', 'bot_kind', 'layer', 'eta', 'body'}`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:361-364` — the false claim
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:376-398` — Branch 0, whose
    guard and whose `{cap}` interpolation both depend on the missing fields
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:918-920` — the
    `refusal_structural` envelope's `refusal_cause:` / `cap:` / `measured_diff_size:` fields
  - field contracts to move with it:
    `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md:147`
    and `:163`, `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md:394-398`,
    `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md:225-237`
- **Evidence:** `automatic-review/SKILL.md:361-364` states *"Both carry the same discriminators, so
  this section treats them uniformly: `{bot_kind}`, its `rate_limit_class` …, the refusal's `cause`
  (`size` / `quota`, from the `refused_causes[]` overlay), plus the stated `eta` … and the stated
  `cap` when its `refusal_size_cap_patterns` matched."* Reading both producers shows neither record
  carries a `cause` or a `cap`. `refused_causes[]` / `refused_size_caps[]` exist only on the
  `fetch_findings` return, produced in § "Producer: FIND" (`SKILL.md:589`), which the same section
  says runs **after** it ("skip this entire subsection and proceed directly to 'Producer: FIND'
  below", `:366`). `pr-review-operations.md:257-258` independently confirms the asymmetry:
  `refused_structural` is fed by `fetch_findings` alone, while `rate_limited_bots[]` feeds only the
  three temporal members. The one body-bearing record — `refusals[]`'s `body` — is a truncated
  `_body_excerpt` (`github_re_review.py:142-147`) and no instruction tells the leaf to re-derive a
  cause from it. Confirmed by reading all six files at `HEAD` = `61a43e53`.
- **Impact:** two distinct consequences, and the first is **not** hypothetical.
  1. **Non-option pairing #1 — the defect D1 was written to remove — survives on the opt-in path for
     a bot in the tree today.** With `review_rate_window_await == true` and Sourcery's size refusal
     detected through `rate_limited_bots[]`, Branch 0's `cause: size` guard has no input, so the
     refusal falls to Branch 1 (`hard_quota`) and returns
     `escalate_ask{reason: rate_window_not_awaitable}`. Item 7a routes that reason into the four
     TEMPORAL reasons' shared option set, whose first option is literally
     `"Wait another {review_rate_window_timeout_seconds}s"` (`automatic-review/SKILL.md:902`,
     `phase-6-finalize/SKILL.md:1345`) — a wait offered on a diff-size ceiling, which is the report's
     own non-option pairing #1 verbatim. No hypothetical registry entry is needed: Sourcery declares
     both the size pattern and `rate_limit_class: hard_quota` (`sourcery.md:43-49`).
  2. **Non-option pairing #2 stays unguarded.** An `awaitable_window` bot that refuses on size still
     falls to Branch 2 `claim_and_await`, burning the whole `review_rate_window_timeout_seconds`
     budget on a ceiling waiting cannot move, then re-triggering a bot whose answer cannot change.
     This half additionally requires a bot declaring `awaitable_window` **and** a size pattern, which
     no registry doc does today.

  The `refusal_structural` envelope's two audit figures are likewise unbindable, so item 7a would
  render them unresolved. Both consequences are gated on `review_rate_window_await`, which defaults
  to `false` — a configuration default, not a structural barrier, and one an operator may flip.
- **Task:** Add `cause` (via `_github_pr.refusal_cause`) and `cap` (via `_github_pr.refusal_size_cap`)
  to both refusal records — `_detect_rate_limited_bots` has the body in hand at `_github_pr.py:400`,
  and `_refusal_record` takes it as its first parameter (`github_re_review.py:277`). Update the
  three field contracts and the two worked TOON examples to the new shapes. Then either keep `SKILL.md:361-364` (now true) or, if the
  producers are deliberately left thin, rewrite Branch 0 to name the field it really reads and state
  that the branch is unreachable from `rate_limited_bots[]`. Extend
  `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py` with a case that
  feeds a size notice from an `awaitable_window` bot and asserts the record carries `cause: size`.
- **Done when:** both producer records carry `cause` and `cap`; a test asserts that a size refusal
  from an `awaitable_window` bot yields a record whose `cause == 'size'`; a test asserts that the
  recovery arms `escalate_immediately` (not `claim_and_await`) for that record; and a test asserts
  that a `hard_quota` bot's **size** refusal escalates with `reason: refusal_structural`, not
  `rate_window_not_awaitable`.
- **Suggested grouping:** automatic-review / refusal-recovery producer seam

## G2 — Fix `_extract_rate_limit_eta`'s `group(1) is None` crash, and correct the record of why it was deferred

- **Severity:** major
- **Kind:** bug (latent crash under a false docstring promise) + false-report-claim
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:347`
  and its docstring promise at `:337-338`; the false justification in
  `doc/plans/review-apparatus/120-review-barrier-deadlocks-on-a-refusing-bot/report-01.md` finding F29
- **Evidence:** the line is
  `return (match.group(1) if match.groups() else match.group(0)).strip()` — identical to the shape
  fixed 105 lines above in the same file (`refusal_size_cap`, `:221`, whose resolution is
  `:270-283`), under
  the identical docstring promise that *"a bad registry edit must not break the poll return path"*
  (`:337-338`). F29's stated bound is *"latent-only (no registered bot declares
  `rate_limit_eta_patterns`)"*, which is **false**:
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md:57-60` declares
  three. Latency does hold, but for a fact the report never states and that had to be derived: all
  three declared patterns carry exactly one *mandatory* capturing group, so `group(1)` cannot be
  `None` for them. F29's second bound — "a sibling function this plan does not own" — is also weak:
  the landing edited that file by 110 lines and wrote the twin function in it.
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

## G3 — Give `{cap}` a stated derivation at the pre-merge barrier

- **Severity:** minor
- **Kind:** stale-doc (a placeholder with no derivation, and scalar for a per-bot value)
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1089`
    (headless decision-log, twice), `:1113` (`ask` prompt body), `:1149`, `:1150`
    (pending-findings obligations) — five interpolations at four sites
  - the two places the cap's source IS named: `:814` (retains `{refusal_size_caps}`, defined as
    `{bot_kind}:{cap}` **pair list**, plus the scalar `{measured_diff_size}`) and `:864` ("name BOTH
    figures … the **cap** from `refusal_causes[]`")
  - the contrast: `{structural_bots}`, which the same section derives explicitly in a fenced `text`
    block at `:1050`
  - the test that pins the placeholder rather than its binding:
    `test/plan-marshall/automatic-review/test_structural_refusal.py:759`
- **Evidence:** the barrier binds `{refusal_size_caps}` and `{measured_diff_size}` at `:814` and names
  `refusal_causes[]` as the cap's source at `:864`, but the bare token `{cap}` is never assigned — it
  appears only as a sub-token of the `{bot_kind}:{cap}` pair-rendering description at `:814`. So the
  value is available; what is missing is the derivation step from the pair list to the token the
  prompt actually interpolates, and a decision on how a **scalar** token renders when
  `{structural_bots}` holds two bots. The naming compounds it: the payload field is spelled
  `refused_causes[]` / `refused_size_caps[]` on the `fetch_findings` return (`:814`) and
  `refusal_causes[]` on the `review_completeness check` return (`:864`), and neither line says which
  one `{cap}` is drawn from. `test_the_barriers_own_prompt_quantifies_the_gap` asserts only
  `'{cap}' in block`, so it pins the placeholder's presence and cannot detect that nothing binds it.
- **Impact:** an executor rendering `**Declared cap**: {cap}` has to improvise the mapping from the
  pair list to a scalar, which the workflow-discipline rule forbids; with two structural bots there
  is no single correct value. The same token lands in the decision-log message the barrier itself
  calls *"the ONLY operator-facing surface on the default configuration"* and inside the
  `--granted-over` string of a copy-runnable grant. This is **not** the `:901-904` "structurally
  unbound … would report a fiction" case — that standard is about the UNKNOWN path, where the
  producer never emitted the value at all; here it did.
- **Task:** Add a derivation next to `{structural_bots}` at `branch-cleanup.md:1050`, e.g.
  `{cap} = the cap from refusal_causes[] for each bot in {structural_bots}, rendered as
  bot_kind:cap pairs; the literal unknown for a bot whose notice stated no figure` — and extend the
  read instruction at `:860` to name `refusal_causes[]` among the fields read from the
  `review_completeness check` return, so `:864`'s instruction has a matching read. Decide the
  multi-bot rendering explicitly (a pair list, like `{refusal_size_caps}`) rather than leaving a
  scalar for a per-bot value. Strengthen `test_the_barriers_own_prompt_quantifies_the_gap` to also
  assert that every placeholder the prompt interpolates is bound somewhere in the document.
- **Done when:** `{cap}` has a stated derivation in `branch-cleanup.md`, that derivation names the
  payload field it reads, and a test asserts the derivation block exists rather than only that the
  placeholder appears.
- **Suggested grouping:** phase-6-finalize / pre-merge barrier

## G4 — Re-model `test_refusal_recovery_arming.py` on the cause-first rule

- **Severity:** minor
- **Kind:** stale test fixture / missing-test
- **Where:** `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py:49-53`
  (`_RECOVERY_BY_CLASS`), `:56-58` (`_arms`), `:152-153` (class name and docstring), `:61-73`
  (`_refusal_body`), `:178-179` (`test_a_hard_quota_escalates_immediately`'s docstring)
- **Evidence:** the file models the arming rule as `_RECOVERY_BY_CLASS[bot_registry.rate_limit_class(bot_kind)]`
  with no cause axis, under a class named `TestRecoveryArmingFollowsTheRegistryClass` whose docstring
  reads *"The recovery is chosen by the refusing bot's own declared class"* — the rule this plan
  replaced with "the CAUSE branch first, then the `rate_limit_class` branches"
  (`automatic-review/SKILL.md:368`). `_refusal_body` builds each bot's notice from
  `refusal_patterns[0]`, and for `sourcery` that entry **is** its size pattern
  (`sourcery.md:43`), so the suite already exercises a size refusal and asserts the class-only
  outcome for it. Additionally `test_a_hard_quota_escalates_immediately`'s docstring calls
  `hard_quota` *"A per-PR ceiling"* — the size/quota conflation the plan removed from every other
  consumer, and the last live instance of it. The landing never touched this file
  (`git show --stat 9e9e9880`).
- **Impact:** nothing the file asserts is false today — `escalate_immediately` is the coarse-grained
  right answer for Sourcery even under the new rule — so this is a stale model rather than a wrong
  test. But the model has no room for the reason that distinguishes `refusal_structural` from
  `rate_window_not_awaitable` (G1's live half), and the moment an `awaitable_window` bot declares a
  size pattern this file asserts `claim_and_await` for it, blessing the defect with a green test. It
  is also the last surviving restatement of the pre-fix rule in an executable file.
- **Task:** Give `_arms` the cause axis (cause `size` → `escalate_structurally`, else the class map),
  rename the class to name the two-axis rule, add a case for an `awaitable_window` bot fed a
  size-shaped notice asserting it does **not** arm `claim_and_await`, and correct the
  `hard_quota` docstring to describe an account/plan-level quota rather than a per-PR ceiling.
- **Done when:** the arming model in that file consults the cause before the class, and a test would
  fail if an `awaitable_window` bot's size refusal armed `claim_and_await`.
- **Suggested grouping:** automatic-review / refusal-recovery producer seam (pairs with G1)

## G5 — Add `--refusal-size-caps` to the `deficit` usage synopsis in `review_completeness.py`

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:116`
- **Evidence:** the synopsis line reads
  `review_completeness.py deficit --plan-id <id> [... ] [--refused-causes [<csv>]] [--min-deficit <n>]`
  with no `--refusal-size-caps`, while `_add_bot_observation_flags(deficit_parser)` (`:1525`) declares
  it at `:1434`. The `check` synopsis one line above (`:115`) does carry it. This is the same defect
  F43 recorded and fixed only in `automatic-review/SKILL.md`, whose `deficit` canonical block now
  documents the flag correctly (`:1007`).
- **Impact:** a caller following the module's own `--help`-adjacent synopsis passes the cap to `check`
  and not to `deficit`, making the cap-only cause recovery absent from this module synopsis — the
  one scenario the shared flag exists for, and the cross-command disagreement three documents forbid.
  The flag itself stays executable on `deficit` (declared at `:1434`, and documented in the canonical
  `deficit` block at `automatic-review/SKILL.md:1007`); it is the synopsis that is incomplete.
  plugin-doctor validates docs-against-parser, never parser-against-docs, so it stays green.
- **Task:** Add `[--refusal-size-caps [<csv>]]` to the `deficit` synopsis line, in the same position
  it occupies on the `check` line.
- **Done when:** the two synopsis lines differ only by `--triage-ran` / `--measured-diff-size` (check)
  and `--min-deficit` (deficit).
- **Suggested grouping:** automatic-review / review_completeness CLI

## G6 — Qualify "knowable in advance" where the disclosure carries no cap value

- **Severity:** minor
- **Kind:** stale-doc (overstatement) / partially-met deliverable
- **Where:**
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:409-412`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:213-218`,
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:1057-1098`
  (`declared_size_caps`)
- **Evidence:** the contract says *"a diff's size is measurable at PR creation, so the exclusion is
  knowable in advance"* (`:411-412`). Running the surface returns only booleans:
  `size_capped_reviewers[3]{bot_kind,structural_cap,cap_extractable}` →
  `coderabbit,false,false` / `pr-agent,false,false` / `sourcery,true,true`. `cap_extractable: true`
  means only that a pattern exists to read a figure **out of a future notice** — the figure itself
  exists nowhere until a refusal happens. The plan's D1 ⭐ asked to "surface each bot's declared size
  **limits**". ⚠ Both sites already carry an explicit disclaimer of the per-diff reading — the
  contract enumerates the two booleans honestly at `:419-423`, and `create-pr.md:227-231` says in as
  many words that the surface *"neither blocks PR creation nor predicts a refusal for this particular
  diff"*. The residual defect is narrow: the unqualified sentence, not the surrounding treatment.
- **Impact:** a reader reaching the "knowable in advance" sentence alone takes away that a plan can
  decide whether its own diff exceeds a ceiling; it cannot. The disclaimer is three paragraphs away
  in `create-pr.md` and four in the contract.
- **Task:** Either (a) re-word the two sentences to promise what the surface delivers — *which*
  reviewers carry a ceiling, not whether this diff exceeds one — or (b) add an optional
  `declared_cap` registry field (accepting that a declared figure goes stale, which the design note
  at `_github_pr.py:230-234` deliberately rejected) and report it alongside. Option (a) is consistent
  with the shipped design; pick it unless the advance comparison is wanted enough to accept a
  declared constant.
- **Done when:** no shipped document claims the exclusion is decidable in advance unless the
  disclosure emits a comparable figure.
- **Suggested grouping:** automatic-review / advance disclosure

## G7 — Include `refused_structural` in the barrier's widened-member parity sweep

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py:666-688`
  (the `pytest.mark.parametrize` list and `test_widened_member_gates_byte_identically_to_absent`)
- **Evidence:** the parametrisation hand-lists three members — `STATE_PARTICIPATED_STALE`,
  `STATE_NOT_TRIGGERED`, `STATE_DECLINED` — and omits `STATE_REFUSED_STRUCTURAL`. A search of the
  whole file for `structural` returns one hit, in an unrelated comment at `:296`: the landing did not
  touch this file at all, though the plan's Expected surface named it.
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
  **9** failures: `test_size_refusal_is_structural_not_a_rate_refusal`,
  `test_cause_dominates_an_awaitable_window_class`,
  `test_a_size_refusal_is_structural_for_every_registered_bot` ×3,
  `test_check_and_deficit_agree_on_the_member` ×2,
  `test_the_summary_distinguishes_structural_from_temporal`, and
  `TestTheCapIsRecorded::test_a_cap_arriving_without_its_cause_still_resolves_structural`, the last of
  which is in case (c) and is not mentioned by the row's composition. Rows D (3), E (1) and I
  (1, cap-only) reproduce exactly.
- **Impact:** the discrimination is *stronger* than reported, so nothing is unsafe — but the row is a
  count written beside a result rather than from it, which is the same defect F64 / F72 / F78 / F79
  record. A later reader re-deriving the mutation set from this row will under-expect.
- **Task:** Re-run mutation A and restate the row from the observed failure list, naming the case-(c)
  test explicitly.
- **Done when:** the row's count and composition match a re-run.
- **Suggested grouping:** report hygiene / stale-count defect

## G9 — Reconcile the report's finding tables with its own "one row per INSTANCE" rule

- **Severity:** minor
- **Kind:** false-report-claim (self-inconsistency) + two stale counts
- **Where:** `report-01.md` § "Findings" preamble (*"One row per INSTANCE, never bundled."*) against
  rows `F8–F20`, `F30–F36`, `F44–F47` and `F65–F69`
- **Evidence:** four rows each carry a range of finding ids and a prose enumeration in a single cell,
  directly under the sentence forbidding it. Two of those four also miscount their own enumeration:
  - `F8–F20` is 13 ids and is labelled *"Thirteen stale beyond-diff statements"*, but its enumeration
    names **fifteen** — two "the cause is advisory" sites, one "it only labels", five "three refusal
    members", the `--refused-bots` help text, three producer-side enumerations, two CLI flag counts,
    and the `fetch_findings` field enumeration.
  - `F30–F36` is 7 ids and is labelled *"Seven further stale statements"*, but its enumeration names
    **eight** — the knob description, the "can route them identically" field-contract line, "four
    distinct escalations", "a fourth shape", two literal `'size'` comparisons, item 7a's
    recording-branch preamble, and the ambiguous "all three".

  `F44–F47` (4) and `F65–F69` (5) do match their enumerations. F71 records that one bundled row
  overstated its disposition ("I marked F65–F69 'ALL FIXED' when two had not landed"), which is the
  failure mode bundling produces.
- **Impact:** a bundled row's disposition column is one verdict over many instances, so a partial fix
  reads as complete — the defect F71 caught once and that nothing prevents recurring. The two
  id-count/enumeration mismatches make the finding total unauditable and are two further instances of
  the stale-count defect the report's own F64 / F72 / F78 / F79 chain is about.
- **Task:** Either split the four ranges into one row per instance, or amend the preamble to state the
  actual rule (one row per instance except for enumerated same-shape sweeps, which carry their member
  list and a per-member disposition). Either way, re-derive each bundled row's count from its own
  enumeration rather than restating it.
- **Done when:** the stated discipline and the tables agree, and every bundled row's stated count
  equals the number of instances its own cell enumerates.
- **Suggested grouping:** report hygiene

## G10 — Correct two stale statements in `pr-agent.md`

- **Severity:** minor
- **Kind:** stale-doc (first) / bug (second, pre-existing)
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:252-256`
- **Evidence:**
  1. `:252-253` states unconditionally *"The recovery sequence therefore escalates immediately for
     this class (`escalate_ask{reason: rate_window_not_awaitable}`)"*. Branch 1 is now conditional —
     *"`hard_quota` or `unknown` **(and `cause` is not `size`)**"*
     (`automatic-review/SKILL.md:400`) — so an `unknown`-class bot refusing on size escalates with
     `refusal_structural`, not `rate_window_not_awaitable`. It is the only surviving occurrence of
     `rate_window_not_awaitable` outside the two SKILL files
     (`grep -rn "rate_window_not_awaitable" marketplace/ test/`), and it sits in a registry doc the
     plan's Expected surface named.
  2. `:254-255` instructs *"record its OBSERVED text in `ignore_patterns`"* for a refusal.
     `sourcery.md:110-112` says the opposite in as many words — a refusal *"is **not** a noise drop
     and lives in the separate `refusal_patterns` list, not in `ignore_patterns`"* — and
     `bot-participation-contract.md:457` defines `ignore_patterns` as an **unconditional drop**.
     `git log -S "record its OBSERVED text in"` dates this to #1041, so it is pre-existing and this
     plan inherited no obligation for it.
- **Impact:** (1) a reader of the PR-Agent registry doc learns the pre-fix escalation rule. (2) an
  editor following `:254-255` after observing a PR-Agent refusal would file the refusal phrasing as a
  noise pattern, causing the refusal to be dropped rather than branched — the exact failure the
  contract calls out as letting *"a PR whose every required reviewer refused report a clean, complete
  review"*.
- **Task:** Qualify `:252-253` with "(and the cause is not `size`)" and cross-reference Branch 0;
  change `:254-255` to `refusal_patterns`, and add the size overlay note (`refusal_size_patterns`) so
  a future observed size refusal is filed on both lists.
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
