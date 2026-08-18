# Gaps — 030-a-workflow-doc-prescribes-a-flag-no-script-declares

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Fix the `ci` exemplar in the envelope contract's `--plan-id` cell, which prescribes an argparse rejection for six verbs

- **Severity:** blocker
- **Kind:** bug (stale-doc with executable consequence)
- **Where:** `marketplace/bundles/plan-marshall/agents/execution-context.md:23`. Contradicted by
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py:260-277`
  (`add_body_consumer_args`), and by the canonical forms at
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md:163` and
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md:133,261,268`.
- **Evidence:** the cell states — "a script that declares `--plan-id` as a **top-level/router flag
  consumed before the subcommand verb** (the `ci` router reads it before `pr`/`checks`, so
  `--plan-id` goes **before** the verb — placing it after the verb is an argparse rejection)".
  `ci_base.add_body_consumer_args` declares `--plan-id` with `required=True` on `pr create`,
  `pr edit`, `pr reply`, `pr thread-reply`, `issue create` and `issue comment`, i.e. **after** the
  verb, and the canonical block writes it that way: `ci pr create --title "Add feature X" --plan-id
  {plan_id} --base main`. Pre-verb placement is consumed and stripped by the router before the
  subparser runs — confirmed by executing the real function:
  `extract_routing_args(['--plan-id','NO_PLAN','pr','create','--title','T','--base','main'])`
  returns `('/home/user/plan-marshall', ['pr', 'create', '--title', 'T', '--base', 'main'])`.
- **Impact:** a dispatched leaf that obeys the envelope contract for `ci pr create` / `ci pr reply` /
  `ci issue create` moves `--plan-id` left of the verb and gets
  `error: the following arguments are required: --plan-id` — exit 2, the exact rejection class this
  plan exists to eliminate, now prescribed by the contract the plan rewrote to stop prescribing it.
  Two normative docs also disagree head-on, so a reader has no way to adjudicate.
- **Task:** rewrite the parenthetical so `ci` is presented as what it is — a router that consumes
  `--plan-id` before the verb **only for the verbs that do not declare it themselves**, e.g. the
  read verbs (`checks …`, `pr view`, `pr list`), while the body-consumer verbs (`pr create`,
  `pr edit`, `pr reply`, `pr thread-reply`, `issue create`, `issue comment`) declare a **required**
  `--plan-id` after the verb and must be written that way. Either name a different script as the
  pure before-the-verb exemplar or state the split explicitly; do not leave a blanket "placing it
  after the verb is an argparse rejection" attached to `ci`.
- **Done when:** the cell contains no statement that is false for any `ci` subcommand, and a cold
  read of it against `ci pr create` yields a post-verb `--plan-id`, while a cold read against
  `ci checks pull-request-runs` still yields a pre-verb one. Ideally pinned by a test that derives
  the `ci` subcommands declaring `--plan-id` from `ci_base.py` and asserts the contract text does not
  contradict them.
- **Suggested grouping:** envelope contract / `execution-context` + `tools-integration-ci`

## G2 — Give `branch-cleanup-rereview.md` an exit-code convention and put it in the merge-and-review population

- **Severity:** major
- **Kind:** omission (D0 population miss)
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md`
  — invocations at `:45` (`github_re_review re-review`) and `:55` (`github_pr fetch_findings`); the
  file has exactly one `## ` heading, `## Re-review the rebased HEAD (trigger A)` at `:5`, and no
  exit-code convention section. Population literals at
  `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py:75,77`.
- **Evidence:** `branch-cleanup.md:489` — "The full walkthrough … lives in the same-directory
  sub-standard [`branch-cleanup-rereview.md`](branch-cleanup-rereview.md). **Load and execute it
  here**". The doc produces `{declined_bots}`, which `branch-cleanup.md:830-836` feeds straight into
  `review_completeness check`. It existed at the landing commit
  (`git cat-file -e 3c7a1cc8:…/branch-cleanup-rereview.md` succeeds), so it was inside D0's stated
  population — "*every script invocation reachable in the finalize merge-and-review path*" — at the
  time and was missed. Confirmed by a scripted WIDE/NARROW/NONE sweep over every `*.md` under
  `phase-6-finalize`, which classifies this file NONE while it invokes two non-`manage-*` scripts.
