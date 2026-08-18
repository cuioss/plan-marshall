# Gaps — 130-review-bots-catch-what-in-house-gates-cannot

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Anchor the delta's coverage denominator so a roster shrink cannot restore a share

- **Severity:** blocker
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py:415-425`
  (`_share_withheld_reason`); the guarantee is restated at `review_gate_delta.py:52-60`, at
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:601-611`,
  and in the plan's own commit message. The untested axis is
  `test/plan-marshall/automatic-review/test_review_gate_delta.py:142-168`.
- **Evidence:** the withholding test is `if len(covered) < len(roster)` against a **caller-supplied**
  roster. Executed probe (`assess_delta` called directly, gates green, SHAs equal, two escapes both
  `gate_structural`):

  ```
  enabled_bots=['coderabbit'] reviewed_bots=['coderabbit']
    -> verdict=measured  structural_share=100.0  reviewer_coverage=1/1  share_withheld=None
  ```

  That is verbatim the number `bot-participation-contract.md:606-611` names as the failure mode
  (*"a naive share reports 100% — 'the gates are perfectly configured' — when the only thing that
  changed is who spoke"*), produced without the guard firing. The route is live rather than
  theoretical: `bot-participation-contract.md:62` gives `refused_structural`'s remedy set as
  *"split, accept the gap, or **disable this reviewer for this PR**"*, and disabling a reviewer
  removes it from `required_bots ∪ optional_bots`, which is the roster the consumer passes
  (`.claude/skills/finalize-step-review-retrospective/SKILL.md:354-360`). The plan's inversion test
  passes `enabled_bots=_ROSTER` on **both** arms, so it varies only `reviewed_bots` and cannot see
  this.
- **Impact:** the plan's ⛔⛔ prohibition — *"a metric that can produce [the inversion] must not
  ship"* — is not satisfied. The single most likely operational response to a chronically refusing
  reviewer (disable it) is exactly the action that makes the metric report perfect gate parity.
- **Task:** make the denominator an observed constant rather than a caller argument, or make a
  shrink observable and disqualifying. Concretely: add a `--roster-baseline` (or equivalent) input
  carrying the configured roster independent of any per-PR disable, and emit a new
  `WITHHELD_ROSTER_NARROWED` reason when the effective roster is a proper subset of the baseline;
  publish both sets on the verdict. Update `bot-participation-contract.md` § "Two properties" and the
  module docstring to state the guarantee in terms of the baseline rather than the passed roster.
- **Done when:** a test that shrinks `enabled_bots` between two arms — same escapes, same partition,
  same SHAs — asserts the second arm withholds the share; and no input reachable from
  `finalize-step-review-retrospective` Step 3b can produce a share at reduced real coverage.
- **Suggested grouping:** automatic-review / review-gate-delta

## G2 — Exclude findings the run rejected from the gate-escape count

- **Severity:** major
- **Kind:** bug
- **Where:** `review_gate_delta.py:250-258` (`_is_actionable`) and `:310-323` (the escape
  comprehension); the counting rule it consumes is
  `bot-participation-contract.md:513-521`.
- **Evidence:** `grep -n "resolution" review_gate_delta.py` returns **no match** — the module never
  reads a finding's disposition. Executed probe with one finding
  `{'resolution': 'rejected', 'kind': 'inline', 'bot_kind': 'coderabbit'}` labelled
  `gate_structural`: `escapes_total=1  structural_share=100.0`. The module's own definition of an
  escape (`review_gate_delta.py:12-16`) is *"something the gates ran over and did not report"* — a
  finding the run rejected as wrong is not that; the gates were right and the reviewer was not.
- **Impact:** every bot false positive inflates `escapes_total` and, when labelled, the residual
  attributed to the gates. The partition taxonomy has no member for "not a defect", so such a finding
  must either be mislabelled into one of the two real buckets or left `unpartitioned`, which withholds
  the whole PR's share.
- **Task:** decide and document whether the escape set is filed-and-actionable **and not rejected**.
  If yes: filter `RELEASED_RESOLUTIONS`-style dispositions out of the escape comprehension, add the
  excluded count to the published population (as `review_commitments.count_unanchored` does, so the
  exclusion is visible rather than shrinking a denominator silently), and extend
  `bot-participation-contract.md` § "The counting rule" with the resolution axis so both counters
  apply it. If no: state in the module docstring and the contract why a rejected finding still counts
  as a gate escape.
- **Done when:** the delta's treatment of `rejected` / `suppressed` findings is stated in the
  contract, implemented, and pinned by a test that supplies one of each and asserts the resulting
  `escapes_total` and published exclusion count.
- **Suggested grouping:** automatic-review / review-gate-delta

## G3 — Make the GitLab path real, or stop claiming the fallback serves it

- **Severity:** major
- **Kind:** bug
- **Where:** `review_gate_delta.py:176-194` (`resolve_bot_kind`, the rationale at `:181-184`);
  `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py:274-280`
  (the `add_finding` call); the mirroring fixture at
  `test/plan-marshall/automatic-review/test_counting_rule_parity.py:148-153`.
- **Evidence:** the docstring justifies the `author` fallback with *"the GitLab producer
  (`gitlab_pr`) never sets [`bot_kind`] at all. Keying on `bot_kind` alone would silently disable
  every per-bot rule on the whole GitLab path"*. The GitLab producer's call is

  ```python
  add_finding(
      plan_id=plan_id, finding_type='pr-comment', title=title, detail=detail,
      file_path=path or None, line=line_arg, raw_input={'body': body},
  )
  ```

  — no `author=`, no `kind=`, no `bot_kind=`, no `reviewed_commit_sha=`, even though `kind` and
  `author` are computed locally at `gitlab_pr.py:246-248` and used only to build the `title` /
  `detail` strings. So on a GitLab record: `_is_actionable` sees no `kind` and returns `False` for
  every record (`escapes_total` always 0); `resolve_bot_kind` returns `''`; and
  `EXCLUSION_GATE_TREE_UNKNOWN` fires because no `reviewed_commit_sha` exists. The parity corpus case
  labelled *"summary identified from the author login with no bot_kind"* encodes
  `{'author': 'coderabbitai', …}` — a shape no producer emits — which is precisely the
  fixture-encodes-an-unemitted-shape class the run's own § "What have we learned" proposes a contract
  bullet for.
- **Impact:** the delta is inert on GitLab and silently so; a production rationale in the shared
  bundle is false; and a test "proves" a fallback over a record shape production never produces.
- **Task:** either (a) pass `author`, `kind`, `bot_kind` and `reviewed_commit_sha` through
  `gitlab_pr.py`'s `add_finding` call so GitLab records carry the same first-class fields as GitHub's,
  and re-point the parity corpus case at the resulting real shape; or (b) correct
  `resolve_bot_kind`'s docstring and the corpus comment to say the GitLab path stores neither
  selector, and record the GitLab inertness explicitly in
  `bot-participation-contract.md` § "The review-versus-gate delta".
- **Done when:** the claim in `review_gate_delta.py:181-184` is true of the producer as it stands,
  and every parity-corpus record is a shape some producer demonstrably emits (assert it against the
  producer, not against the comment).
- **Suggested grouping:** automatic-review / cross-provider finding shape

## G4 — Correct the delta's published selection effect

- **Severity:** major
- **Kind:** bug
- **Where:** `review_gate_delta.py:158-172` (`_PROVENANCE`);
  `bot-participation-contract.md:640-646`; `.claude/skills/finalize-step-review-retrospective/SKILL.md:369-386`;
  and the same sentence in the run report's D2 section.
- **Evidence:** all three sites assert *"the ONLY measurable PRs are those where **neither** post-gate
  mutating step committed anything"*. But `pre-push-quality-gate.md:315` states the gate *"declares
  **no** `verdict_inputs` … so the dispatcher's verdict-currency classifier never narrows its
  re-fire: **every HEAD advance re-runs it**"*, and
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py:434-438`
  confirms the mechanism (`REASON_UNDECLARED` → `VERDICT_INVALIDATED`), which the dispatcher turns
  into RE-FIRE at `phase-6-finalize/SKILL.md:686`. So after any loop-back re-entry the gate re-fires
  and re-stamps `head_at_completion`; if simplify (8) and security-audit (9) commit nothing on that
  final pass, the two SHAs agree and the PR **is** measurable.
- **Impact:** the measurable set is "PRs whose final pass had no post-gate commit", which is biased
  **toward** PRs that looped back — i.e. toward PRs where review found something, inflating the
  measured escape rate. The published provenance names neither the mechanism nor that bias direction,
  and the report's conclusion ("few or no measurements will accumulate") does not follow. Provenance
  accuracy is a plan-mandated deliverable, so a wrong provenance is a defect in D2 itself.
- **Task:** rewrite `_PROVENANCE`'s selection-effect clause to describe the loop-back re-gate and the
  actual measurable set, and state the bias direction (over-represents PRs with review findings).
  Mirror the correction in the contract section and in Step 3b's consumer text, which must stay
  verbatim-consistent with the emitted string.
- **Done when:** the three sites describe the same, correct mechanism, and a test asserts the
  `provenance` string emitted by `assess_delta` matches the contract's stated wording (so the two
  cannot drift again).
- **Suggested grouping:** automatic-review / review-gate-delta

## G5 — Render the structural-limit block on a PARTIAL verdict whose first dimension degraded

- **Severity:** major
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:322-324`;
  reachable via `build.py:442-450`; the test that misses it is
  `test/plan-marshall/build-pyproject/test_gate_coverage.py:285`.
- **Evidence:** `_render_structural_limits` opens with

  ```python
  pairs = structural_limits(boundary.checked)
  if not pairs:
      return []
  ```

  and `cmd_quality_gate` calls `cmd_compile` **first** (`build.py:442`), so a freshness-suspect mypy
  produces `checked == []`, `degraded == [('mypy(production)', 'freshness suspect — …')]` and an
  early `render_coverage_summary` at `build.py:448`. That PARTIAL verdict carries neither the
  per-analysis limits nor the `not run in this gate at all: …` line. The covering test seeds
  `record_checked('ruff [marketplace/bundles]')` before `record_degraded`, so the reachable shape is
  untested — searched `test_gate_coverage.py` for every `record_degraded` call site (`:288`, `:365`),
  both paired with a `record_checked`.
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

## G6 — An empty coverage boundary must not render COMPLETE

- **Severity:** major
- **Kind:** bug
- **Where:** `_gate_coverage.py:181-184` (`CoverageBoundary.complete`) and `:388-394` (the COMPLETE
  branch); pinned as intended by `test_gate_coverage.py:372`.
- **Evidence:** `complete` is `return not self.degraded`, so a boundary that recorded nothing at all
  renders

  ```
  >>> coverage: COMPLETE over the dimensions below — checked over full scope: (nothing)
  ```

  with no limit block and no un-run line. "No dimension was analysed" and "every dimension passed"
  produce the same verdict word. This is the one-signal-two-meanings archetype the plan's own Notes
  identify as living in at least three places (*"'No module matched' and 'no tests needed' are one
  signal in both places"*), now demonstrably in a fourth — inside the function D0 rewrote. The plan
  asked the run to **say so** if it reached that branch; the report's Residue instead records the
  branch as not reached, which is true of the sibling epic's footprint code but not of this one.
- **Impact:** a gate that analysed nothing prints the word a reader treats as strongest assurance.
- **Task:** introduce a third verdict form for an empty boundary — e.g. `>>> coverage: NONE — this
  pass analysed no dimension; it certifies nothing` — and make `complete` false when nothing was
  checked. Replace `test_empty_boundary_does_not_claim_a_limit_block_it_cannot_populate` with one
  asserting the new form. Record the instance in the epic's archetype note so it is counted rather
  than re-discovered.
- **Done when:** `render_coverage_summary(CoverageBoundary())` contains neither `COMPLETE` nor
  `PARTIAL`, and a test asserts that.
- **Suggested grouping:** build-gate / gate-coverage honesty

## G7 — The counting rule's "two independent implementations" claim is stale

- **Severity:** major
- **Kind:** stale-doc
- **Where:** `bot-participation-contract.md:663` (Consumers table, `review_gate_delta assess` row);
  the code that falsifies it is
  `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:160-174`; the
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
  kind classification (`review_gate_delta._is_actionable:250-258` vs
  `review_retrospective._is_actionable:180-192`) remains genuinely duplicated.
- **Impact:** the contract instructs a future editor to mirror a change into a second implementation
  that no longer exists, and the parity test's stated guarantee is stronger than what it checks.
- **Task:** rewrite the Consumers row to say the summary predicate is a single shared implementation
  the retrospective imports, and that only the kind classification is duplicated; narrow the parity
  test's docstring to the axis it actually pins, or collapse the remaining duplication so the file
  becomes a delegation test.
- **Done when:** no site claims two independent implementations, and the parity test's docstring
  names the axis it discriminates on.
- **Suggested grouping:** automatic-review / counting rule

## G8 — D2's instrument has no consumer outside the meta-project

- **Severity:** major
- **Kind:** incomplete
- **Where:** the only invocation site is
  `.claude/skills/finalize-step-review-retrospective/SKILL.md:354` (project-local); the script,
  contract and canonical block ship in the shared bundle
  (`marketplace/bundles/plan-marshall/skills/automatic-review/`).
- **Evidence:** `grep -rn "review_gate_delta"` over `--include=*.py --include=*.md --include=*.json
  --include=*.toon`, excluding `doc/plans/` and `target/`, returns: the script itself, its tests, the
  bundle's `SKILL.md` canonical block, the contract's two references, and the one project-local
  consumer. No bundle-level finalize step invokes it.
- **Impact:** D2's *Done when* speaks of a recurring measured signal; as landed it can only recur in
  this repository. Every consuming project receives the instrument and the contract, and nothing that
  runs it — so the epic's parity hypothesis can never be tested outside the meta-project.
- **Task:** decide the intended home. Either promote a delta-emitting step into the shared bundle
  (its natural seat is beside `automatic-review`, after the findings are triaged and the partition
  judgment exists), or state explicitly in `bot-participation-contract.md` § "The review-versus-gate
  delta" that the instrument is meta-project-instrumented only, and why.
- **Done when:** either a bundle-shipped step invokes `review_gate_delta assess`, or the contract
  names the meta-project-only scope as a deliberate boundary.
- **Suggested grouping:** automatic-review / review-gate-delta

## G9 — Publish the resolved `bot_kind` on each escape

- **Severity:** minor
- **Kind:** bug
- **Where:** `review_gate_delta.py:317`.
- **Evidence:** the escape record is built with `'bot_kind': str(record.get('bot_kind') or '')`,
  reading the raw key, while `resolve_bot_kind` (`:176-194`) exists two functions above to answer
  exactly the case where that key is absent. Executed probe with
  `{'hash_id': 'g1', 'author': 'coderabbitai', 'kind': 'inline', 'body': 'x'}`:
  `escapes[0]['bot_kind'] == ''`, even though `is_status_summary` on the same record resolves the bot
  correctly through the registry.
- **Impact:** the per-escape attribution field a reader uses is blank precisely on the records the
  module went to trouble to classify; two code paths in one function answer "which bot" differently.
- **Task:** call `resolve_bot_kind(record)` when building the escape entry.
- **Done when:** a test asserts a record carrying only `author` yields a non-empty `bot_kind` on its
  escape row.
- **Suggested grouping:** automatic-review / review-gate-delta

## G10 — The "not run in this gate at all" line is false for an attempted-but-empty scope

- **Severity:** minor
- **Kind:** bug
- **Where:** `build.py:344-346` and `:365-367` (`_skip_empty_mypy_scope` returning 0 with no record);
  the wording at `_gate_coverage.py:353-357`.
- **Evidence:** when no file under the scoped path survives mypy's excludes, `cmd_compile` /
  `cmd_test_compile` `return 0` before `_run_mypy`, so the dimension is recorded neither as checked
  nor as degraded. `_render_structural_limits` then derives `not_run` from
  `_ANALYSIS_LIMITS` minus the attempted stems and prints *"absent from the list above because this
  gate **never performs them**, NOT because they passed"* — false for a gate that did attempt the
  analysis and found nothing to analyse.
- **Impact:** the line intended to separate "not run" from "passed" introduces a third, unlabelled
  state and mislabels it as the first.
- **Task:** record an explicit third outcome for an empty analysis scope (a `record_skipped` on the
  boundary, or a `record_degraded` with reason "no file in scope"), and render it as its own line
  distinct from both the checked list and the never-performed list.
- **Done when:** a module-scoped `quality-gate` over a bundle with no type-checkable file prints a
  verdict that says the analysis was attempted over an empty scope, and a test pins it.
- **Suggested grouping:** build-gate / gate-coverage honesty

## G11 — Carry the self-review structural limit onto the step's recorded verdict

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:270`
  and `:279`; the emit site is
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py:409`;
  the contract is
  `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md:64-65,80`.
- **Evidence:** the standard states *"the `--display-detail` budget … carries neither, and the
  dispatched-envelope schema below has no field for either"*, concluding *"it is published, not
  discharged"*. So the limit reaches the dispatched agent's TOON and stops there; the step's recorded
  verdict — what a later reader of `status.metadata.phase_steps` sees — still reads only
  `clean: {N} candidates examined, no check matched`.
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

## G12 — Give the three unlimited gates a structural limit

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md`,
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md` (its own step verdict).
- **Evidence:** greps for `structural limit` / `does NOT evaluate` / `cannot evaluate` return no hit
  in the first two; plugin-doctor's two hits (`:23`, `:167`) are a **scope** statement about scoped
  vs whole-tree mode — cured by widening, which `pre-push-quality-gate.md:86-88` says a structural
  limit by definition is not. The report records this as a deliberate boundary rather than an
  oversight; it remains open.
- **Impact:** D0's rule ("a gate whose green is scope-limited says so in its verdict") holds for
  three of six in-house gates.
- **Task:** for each of the three, name the analysis it performs and the defect class it cannot reach,
  and put the statement on its verdict — following `pre-push-quality-gate.md` § "A gate states what
  its green does not evaluate" as the pattern. `ci-verify` is the highest-value of the three: its
  green is the one most often read as whole-tree assurance.
- **Done when:** each of the three gates' verdicts carries a limit that is a property of its analysis
  rather than of its file set.
- **Suggested grouping:** finalize gates / gate honesty

## G13 — Correct the run report's test and file tallies

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/130-review-bots-catch-what-in-house-gates-cannot/report-01.md`
  § D3 ("100 tests added across six files") and § "Build gate" ("5 production scripts, 7 test files").
- **Evidence:** `git show 622f4484 -- 'test/**' | grep -c "^+.*def test_"` → **91**, across **eight**
  test files (4 / 3 / 4 / 32 / 11 / 4 / 29 / 4). `grep -c "^+.*parametrize"` → **0**, so
  parametrisation does not close the gap. `git show --stat --name-only 622f4484` lists **six**
  production `.py` files: `review_retrospective.py`, `bot_registry.py`, `review_gate_delta.py`,
  `review_commitments.py`, `_gate_coverage.py`, `self_review.py`.
- **Impact:** small in isolation, but this plan's own thesis is that a count restated without
  re-derivation is a defect class; a report of that plan carrying two wrong counts is the archetype
  reproduced in the record of the fix.
- **Task:** correct both figures in `report-01.md`. Do not add a correction note or a dated entry —
  restate the numbers.
- **Done when:** both figures match `git show --stat --name-only 622f4484`.
- **Suggested grouping:** plan records / report accuracy

## G14 — Reconcile the two `./pw verify` totals recorded for the same run

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `report-01.md` § "Build gate" (**19748 passed**) versus the squash commit message of
  `622f4484` (**19752 passed**).
- **Evidence:** both purport to be the final `./pw verify` of the same run and differ by four.
- **Impact:** one of the two is not the final run; a reader cannot tell which, and the figure is the
  report's only quantitative evidence that the build gate passed.
- **Task:** determine which figure is the final verify (the commit message is the later artifact) and
  make the report agree, or state that the report's figure is from the penultimate round.
- **Done when:** one figure appears in both places, or the report says which round each belongs to.
- **Suggested grouping:** plan records / report accuracy

## G15 — Give Step 3b a canonical invocation for the two SHAs it must resolve

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:340-350`.
- **Evidence:** every other command in that step is a fenced bash block, but the two inputs the
  escape claim rests on are prose: *"`{gate_head_sha}` — the `head_at_completion` recorded by
  `pre-push-quality-gate` (read the step record via `manage-status`)"* and
  *"`{reviewed_head_sha}` — the `reviewed_commit_sha` carried by the `pr-comment` findings"*. Both
  are reachable (`manage-status read|get` returns `metadata.phase_steps`;
  `manage-findings list --type pr-comment` returns the records), but neither is written down, and the
  agreement rule for the second is left entirely to the agent.
- **Impact:** the plan's own thesis names "a documented remedy with no reachable invocation" as the
  archetype the gates cannot catch; this is the weaker cousin — a reachable remedy with no written
  invocation, on the step whose omission silently excludes the PR.
- **Task:** add the two concrete commands, and state the disagreement rule as a mechanical check over
  the returned `reviewed_commit_sha` values rather than as prose.
- **Done when:** Step 3b resolves both SHAs through named commands with no undocumented step.
- **Suggested grouping:** review-retrospective / consumer wiring

## G16 — Align the two new CLIs' load-failure exception sets

- **Severity:** minor
- **Kind:** bug
- **Where:** `review_gate_delta.py:466-471` (`cmd_assess`) versus
  `review_commitments.py:400-407` (`cmd_reconcile`).
- **Evidence:** both wrap the identical expression `query_findings(plan_id,
  finding_type='pr-comment')['findings']`. The commitments CLI catches
  `(OSError, ValueError, KeyError)`; the delta CLI catches `(OSError, ValueError)`. A payload missing
  the `findings` key therefore renders as a structured error TOON from one and as an uncaught
  traceback from the other.
- **Impact:** the delta's stated contract — a load failure is a structured error, never a clean zero —
  has a hole its sibling does not.
- **Task:** add `KeyError` to `cmd_assess`'s except tuple.
- **Done when:** both CLIs catch the same exception set over the same call, and a test drives the
  delta CLI against an unreadable store expecting `status: error` with no `verdict`.
- **Suggested grouping:** automatic-review / review-gate-delta
