> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The instruments that measure our gates report only what they measured

**Epic:** review-apparatus
**Branch prefix:** fix — this is a bug fix across three measurement instruments, not a new capability.

## Problem

Three instruments in this repository exist to tell an operator how good our in-house gates are: the
**review-versus-gate delta** (`review_gate_delta.py`), the **build gate's coverage verdict**
(`_gate_coverage.py`), and the **self-review count-prose detector**
(`ext-self-review-plan-marshall`). Each of the three currently publishes a figure or a verdict that a
reader will take as a statement about gate quality, and each can produce that figure in a state where
it measured nothing, measured a different population than the one it names, or measured a population
it cannot reach. The instruments are not merely incomplete: at least one of them **inverts** — it
reports its best possible number in its worst possible state.

**The inversion, concretely.** `assess_delta` in
`marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py` computes
reviewer coverage as `covered = set(enabled_bots) & set(reviewed_bots)` against
`roster = set(enabled_bots)`, and `_share_withheld_reason` then withholds `structural_share` only when
`len(covered) < len(roster)`. **`enabled_bots` is a caller argument**, supplied on the CLI as
`--enabled-bots` and documented as `required_bots ∪ optional_bots`. So the coverage denominator is
whatever roster the caller passed, not the roster the project configured. Narrowing that roster is not
a hypothetical: it is a **first-class remedy this epic itself introduced** — a `refused_structural`
reviewer (one that refused because the diff exceeds its own size ceiling) has exactly three sanctioned
remedies in
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`,
and one of them is *"disable this reviewer for this PR"*, which is enacted by narrowing the step's
`required_bots` / `optional_bots` — the very roster passed as `--enabled-bots`. Enact it and the same
diff, the same escapes, the same partition, and the same single reviewer that actually spoke move the
verdict from `structural_share: null` / `share_withheld: partial_reviewer_coverage` at
`reviewer_coverage: 1/3` to `structural_share: 100.0` / `share_withheld: null` at
`reviewer_coverage: 1/1`. **`100.0` is verbatim the number the contract names as the failure mode**:
*"a naive share reports 100% — 'the gates are perfectly configured' — when the only thing that changed
is who spoke."* The guard designed to make a coverage collapse move the metric from *a number* to *no
number* instead lets it move to the best number the scale has.

**Stated precondition, not assumed.** The shrink is not automatic — an operator must enact the
disable-for-this-PR remedy. The other two remedies do not reach it: *split* changes the diff, and
*accept the gap* leaves the refusing reviewer on the roster, so coverage stays partial and the share
stays withheld. The route is nonetheless real rather than theoretical, because `refused_structural`
and its remedy set landed in this repository after the delta did.

**The same shape, three more times.** Four sites restate the withholding guarantee as an unqualified
property of coverage — the module docstring, the contract, the bundle `SKILL.md` canonical block, and
the caller's own step doc — so a maintainer reads a guarantee the code does not have. The build gate's
`_render_structural_limits` returns nothing at all when a boundary recorded a degraded dimension and no
checked one, which is the **first and most likely** gate failure path, so the most common non-green
verdict carries no scope limit; an entirely empty boundary renders `COMPLETE`, so *"nothing was
analysed"* and *"everything passed"* print the same word; and the closing *"not run in this gate at
all … because this gate never performs them"* line is false of two reachable states (an analysis
attempted over an empty scope, and an analysis this invocation did not reach but the same gate does
perform in another mode). And the count-prose detector — the instrument that catches stale count
claims — cannot reach the one real-world finding advanced as its justification, because its predicate
requires the noun **immediately adjacent** to the number, its noun set omits the noun that finding
used, and its file scope excludes every `.py` docstring in the tree, where two live instances of the
exact archetype sit today inside the test file that guards the very population the finding was about.

Across all three, the pattern is one thing: **a published number whose population is not the
population it names, and whose zero, null, or green is indistinguishable from a genuine one.**

## Goal

Every figure and every verdict these three instruments publish names the population it was computed
over, and cannot be improved by shrinking that population. A coverage collapse — however enacted, and
whether or not an operator enacted it deliberately — moves the delta's share from a number to no
number, never to a better one. A gate verdict distinguishes *checked*, *attempted but degraded*, *not
reached by this invocation*, and *never performed by this gate*, and never renders an assurance word
over an empty boundary. The count-prose detector's three reach axes — noun set, number-noun adjacency,
and file scope — are each measured from the tree by a committed, reproducible artifact and each named
as a known limit where a future editor will read it. Where a measurement-semantics choice is genuinely
open, the plan records a proposal with its measured cost rather than enacting one silently.

## Deliverables

Seven items: one gate that mutates nothing, and six deliverables. Each names the gap identifiers it
discharges. The detailed per-gap evidence lives in two git-tracked files that will be on `main` when
this runs — `doc/plans/review-apparatus/130-review-bots-catch-what-in-house-gates-cannot/gaps.md` and
`doc/plans/review-apparatus/090-feed-pr-findings-back-into-local-review/gaps.md`, with the supporting
analysis in the `verification.md` beside each. **They are corroboration, not required reading**:
everything this plan needs is stated here.

⛔ **Do not look for `.plan/` anything.** The orchestrator ledger, the plan specs and the landing
records are git-ignored and are absent from this clone. Nothing in this plan requires them.

---

0. **D0 — GATE: derive three populations from the tree, or HALT.** Mutates nothing. Every later
   deliverable rests on one of these three being derivable; if any cannot be derived **from files in
   this clone**, stop and report the plan blocked for that arm. ⛔ **Do not write a hand-maintained
   fallback list for any of them** — a hand-maintained population is the defect class this plan is
   closing, so a fallback would reproduce it inside the fix.

   - **P1 — the roster baseline.** The reviewer roster the project *configured*, derived from the
     machine-readable bot registry and the participation configuration in the tree, independent of any
     per-PR narrowing. Start from `bot_registry` (the module `review_gate_delta` already imports) and
     the `required_bots` / `optional_bots` definitions the bot-participation contract names as their
     source. Report the derived member set and the file(s) it came from. This is **also the reviewer
     population the escape set is filtered against** in D2 — the numerator and the denominator are the
     same set or the ratio is meaningless. **HALT D1 and D2's reviewer-population arm if the
     configured roster cannot be distinguished from the per-PR roster by reading the tree** — without
     that distinction there is no baseline to anchor against and no population to filter to, and
     neither fix is implementable as written.
   - **P2 — the in-house gate roster.** Every in-house gate whose verdict a reader treats as
     assurance. Derive it from the finalize step declarations in the tree: each step doc under
     `marketplace/bundles/plan-marshall/skills/phase-6-finalize/{standards,workflow}/` carries an
     `order:` in its frontmatter, and the project-local steps under `.claude/skills/finalize-step-*/`
     carry theirs. A gate is a step whose recorded outcome is a pass/fail assurance claim about the
     tree. Also derive the build gate's own dimension registry, `_ANALYSIS_LIMITS` in
     `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py`. Report
     both sets and, per member, whether its verdict currently carries a structural limit. ⚠ **A prior
     analysis put this at three of six carrying one — treat that as a lead and re-derive it; do not
     copy the figure.**
   - **P3 — the count-prose domain.** The detector's contract-source file set, derived by running
     `_collect_skill_contract_sources` (`SKILL.md` plus every `standards/*.md` per skill directory)
     over `marketplace/bundles/*/skills/*/`, and over that set: the follower-token distribution after
     a number, the line count the landed `_COUNT_PROSE` predicate matches, and the additional line
     count a **one-intervening-word-token** allowance (`\s+(?:\w[\w-]*\s+)?`) would match. ⚠ **A prior
     analysis put these at 517 files, 189 matched lines and +113 with the allowance — leads, all
     three. Re-derive every one; the tree has moved.**

   *Done when:* the run report states, for each of P1/P2/P3, the derived population, the file(s) it
   was derived from, and the command or script that reproduces it — or states which arm halted and
   why. No population in this plan is asserted without one of those two.

1. **D1 — Anchor the delta's coverage denominator so a roster shrink cannot restore a share.**
   Discharges **130/G1 (blocker)**. In `review_gate_delta.py`: add a baseline-roster input (a
   `--roster-baseline` flag or equivalent) carrying P1's configured roster independent of any per-PR
   disable; emit a new `WITHHELD_ROSTER_NARROWED` reason when the effective roster is a **proper
   subset** of the baseline; and publish **both** sets on the verdict payload beside
   `reviewer_coverage`, so a reader sees the narrowing rather than having to compare rosters across
   PRs (nothing in the tree performs that comparison today, and no baseline is recorded against which a
   shrink is even detectable). Then restate the guarantee in terms of the **baseline** — not as an
   unqualified property of coverage — at all four sites that currently state it absolutely:
   `review_gate_delta.py`'s module docstring (the "Two properties that keep the signal from becoming
   harmful" section), `automatic-review/standards/bot-participation-contract.md`
   § "The review-versus-gate delta", `automatic-review/SKILL.md`'s canonical `review_gate_delta assess`
   block, and `.claude/skills/finalize-step-review-retrospective/SKILL.md` Step 3b.
   *Done when:* a test drives `assess_delta` twice with the **same** escapes, the **same** partition
   labels and the **same** two SHAs, differing only in that the second arm's `enabled_bots` is a proper
   subset of the first's, and asserts the second arm **withholds** the share with
   `WITHHELD_ROSTER_NARROWED`; and no input reachable from
   `.claude/skills/finalize-step-review-retrospective/SKILL.md` Step 3b can produce a `structural_share`
   at reduced real coverage.

2. **D2 — Make the escape set's population explicit, and match it to the denominator it is divided
   by.** Discharges **130/G2, 130/G6, 130/G11**. Three defects, one mechanism: the numerator is
   computed over a different population than the denominator, and the difference is invisible.
   - **Rejected findings (G2).** `review_gate_delta.py` never reads a finding's `resolution` — a
     `grep` for the word returns nothing in that module. Meanwhile
     `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` defines
     `RELEASED_RESOLUTIONS = frozenset({'rejected', 'suppressed'})` and treats exactly those as *the
     reviewer was wrong, nothing is owed*, and `add_finding` seeds every record at
     `resolution: 'pending'`. **The decision is taken by this plan, so the run makes none:** a finding
     the run rejected or suppressed is **not** a gate escape, because the module's own definition of
     an escape is *"something the gates ran over and did not report"* — for a rejected finding the
     gates were right and the reviewer was not. Filter those dispositions out of the escape
     comprehension, and publish the **excluded count** on the payload (following
     `review_commitments.count_unanchored`, so the exclusion is visible rather than shrinking a
     denominator silently). Extend the contract's § "The counting rule" with the resolution axis so
     both counters apply it.
   - **Reviewer population (G6).** The escape comprehension filters on `_is_actionable` only — never
     on `bot_kind`, never on the roster — while the coverage denominator is the roster. Human PR
     comments are stored as ordinary `pr-comment` findings (`github_pr` resolves `bot_kind` to `None`
     for a human author, `add_finding` then omits the key, and the noise pre-filter explicitly *keeps*
     human comments), and the qualitative partition pass produces one row per **enabled reviewer**, so
     a human finding gets no partition label, lands `unpartitioned`, and withholds the whole PR's
     share. **The decision is taken by this plan:** restrict the escape set to records whose *resolved*
     `bot_kind` is in the roster, and publish the excluded count beside the population — because the
     numerator and the denominator must be the same population, which is precisely what the counting
     rule's invisible-denominator prohibition demands. State the decision in `_PROVENANCE` and in the
     contract § "The review-versus-gate delta".
   - **Escape attribution (G11).** The escape row is built as
     `'bot_kind': str(record.get('bot_kind') or '')` — the raw key — while `resolve_bot_kind` sits two
     functions above to answer exactly the case where that key is absent. Call `resolve_bot_kind(record)`
     when building the escape entry, so the two code paths in one function stop answering "which bot"
     differently.

   *Done when:* three tests pin the three, each asserting a **published population figure** and not
   only a filtered total — one supplying a `rejected` and a `suppressed` finding and asserting both the
   resulting `escapes_total` and the published exclusion count; one supplying a record with **no**
   `bot_kind` and asserting the documented treatment plus the reviewer population named in the emitted
   provenance; and one supplying a record carrying only `author` and asserting its escape row's
   `bot_kind` is non-empty.

3. **D3 — Make the delta's published claims about itself true.** Discharges **130/G3, 130/G4,
   130/G7, 130/G10, 130/G16, 130/G17**. Six false or stale claims the instrument makes about its own
   reach, provenance, duplication and wiring.
   - **Selection effect (G4).** `_PROVENANCE` and four sites that restate it assert *a forward pass
     never re-gates*, therefore *"the ONLY measurable PRs are those where **neither** post-gate
     mutating step committed anything"*. The first clause is true only of a forward pass:
     `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
     § "Verdict-input surface — deliberately undeclared" states the gate declares **no**
     `verdict_inputs`, so *"every HEAD advance re-runs it"*, and `verdict_currency.py` turns that into
     `VERDICT_INVALIDATED` → RE-FIRE. On a loop-back re-entry the gate **does** re-fire and re-stamp
     `head_at_completion`, so the measurable condition is a property of the **final** pass.
     ⚠ **The correction does not widen the measurable set** and must not be written as though it does:
     `github_pr`'s pre-filter dedups on `(bot_kind, comment_id)` and never re-stamps an existing
     finding's `reviewed_commit_sha`, so after a review-driven loop-back the store holds findings from
     two iterations carrying two SHAs, and Step 3b's own rule ("pass the value only when every finding
     agrees; when they disagree, pass nothing") excludes the PR as `gate_tree_unsubstantiated`; and if
     the re-review filed nothing new, every finding carries the pre-loop-back SHA while the gate
     re-stamped the new one, excluding as `gates_did_not_cover_reviewed_tree`. Write the measurable
     condition as *"PRs whose final pass had no post-gate commit and whose findings all carry one SHA
     equal to the gate's final stamp"*. Correct all five sites together: `_PROVENANCE`, the module
     docstring, the contract section, the bundle `SKILL.md` canonical block, and Step 3b's consumer
     text, which must stay verbatim-consistent with the emitted string.
   - **The `author` fallback (G3).** `resolve_bot_kind`'s docstring justifies the fallback with *"the
     GitLab producer (`gitlab_pr`) never sets [`bot_kind`] at all. Keying on `bot_kind` alone would
     silently disable every per-bot rule on the whole GitLab path."* The first half is true; the second
     does not follow, because the fallback's own selector is absent there too — `gitlab_pr.py`'s
     `add_finding` call passes `plan_id`, `finding_type`, `title`, `detail`, `file_path`, `line` and
     `raw_input` and **no** `author=`, `kind=`, `bot_kind=` or `reviewed_commit_sha=`, even though
     `kind` and `author` are computed locally a few lines above and used only to build the title and
     detail strings; the GitHub producer passes all four. Consequences on a GitLab record: `_is_actionable`
     sees no `kind` and returns `False` for every record, so `escapes_total` is always 0;
     `resolve_bot_kind` returns `''`; and `EXCLUSION_GATE_TREE_UNKNOWN` fires because there is no
     `reviewed_commit_sha`. Take branch (a): pass `author`, `kind`, `bot_kind` and
     `reviewed_commit_sha` through `gitlab_pr.py`'s `add_finding` call so GitLab records carry the same
     first-class fields as GitHub's, and re-point the parity-corpus case in
     `test/plan-marshall/automatic-review/test_counting_rule_parity.py` labelled *"summary identified
     from the author login with no bot_kind"* at a shape a producer demonstrably emits. If, on reading
     `gitlab_pr.py`, those four values are not all available at the call site, fall back to branch (b):
     correct the docstring and the corpus comment to say the GitLab path stores neither selector, and
     record the GitLab inertness explicitly in the contract § "The review-versus-gate delta". **State in
     the report which branch was taken and the observation that decided it.**
   - **The duplication claim (G7).** The contract's Consumers table says of `review_gate_delta assess`
     that *"the two implement the same rule **independently** because they live in different bundles,
     so a change to the rule must land in both."* `review_retrospective._is_status_summary` now reads
     `from review_gate_delta import is_status_summary` and its own docstring says *"there is now one
     implementation"* — so on the status-summary axis the parity test compares a function with itself.
     Only the kind classification remains genuinely duplicated, and the two differ there
     (`return kind in _ACTIONABLE_KINDS` versus an explicit `if kind == 'inline': return True` /
     `return False`). Rewrite the Consumers row to say the summary predicate is one shared
     implementation the retrospective imports and that only the kind classification is duplicated, and
     narrow the parity test's docstring to the axis it actually discriminates on.
   - **The instrument's home (G10).** The script, the contract and the canonical block ship in the
     shared bundle, but the only invocation site is the project-local
     `.claude/skills/finalize-step-review-retrospective/SKILL.md`, so every consuming project receives
     the instrument and nothing that runs it. Take the reversible option: **state in the contract
     § "The review-versus-gate delta" that the instrument is meta-project-instrumented only, and
     why** — and record promoting a bundle-shipped delta-emitting step as a proposal under D6 rather
     than enacting it, because where a finalize step ships is an architectural call this run must not
     make alone.
   - **Step 3b's two SHAs (G16).** Every other command in that step is a fenced bash block, but the two
     inputs the escape claim rests on are prose: the `head_at_completion` recorded by
     `pre-push-quality-gate` ("read the step record via `manage-status`") and the
     `reviewed_commit_sha` carried by the `pr-comment` findings, whose agreement rule is left to the
     agent. Both are reachable — `manage-status` persists
     `status.metadata.phase_steps[{phase}][{step}]` including `head_at_completion`, and
     `manage-findings list` returns the records. Add the two concrete commands, and state the
     disagreement rule as a mechanical check over the returned `reviewed_commit_sha` values.
   - **The dead guard (G17).** `review_commitments.cmd_reconcile` catches
     `(OSError, ValueError, KeyError)` over `query_findings(plan_id, finding_type='pr-comment')['findings']`;
     `review_gate_delta.cmd_assess` catches `(OSError, ValueError)` over the identical expression. The
     narrower tuple is correct — `query_findings` has no error-return branch and unconditionally
     returns a dict containing `findings` — and `review_commitments`' own `_read_pr_comment_findings`
     docstring states the governing rule three lines above the guard (*"a dead guard against a shape
     the callee never produces reads as defence and provides none"*). Drop `KeyError`.

   *Done when:* a test asserts the `provenance` string emitted by `assess_delta` matches the contract's
   stated wording verbatim (so the two cannot drift again); every parity-corpus record is asserted
   against the producer that emits its shape rather than against a comment; no site claims two
   independent implementations; the contract names the instrument's scope as a deliberate boundary;
   Step 3b resolves both SHAs through named commands with no undocumented step; and both CLIs catch the
   same exception set over the same call.

4. **D4 — Make every gate verdict distinguish checked, degraded, not-reached, and never-performed.**
   Discharges **130/G5, 130/G8, 130/G9, 130/G12, 130/G13**. All five are the same defect at different
   gates: an assurance word or a green rendered over a state it does not describe.
   - **The degraded-only boundary renders no limit block (G5).** `_render_structural_limits` opens
     `pairs = structural_limits(boundary.checked)` / `if not pairs: return []`, and `cmd_quality_gate`
     calls `cmd_compile` **first**, so a freshness-suspect mypy records `degraded` only and halts
     straight to `render_coverage_summary` — producing a PARTIAL verdict with **no** per-analysis
     limits and **no** `not run in this gate at all:` line. That contradicts the governing standard's
     own table row in
     `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`,
     which states the structural limit is *"a per-analysis block on **both** the COMPLETE and PARTIAL
     verdicts"*. This is the **first and most likely** gate failure path. Change the early-return
     condition to suppress only when the boundary is entirely empty
     (`not boundary.checked and not boundary.degraded`), and derive the limit pairs from
     `checked + degraded` stems so a degraded analysis still states what it structurally cannot see.
     The guard's stated justification ("a run that performed no analysis") conflates *checked nothing*
     with *attempted nothing* — a degraded dimension **was** attempted.
   - **The un-run line is false for two reachable states (G8).** `not_run` is `_ANALYSIS_LIMITS` minus
     the attempted stems, printed as *"absent from the list above because this gate **never performs
     them**, NOT because they passed"*. Two reachable states are neither: (1) an analysis **attempted
     over an empty scope** — when no file under the scoped path survives mypy's excludes,
     `_skip_empty_mypy_scope` makes `cmd_compile` / `cmd_test_compile` `return 0` before `_run_mypy`,
     so the dimension is recorded neither checked nor degraded, yet the gate *did* perform that
     analysis and found nothing to analyse; and (2) an analysis **conditionally performed** —
     `cmd_quality_gate` runs plugin-doctor only when `module is None`, so a module-scoped
     `quality-gate` (the ordinary per-commit invocation) leaves `plugin-doctor` unattempted and prints
     it under *"this gate never performs them"*, which is false of the same gate in whole-tree mode.
     Record an explicit third outcome for an empty analysis scope, render it as its own line, and
     narrow the un-run wording so it distinguishes *this gate never performs it* from *this invocation
     did not reach it*.
   - **An empty boundary renders COMPLETE (G9).** `CoverageBoundary.complete` is `return not
     self.degraded`, so `render_coverage_summary(CoverageBoundary())` prints
     `>>> coverage: COMPLETE over the dimensions below — checked over full scope: (nothing)` with no
     limit block and no un-run line: *"no dimension was analysed"* and *"every dimension passed"*
     produce the same verdict word. ⚠ **This shape is latent, not reachable from production** — every
     `render_coverage_summary` call site in `build.py` is preceded by at least one `record_checked` or
     `record_degraded`, and `build.py` is the only consumer of `_gate_coverage`. Fix it anyway and say
     so plainly: introduce a third verdict form for an empty boundary (e.g. `>>> coverage: NONE — this
     pass analysed no dimension; it certifies nothing`), make `complete` false when nothing was
     checked, and replace the test that currently pins the empty boundary as intended.
   - **The self-review limit stops at the tool's stdout (G12).**
     `ext-self-review-plan-marshall/scripts/self_review.py` emits `structural_limit` on its surfacer
     TOON, and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
     states that *"the `--display-detail` budget … carries neither, and the dispatched-envelope schema
     below has no field for either"*, concluding *"it is published, not discharged"*. So the limit
     reaches the dispatched agent and stops there; the step's **recorded verdict** — what a later
     reader of `status.metadata.phase_steps` sees — still reads only `clean: {N} candidates examined,
     no check matched`. Add a `structural_limit` field to the dispatched-envelope schema in
     `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`
     and have the step forward the surfacer's value into it. The `display_detail` budget stays
     untouched.
   - **Three gates carry no structural limit at all (G13).** Using P2's derived gate roster: for each
     gate whose verdict carries no limit, name the analysis it performs and the defect class it
     structurally cannot reach, and put that statement on its verdict, following
     `pre-push-quality-gate.md` § "A gate states what its green does not evaluate" as the pattern.
     A prior analysis named `ci-verify.md`, `sonar-roundtrip.md` and the project-local
     `finalize-step-plugin-doctor` step verdict as the three, with `ci-verify` the highest-value
     because its green is the one most often read as whole-tree assurance — ⚠ **treat that trio as a
     lead and re-derive it from P2.** Note that plugin-doctor's two existing "cannot evaluate" mentions
     are a **scope** statement about scoped-vs-whole-tree mode, which is cured by widening and is
     therefore by definition not a structural limit.

   *Done when:* a test seeding a boundary with one degraded dimension and **no** checked dimension
   asserts the rendered summary contains both `does NOT evaluate` and `not run in this gate`; a
   module-scoped `quality-gate` prints a verdict distinguishing all three un-checked states, with the
   empty-scope and module-scoped-plugin-doctor cases pinned by test;
   `render_coverage_summary(CoverageBoundary())` contains neither `COMPLETE` nor `PARTIAL` and a test
   asserts that; a test asserts the self-review dispatched-envelope's `structural_limit` field is
   populated on a clean full-surface round; and every gate P2 identified as limitless carries a limit
   that is a property of its **analysis** rather than of its file set.

5. **D5 — Measure the count-prose detector's three reach axes, and fix the instances outside them.**
   Discharges **090/G2, 090/G3, 090/G4, 090/G6, 090/G7**.
   - **Land the derivation as a reproducible artifact (G3).** The `_CARDINALITY_NOUNS` comment in
     `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py`
     carries a derivation's *conclusion* ("it is a CURATED set, not 'any noun'") but the scan that
     produced it never landed, so a future widening must redo it from scratch. Land P3's derivation as
     a committed utility or as a test that asserts the closed set against a derived candidate list,
     under the `ext-self-review-plan-marshall` scripts or test tree. **Follow the existing precedent
     rather than inventing a shape:**
     `test/plan-marshall/automatic-review/test_bot_participation_contract.py` §
     `test_the_contracts_closure_count_agrees_with_the_derived_member_count` reads a closure count
     stated in prose out of a contract doc and asserts it against the derived member set. Record in the
     `_CARDINALITY_NOUNS` comment which high-frequency candidates were considered and rejected and why,
     naming `deliverable` and `module` as the two the existing negative test
     (`test_count_prose_does_not_fire_on_nouns_outside_closed_set`) already pins as must-not-fire.
     ⚠ A prior analysis put the un-adjudicated structural-noun candidates at `state`, `phase`, `flag`,
     `column` and `member`, each more frequent than `check` (the one member the last widening added) —
     a lead; re-derive from P3.
   - **The adjacency axis (G2).** `_COUNT_PROSE` is
     `rf'(?i)\b(?:\d+|{_NUMBER_WORDS})\s+(?:{_CARDINALITY_NOUNS})\b'` — the noun must be
     **immediately adjacent** to the number, so `'the eight list flags'` does not match even if
     `flags?` is added to the noun set, while `'nine flags'` does. That is why the detector cannot
     surface the one real-world instance advanced as its justification. ⛔ **Derive, do not loosen.**
     Using P3's measured allowance cost, **record the bounded-allowance decision as a proposal under
     D6 rather than enacting it**, and record the measured reason in the `_CARDINALITY_NOUNS` comment
     so the next editor inherits the measurement rather than the argument.
   - **The file-scope axis (G7).** `_collect_skill_contract_sources` resolves `SKILL.md` plus every
     `standards/*.md` in a skill directory, so **every `.py` docstring and comment in the tree is
     outside the detector's file scope entirely** — a third reach axis alongside the noun set and the
     adjacency. Record it as a known limit in the `_CARDINALITY_NOUNS` comment beside the other two, so
     a future widening decision weighs all three.
   - **The two live instances the file scope excludes (G7).** In
     `test/plan-marshall/automatic-review/test_bot_participation_contract.py`, two prose count claims
     contradict the file's own derived data — neither is asserted, so the suite passes: (1) the
     docstring of `test_confirmed_site_carries_its_own_flag_set_fully_quoted` reads *"the sites
     genuinely differ — the pre-merge barrier passes five flags, not the participation guard's six"*,
     while `_CONFIRMED_SITES` declares **6** for both family-A sites and the module comment above it
     says the barrier passes six; and (2) the `#:` comment above the list-flag alternation says *"a
     sixth flag reaches the quoting scan automatically"* while `_ALL_LIST_FLAGS` is derived live from
     the parser and holds **seven** members. Correct both against the derived data — the second phrased
     without a bare ordinal so it cannot go stale again. ⚠ Re-derive both figures before writing them.
   - **The eight-versus-nine scope split (G6).** `automatic-review/SKILL.md` says *"eight list flags"*
     in three places and *"nine list flags"* in another, and `review_completeness.py` also says nine.
     ⛔ **Both figures are correct** — they count two different populations: the "eight" sites are
     scoped to the `review_completeness check` invocation printed immediately above them, which passes
     exactly eight list flags, while "nine" is the parser's whole flag surface (the ninth,
     `--declined-bots`, is supplied only from the phase-6 re-review path, which is why the FIND-step
     call omits it). **Nothing is stale; what is missing is any statement of that scoping.** State the
     population on each figure — "the eight list flags **this call passes**" and "all nine list flags
     **the parser declares**" — so the two can be reconciled without leaving the document. ⚠ Re-derive
     both counts from the parser before writing them; do not copy eight and nine from this plan.
   - **The `## Tests` coverage index (G4).** The count-prose row in
     `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md`
     enumerates its cases exhaustively but names neither `test_count_prose_surfaces_check_noun` nor
     `test_count_prose_does_not_fire_on_nouns_outside_closed_set`; sibling rows in the same section do
     enumerate every case, so this is drift, not a style difference — and the repo's own rule
     (`persona-plan-marshall-agent/standards/agent-behavior-rules.md`) says *"When you add a member to
     the indexed set, add its index row in the SAME change."* Extend the row with the `check`-noun
     positive (including its singular `one check` branch) and the closed-set negative.

   *Done when:* a committed artifact reproduces the follower distribution over the detector's
   contract-source domain and is runnable from a clean clone; the `_CARDINALITY_NOUNS` comment names
   each rejected high-frequency candidate with its reason **and** names all three reach axes (noun set,
   adjacency, file scope) as known limits; no count claim in `test_bot_participation_contract.py`
   contradicts `_CONFIRMED_SITES` or the parser-derived flag family; every list-flag count in
   `automatic-review/SKILL.md` names the population it counts; and every case in `TestDetectCountProse`
   has a clause in the `SKILL.md` `## Tests` row.

6. **D6 — Record the open measurement-semantics proposals, and correct two records that restate rather
   than report.** Discharges **090/G5, 090/G8**, and carries the proposals D3 and D5 defer.
   ⛔ **This deliverable records; it decides nothing.** Each proposal is written as a proposal for an
   operator, with the measurement that motivates it and the cost of adopting it, and is **not
   enacted**.
   - **Proposals**, written into a clearly-marked proposals section of this run's report and — where a
     contract is the natural home — as an explicitly labelled open question in that contract, never as
     a rule: (a) whether to promote a bundle-shipped delta-emitting finalize step beside
     `automatic-review`, versus keeping the instrument meta-project-instrumented (D3/G10); (b) whether
     the count-prose predicate should take the bounded one-intervening-word-token allowance, carrying
     P3's measured added-match count as its cost (D5/G2); (c) whether any of P3's un-adjudicated
     high-frequency structural nouns should join the closed set, each with its measured frequency
     (D5/G3). ⛔ **No proposal may be shipped as a contract change by this run** — the lane forbids
     self-approving a change to the contract that governs it, and these are operator calls.
   - **Report correction — the detector-registry enumeration (090/G5).** The 090 plan's claim-labels
     table obliged the run to re-derive the detector registry at HEAD and publish it; the run's report
     states neither the registry size nor which detectors were ruled out per candidate, so its
     asserted-absence claim ("no existing detector already covers a given candidate's shape") has no
     published population behind it. Add the re-derived registry count and the per-candidate absence
     check to `doc/plans/review-apparatus/090-feed-pr-findings-back-into-local-review/report-01.md`
     § D0 — one line naming the count, and per "yes" candidate which existing detectors were ruled out.
     ⚠ Re-derive the count (`grep -c "^def _detect_"` on `_self_review_detectors.py`, cross-checked
     against the names `self_review.py` imports and against `len(CANDIDATE_LISTS)`, which is a
     **different** figure) — a prior analysis put these at 20 and 22 respectively; leads, both.
   - **Report correction — two *Done when* clauses restated rather than met (090/G8).** That run marked
     two clauses satisfied by rewording them. D2's clause required *"each yes has either a new detector
     or a justified widening"*; the three "yes" answers produced neither (one was already covered by
     markdownlint, two were routed out to the cloud-plan-lane), and the report substituted a different
     clause. D3's clause required *"one **positive** case drawn from the real accepted finding that
     motivated it"*; no accepted finding motivated the widening — the corroborating finding is
     **unanswered**, not accepted, and the fixture was drawn from the plan's own docstring observation
     plus a real `phase-1-init/SKILL.md` instance. ⚠ **The dispositions themselves were correct and
     plan-sanctioned** — that plan's own out-of-scope rules required routing such candidates out. The
     defect is only that the deviation was not reported. Record the substitution for both clauses in
     `report-01.md`. Do not rewrite the surrounding analysis, and do not add a dated correction note.

   *Done when:* the run report carries a proposals section in which every entry names its measurement
   and is explicitly marked not-enacted; `report-01.md` § D0 states the enumerated registry size and
   names the detectors excluded per candidate; and `report-01.md` states the substitution for both the
   D2 and D3 clauses.

## Out of scope

Each entry names why. With no operator watching this run, the written boundary is the only thing that
stops mid-run drift.

- **Blocking a merge on any figure this plan touches.** Every instrument here is an OBSERVABILITY
  signal — `review_gate_delta` publishes `proves: gate_escape_only` and `gates_merge: false`
  machine-readably for exactly this reason. Turning any of them into a merge gate is a policy change
  with a blast radius far beyond a measurement fix, and would strand landings on a metric this plan is
  in the middle of proving unreliable.
- **Changing the finalize step ordering so the quality gate re-fires after the `mutates_source`
  steps.** That is the standing unblocking condition for the delta's narrow measurable population, and
  it is named as deliberately-not-made in three existing documents. It is a change to dispatch
  ordering, not to a measurement, and it would invalidate this plan's own before/after comparisons
  mid-run.
- **Enacting any D6 proposal.** Each is an operator call — where a finalize step ships, and whether a
  detector's precision should be traded for reach. The lane forbids self-approving a change to the
  contract that governs the run, and there is no operator here to approve one.
- **The mutation-coverage sweep over the four suites the 130 plan owns, and the two arithmetic
  corrections to that plan's report (its test/file tallies and its two `./pw verify` totals).** Those
  are plan-record accuracy and test-discrimination work with a different mechanism and a different
  surface (`report-01.md` plus four whole test suites); folding them in would double this plan's
  surface for no shared machinery.
- **The 090 report's misattributed PR number, and its "Three." versus four-deliverables ambiguity.**
  Same reason: both are single-line record corrections in a different plan's report, with no mechanism
  in common with the three instruments this plan is about.
- **`_detect_count_prose`'s silent `except OSError: continue`.** An unreadable contract source is
  dropped with no counter and no note — a real fail-open, but it predates the work this plan follows,
  it cannot flip a verdict (the `count_prose` list is excluded from `counts.total`), and closing it
  means adding a counter to the surfacer envelope, which is D4's mechanism applied to a different
  instrument. Recorded here so it is not re-discovered as new.
- **Widening the escape set's provider coverage beyond making the GitLab producer's records
  well-formed.** D3 fixes the record shape; it does not add GitLab-specific partition machinery or a
  GitLab reviewer roster, because no GitLab measurement exists to validate that against.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py` — D1's
  baseline denominator and new withheld reason, D2's escape-set population and attribution, D3's
  provenance and `resolve_bot_kind` docstring.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  — the withholding guarantee, the counting rule's resolution axis, the reviewer population, the
  selection effect, the Consumers table's duplication claim, and the instrument's declared scope.
- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — the canonical
  `review_gate_delta assess` block (D1, D3) and the list-flag population statements (D5).
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py` — D3's
  `add_finding` field pass-through.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` — D3's
  dead `KeyError` clause.
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — D4's
  verdict forms, limit-block condition, and un-run wording.
- `build.py` — D4's empty-analysis-scope outcome recording.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`,
  `.../standards/ci-verify.md`, `.../workflow/sonar-roundtrip.md`,
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — D4's per-gate structural limits (final set
  from P2).
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`
  and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
  — D4's dispatched-envelope `structural_limit` field.
- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py`
  and `.../SKILL.md` — D5's reach-axis record and `## Tests` index row.
- `.claude/skills/finalize-step-review-retrospective/SKILL.md` — D1's guarantee restatement and D3's
  Step 3b invocations.
- `test/plan-marshall/automatic-review/test_review_gate_delta.py`,
  `test_counting_rule_parity.py`, `test_bot_participation_contract.py`,
  `test/plan-marshall/build-pyproject/test_gate_coverage.py`,
  `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py` — the tests every
  *Done when* names, plus D5's committed derivation artifact.
- `doc/plans/review-apparatus/090-feed-pr-findings-back-into-local-review/report-01.md` — D6's two
  record corrections only.

## Claim labels

Every scoping premise is labelled. Each confirm/refute artifact is **git-reachable from this clone**,
and none is a `.plan/` path. That is a scoping choice, not a reachability fact: `.plan/` carries two
tracked exceptions (`.plan/marshal.json` and `.plan/project-architecture/`, per `.gitignore:45-47`),
and this plan simply settles no premise from either.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `_share_withheld_reason` tests `len(covered) < len(roster)` against a caller-supplied `enabled_bots`, so narrowing the roster removes the withholding | OBSERVED | `review_gate_delta.py` — `assess_delta` (the `roster` / `covered` / `coverage` assignments) and `_share_withheld_reason` |
| A narrowed roster yields `structural_share: 100.0` at `reviewer_coverage: 1/1` on the same escapes and SHAs | HYPOTHESIS — the mechanism is read, the output is not executed here | The two-arm test D1's *Done when* requires; run it against pre-fix code first and record what it printed |
| "Disable this reviewer for this PR" is a sanctioned `refused_structural` remedy enacted by narrowing `required_bots`/`optional_bots`, which is the `--enabled-bots` roster | OBSERVED | `bot-participation-contract.md` — the `refused_structural` taxonomy row and its remedy restatements; the Consumers table row for `review_gate_delta assess` |
| `review_gate_delta.py` never reads a finding's `resolution` | OBSERVED (asserted absence — re-verify by grep before relying on it) | `grep -n "resolution" review_gate_delta.py` returns nothing; `review_commitments.RELEASED_RESOLUTIONS` and `_findings_core`'s `'resolution': 'pending'` seed are the counterparts |
| The escape comprehension filters on `_is_actionable` only, never on `bot_kind` or the roster | OBSERVED | `assess_delta`'s `escapes = [...]` comprehension |
| `gitlab_pr.py`'s `add_finding` call passes no `author`, `kind`, `bot_kind` or `reviewed_commit_sha` | OBSERVED (asserted absence) | The `add_finding(` call in `gitlab_pr.py`; the GitHub counterpart in `github_pr.py` passes all four |
| The quality gate declares no `verdict_inputs`, so every HEAD advance re-runs it and a loop-back does re-gate | OBSERVED | `pre-push-quality-gate.md` § "Verdict-input surface — deliberately undeclared" |
| `_render_structural_limits` returns `[]` for a degraded-only boundary, and `CoverageBoundary.complete` is `not self.degraded` | OBSERVED | `_gate_coverage.py` — `_render_structural_limits`' opening two statements and the `complete` property |
| `build.py` is the only consumer of `_gate_coverage`, and every `render_coverage_summary` call site there is preceded by a `record_checked` or `record_degraded` | HYPOTHESIS — the call sites were read, the exclusivity was not swept | Grep `render_coverage_summary\|CoverageBoundary\|_gate_coverage` across the repo excluding `target/`, `test/` and `doc/plans/`, then read each `build.py` call site |
| The self-review `structural_limit` reaches the surfacer TOON but has no dispatched-envelope field | OBSERVED | `self_review.py`'s `'structural_limit': _format_structural_limit()` emission; `pre-submission-self-review.md` § "it is published, not discharged" |
| `ci-verify.md` and `sonar-roundtrip.md` carry no structural-limit statement, and plugin-doctor's two mentions are scope statements | OBSERVED (asserted absence) | `grep -n "structural limit\|does NOT evaluate\|cannot evaluate"` over the three files; compare each hit against `pre-push-quality-gate.md`'s scope-versus-structural-limit table |
| `_COUNT_PROSE` requires the noun immediately adjacent to the number, and `_CARDINALITY_NOUNS` omits `flags?` | OBSERVED | `_self_review_patterns.py` — `_CARDINALITY_NOUNS` and the `_COUNT_PROSE` regex |
| The detector's file scope is `SKILL.md` plus `standards/*.md` only, excluding every `.py` docstring | OBSERVED | `_collect_skill_contract_sources` and its use inside `_detect_count_prose` in `_self_review_detectors.py` |
| No committed artifact reproduces the noun-set derivation | OBSERVED (asserted absence — the higher-risk half; re-verify before building one) | Grep `derive_nouns\|follower distribution\|cardinality noun` across `test/` and `marketplace/`; the only hits are prose, not a derivation |
| The two prose count claims in `test_bot_participation_contract.py` contradict that file's own derived data | OBSERVED | The docstring of `test_confirmed_site_carries_its_own_flag_set_fully_quoted` against `_CONFIRMED_SITES`; the `#:` comment above the list-flag alternation against the parser-derived `_ALL_LIST_FLAGS` |
| `automatic-review/SKILL.md`'s eight and nine list-flag figures are both correct for their own call sites | OBSERVED | The `review_completeness check` invocation printed above the "eight" sites; `_add_bot_observation_flags`' docstring in `review_completeness.py` for the nine |
| Every count in this plan (files, matched lines, detector registry size, candidate lists, gates, restatement sites) | HYPOTHESIS — all are leads | ⛔ **Re-derive each at HEAD. Do not trust a number written in this plan.** The tree has moved since it was authored, and this plan's whole subject is a count restated without re-derivation |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half here:
four of the claims above are absences, and each sends the run to build something if it holds. Verify
each before building against it.

## Verification

Beyond every per-deliverable *Done when*:

1. **Build gate.** `./pw verify` per the lane contract's build-gate rule. The diff touches `*.py`, so
   the Python gate applies.

2. ⚠ **Metric-precision probes — every published metric, at the boundaries of its own precision.**
   This plan touches computed shares and counts, and a share is exactly the kind of figure whose
   defects hide at the edges. For **each** metric this plan emits or changes (`structural_share`,
   `reviewer_coverage`, `escapes_total`, `by_partition`, every published exclusion count, and the
   coverage verdict word), drive and assert all of:
   - **an empty population** — no findings, no roster members, no dimensions recorded;
   - **a divide-by-zero** — a share whose denominator is 0, including the `0/0` roster case, which
     must never render as full coverage;
   - **a single-member roster** — the exact state the blocker exploits, at `1/1`;
   - **distinguishability of zeros** — assert that a *withheld* zero, an *unmeasured* zero and a
     *genuine* zero are each distinguishable in the emitted payload without reading prose. A
     `structural_share: null` with `share_withheld` set, an `escapes_total: 0` at full coverage, and a
     `verdict: excluded` must not be collapsible by a consumer into the same reading. State in the
     report, per metric, which of the four probes it passed and what the payload looked like at each.

3. ⚠ **Cold read of the operator-facing text.** The published metric, its `share_withheld` and
   `exclusion_reason` strings, and the build gate's coverage verdict are text an operator reads to
   decide something, so "implemented as specified" cannot verify them. Dispatch the lane's pre-PR
   verification sub-agent (`cloud-plan-lane` § Step 6) with the text **and nothing else** — no plan, no
   deliverable list — and have it answer, in its own words:
   - Given this verdict payload, **what is the state of our gates?** Run this once for a payload at
     `WITHHELD_ROSTER_NARROWED`, once for one at `verdict: excluded`, and once for a genuine
     `structural_share` at full coverage against the baseline.
   - Given this coverage verdict, **what did this gate check, and what did it not?** Run it for the
     empty boundary, the degraded-only boundary, and a module-scoped `quality-gate`.

   ⛔ The narrowed-roster and excluded readings **must not** come back as any form of "the gates are
   fine" or "nothing escaped". If a reading is wrong, the wording failed however complete it looks —
   fix the wording and re-read. **Record in the report which reading each cold read returned, verbatim,
   including any that had to be re-read.**

4. **Re-derivation of every count.** Re-derive D0's three populations and every count this plan
   states, at the moment of the claim, and record each derived figure in the report beside the command
   that produced it. A count carried forward from this plan's text without re-derivation is a defect,
   and it is the defect this epic exists to close.

5. **Read-only checks (not executable).** Confirm by reading that: the four sites restating the
   withholding guarantee say the same thing as the code after D1; the five sites carrying the selection
   effect are verbatim-consistent with the emitted `_PROVENANCE` string after D3; and no D6 proposal
   was written as a rule, a default, or a contract requirement.

6. **Collateral-change check.** Diff the touched-file set against § Expected surface and report every
   file outside it, with why it was touched.

## Notes

- **This plan's subject is its own risk.** Its thesis is that a restated count is a defect class, so a
  count restated from this plan without re-derivation would reproduce the archetype inside the fix.
  Every figure here is written as a lead for that reason.
- **The blocker is a prohibition already on the books.** The 130 plan stated ⛔⛔ *"a metric that can
  produce [the inversion] must not ship"*, and the contract names `100.0` as the exact failure mode.
  D1 is not a new rule — it is the existing rule made true of the code.
- **The delta's verdict already publishes `enabled_bots` and `reviewer_coverage`**, so a reader who
  compares rosters across PRs can in principle see a shrink. Nothing in the tree performs that
  comparison, and no baseline is recorded against which a shrink is even detectable — which is why D1
  publishes the baseline rather than relying on a reader to notice.
- **G9's empty-boundary defect is latent, not production-reachable.** Fix it and say so plainly in the
  report; do not describe it as a live escape. The 130 plan asked its run to *say so* if that branch
  was reached, and its report recorded the branch as not reached — true of a sibling instance, not of
  this one.
- **The 090 corpus corrections are not stale-count fixes.** Both list-flag figures in
  `automatic-review/SKILL.md` are correct; what is missing is the statement of which population each
  counts. A run that "fixes" one of those numbers has made the document worse.
- **Nothing was dropped from the two gaps files as non-reproducing.** Every defect this plan carries
  was re-read at the source before it was written down. The gaps those files carry that this plan does
  **not** take are excluded on scope, not on validity — see § Out of scope, which names each and why.
- **No plugin-cache sync is owed.** This plan edits `marketplace/bundles/`, but a cloud lane run
  neither performs a `/sync-plugin-cache` nor records one as owed: the sync reads a git-ignored
  `target/` tree and writes outside the repository, and the merged bundle source is authoritative.
