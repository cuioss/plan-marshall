# Gaps — 130-review-bots-catch-what-in-house-gates-cannot

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis. Eighteen entries: 1 blocker, 7 major, 10 minor.

## G1 — Anchor the delta's coverage denominator so a roster shrink cannot restore a share

- **Severity:** blocker
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py:408-427`
  (`_share_withheld_reason`, the test at `:417`). The guarantee is restated in four places, all of them
  wrong in the same way: `review_gate_delta.py:52-59`,
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:604-609`,
  `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:1095-1100`, and the plan's own
  commit message. The untested axis is
  `test/plan-marshall/automatic-review/test_review_gate_delta.py:142-168`.
- **Evidence:** the withholding test is `if len(covered) < len(roster)` against a **caller-supplied**
  roster. Executed probe (`assess_delta` called directly, gates green, both SHAs `'a'*40`, two escapes
  both labelled `gate_structural`):

  ```
  enabled_bots=['coderabbit','sourcery','pr-agent'] reviewed_bots=['coderabbit']
    -> verdict=measured  structural_share=None  cov=1/3  share_withheld=partial_reviewer_coverage
  enabled_bots=['coderabbit']                    reviewed_bots=['coderabbit']
    -> verdict=measured  structural_share=100.0 cov=1/1  share_withheld=None
  ```

  Same diff, same escapes, same partition, same one reviewer actually speaking — the guard fires on the
  first and not on the second. `100.0` is verbatim the number `bot-participation-contract.md:604-609`
  names as the failure mode (*"a naive share reports 100% — 'the gates are perfectly configured' —
  when the only thing that changed is who spoke"*).
- **Precondition, stated rather than assumed:** the shrink is not automatic. It requires an operator to
  enact the `refused_structural` remedy *disable this reviewer for this PR*
  (`bot-participation-contract.md:62`, `:90`, `:125`, `:344`) by narrowing the step's `required_bots` /
  `optional_bots` — which is the roster the caller passes as `--enabled-bots`
  (`automatic-review/SKILL.md:1085`, `bot-participation-contract.md:663`). The other two remedies do
  **not** reach it: *split* changes the diff, and *accept the gap* leaves the refusing bot enabled, so
  coverage stays partial and the share stays withheld. The route is nonetheless first-class rather than
  hypothetical — `9e9e9880` (PR #1241) introduced `refused_structural` and its remedy set after this
  plan landed.
- **Impact:** the plan's ⛔⛔ prohibition — *"a metric that can produce [the inversion] must not
  ship"* — is not satisfied, and four sites (two of them production docstrings a maintainer will read
  as a guarantee) state an absolute property the code does not have. The verdict does publish
  `enabled_bots` and `reviewer_coverage`, so a reader who compares rosters across PRs can see the
  shrink; nothing in the tree performs that comparison, and no baseline is recorded against which a
  shrink is even detectable.
- **Task:** make the denominator an observed constant rather than a caller argument, or make a
  shrink observable and disqualifying. Concretely: add a `--roster-baseline` (or equivalent) input
  carrying the configured roster independent of any per-PR disable, and emit a new
  `WITHHELD_ROSTER_NARROWED` reason when the effective roster is a proper subset of the baseline;
  publish both sets on the verdict. Restate the guarantee in terms of the baseline at all four sites
  above, rather than as an unqualified property of coverage.
- **Done when:** a test that shrinks `enabled_bots` between two arms — same escapes, same partition,
  same SHAs — asserts the second arm withholds the share; and no input reachable from
  `finalize-step-review-retrospective` Step 3b can produce a share at reduced real coverage.
- **Suggested grouping:** automatic-review / review-gate-delta

## G2 — Exclude findings the run rejected from the gate-escape count

- **Severity:** major
- **Kind:** bug
- **Where:** `review_gate_delta.py:249-259` (`_is_actionable`) and `:313-326` (the escape
  comprehension); the counting rule it consumes is
  `bot-participation-contract.md:508-521`; the sibling that already classifies resolutions is
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py:95-101`.
- **Evidence:** `grep -n "resolution" review_gate_delta.py` returns **no match** (exit 1) — the module
  never reads a finding's disposition. Executed probe with one finding
  `{'hash_id': 'h1', 'kind': 'inline', 'bot_kind': 'coderabbit', 'resolution': 'rejected'}` labelled
  `gate_structural`, at full coverage: `escapes_total=1  structural_share=100.0`. `rejected` is a real
  stored value, not a hypothetical: `review_commitments.RELEASED_RESOLUTIONS`
  (`{'rejected', 'suppressed'}`) treats exactly it as *the reviewer was wrong, nothing is owed*, and
  `add_finding` seeds every record at `resolution: 'pending'`
  (`manage-findings/scripts/_findings_core.py:268`). The delta's own definition of an escape
  (`review_gate_delta.py:12-16`) is *"something the gates ran over and did not report"* — a finding the
  run rejected as wrong is not that; the gates were right and the reviewer was not.
- **Impact:** every bot false positive inflates `escapes_total` and, when labelled, the residual
  attributed to the gates. The partition taxonomy has no member for "not a defect", so such a finding
  must either be mislabelled into one of the two real buckets or left `unpartitioned`, which withholds
  the whole PR's share. Two counters over one findings store disagree about what a rejected finding is.
- **Task:** decide and document whether the escape set is filed-and-actionable **and not rejected**.
  If yes: filter `RELEASED_RESOLUTIONS`-style dispositions out of the escape comprehension, add the
  excluded count to the published population (as `review_commitments.count_unanchored` does, so the
  exclusion is visible rather than shrinking a denominator silently), and extend
  `bot-participation-contract.md` § "The counting rule" with the resolution axis so both counters
  apply it. If no: state in the module docstring and the contract why a rejected finding still counts
  as a gate escape, and why the two modules differ.
- **Done when:** the delta's treatment of `rejected` / `suppressed` findings is stated in the
  contract, implemented, and pinned by a test that supplies one of each and asserts the resulting
  `escapes_total` and published exclusion count.
- **Suggested grouping:** automatic-review / review-gate-delta

## G3 — The `author` fallback is unreachable on every producer; make it real or stop justifying it

- **Severity:** major
- **Kind:** bug
- **Where:** `review_gate_delta.py:177-194` (`resolve_bot_kind`, the rationale at `:180-186`);
  `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py:274-282`
  (the `add_finding` call); the mirroring fixture at
  `test/plan-marshall/automatic-review/test_counting_rule_parity.py:144-148` (the rationale comment)
  and `:154-158` (the case).
- **Evidence:** the docstring justifies the `author` fallback with *"the GitLab producer
  (`gitlab_pr`) never sets [`bot_kind`] at all. Keying on `bot_kind` alone would silently disable
  every per-bot rule on the whole GitLab path"*. The first half is true; the second does not follow,
  because the fallback's own selector is absent there too. The GitLab producer's call is

  ```python
  add_finding(
      plan_id=plan_id, finding_type='pr-comment', title=title, detail=detail,
      file_path=path or None, line=line_arg, raw_input={'body': body},
  )
  ```

  — no `author=`, no `kind=`, no `bot_kind=`, no `reviewed_commit_sha=`, even though `kind` and
  `author` are computed locally at `gitlab_pr.py:247-249` and used only to build the `title` /
  `detail` strings. `add_finding` accepts all four kwargs (`_findings_core.py:224-241`) and
  `github_pr.py:1141-1144` passes all four, so the omission is GitLab-side only, and `add_finding`
  omits a falsy key entirely (`_findings_core.py:285-292`). Consequences on a GitLab record:
  `_is_actionable` sees no `kind` and returns `False` for every record (`escapes_total` always 0);
  `resolve_bot_kind` returns `''`; and `EXCLUSION_GATE_TREE_UNKNOWN` fires because no
  `reviewed_commit_sha` exists.

  The fallback is equally unreachable on the **GitHub** path today. `github_pr` derives `bot_kind` via
  `github_re_review.bot_kind_for_author`, and `resolve_bot_kind` falls back to
  `bot_registry.bot_kind_for_login`. Executed probe over every registered login and its `[bot]` /
  mixed-case variants (`coderabbitai`, `CodeRabbitAI`, `coderabbitai[bot]`, `sourcery-ai`,
  `cuioss-review-bot`, plus an unregistered login): the two functions agree on all six, so a record
  carrying `author` but no `bot_kind` is one whose author no registry doc claims — and the fallback
  returns `''` for it as well. The parity corpus case labelled *"summary identified from the author
  login with no bot_kind"* encodes `{'author': 'coderabbitai', 'kind': 'review_body', …}` — a shape no
  producer emits — which is precisely the fixture-encodes-an-unemitted-shape class the run's own
  § "What have we learned" proposes a contract bullet for.
- **Impact:** the delta is inert on GitLab and silently so; a production rationale in the shared
  bundle claims a remedy that cannot fire on either provider; and a test "proves" a fallback over a
  record shape production never produces.
- **Task:** either (a) pass `author`, `kind`, `bot_kind` and `reviewed_commit_sha` through
  `gitlab_pr.py`'s `add_finding` call so GitLab records carry the same first-class fields as GitHub's,
  and re-point the parity corpus case at the resulting real shape; or (b) correct
  `resolve_bot_kind`'s docstring and the corpus comment to say the GitLab path stores neither
  selector and that the GitHub path's two resolvers currently agree, and record the GitLab inertness
  explicitly in `bot-participation-contract.md` § "The review-versus-gate delta".
- **Done when:** the claim in `review_gate_delta.py:180-186` is true of the producers as they stand,
  and every parity-corpus record is a shape some producer demonstrably emits (assert it against the
  producer, not against the comment).
- **Suggested grouping:** automatic-review / cross-provider finding shape

## G4 — Correct the delta's published selection effect

- **Severity:** major
- **Kind:** bug
- **Where:** `review_gate_delta.py:162-176` (`_PROVENANCE`) and its module docstring `:19-27`;
  `bot-participation-contract.md:633-639`;
  `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:1080-1084`;
  `.claude/skills/finalize-step-review-retrospective/SKILL.md:369-386`; and the same sentence in the
  run report's D2 section.
- **Evidence:** all five sites assert that *a forward pass never re-gates*, and therefore that *"the
  ONLY measurable PRs are those where **neither** post-gate mutating step committed anything"*. The
  first clause is true only of a forward pass. `pre-push-quality-gate.md:315` states the gate
  *"declares **no** `verdict_inputs` … so the dispatcher's verdict-currency classifier never narrows
  its re-fire: **every HEAD advance re-runs it**"*, its frontmatter declares `order: 5` /
  `head_dependent: true`, and
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py:435-438`
  confirms the mechanism (`REASON_UNDECLARED` → `VERDICT_INVALIDATED`), which the dispatcher turns
  into RE-FIRE at `phase-6-finalize/SKILL.md:690`. So on a loop-back re-entry the gate **does**
  re-fire and re-stamp `head_at_completion`, and the measurable condition is a property of the
  **final** pass, not of the whole run.
- **What the correction does NOT license:** the re-gate does not widen the measurable set for the
  loop-backs that matter. `github_pr` pre-filter 5 dedups on `(bot_kind, comment_id)` and never
  re-stamps an existing finding's `reviewed_commit_sha` (`github_pr.py:1093-1103`), so after a
  review-driven loop-back the store holds findings from two iterations carrying two different SHAs;
  Step 3b's own rule is *"pass the value only when every finding agrees on it; when they disagree,
  pass nothing"* (`finalize-step-review-retrospective/SKILL.md:347-348`), which excludes the PR as
  `gate_tree_unsubstantiated`. If instead the re-review filed nothing new, every finding still carries
  the pre-loop-back SHA while the gate re-stamped the new one, and the PR excludes as
  `gates_did_not_cover_reviewed_tree`. A re-gate therefore only helps a loop-back driven by something
  **other** than review findings. The measurable set is *"PRs whose final pass had no post-gate commit
  and whose findings all carry one SHA equal to the gate's final stamp"* — narrower than the
  correction alone suggests, and with no established bias toward PRs where review found something.
- **Impact:** provenance accuracy is a plan-mandated deliverable (*"publishes its population and
  provenance"*), so a provenance that mis-states the mechanism is a defect in D2 itself. Five sites
  must be corrected together or they drift apart.
- **Task:** rewrite `_PROVENANCE`'s selection-effect clause to describe the loop-back re-gate, the
  actual measurable condition, and the mixed-SHA exclusion that follows a review-driven loop-back.
  Mirror the correction in the module docstring, the contract section, the bundle SKILL.md canonical
  block, and Step 3b's consumer text, which must stay verbatim-consistent with the emitted string.
- **Done when:** the five sites describe the same, correct mechanism, and a test asserts the
  `provenance` string emitted by `assess_delta` matches the contract's stated wording (so the two
  cannot drift again).
- **Suggested grouping:** automatic-review / review-gate-delta

## G5 — Render the structural-limit block on a PARTIAL verdict whose first dimension degraded

- **Severity:** major
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:322-324`;
  reachable via `build.py:442-449`; the test that misses it is
  `test/plan-marshall/build-pyproject/test_gate_coverage.py:285`.
- **Evidence:** `_render_structural_limits` opens with

  ```python
  pairs = structural_limits(boundary.checked)
  if not pairs:
      return []
  ```

  and `cmd_quality_gate` calls `cmd_compile` **first** (`build.py:442`), so a freshness-suspect mypy
  records `degraded` only (`build.py:317`) and halts to `render_coverage_summary` at `build.py:448`.
  Executed probe on a boundary seeded with one `record_degraded` and no `record_checked`:

  ```
  >>> coverage: PARTIAL — this pass does NOT certify the whole tree. The gate did NOT fully check:
        - mypy(production) [660 files, cache disabled]: freshness suspect — too fast
      A clean exit here is NOT a full pass — the dimensions above are un-certified, …
  ```

  — no per-analysis limits and no `not run in this gate at all: …` line. That contradicts the
  governing standard's own table row (`pre-push-quality-gate.md:87`), which states the structural
  limit is *"Reported as: a per-analysis block on **both** the COMPLETE and PARTIAL verdicts"*. The
  covering test seeds `record_checked('ruff [marketplace/bundles]')` before `record_degraded`, so the
  reachable shape is untested — every `record_degraded` call site in the suite (`:126`, `:146`,
  `:293`, `:368`) is paired with a `record_checked`.
- **Impact:** the first and most likely gate failure path emits a verdict with no scope limit at all,
  against D0's *Done when* ("each gate's verdict carries its own scope limit"). The guard's
  justification ("a run that performed no analysis") conflates *checked nothing* with *attempted
  nothing*: a degraded dimension **was** attempted.
- **Task:** change the early-return condition so it suppresses only when the boundary is entirely
  empty (`not boundary.checked and not boundary.degraded`), and derive the limit pairs from
  `checked + degraded` stems so a degraded analysis still states what it structurally cannot see.
  Keep the un-run line derived from the union of attempted stems, as today.
- **Done when:** a test seeding a boundary with one degraded dimension and **no** checked dimension
  asserts the rendered summary contains both `does NOT evaluate` and `not run in this gate`.
- **Suggested grouping:** build-gate / gate-coverage honesty

## G6 — The escape set has no reviewer population, so a human review comment withholds the share

- **Severity:** major
- **Kind:** bug
- **Where:** `review_gate_delta.py:313-326` (the escape comprehension) and `:249-259`
  (`_is_actionable`); the coverage denominator it is compared against is `:310-312`; the partition
  labels come from `.claude/skills/finalize-step-review-retrospective/SKILL.md` Step 2–3, whose row
  domain is the **enabled reviewer roster** (`:209-211`, `:479`).
- **Evidence:** the escape comprehension filters on `_is_actionable` only — never on `bot_kind`, never
  on the roster. Human PR comments are stored as ordinary `pr-comment` findings: `github_pr` resolves
  `bot_kind` to `None` for a human author (`github_pr.py:1025`), `add_finding` then omits the key
  (`_findings_core.py:291-292`), and the noise pre-filter explicitly keeps human comments
  (`github_pr.py:318-338`: *"Human comments (`bot_kind is None`) are checked against the shared layer
  …"*). Executed probes at full 3/3 coverage:

  ```
  one labelled bot escape                       -> share=100.0  withheld=None      total=1
  same + one human inline comment, unlabelled   -> share=None   withheld=unpartitioned_escapes  total=2
  one human inline comment only                 -> share=None   withheld=unpartitioned_escapes  total=1
  ```

  Step 3's qualitative pass produces one row per **enabled reviewer**, so a human finding gets no
  `--partitions` label, lands `unpartitioned`, and withholds the share for the whole PR. No test in
  `test_review_gate_delta.py` drives a record with no `bot_kind`
  (`test_a_substantive_review_body_from_another_author_is_still_an_escape:539` uses a second **bot**),
  and no site — `_PROVENANCE`, the contract, or Step 3b — mentions the effect.
- **Impact:** the numerator's population and the denominator's population are different sets, which is
  exactly the invisible-denominator defect § "The counting rule" exists to remove. The direction is
  fail-closed rather than inverting, but it silently removes from the measurable set every PR a human
  commented on — compounding the tree-identity exclusion the report already names as the reason few
  measurements will accumulate, and doing so undisclosed.
- **Task:** decide whether a human review comment is a gate escape. If yes, extend the partition
  judgment to cover findings outside the bot roster and say so in the contract; if no, filter the
  escape set to records whose resolved `bot_kind` is in the roster and publish the excluded count
  beside the population. Either way, state the decision in `_PROVENANCE` and in
  `bot-participation-contract.md` § "The review-versus-gate delta".
- **Done when:** a test drives `assess_delta` with a record carrying no `bot_kind` and asserts the
  documented treatment, and the emitted provenance names the reviewer population the escape count is
  computed over.
- **Suggested grouping:** automatic-review / review-gate-delta

## G7 — The counting rule's "two independent implementations" claim is stale

- **Severity:** major
- **Kind:** stale-doc
- **Where:** `bot-participation-contract.md:663` (Consumers table, `review_gate_delta assess` row);
  the code that falsifies it is
  `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:156-174`; the
  test whose motivation it supplies is `test/plan-marshall/automatic-review/test_counting_rule_parity.py:174-190`.
- **Evidence:** the contract says *"the two implement the same rule **independently** because they
  live in different bundles, so a change to the rule must land in both."* But
  `review_retrospective._is_status_summary` now reads

  ```python
  from review_gate_delta import is_status_summary
  return bool(is_status_summary(record))
  ```

  and its own docstring says *"there is now one implementation"*. So on the status-summary axis —
  the load-bearing half, and the one both implementations were previously wrong about —
  `test_both_implementations_agree_on_every_corpus_record` compares a function with itself. Only the
  kind classification (`review_gate_delta._is_actionable:249-259` vs
  `review_retrospective._is_actionable:177-192`) remains genuinely duplicated, and the two differ
  there: the delta's `return kind in _ACTIONABLE_KINDS` versus the retrospective's explicit
  `if kind == 'inline': return True` / `return False`.
- **Impact:** the contract instructs a future editor to mirror a change into a second implementation
  that no longer exists, and the parity test's stated guarantee is stronger than what it checks.
- **Task:** rewrite the Consumers row to say the summary predicate is a single shared implementation
  the retrospective imports, and that only the kind classification is duplicated; narrow the parity
  test's docstring to the axis it actually pins, or collapse the remaining duplication so the file
  becomes a delegation test.
- **Done when:** no site claims two independent implementations, and the parity test's docstring
  names the axis it discriminates on.
- **Suggested grouping:** automatic-review / counting rule

## G8 — The "not run in this gate at all" line is false for two reachable states

- **Severity:** major
- **Kind:** bug
- **Where:** the wording at `_gate_coverage.py:352-358`; the two states that reach it are
  `build.py:344-345` and `:364-365` (`_skip_empty_mypy_scope` returning 0 with no record) and
  `build.py:485-499` (the `if module is None:` guard around plugin-doctor).
- **Evidence:** `_render_structural_limits` derives `not_run` as `_ANALYSIS_LIMITS` minus the
  attempted stems and prints *"absent from the list above because this gate **never performs them**,
  NOT because they passed"*. Two reachable states are neither:

  1. **Attempted over an empty scope.** When no file under the scoped path survives mypy's excludes,
     `cmd_compile` / `cmd_test_compile` `return 0` before `_run_mypy`, so the dimension is recorded
     neither as checked nor as degraded. The gate *does* perform that analysis; it found nothing to
     analyse.
  2. **Conditionally performed.** `cmd_quality_gate` runs plugin-doctor only when `module is None`
     (`build.py:485`), so a module-scoped `quality-gate` — the ordinary per-commit invocation — leaves
     `plugin-doctor` unattempted and prints it under *"this gate never performs them"*, which is false
     of the same gate in whole-tree mode. The governing standard names only the true case
     (`pre-push-quality-gate.md:116-117`: *"`quality-gate` runs no pytest and no test-tree mypy"*) and
     is silent on both of these.
- **Impact:** the line intended to separate "not run" from "passed" introduces two further unlabelled
  states and mislabels both as the first — inside the very function D0 rewrote to remove exactly that
  ambiguity.
- **Task:** record an explicit third outcome for an empty analysis scope (a `record_skipped` on the
  boundary, or a `record_degraded` with reason "no file in scope"), render it as its own line, and
  narrow the un-run wording so it distinguishes *this gate never performs it* from *this invocation
  did not reach it*.
- **Done when:** a module-scoped `quality-gate` prints a verdict that distinguishes the three states,
  and tests pin the empty-scope and the module-scoped-plugin-doctor cases.
- **Suggested grouping:** build-gate / gate-coverage honesty

## G9 — An empty coverage boundary renders COMPLETE

- **Severity:** minor
- **Kind:** bug
- **Where:** `_gate_coverage.py:181-184` (`CoverageBoundary.complete`) and `:387-393` (the COMPLETE
  branch); pinned as intended by `test_gate_coverage.py:376`.
- **Evidence:** `complete` is `return not self.degraded`. Executed probe on
  `render_coverage_summary(CoverageBoundary())`:

  ```
  >>> coverage: COMPLETE over the dimensions below — checked over full scope: (nothing)
  ```

  with no limit block and no un-run line. "No dimension was analysed" and "every dimension passed"
  produce the same verdict word. This is the one-signal-two-meanings archetype the plan's own Notes
  identify as living in at least three places (*"'No module matched' and 'no tests needed' are one
  signal in both places"*), now in a fourth — inside the function D0 rewrote. The plan asked the run
  to **say so** if it reached that branch; the report's Residue instead records the branch as not
  reached, which is true of the sibling epic's footprint code but not of this instance.
- **Impact, and why this is minor rather than major:** the shape is real but **not reachable from
  production**. `build.py` is the only consumer of `_gate_coverage`
  (`grep -rn "render_coverage_summary\|CoverageBoundary\|_gate_coverage"` over the repo excluding
  `target/`, `doc/plans/` and `test/` returns `build.py` and the two standards docs only), and every
  one of its five `render_coverage_summary` call sites (`build.py:448`, `:502`, `:556`, `:563`,
  `:572`) is preceded by at least one `record_checked` or `record_degraded`. The defect is latent, and
  the reporting obligation the plan set is the live part of it.
- **Task:** introduce a third verdict form for an empty boundary — e.g. `>>> coverage: NONE — this
  pass analysed no dimension; it certifies nothing` — and make `complete` false when nothing was
  checked. Replace `test_empty_boundary_does_not_claim_a_limit_block_it_cannot_populate` with one
  asserting the new form. Record the instance in the epic's archetype note so it is counted rather
  than re-discovered.
- **Done when:** `render_coverage_summary(CoverageBoundary())` contains neither `COMPLETE` nor
  `PARTIAL`, and a test asserts that.
- **Suggested grouping:** build-gate / gate-coverage honesty

## G10 — D2's instrument has no consumer outside the meta-project

- **Severity:** minor
- **Kind:** incomplete
- **Where:** the only invocation site is
  `.claude/skills/finalize-step-review-retrospective/SKILL.md:354` (project-local); the script,
  contract and canonical block ship in the shared bundle
  (`marketplace/bundles/plan-marshall/skills/automatic-review/`).
- **Evidence:** `grep -rn "review_gate_delta"` over `--include=*.py --include=*.md --include=*.json
  --include=*.toon`, excluding `doc/plans/`, `target/` and `.plan/`, returns: the script itself, its
  tests, the bundle's `SKILL.md` canonical block (`:962`, `:1055-1058`), the contract's two references
  (`:572`, `:663`), and the one project-local consumer. `find marketplace -type d -name
  "*review-retrospective*"` returns nothing, so no bundle-level finalize step invokes it.
- **Impact, and why this is minor:** every consuming project receives the instrument and the contract
  and nothing that runs it, so the epic's parity hypothesis can only be tested in this repository.
  That is a narrower miss than it first looks: the plan's Expected surface named *"`manage-metrics` or
  a retrospective check"* as D2's measurement home, and this repository's only retrospective check is
  project-local — so the run shipped into a surface the plan named. No *Done when* clause requires a
  bundle consumer.
- **Task:** decide the intended home. Either promote a delta-emitting step into the shared bundle
  (its natural seat is beside `automatic-review`, after the findings are triaged and the partition
  judgment exists), or state explicitly in `bot-participation-contract.md` § "The review-versus-gate
  delta" that the instrument is meta-project-instrumented only, and why.
- **Done when:** either a bundle-shipped step invokes `review_gate_delta assess`, or the contract
  names the meta-project-only scope as a deliberate boundary.
- **Suggested grouping:** automatic-review / review-gate-delta

## G11 — Publish the resolved `bot_kind` on each escape

- **Severity:** minor
- **Kind:** bug
- **Where:** `review_gate_delta.py:317`.
- **Evidence:** the escape record is built with `'bot_kind': str(record.get('bot_kind') or '')`,
  reading the raw key, while `resolve_bot_kind` (`:177-194`) exists two functions above to answer
  exactly the case where that key is absent. Executed probe with
  `{'hash_id': 'g1', 'author': 'coderabbitai', 'kind': 'inline', 'body': 'x'}`:
  `escapes[0]['bot_kind'] == ''`, while `resolve_bot_kind` on the same record returns `'coderabbit'`.
- **Impact, and why this is latent rather than live:** two code paths in one function answer "which
  bot" differently, which will diverge the moment the fallback becomes reachable. It does not diverge
  today: no producer emits a record with a resolvable `author` and no `bot_kind` — `github_pr` sets
  `bot_kind` whenever `bot_kind_for_author` resolves, and that function and `bot_kind_for_login` agree
  on every registered login and its `[bot]` / mixed-case variants (executed probe, see G3). Fixing it
  is a one-line consistency repair, not a live-attribution repair.
- **Task:** call `resolve_bot_kind(record)` when building the escape entry.
- **Done when:** a test asserts a record carrying only `author` yields a non-empty `bot_kind` on its
  escape row.
- **Suggested grouping:** automatic-review / review-gate-delta

## G12 — Carry the self-review structural limit onto the step's recorded verdict

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:270`
  and `:272`; the emit site is
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py:409`;
  the contract is
  `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md:64-65,80`.
- **Evidence:** the workflow doc states *"the `--display-detail` budget … carries neither, and the
  dispatched-envelope schema below has no field for either"* (`:270`), concluding *"it is published,
  not discharged"* (`:272`). So the limit reaches the dispatched agent's TOON and stops there; the
  step's recorded verdict — what a later reader of `status.metadata.phase_steps` sees — still reads
  only `clean: {N} candidates examined, no check matched`.
- **Impact:** D0's *Done when* asks the **verdict** to carry the limit. The build gate does this (the
  block is part of the rendered verdict); self-review does not, so the asymmetry means one of the two
  gates D0 changed still hands a downstream reader an unqualified green.
- **Task:** add a `structural_limit` field to the dispatched-envelope schema in
  `ext-point-self-review-surfacing.md` and have the step forward the surfacer's value into it, so the
  limit lands on the step record rather than only on an intermediate tool's stdout. The
  `display_detail` budget stays untouched.
- **Done when:** the self-review step's recorded outcome carries the structural limit, and a test
  asserts the envelope field is populated on a clean full-surface round.
- **Suggested grouping:** self-review / gate honesty

## G13 — Give the three unlimited gates a structural limit

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md`,
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md` (its own step verdict).
- **Evidence:** `grep -n "structural limit\|does NOT evaluate\|cannot evaluate"` over the three files
  returns no hit in the first two; plugin-doctor's two hits (`:23`, `:167`) are a **scope** statement
  about scoped vs whole-tree mode — cured by widening, which `pre-push-quality-gate.md:85-88` says a
  structural limit by definition is not. The report records this as a deliberate boundary rather than
  an oversight; it remains open.
- **Impact:** D0's rule ("a gate whose green is scope-limited says so in its verdict") holds for
  three of six in-house gates.
- **Task:** for each of the three, name the analysis it performs and the defect class it cannot reach,
  and put the statement on its verdict — following `pre-push-quality-gate.md` § "A gate states what
  its green does not evaluate" as the pattern. `ci-verify` is the highest-value of the three: its
  green is the one most often read as whole-tree assurance.
- **Done when:** each of the three gates' verdicts carries a limit that is a property of its analysis
  rather than of its file set.
- **Suggested grouping:** finalize gates / gate honesty

## G14 — Correct the run report's test and file tallies

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/130-review-bots-catch-what-in-house-gates-cannot/report-01.md`
  § D3 ("100 tests added across six files") and § "Build gate" ("5 production scripts, 7 test files").
- **Evidence:** `git show 622f4484 -- 'test/**' | grep -c "^+.*def test_"` → **91**, across **eight**
  test files (4 / 3 / 4 / 32 / 11 / 4 / 29 / 4, re-derived per file). `grep -c "^+.*parametrize"` →
  **0**, so parametrisation does not close the gap. `git show --name-only --format="" 622f4484` lists
  **six** production `.py` files (`review_retrospective.py`, `bot_registry.py`, `review_gate_delta.py`,
  `review_commitments.py`, `_gate_coverage.py`, `self_review.py`) and eight under `test/`.
- **Impact:** small in isolation, but this plan's own thesis is that a count restated without
  re-derivation is a defect class; a report of that plan carrying two wrong counts is the archetype
  reproduced in the record of the fix.
- **Task:** correct both figures in `report-01.md`. Do not add a correction note or a dated entry —
  restate the numbers.
- **Done when:** both figures match `git show --name-only --format="" 622f4484`.
- **Suggested grouping:** plan records / report accuracy

## G15 — Reconcile the two `./pw verify` totals recorded for the same run

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `report-01.md` § "Build gate" (**19748 passed**) versus the squash commit message of
  `622f4484` (**19752 passed**, `git log --format="%B" -1 622f4484`).
- **Evidence:** both purport to be the final `./pw verify` of the same run and differ by four.
- **Impact:** one of the two is not the final run; a reader cannot tell which, and the figure is the
  report's only quantitative evidence that the build gate passed.
- **Task:** determine which figure is the final verify (the commit message is the later artifact) and
  make the report agree, or state that the report's figure is from the penultimate round.
- **Done when:** one figure appears in both places, or the report says which round each belongs to.
- **Suggested grouping:** plan records / report accuracy

## G16 — Give Step 3b a canonical invocation for the two SHAs it must resolve

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:342-351`.
- **Evidence:** every other command in that step is a fenced bash block, but the two inputs the
  escape claim rests on are prose: *"`{gate_head_sha}` — the `head_at_completion` recorded by
  `pre-push-quality-gate` (read the step record via `manage-status`)"* and
  *"`{reviewed_head_sha}` — the `reviewed_commit_sha` carried by the `pr-comment` findings"*. Both
  are reachable — `manage-status` persists `status.metadata.phase_steps[{phase}][{step}]` including
  `head_at_completion` (`manage-status/SKILL.md:379-390`), and `manage-findings list` returns the
  records (`manage-findings/SKILL.md:309`) — but neither is written down, and the agreement rule for
  the second is left entirely to the agent.
- **Impact:** the plan's own thesis names "a documented remedy with no reachable invocation" as the
  archetype the gates cannot catch; this is the weaker cousin — a reachable remedy with no written
  invocation, on the step whose omission silently excludes the PR.
- **Task:** add the two concrete commands, and state the disagreement rule as a mechanical check over
  the returned `reviewed_commit_sha` values rather than as prose.
- **Done when:** Step 3b resolves both SHAs through named commands with no undocumented step.
- **Suggested grouping:** review-retrospective / consumer wiring

## G17 — Remove the dead `KeyError` guard from `cmd_reconcile`

- **Severity:** minor
- **Kind:** dead-code
- **Where:** `review_commitments.py:401-405` (`cmd_reconcile`), against its own rationale at
  `:376-381`; the sibling for comparison is `review_gate_delta.py:465-471` (`cmd_assess`).
- **Evidence:** both CLIs wrap the identical expression `query_findings(plan_id,
  finding_type='pr-comment')['findings']`. `cmd_reconcile` catches `(OSError, ValueError, KeyError)`;
  `cmd_assess` catches `(OSError, ValueError)`. The delta's narrower tuple is the correct one:
  `_findings_core.query_findings:316-353` has no error-return branch and unconditionally returns a
  dict containing `findings`, so no `KeyError` is reachable at that call. `review_commitments`'
  own `_read_pr_comment_findings` docstring states the governing rule three lines above the guard —
  *"a dead guard against a shape the callee never produces reads as defence and provides none"* — and
  the `KeyError` clause is exactly that.
- **Impact:** trivial at runtime; the cost is that a reader comparing the two siblings concludes the
  delta is missing a guard, when the sibling is carrying a superfluous one that its own docstring
  argues against.
- **Task:** drop `KeyError` from `cmd_reconcile`'s except tuple so the two agree, and leave the
  docstring's rule as the stated reason.
- **Done when:** both CLIs catch the same exception set over the same call, and no dead clause remains.
- **Suggested grouping:** phase-6-finalize / review-commitments

## G18 — Mutation evidence covers eleven of ninety-one added tests

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `report-01.md` § D3 (the mutation table) against the plan's Verification clause
  *"Every D3 test proven discriminating by mutation."*
- **Evidence:** the report's mutation table lists six mutations covering, by its own attribution,
  3 + 1 + 2 + 2 + 2 + 1 = **11** tests. The commit added **91** (`git show 622f4484 -- 'test/**' |
  grep -c "^+.*def test_"`). The remaining eighty are asserted red-first, which is a weaker claim than
  mutation-discrimination — the report presents exactly what it did and does not overclaim, but the
  plan's demand is not met in full.
- **Impact:** the plan's own § "What have we learned" documents two cases in this very run where a
  test passed while the production predicate was dead or backwards, which is precisely the failure
  red-first does not catch and mutation does. The eighty un-mutated tests are the population that
  weakness applies to.
- **Task:** run a mutation pass over the four suites this plan owns
  (`test_review_gate_delta.py`, `test_review_commitments.py`, `test_gate_coverage.py`,
  `test_counting_rule_parity.py`), record which tests each mutation kills, and repair or delete any
  test no mutation of its subject can fail.
- **Done when:** every added test in those four suites is named against a mutation that kills it, or
  is recorded as deliberately un-mutatable with its reason.
- **Suggested grouping:** plan records / test discrimination