- **Impact:** the barrier's own re-review sub-step is the one place in the path where a non-zero exit
  carries no disposition at all — neither the widened convention nor an UNKNOWN branch. A failed
  `github_re_review re-review` or `fetch_findings` there can be read as "no fresh review found",
  which routes to the timeout disposition (proceed / defer / ask) rather than to an error — the same
  swallow, one document over. Its `fetch_findings` invocation is also outside D3's parse sweep, so a
  reintroduced bad flag there would not be caught.
- **Task:** add the wide `## Exit-code convention for every script call` section to
  `branch-cleanup-rereview.md` (matching `branch-cleanup.md:59-66`, including the stricter-disposition
  carve-out sentence if the re-review branches warrant one), and add `_REREVIEW_DOC` to both
  `_INVOCATION_DOCS` and `_CONVENTION_DOCS` in the contract test.
- **Done when:** `test_convention_is_widened_wherever_a_non_manage_star_script_is_invoked` runs a
  fourth parametrized case for `branch-cleanup-rereview.md` and passes, and the D3 population grows
  to include that doc's `fetch_findings` invocation (raise the floor accordingly).
- **Suggested grouping:** phase-6-finalize merge-and-review docs

## G3 — Stop `--stale-participation-bots` silently dropping a pair whose evidence kind is not registry-admissible

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:1216-1221`
  (the `_parse_bot_observations` entry and its comment) and `:363-379` (the admissibility filter
  inside `parse_participation`).
- **Evidence:** the comment at `:1216-1218` asserts "it takes the same pair form and **the classifier
  reads only the bot_kinds**", but the shared parser filters first:
  `if evidence_kind in bot_registry.participation_evidence(bot_kind): proven[bot_kind] = evidence_kind`.
  Confirmed by execution against the live module —
  `parse_participation('pr-agent:bogus', '--stale-participation-bots')` → `{}`,
  `parse_participation('nonexistent-bot:issue_comment', …)` → `{}`, while
  `parse_participation('pr-agent:issue_comment', …)` → `{'pr-agent': 'issue_comment'}`.
- **Impact:** a stale record the producer emitted is dropped without a word, and the bot falls
  through to `absent` instead of `participated_stale`. Both block, so this is not a false pass — but
  `branch-cleanup.md` states that the two members carry **opposite remedies** ("a required bot on
  `participated_stale` DID publish … so the productive action is a re-review trigger"), and the
  barrier renders those remedies to an operator. This is the same class of polarity-selecting silent
  drop D1 was written to abolish, surviving on the flag D1 converted. It fires whenever the producer's
  emitted `evidence_kind` and the consumer's registry read diverge — a registry edit between the two
  reads, or an unregistered bot.
- **Task:** decide the intended semantics and make code and comment agree. Either (a) give the stale
  flag its own parse that enforces the pair SHAPE but does **not** apply the participation
  admissibility filter — the producer already established the kind matched a publish shape, so the
  filter is redundant on the happy path and destructive off it; or (b) keep the filter and make a
  non-admissible pair a loud `MalformedBotFlag` rather than a drop. Correct the comment at
  `:1216-1218` either way.
- **Done when:** a test feeds `--stale-participation-bots pr-agent:not-a-declared-kind` with
  `pr-agent` required and asserts the outcome is either `participated_stale` (option a) or a
  `status: error` / non-zero exit (option b) — and in no case `absent`.
- **Suggested grouping:** `automatic-review` / `review_completeness` bot-flag parsing

## G4 — Extend the widened exit-code convention to the rest of the finalize review-and-merge docs, or record the boundary honestly

- **Severity:** major
- **Kind:** incomplete
- **Where:** narrow heading (`## Exit-code convention for `manage-*` script calls`) while invoking
  non-`manage-*` scripts —
  `phase-6-finalize/workflow/create-pr.md:22` (`ci`),
  `phase-6-finalize/workflow/sonar-roundtrip.md:42` (`ci`, `sonar`),
  `phase-6-finalize/standards/output-template.md:9` (`ci`),
  `phase-6-finalize/standards/architecture-refresh.md:17` (`ci`),
  `phase-6-finalize/standards/archive-plan.md:23`,
  `phase-6-finalize/standards/emit-landing.md:37`,
  `phase-6-finalize/standards/finalize-step-preference-emitter.md:38`,
  `phase-6-finalize/standards/finalize-step-security-audit.md:25`,
  `phase-6-finalize/standards/finalize-step-simplify.md:23`,
  `phase-6-finalize/standards/finalize-step-sync-baseline.md:32`,
  `phase-6-finalize/standards/pre-push-quality-gate.md:129`,
  `phase-6-finalize/workflow/lessons-capture.md:26`,
  `phase-6-finalize/workflow/pre-submission-self-review.md:25`.
  No convention at all — `phase-6-finalize/standards/ci-verify.md`,
  `phase-6-finalize/standards/verdict-currency.md`,
  `workflow-pr-doctor/standards/automated-review-lifecycle.md` (invokes `ci` and `github_pr`),
  `workflow-integration-github/SKILL.md`.
