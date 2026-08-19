# Gaps — 030-a-workflow-doc-prescribes-a-flag-no-script-declares

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

Eleven gaps: **1 blocker, 5 major, 5 minor.**

## G1 — Fix the `ci` exemplar in the envelope contract's `--plan-id` cell, which prescribes an argparse rejection for ten subcommands

- **Severity:** blocker
- **Kind:** bug (stale-doc with executable consequence)
- **Where:** `marketplace/bundles/plan-marshall/agents/execution-context.md:23`. Contradicted by
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py:260-275`
  (`add_body_consumer_args`) and `:1172,1190,1201,1217` (`add_plan_id_arg`, which is
  `input_validation.add_plan_id_arg` — `tools-input-validation/scripts/input_validation.py:387-400`,
  `required=True` by default), and by the canonical forms at
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md:163`,
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md:133,261,268`
  and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:280-281`.
- **Evidence:** the cell states — "a script that declares `--plan-id` as a **top-level/router flag
  consumed before the subcommand verb** (the `ci` router reads it before `pr`/`checks`, so
  `--plan-id` goes **before** the verb — placing it after the verb is an argparse rejection)".
  Walking the live parser tree (`ci_base.build_parser` + `ci_base.add_pr_create_args`) enumerates
  **ten** subcommands that declare `--plan-id` themselves, every one of them `required=True`:
  `pr create`, `pr edit`, `pr reply`, `pr thread-reply`, `pr prepare-body`, `pr prepare-comment`,
  `issue create`, `issue comment`, `issue prepare-body`, `issue prepare-comment`. For each, the
  router consumes and strips a pre-verb `--plan-id` before the subparser runs — confirmed by
  executing `ci_base.extract_routing_args(['--plan-id','NO_PLAN','pr','create','--title','T','--base','main'])`,
  which returns `('/home/user/plan-marshall', ['pr','create','--title','T','--base','main'])` — after
  which parsing the returned argv against the real parser exits 2 with
  `error: the following arguments are required: --plan-id`. Re-run against all ten: **ten exit-2
  rejections, zero survivors.** The post-verb form parses cleanly (`plan_id = NO_PLAN`).
- **Impact:** a dispatched leaf that obeys the envelope contract for any of those ten verbs moves
  `--plan-id` left of the verb and gets an exit-2 argparse rejection — the exact failure class this
  plan exists to eliminate, now prescribed by the contract the plan rewrote to stop prescribing it.
  Two normative surfaces disagree head-on, so a reader has no way to adjudicate. The three doc sites
  that DO place `--plan-id` pre-verb (`tools-integration-ci/SKILL.md:159-160`,
  `ref-workflow-architecture/standards/dispatch-walkthrough.md:136-137`,
  `phase-6-finalize/workflow/sonar-roundtrip.md:73-74`) all name verbs that declare no `--plan-id`
  of their own (`pr view`, `pr wait-for-comments`), so no authored invocation is currently broken —
  the exposure is exactly the runtime-composed invocation the plan's Notes name as the uncovered
  case.
- **Task:** rewrite the parenthetical so `ci` is presented as what it is — a router that consumes
  `--plan-id` before the verb **only for the verbs that do not declare it themselves** (the read
  verbs: `checks …`, `pr view`, `pr list`, `pr wait-for-comments`), while the ten verbs above declare
  a **required** `--plan-id` after the verb and must be written that way. Either name a different
  script as the pure before-the-verb exemplar or state the split explicitly; do not leave a blanket
  "placing it after the verb is an argparse rejection" attached to `ci`.
- **Done when:** the cell contains no statement that is false for any `ci` subcommand, and a cold
  read of it against `ci pr create` yields a post-verb `--plan-id`, while a cold read against
  `ci checks pull-request-runs` still yields a pre-verb one. Pinned by a test that derives, from
  `ci_base`'s own parser tree, the set of subcommands declaring `--plan-id`, and asserts the contract
  text does not contradict them — the derivation, not a transcribed list of ten.
- **Suggested grouping:** envelope contract / `execution-context` + `tools-integration-ci`