- **Evidence:** `report-01.md` justifies the three-doc scope with "the ~35 other docs carrying the
  boilerplate convention are **other phases/steps**, out of scope". A scripted sweep that classifies
  every `*.md` under `phase-6-finalize`, `automatic-review`, `workflow-integration-github` and
  `workflow-pr-doctor` as WIDE / NARROW / NONE against its own derived non-`manage-*` invocations
  shows 13 NARROW and 3 NONE docs **inside `phase-6-finalize` itself**, several of them PR/review
  path (`create-pr.md`, `sonar-roundtrip.md`). The justification is therefore inaccurate as written.
- **Impact:** the `manage-*`-scoped convention still structurally excludes non-`manage-*` calls in
  most of the finalize phase, including PR creation and the Sonar review roundtrip. The defect class
  the plan closed for three docs remains open for the rest of the same phase, and the recorded reason
  for stopping is wrong, so a future reader will not know the boundary was arbitrary.
- **Task:** either widen the heading in every `phase-6-finalize` doc whose derived invocation set
  contains a non-`manage-*` notation (mechanical, and the obligation is already derivable by the
  existing `_invoked_notations` / `_is_manage_star` helpers), or state a defensible boundary in the
  test docstring and correct the report's rationale. Prefer the first: the widening costs one line
  per doc and removes the need for a boundary at all.
- **Done when:** the WIDE/NARROW/NONE sweep over `phase-6-finalize` returns no NARROW or NONE doc
  that invokes a non-`manage-*` script — or the surviving exceptions are enumerated in the test with
  a per-doc reason, and the test fails when a new such doc appears.
- **Suggested grouping:** phase-6-finalize merge-and-review docs

## G5 — State the token FORM at every site that renders a pair-form bot flag

- **Severity:** minor
- **Kind:** stale-doc / incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:830-836`
  (the barrier's `review_completeness check` invocation) and its surrounding prose `:840-856`;
  `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:970-990`
  (`## Canonical invocations` → `review_completeness — check`, and the same for `deficit` at
  `:1000-1010`).
- **Evidence:** the barrier's one command carries `--participated-bots` and
  `--stale-participation-bots` (both now pair-form) alongside `--refused-bots`, `--declined-bots`,
  `--optional-bots`, `--required-bots` (bare-form), and the prose beneath it discusses emptiness and
  quoting at length — "the eight list flags above are the set here … **The load-bearing defence is
  the parser, not the quoting**" — without ever stating which flags take pairs. The canonical block
  says only "All nine list flags take an OPTIONAL value" (`automatic-review/SKILL.md:980`) and says
  nothing about form, although `_analyze_manage_invocation.py` treats that block as source of truth.
  Only `automatic-review/SKILL.md:661` (item 4) states the pair form, and only for the FIND step.
- **Impact:** since this plan, a wrong-form token is a hard error (`status: error`, exit 1) rather
  than a silent misparse. A reader composing the barrier call from the producer's records has no
  local statement of which of the eight flags need `bot_kind:evidence_kind` — the failure is now loud,
  but the doc does not prevent it.
- **Task:** add one sentence at the barrier invocation naming the two pair-form flags and the
  bare-form remainder (mirroring the wording already at `automatic-review/SKILL.md:661`), and add a
  form column or a one-line note to the `## Canonical invocations` blocks for both `check` and
  `deficit`.
- **Done when:** each of the three sites states, in its own text, which list flags take
  `bot_kind:evidence_kind` pairs and which take bare `bot_kind` tokens.
- **Suggested grouping:** `automatic-review` / bot-flag documentation

## G6 — Publish D3's population size on a passing run, not only in failure messages

- **Severity:** minor
- **Kind:** incomplete (unmet Verification clause)
- **Where:** `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py:297-306`
  (`test_the_population_size_is_published`).
- **Evidence:** the plan's Verification section states "**D3's population size is published in the
  test output**, so a future reader can tell a passing test from an empty one." The count appears
  only inside the two assertion messages; `grep -n "print(\|record_property\|capsys"` over the file
  returns nothing. Observed: `-q` prints `11 passed`; `-v` enumerates six parametrized ids but states
  no count. `report-01.md` claims the test "publishes size (6 invocations, floor ≥ 4)".
- **Impact:** the guarantee the clause exists to give — that a reader of a green run can distinguish
  a real sweep from a shrunken one — is not delivered. The `>= 4` floor also under-constrains a true
  population of 6, so two invocations could silently drop out and the suite would stay green.
- **Task:** emit the size on success (a `print` that `-s` surfaces, or `record_property('population_size', …)`,
  or a `pytest.ini`-visible `caplog`/`terminal_summary` line — whichever the repo's test conventions
  prefer), and raise the floor to the true derived population or make the floor itself derived.
- **Done when:** a passing run of the suite emits the population count, and dropping one invocation
  from either population doc fails the size test rather than passing it.
- **Suggested grouping:** `automatic-review` / merge-and-review contract test

## G7 — Correct the test docstring's now-false claim that no parser declares `--enabled-bots`

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py:18` and
  `:291`. Contradicted by
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py:504`.
- **Evidence:** `:18` — "A workflow doc that prescribes a flag no script declares
  (``--enabled-bots``)"; `:291` — "A documented ``--enabled-bots`` (a flag no parser declares)".
  `review_gate_delta.py:504` declares `--enabled-bots`, documented at
  `automatic-review/SKILL.md:1085` as "the coverage DENOMINATOR (`required_bots ∪ optional_bots`)".
  The claim was true at this plan's landing — `git cat-file -e 3c7a1cc8:…/review_gate_delta.py`
  fails, so the script did not exist then; it arrived later with the review-versus-gate delta work.
- **Impact:** the suite's own rationale now misstates the tree. A reader checking the docstring
  against the code finds a declared `--enabled-bots` and may conclude the guard is obsolete, or may
  reintroduce the flag on a `github_pr` invocation believing it exists.
- **Task:** reword both passages to name the real invariant — a flag prescribed on a parser that does
  not declare it (`--enabled-bots` on `github_pr fetch_findings`), rather than a flag no parser
  declares — and mention that `review_gate_delta assess` legitimately declares it.
- **Done when:** neither docstring passage asserts anything falsifiable by grepping the tree for
  `--enabled-bots`.
- **Suggested grouping:** `automatic-review` / merge-and-review contract test

## G8 — Record the confirm/refute artefact for the executor empty-value claim-label

- **Severity:** minor
- **Kind:** omission (unreported plan obligation)
- **Where:** `doc/plans/review-apparatus/030-…/report-01.md` § Findings and § Deliverables. The claim
  is in `plan.md` § Claim labels: "`--in-progress-bots ""` is dropped by the executor so argparse
  sees a flag with no argument, while omitting the flag works | OBSERVED | The executor's argument
  marshalling — **reproduce it once before building on it**".
- **Evidence:** the report never mentions this claim, the reproduction, or its disposition — unlike
  the three D2 null results, which it reports in a dedicated table. The cause class is in fact
  already closed: all nine list flags carry `nargs='?'` with `const=''`
  (`review_completeness.py`, `_add_bot_observation_flags`), and `branch-cleanup.md:740-746` documents
  the executor's `script_args = [a for a in script_args if a]` stripping and why the parser (not the
  quoting) is the defence.
- **Impact:** no behaviour is wrong, but one of the plan's seven required confirm/refute artefacts is
  missing from the record. A later reader auditing cause class 4 ("Empty value dropped by the
  harness") cannot tell from the report whether it was examined, dismissed, or forgotten — which is
  the "a defect recorded under a plausible-but-wrong cause looks owned" failure the plan's own Notes
  warn about, in its milder form.
- **Task:** add a short null-result row to the plan's record stating that cause class 4 is closed by
  the pre-existing `nargs='?'` / `const=''` relaxation plus the executor's documented empty-argument
  stripping, citing the two sites. Same for the conditional "endorsement trap" hint in § Verification,
  which never fired because D0 did not touch the rejection reporting.
- **Done when:** every row of the plan's Claim-labels table has a stated disposition somewhere in the
  plan directory.
- **Suggested grouping:** plan record hygiene / review-apparatus epic