## G2 — Give `ci pr create` in `create-pr.md` a `status` check: a failed PR creation currently marks the step `done`

- **Severity:** major
- **Kind:** bug (live swallowed failure, uncovered by D0's derivation)
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:277-289`
  (Step 4, the `ci pr create` call and the "Read `pr_number` and `pr_url` from the TOON output"
  instruction), `:294` (the `[ARTIFACT] … Created PR #{pr_number}` log) and `:306-310` (Branch A
  `mark-step-done --outcome done --display-detail "#{pr_number}"`), under the NARROW exit-code
  convention at `:22`. Same shape, lower stakes, at
  `phase-6-finalize/standards/architecture-refresh.md:290-305` (`pr prepare-body` / `pr edit`).
- **Evidence:** both CI providers' `main()` returns **0 unconditionally** after dispatch —
  `workflow-integration-github/scripts/github_ops.py:1906-1908` and
  `workflow-integration-gitlab/scripts/gitlab_ops.py:2600-2602` both do
  `result = dispatch(...)` / `print(serialize_toon(result))` / `return 0`, with no branch on
  `result['status']`. Reproduced against the real script with an emptied `PATH`:

  ```
  $ github_ops.py pr create --title T --plan-id NO_PLAN --base main
  status: error
  operation: pr_create
  error: Not authenticated. Run 'gh auth login' first.
  EXIT 0
  ```

  Step 4 states no positive shape requirement and no `status` branch; the very same document DOES
  branch on `status` for `pr view` at `:69-73` ("`status: error` → no PR exists, proceed to create
  one"), so the omission is a local inconsistency rather than a house style —
  `standards/output-template.md:156` likewise handles its `pr view` error explicitly.
- **Impact:** a failed `pr create` returns exit 0, so the narrow convention's `exit_code == 0` clause
  says "parse the returned TOON and use the value as the step describes". `pr_number` is absent, the
  step logs `Created PR #` and records `--outcome done --display-detail "#"`, and finalize proceeds
  to the review-and-merge steps against a PR that does not exist. This is the plan's Goal class
  verbatim — "a value the surface accepts and misreads … absorbed into a green result" — still live
  in the finalize path, and it was missed because D0's population was a three-doc literal.
- **Task:** add a positive shape requirement at Step 4 in the form the barrier already uses: the call
  is usable when and only when the return carries `status: success` AND a non-empty `pr_number`;
  every other shape STOPS the step with an error TOON and never reaches `mark-step-done`. Do the same
  for `architecture-refresh.md`'s `pr prepare-body` / `pr edit` pair.
- **Done when:** `create-pr.md` Step 4 states the positive shape requirement, no `--outcome done`
  branch in that document is reachable with an absent `pr_number`, and a test derives the `ci`-verb
  invocations in `create-pr.md` and asserts each is followed by a `status`-branching disposition.
- **Suggested grouping:** phase-6-finalize merge-and-review docs

## G3 — Close the exit-code convention's exit-0 hole: `ci` reports failure as `status: error` at exit 0

- **Severity:** major
- **Kind:** incomplete (the widened convention does not cover the class D0 was told not to narrow away)
- **Where:** the three widened conventions —
  `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:172-177`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:44-49`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:59-68`
  — each keying on `exit_code == 0` / `exit_code != 0` alone. The producing surface:
  `tools-integration-ci/scripts/ci_base.py:790-798` (`output_error` prints `status: error` and
  returns `EXIT_SUCCESS`), `github_ops.py:1906-1908` and `gitlab_ops.py:2600-2602` (`return 0` after
  dispatch regardless of `result['status']`).
- **Evidence:** reproduced twice against the real scripts. Router tier, run from a directory with no
  configured provider:

  ```
  $ ci.py checks pull-request-runs --pr-number 1
  status: error
  operation: router
  error: CI provider not configured. Run /marshall-steward first.
  EXIT 0
  ```

  Provider tier, with an emptied `PATH`:

  ```
  $ github_ops.py checks pull-request-runs --pr-number 1
  status: unconfigured
  operation: pull_request_runs
  provider: github
  detail: Not authenticated. Run 'gh auth login' first.
  EXIT 0
  ```

  `ci_base.py:791-794` states the model outright: "Three-tier model: Exit 0 for expected errors
  (status:error in TOON output)." The plan's D0 is explicit that this class was in scope —
  "⛔ **D0's framing must not narrow to 'surface the swallowed rejection'.** … The population is
  *caller-supplied values the surface accepts and misinterprets* **alongside** the ones it rejects
  silently."
- **Impact:** every `ci` call site whose step does not *separately* validate the payload shape reads
  a failed CI operation as a usable value. Three sites do validate and are safe —
  `branch-cleanup.md:825` and `automatic-review/SKILL.md:671` (both name `status: error` /
  `status: unconfigured` explicitly and route to UNKNOWN) and `branch-cleanup.md:762-775` (the
  positive three-field requirement on `fetch_findings`). The `checks status` snapshot at
  `branch-cleanup.md:425-430` does not: it says "Parse `overall_status` … `pending`, `success`, and
  `none` all proceed", and a `status: error` return carries no `overall_status` at all, matching no
  branch. G2 is the sharpest live consequence of the same hole.
- **Task:** add a third clause to the widened convention covering the three-tier model — an
  `exit_code == 0` return whose `status` is anything other than `success` is NOT a usable value and
  takes the `exit_code != 0` disposition — and state the positive shape requirement at the
  `checks status` snapshot. Alternatively make the providers' `main()` return non-zero on
  `status: error`; that is the wider blast radius and needs its own plan, so record the choice rather
  than assuming it.
- **Done when:** the three widened conventions each state a disposition for an exit-0
  non-`success` return, and a test derives the `ci` invocations in those docs and asserts each is
  either covered by a positive shape requirement in its own step or by the convention's new clause.
- **Suggested grouping:** phase-6-finalize merge-and-review docs

## G4 — Give `branch-cleanup-rereview.md` an exit-code convention and put it in the merge-and-review population

- **Severity:** major
- **Kind:** omission (D0 population miss)
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md`
  — invocations at `:46` (`github_re_review re-review`) and `:55-56` (`github_pr fetch_findings`);
  the file has exactly one `## ` heading, `## Re-review the rebased HEAD (trigger A)` at `:5`, and no
  exit-code convention section. Population literals at
  `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py:75,77`.
- **Evidence:** `branch-cleanup.md:489` — "The full walkthrough … lives in the same-directory
  sub-standard [`branch-cleanup-rereview.md`](branch-cleanup-rereview.md). Load and execute it here
  **on that same advanced-HEAD condition**". The doc produces `{declined_bots}`, retained at
  `branch-cleanup.md:812` and forwarded into `review_completeness check` at `:833`. It existed at the
  landing commit (`git cat-file -e 3c7a1cc8:…/branch-cleanup-rereview.md` succeeds), so it was inside
  D0's stated population — "*every script invocation reachable in the finalize merge-and-review
  path*" — at the time and was missed. Confirmed by an independent WIDE/NARROW/NONE sweep over every
  `*.md` under `phase-6-finalize`, `automatic-review`, `workflow-integration-github` and
  `workflow-pr-doctor` that classifies each doc against its own derived non-`manage-*` invocations:
  this file classifies NONE while invoking two non-`manage-*` scripts.
- **Impact:** the barrier's own re-review sub-step is the one place in the path where a non-zero exit
  carries no disposition at all — neither the widened convention nor an UNKNOWN branch. A failed
  `github_re_review re-review` or `fetch_findings` there can be read as "no fresh review found",
  which routes to the timeout disposition (proceed / defer / ask) rather than to an error — the same
  swallow, one document over. Its `fetch_findings` invocation is also outside D3's parse sweep, so a
  reintroduced bad flag there would not be caught.
- **Task:** add the wide `## Exit-code convention for every script call` section to
  `branch-cleanup-rereview.md` (matching `branch-cleanup.md:59-68`, including the
  stricter-disposition carve-out sentence if the re-review branches warrant one), and add a
  `_REREVIEW_DOC` entry to both `_INVOCATION_DOCS` and `_CONVENTION_DOCS` in the contract test.
- **Done when:** `test_convention_is_widened_wherever_a_non_manage_star_script_is_invoked` runs a
  fourth parametrized case for `branch-cleanup-rereview.md` and passes, and the D3 population grows
  to include that doc's `fetch_findings` invocation (raise the floor accordingly — see G9).
- **Suggested grouping:** phase-6-finalize merge-and-review docs

## G5 — Stop `--stale-participation-bots` silently dropping a pair whose evidence kind is not registry-admissible

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:1216-1221`
  (the `_parse_bot_observations` entry and its comment) and `:363-379` (the admissibility filter
  inside `parse_participation`). The same omission rides in the argparse `help=` string at
  `:1380-1394`.
- **Evidence:** the comment at `:1216-1218` asserts "it takes the same pair form and **the classifier
  reads only the bot_kinds**", but the shared parser filters first:
  `if evidence_kind in bot_registry.participation_evidence(bot_kind): proven[bot_kind] = evidence_kind`.
  Confirmed by execution against the live module —
  `parse_participation('pr-agent:bogus', '--stale-participation-bots')` → `{}`,
  `parse_participation('nonexistent-bot:issue_comment', …)` → `{}`, while
  `parse_participation('pr-agent:issue_comment', …)` → `{'pr-agent': 'issue_comment'}`
  (admissible kinds for `pr-agent`: `['issue_comment', 'inline']`). The help string at `:1384-1387`
  says the flag names a bot "whose observed comment matched a declared participation_evidence publish
  shape" and that "the classifier reads only the bot_kind" — never that a non-admissible kind is
  dropped.
- **Impact:** a stale record the producer emitted is dropped without a word, and the bot falls
  through to `absent` instead of `participated_stale`. Both block, so this is not a false pass — but
  `branch-cleanup.md` states that the two members carry **opposite remedies** ("a required bot on
  `participated_stale` DID publish … so the productive action is a re-review trigger"), and the
  barrier renders those remedies to an operator. This is the same class of polarity-selecting silent
  drop D1 was written to abolish, surviving on the flag D1 converted. It fires whenever the producer's
  emitted `evidence_kind` and the consumer's registry read diverge — a registry edit between the two
  reads, or an unregistered bot. It is a residual, not a regression: pre-fix the flag was parsed by
  `_split_bots`, so every pair was lost unconditionally, and both sides read the same registry
  (`github_pr.py:953` admits only `_kind in participation_evidence(_bot_kind)` before recording).
- **Task:** decide the intended semantics and make code, comment and `help=` agree. Either (a) give
  the stale flag its own parse that enforces the pair SHAPE but does **not** apply the participation
  admissibility filter — the producer already established the kind matched a publish shape, so the
  filter is redundant on the happy path and destructive off it; or (b) keep the filter and make a
  non-admissible pair a loud `MalformedBotFlag` rather than a drop.
- **Done when:** a test feeds `--stale-participation-bots pr-agent:not-a-declared-kind` with
  `pr-agent` required and asserts the outcome is either `participated_stale` (option a) or a
  `status: error` / non-zero exit (option b) — and in no case `absent`; and neither the comment at
  `:1216-1218` nor the `help=` string asserts "the classifier reads only the bot_kind" without naming
  the filter.
- **Suggested grouping:** `automatic-review` / `review_completeness` bot-flag parsing

## G6 — Extend the widened exit-code convention to the rest of the finalize review-and-merge docs, or record the boundary honestly

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
  `workflow-pr-doctor/SKILL.md`, `workflow-integration-github/SKILL.md` (and
  `branch-cleanup-rereview.md`, tracked separately as G4).
- **Evidence:** `report-01.md` justifies the three-doc scope with "the ~35 other docs carrying the
  boilerplate convention are **other phases/steps**, out of scope". An independent sweep that
  classifies every `*.md` under `phase-6-finalize`, `automatic-review`, `workflow-integration-github`
  and `workflow-pr-doctor` as WIDE / NARROW / NONE against its own derived non-`manage-*` invocations
  returns **3 WIDE, 13 NARROW, 6 NONE**; 13 NARROW and 3 of the NONE docs are **inside
  `phase-6-finalize` itself**, several of them PR/review path (`create-pr.md`, `sonar-roundtrip.md`).
  The justification is therefore inaccurate as written. The tree-wide heading count corroborates the
  scale: `grep -rn "Exit-code convention for" marketplace/bundles/` returns 42 headings, 3 wide and
  39 narrow.
- **Impact:** the `manage-*`-scoped convention still structurally excludes non-`manage-*` calls in
  most of the finalize phase, including PR creation (G2 is the live consequence) and the Sonar review
  roundtrip. The defect class the plan closed for three docs remains open for the rest of the same
  phase, and the recorded reason for stopping is wrong, so a future reader will not know the boundary
  was arbitrary.
- **Task:** either widen the heading in every `phase-6-finalize` doc whose derived invocation set
  contains a non-`manage-*` notation (mechanical, and the obligation is already derivable by the
  existing `_invoked_notations` / `_is_manage_star` helpers), or state a defensible boundary in the
  test docstring and correct the report's rationale. Prefer the first: the widening costs one line
  per doc and removes the need for a boundary at all.
- **Done when:** the WIDE/NARROW/NONE sweep over `phase-6-finalize` returns no NARROW or NONE doc
  that invokes a non-`manage-*` script — or the surviving exceptions are enumerated in the test with
  a per-doc reason, and the test fails when a new such doc appears.
- **Suggested grouping:** phase-6-finalize merge-and-review docs

## G7 — State the token FORM at every site that renders a pair-form bot flag

- **Severity:** minor
- **Kind:** stale-doc / incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:830-836`
  (the barrier's `review_completeness check` invocation) and its surrounding prose `:840-856`;
  `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:964-997`
  (`## Canonical invocations` → `review_completeness — check`) and `:999-1010` (the same for
  `deficit`).
- **Evidence:** the barrier's one command carries `--participated-bots` and
  `--stale-participation-bots` (both pair-form) and `--refused-causes` / `--refusal-size-caps` (also
  pair-form) alongside `--required-bots`, `--optional-bots`, `--refused-bots`, `--declined-bots`
  (bare-form), and the prose beneath it discusses emptiness and quoting at length — "the eight list
  flags above are the set here … **The load-bearing defence is the parser, not the quoting**"
  (`:844-846`) — without ever stating which flags take pairs. The canonical block says only "All nine
  list flags take an OPTIONAL value" (`automatic-review/SKILL.md:980`) and nothing about form,
  although `_analyze_manage_invocation.py` treats that block as source of truth. Only
  `automatic-review/SKILL.md:661` (item 4) states the pair form, and only for the FIND step.
- **Impact:** since this plan, a wrong-form token is a hard error (`status: error`, exit 1) rather
  than a silent misparse. A reader composing the barrier call from the producer's records has no
  local statement of which of the eight flags need `bot_kind:value` pairs — the failure is now loud,
  but the doc does not prevent it.
- **Task:** add one sentence at the barrier invocation naming the four pair-form flags and the
  bare-form remainder (mirroring the wording already at `automatic-review/SKILL.md:661`), and add a
  form column or a one-line note to the `## Canonical invocations` blocks for both `check` and
  `deficit`.
- **Done when:** each of the three sites states, in its own text, which list flags take
  `bot_kind:value` pairs and which take bare `bot_kind` tokens.
- **Suggested grouping:** `automatic-review` / bot-flag documentation

## G8 — Correct `review_completeness.py`'s own two-FORM prose, which is false for two of its nine list flags

- **Severity:** minor
- **Kind:** stale-doc (prose-bearing string literals in production code)
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:128-139`
  (module docstring), `:316-322` (the `MalformedBotFlag` docstring), `:1186-1190` (the `_split_bots`
  rejection message, a user-facing error template) and `:116` (the `deficit` usage line).
  Contradicted by `parse_causes` at `:382-423` and by the two cause flags `_add_bot_observation_flags`
  declares at `:1415` and `:1434`.
- **Evidence:** `:128-134` states "The list flags split into two FORMS … The two EVIDENCE-TYPED
  (pair-form) flags — ``--participated-bots`` and ``--stale-participation-bots`` … The remaining list
  flags are bare-form (``bot_kind`` tokens only)." There are **nine** list flags and **four** are
  pair-form: `--refused-causes` and `--refusal-size-caps` both route through `parse_causes`, which
  requires `bot_kind:value` pairs and raises `MalformedBotFlag` on a bare token — confirmed by
  execution (`parse_causes('pr-agent', '--refused-causes')` raises;
  `parse_causes('pr-agent:whatever', …)` returns `{'pr-agent': 'whatever'}`). The
  `MalformedBotFlag` docstring at `:316-322` splits "the flag set" into the same two lists and omits
  both cause flags. The `_split_bots` rejection message tells a caller holding a rejected pair token
  that pairs "belong on a pair-form flag (--participated-bots / --stale-participation-bots)" — wrong
  advice for a `bot_kind:cause` token, and the message a caller actually sees. And the `deficit`
  usage line at `:116` omits `--refusal-size-caps`, which `_add_bot_observation_flags` does declare on
  `deficit` (it is shared by both subcommands) and which `automatic-review/SKILL.md:1007` documents.
- **Impact:** the module's own reference text misdescribes its parser. A caller reading the docstring
  concludes `--refused-causes` takes bare kinds and gets a rejection; a caller reading the rejection
  message is pointed at the wrong flag; a caller reading the `deficit` usage line does not know a
  declared flag exists.
- **Task:** restate the split as four pair-form flags (`--participated-bots`,
  `--stale-participation-bots`, `--refused-causes`, `--refusal-size-caps`, the last two carrying
  `bot_kind:value` rather than `bot_kind:evidence_kind`) and five bare-form ones, in all three
  passages; make the `_split_bots` message name the pair-form set generically rather than two of the
  four; add `--refusal-size-caps` to the `deficit` usage line.
- **Done when:** no passage in the module names a flag-FORM partition that a sweep of
  `_add_bot_observation_flags`'s nine list flags against their parse functions contradicts — ideally
  pinned by a test that derives the two form-sets from the parse routing and asserts the docstring
  names both completely.
- **Suggested grouping:** `automatic-review` / `review_completeness` bot-flag parsing

## G9 — Publish D3's population size on a passing run, raise the floor, and harden the derivation against silent shrinkage

- **Severity:** minor
- **Kind:** incomplete (unmet Verification clause) + latent fragility
- **Where:** `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py:297-309`
  (`test_the_population_size_is_published`), `:162-185` (`_documented_invocations`) and `:182`
  (the `if '[' in block: continue` skip).
- **Evidence:** the plan's Verification section states "**D3's population size is published in the
  test output**, so a future reader can tell a passing test from an empty one." The count appears
  only inside the two assertion messages at `:299` and `:304-309`;
  `grep -n "print(\|record_property\|capsys"` over the file returns nothing (exit 1). Observed: `-q`
  prints `11 passed`; `--collect-only` enumerates six parametrized ids but no run states a count.
  `report-01.md` claims the test "publishes size (6 invocations, floor ≥ 4)". Separately,
  `_documented_invocations` takes `_EXEC_CALL.search(block)` — the *first* notation in a fenced block
  — and then passes `tokens[notation_idx + 1:]` (`:331`), *all* remaining tokens, as that script's
  arguments; a fenced block holding two commands would feed the second command's tokens to the first
  parser. Every block in the current population holds exactly one command, so nothing fails today.
  The `'[' in block` skip is similarly broad: any invocation that grows a bracket silently leaves the
  population.
- **Impact:** the guarantee the clause exists to give — that a reader of a green run can distinguish
  a real sweep from a shrunken one — is not delivered. The `>= 4` floor under-constrains a true
  population of 6, so two invocations could silently drop out (via the bracket skip, a reworded
  fence, or a notation rename) and the suite would stay green.
- **Task:** emit the size on success (a `print` that `-s` surfaces, or
  `record_property('population_size', …)` — whichever the repo's test conventions prefer); make the
  floor derived rather than the literal `4`, or raise it to the true population; narrow the bracket
  skip so it excludes only the `## Canonical invocations` advertised forms rather than any block
  containing a `[`; and either assert one command per matched block or iterate every `_EXEC_CALL`
  match in a block instead of only the first.
- **Done when:** a passing run of the suite emits the population count, and dropping one invocation
  from either population doc fails the size test rather than passing it.
- **Suggested grouping:** `automatic-review` / merge-and-review contract test

## G10 — Correct the test docstring's now-false claim that no parser declares `--enabled-bots`

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py:18` and
  `:291`. Contradicted by
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py:504`.
- **Evidence:** `:18` — "A workflow doc that prescribes a flag no script declares
  (``--enabled-bots``)"; `:291` — "A documented ``--enabled-bots`` (a flag no parser declares)".
  `review_gate_delta.py:504` declares `--enabled-bots`, advertised at `review_gate_delta.py:94` and
  documented at `automatic-review/SKILL.md:1059,1085` as "the coverage DENOMINATOR
  (`required_bots ∪ optional_bots`)". The claim was true at this plan's landing —
  `git cat-file -e 3c7a1cc8:…/review_gate_delta.py` fails, so the script did not exist then; it
  arrived later with the review-versus-gate delta work.
- **Impact:** the suite's own rationale now misstates the tree. A reader checking the docstring
  against the code finds a declared `--enabled-bots` and may conclude the guard is obsolete, or may
  reintroduce the flag on a `github_pr` invocation believing it exists.
- **Task:** reword both passages to name the real invariant — a flag prescribed on a parser that does
  not declare it (`--enabled-bots` on `github_pr fetch_findings`), rather than a flag no parser
  declares — and mention that `review_gate_delta assess` legitimately declares it.
- **Done when:** neither docstring passage asserts anything falsifiable by grepping the tree for
  `--enabled-bots`.
- **Suggested grouping:** `automatic-review` / merge-and-review contract test

## G11 — Record the confirm/refute artefacts the plan required and the report never dispositioned

- **Severity:** minor
- **Kind:** omission (unreported plan obligation)
- **Where:** `doc/plans/review-apparatus/030-…/report-01.md` § Findings and § Deliverables. The
  obligations are in `plan.md` § Claim labels (eight rows) and § Verification.
- **Evidence:** the Claim-labels row "`--in-progress-bots ""` is dropped by the executor so argparse
  sees a flag with no argument, while omitting the flag works | OBSERVED | The executor's argument
  marshalling — **reproduce it once before building on it**" is never mentioned in the report — not
  the claim, not the reproduction, not a disposition — unlike the three D2 null results, which get a
  dedicated table. The cause class is in fact already closed: all nine list flags carry `nargs='?'`
  with `const=''` (`review_completeness.py:1298`, `_add_bot_observation_flags`), and the
  executor's empty-argument stripping is real and locatable —
  `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template:1419-1420`
  (`# Strip empty string args …` / `script_args = [a for a in script_args if a]`), documented at
  `branch-cleanup.md:740-748`. Separately, the plan's § Verification asks for an "endorsement trap"
  hint *if* D0's work touches the rejection reporting; it did not (no `tools-script-executor` path in
  `git show --stat 3c7a1cc8`), so the condition never fired — but the report does not say so.
- **Impact:** no behaviour is wrong, but two of the plan's required confirm/refute artefacts are
  missing from the record. A later reader auditing cause class 4 ("Empty value dropped by the
  harness") cannot tell from the report whether it was examined, dismissed, or forgotten — which is
  the "a defect recorded under a plausible-but-wrong cause looks owned" failure the plan's own Notes
  warn about, in its milder form.
- **Task:** add a short null-result row to the plan's record stating that cause class 4 is closed by
  the pre-existing `nargs='?'` / `const=''` relaxation plus the executor's documented empty-argument
  stripping, citing the template line and the doc; and a one-line "not triggered" for the conditional
  endorsement-trap hint.
- **Done when:** every row of the plan's Claim-labels table, and every conditional clause of its
  § Verification, has a stated disposition somewhere in the plan directory.
- **Suggested grouping:** plan record hygiene / review-apparatus epic
