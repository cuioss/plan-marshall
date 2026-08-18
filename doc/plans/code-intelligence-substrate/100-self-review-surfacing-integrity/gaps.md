# Gaps — 100-self-review-surfacing-integrity

D1 and D2 landed complete and correct, with negative controls this audit re-proved by mutation. What
remains falls into three clusters. **D4's guard is opt-in and nothing opts in**, so the failure mode it
was built for is unchanged in practice (G1). **D5's mechanism is unreachable from the step that would
use it** — Step 4 never points at the termination section, and the remediation sentence that operators
actually read still prescribes the correct-and-re-run cycle D5 identifies as the re-seeding mechanism
(G2, G3). And a residue of stale or imprecise claims survives in shipped docs, in an operator-quotable
string, in the coverage test's own publication of its population, and in the run report (G4–G10). Ten
gaps: one high, four medium, five low.

## G1 — Make the undeliverable-to-running-plan guard reachable from the write sites that need it

- **Kind:** incomplete
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:936`
  (`cmd_inbox_write`, the `if target_plan is not None:` branch); call sites at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:204`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-preference-emitter.md:220`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md:103`,
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md:338`
- **Evidence:** The guard fires only when `--target-plan` is supplied — `target_plan =
  getattr(args, 'target_plan', None)` followed by `if target_plan is not None:`. A content sweep of
  `marketplace/bundles/` and `test/` for `target-plan|target_plan` returns hits **only** in
  `_orchestrator_inbox.py`, `orchestrator.py`, `plan-orchestrator/SKILL.md`, `inbox-envelope.md` and
  `test_inbox_channel_contract.py`. Every one of the five documented `orchestrator inbox write`
  invocations in the bundles omits the flag, and `plan-orchestrator/SKILL.md:195` describes it as
  "Optional". The tests confirm the shape:
  `test_inbox_channel_contract.py:340` — `test_untargeted_write_is_unaffected_by_a_running_plan` —
  asserts that an untargeted write **succeeds** while `plan-alpha` is running.
- **Why it matters:** The originating incident (plan.md arm C) was a message aimed at a plan that was
  already running, written by a sender who did not think of it as "targeted". Under the shipped guard
  that message still queues silently, because the sender never passes `--target-plan`. The deliverable's
  *Done when* — "writing a message that names a running plan produces an explicit undeliverable report"
  — is satisfied only for senders who had already diagnosed the problem themselves. The guard is a
  correct mechanism with no trigger.
- **Action:** Give the guard a reachable trigger. Two viable arms, in preference order: (a) make
  `--target-plan` **required** on the `--kind finding` write path (the kind that carries plan-directed
  content), so a finding aimed at a plan must name it and is then adjudicated; or (b) add a payload-side
  detection — scan the staged payload body for a plan id matching a `running` row and refuse, or at
  minimum emit a warning naming the running plan. Whichever arm, add the obligation to
  `inbox-envelope.md` § Write-side deliverability and to each of the four call-site docs above, so a
  writer is told to name the target.
- **Done when:** A write whose payload names a currently-running plan, issued without any new flag by a
  caller following the documented invocation at `emit-landing.md:204` (or the `finding`-kind path),
  produces `undeliverable_to_running_plan` — and a test drives that case end-to-end from the documented
  invocation form rather than from a hand-constructed `--target-plan` argv.
- **Effort:** M
- **Risk if fixed:** Arm (a) is a breaking argument-surface change for existing `--kind finding` writers;
  arm (b) risks false positives when a payload legitimately *mentions* a running plan without being
  aimed at it, which would refuse a valid write. Arm (b) must therefore refuse only on an unambiguous
  addressing form, or warn rather than refuse.

## G2 — Wire the self-seeding classification into Step 4, where a non-clean round is actually processed

- **Kind:** omission
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:378-403`
  (Step 4 Branch B), against `:409-427` (§ "Round-loop termination")
- **Evidence:** `:420` states the obligation — *"Reporting is a `manage-logging decision --level WARNING`
  naming the round self-seeding … so the classification is an auditable record rather than merely
  narrative"*. Step 4 Branch B is the only place a non-clean round is handled; it emits the
  `manage-findings qgate add` loop (`:385-389`), a `git rev-parse` (`:395`) and `mark-step-done
  --outcome failed` (`:399-402`), and contains no reference to self-seeding, to the WARNING log, or to
  the termination section. Grepping the whole doc for `self-seed|out of budget` returns matches only at
  `:409, 416, 418, 420, 422, 425, 427` — all inside the terminal section. The reference direction is
  one-way: the termination section names Step 4, Step 4 does not name it.
- **Why it matters:** An executor works this workflow as a numbered step sequence. Reaching Step 4 with
  findings, it records `failed` and stops — never learning that a classification and a WARNING log are
  owed. The D5 mechanism therefore never fires in practice, which reproduces the exact defect this plan
  fixed elsewhere: a documented contract with no consuming path. It also makes the CodeRabbit finding
  the report records as *"FIXED — recorded via the existing `failed` outcome + `manage-logging decision
  --level WARNING`"* effectively unfixed.
- **Action:** In Step 4 Branch B, immediately before the `mark-step-done` block, insert a classification
  sub-step: determine whether every finding in this round is a doc-claim defect class inside the round's
  delta scope (per § "Round-loop termination"), and when it is, emit the
  `manage-logging decision --level WARNING` call naming the round self-seeding, with the concrete
  command block. Cross-reference `:409` by section name from Step 4.
- **Done when:** Step 4 Branch B contains an explicit link to § "Round-loop termination" and a runnable
  `manage-logging decision --level WARNING` block for the self-seeding case, so a reader executing Steps
  1–4 in order performs the classification without reading past Step 4.
- **Effort:** S
- **Risk if fixed:** Step 4 grows a conditional an executor may mis-evaluate, adding a WARNING log line
  to ordinary non-clean rounds if the doc-claim/delta-scope predicate is stated loosely. State the
  predicate by reference to `:416` rather than restating it.

## G3 — Give the Step 4 remediation sentence a self-seeding carve-out

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:407`
- **Evidence:** Verbatim: *"The operator must address every finding (amend the diff: rename, tighten
  regex, rewrite wording, delete duplicate section, fix contract drift), re-run the step, and only then
  advance to `push`."* Against `:418`: *"**Resolve a self-seeding finding by deletion, not correction.**
  … Rewriting authors the next round's finding; deletion ends the class."* Three of the five prescribed
  remedies at `:407` (`rename`, `rewrite wording`, `fix contract drift`) are corrections that author new
  prose, and `:407` carries no exception.
- **Why it matters:** `:407` is the sentence positioned where the operator acts — at the close of Step
  4, immediately after the failure bookkeeping. `:418` sits 11 lines later in a section Step 4 never
  references (see G2). An operator following the document in order performs exactly the
  correct-and-re-run cycle D5 exists to interrupt. This is a same-document normative narrowing with no
  pointer — the defect class check 8 (`same_document_contradiction`) is built to catch, shipped inside
  the workflow that hosts check 8.
- **Action:** Append a carve-out clause to `:407`: for a round classified self-seeding per § "Round-loop
  termination", the remedy is DELETION of the over-claiming prose, not rewriting — with a link to the
  section.
- **Done when:** `:407` names the self-seeding exception and links § "Round-loop termination", so the
  two normative statements about how to resolve a finding no longer disagree when read in document
  order.
- **Effort:** S
- **Risk if fixed:** An operator over-applies deletion to ordinary (non-self-seeding) doc-claim findings
  where a correction is the right fix. The clause must be gated on the classification, not on the
  defect class alone.

## G4 — Correct the stale `count_prose` rationale in the implementor SKILL.md

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md:206`
- **Evidence:** The blockquote reads: *"`count_prose` because it anchors a **sibling-SKILL.md re-check**
  rather than flagging an added line"*. The detector no longer scans a sibling `SKILL.md`: since
  `_self_review_detectors.py:1078` it scans every contract source —
  `SKILL.md` **plus** every `standards/*.md` — and the same SKILL.md says so correctly 50 lines earlier
  at rule 14 (`:256`) and in the schema placeholder at `:178`
  (`{repo-relative-contract-source-path}`). A sweep of `marketplace/bundles/` for
  `sibling-SKILL.md|sibling SKILL.md|SKILL.md sibling` returns exactly this one hit.
- **Why it matters:** The document contradicts itself about the detector's file set, in the contract doc
  that is the authoritative statement of the implementor's detection rules. A reader taking `:206` at
  face value concludes a stale count in a `standards/*.md` is out of scope — which is precisely the
  false belief D1 was built to end. It is also the fourth *consumer kind* of the D1 value change that no
  reviewer caught, alongside the three the report's § "What have we learned" enumerates (echo
  enumeration, check description, schema placeholder) — evidence that the sweep-by-consumer-kind
  refinement landed in `#1192` was warranted and that this site predates it.
- **Action:** Change "a sibling-SKILL.md re-check" to "a contract-source re-check (`SKILL.md` plus every
  `standards/*.md`)" at `:206`, matching rule 14's wording.
- **Done when:** No occurrence of `sibling-SKILL.md` remains in `marketplace/bundles/`, and `:206`'s
  description of `count_prose` agrees with rule 14 at `:256`.
- **Effort:** S
- **Risk if fixed:** None — a prose correction in a doc that plugin-doctor lints structurally, not
  semantically.

## G5 — Fix the singular/plural defect in the operator-quotable scope statement

- **Kind:** bug
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py:126-133`
  (`_format_scope_statement`)
- **Evidence:** `noun = 'file' if files_in_scope == 1 else 'files'` is computed once and reused for a
  plural demonstrative later in the same sentence. Exercised directly:
  `_format_scope_statement('delta', 1, 'abc123')` →
  `'searched delta scope: 1 file changed since abc123 — a scoped round, so a clean result covers only
  these file, NOT the full plan surface'`. `files_in_scope` of 0 and of 2+ render correctly.
- **Why it matters:** A one-file delta is the commonest shape of a loop-back round, and
  `pre-submission-self-review.md:257` instructs the reviewer to *quote the round's `scope_statement`* in
  a finding rationale — so the broken text propagates verbatim into findings and PR bodies. The purpose
  of the field is to be restated without rewording; text a reader feels compelled to fix by hand
  defeats that.
- **Action:** Use the plural form for the demonstrative regardless of count (e.g. "covers only the files
  searched"), or compute a second demonstrative-appropriate noun. Extend
  `test_self_review.py:3736` to assert the full sentence for the 1-file delta case, not just its prefix.
- **Done when:** `_format_scope_statement('delta', 1, ref)` returns a grammatical sentence, and a test
  asserts the complete string for `files_in_scope` of 0, 1, and 2.
- **Effort:** S
- **Risk if fixed:** Three existing tests assert on prefixes of this string
  (`test_self_review.py:3736,3760,3804`); a rewording of the prefix would break them. Keep the prefix
  (`searched delta scope: N file(s)`) byte-identical and change only the tail.

## G6 — Make the D2 coverage test actually publish its population

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_check_coverage.py:103`
  (signature) and `:110` (the `print`)
- **Evidence:** `def test_every_counted_candidate_list_has_a_consuming_check(self, capsys):` requests
  `capsys` and never references it. The population is emitted by a bare
  `print(f'counted candidate lists (population size): {len(population)}')`, which pytest captures and
  discards on a passing run — confirmed: the line appears only when the file is run with `-s`. The
  plan's Verification section requires *"D2's population-derived test must publish the population size
  it enumerated"*, on the stated reasoning that a set-guarding test returning zero from an empty
  population is the archetype the plan is about.
- **Why it matters:** On a green CI run — the only run anyone looks at — the population size is
  published nowhere. The `assert len(population) > 0` at `:109` prevents a vacuous pass, but the figure
  itself, which is what a reader would use to notice the population silently shrinking from 17 to 1, is
  invisible. The unused `capsys` fixture is the tell that the publication was intended to be asserted
  and was not.
- **Action:** Either capture and assert the printed line via the already-requested `capsys`, or replace
  the `print` with `record_property('counted_candidate_lists', len(population))` so the figure lands in
  the JUnit XML on a passing run. Remove `capsys` if unused after the change.
- **Done when:** The population size is observable in the output of a **passing** run (JUnit property or
  asserted captured output), and no unused fixture remains in the signature.
- **Effort:** S
- **Risk if fixed:** None — test-only.

## G7 — Correct the registry entry count in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/100-self-review-surfacing-integrity/report-01.md:127`
- **Evidence:** The report states: *"Searched scope: the `CANDIDATE_LISTS` registry in
  `_self_review_patterns.py` (1 file, 23 entries, 17 `in_total`)"*. Re-derived by counting
  `CandidateList(` constructions inside the `CANDIDATE_LISTS` tuple: **22** entries at HEAD and **22**
  at the landed commit `94bcddf`; 17 `in_total` at both. The `17` is right, the `23` is wrong. The PR
  body for the same claim says "1 file, 17 `in_total` entries" and gives no total, so the error is
  confined to the report.
- **Why it matters:** Low blast radius — the report is a record, not a contract — but this is the one
  section whose stated purpose is to demonstrate D3's scope-and-count discipline on the run's own
  claims. A demonstration of "publish your scope and your count" that publishes a wrong count
  undermines the rule it exemplifies, and a later retrospective reading the report would inherit the
  figure.
- **Action:** Change "23 entries" to "22 entries" at `report-01.md:127`.
- **Done when:** `report-01.md:127` states 22 entries, matching a re-derivation from
  `_self_review_patterns.py` at the landed commit.
- **Effort:** S
- **Risk if fixed:** None.

## G8 — Reconcile D3's shipped mechanism with its literal *Done when*

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/100-self-review-surfacing-integrity/plan.md:99`
  (D3 *Done when*) against
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py:402`
  and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:257`
- **Evidence:** The plan requires *"an absence claim without a scope statement is **rejected by the
  surface**"*. What shipped is the converse construction: the surface always **emits**
  `scope_statement` (`self_review.py:402`, unconditional, no early return before it), and the obligation
  on a claim to quote it is prose at `:257` (*"it MUST state the searched scope … quote the round's
  `scope_statement`"*) with no validator. The report declares this openly under "Enforcement split (two
  parts)" and records the CodeRabbit finding accepted as guidance. No rejection path exists anywhere:
  a content sweep for a rationale validator over `findings[]` returns nothing, consistent with the
  report's reasoning that findings are LLM-authored and there is no array for a Python validator to
  inspect.
- **Why it matters:** The plan's own § Verification says *"D3 is verified against this plan's own
  output … if any absence claim in them lacks a scope statement, D3 has failed regardless of what the
  code does"* — i.e. the deliverable was written expecting enforcement, not publication. The
  substitution is defensible (an LLM-rationale validator would be a new enforcement mechanism unlike
  every other check in the workflow), but as it stands the contract documents an obligation with no
  consuming check, which is structurally the same shape as D2's original defect. Left unreconciled, a
  later reader of the ext-point believes the surface refuses scope-less absence claims.
- **Action:** Do not build a validator. Instead record the boundary where a reader will meet it: add one
  sentence to `ext-point-self-review-surfacing.md` § Output Schema (near `:64`) stating that
  `scope_statement` is a **published** field and that the obligation to quote it in an absence claim is
  enforced by the consumer workflow's cognitive review, not by the surfacer — so no consumer infers a
  refusal path that does not exist.
- **Done when:** The ext-point contract states explicitly that the surfacer publishes but does not
  enforce the scope-quoting obligation, and names the workflow section that carries the obligation.
- **Effort:** S
- **Risk if fixed:** Adding prose to a contract doc is itself the doc-claim-half seeding D5 describes;
  keep it to one sentence and cross-reference rather than restate.

## G9 — Decide and pin the deliverability guard's behaviour on an unreadable ledger

- **Kind:** bug
- **Severity:** low
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:299-309`
  (`_running_plan_ids`)
- **Evidence:** `read_json(epic_root / STATUS_FILE)` returning a non-dict, or a `plans` value that is
  not a list, yields `set()`, so the guard at `:941` cannot fire. Documented as intentional at
  `:293-297` (*"with no readable queue there is no plan whose running state can be confirmed, so the
  deliverability guard … does not fire on an unverifiable state"*) and in the contract at
  `inbox-envelope.md:41` (*"or `status.json` is unreadable / carries no queue | the write PROCEEDS"*).
  No test covers the unreadable-ledger case: `test_inbox_channel_contract.py:299-363` covers running,
  landed, untargeted, and malformed-id, but never a corrupt or absent `status.json`.
- **Why it matters:** A corrupt epic ledger silently converts a refusal into a queue — the guard reports
  nothing and the caller cannot distinguish "target is not running" from "I could not tell". The
  fail-open is the right default (refusing on an unverifiable state would block legitimate writes), but
  it is currently invisible: there is no signal at all in the success TOON that the check was
  indeterminate.
- **Action:** Keep the fail-open, but make it legible — emit an advisory field (e.g.
  `target_plan_check: indeterminate`) on the success TOON when `--target-plan` was supplied and the
  status document could not be read as a queue. Add a test covering an absent and a malformed
  `status.json`.
- **Done when:** A `--target-plan` write against an epic with a missing or malformed `status.json`
  succeeds **and** carries an indeterminate marker, pinned by a test.
- **Effort:** S
- **Risk if fixed:** A new output field on the write verb's success TOON; check no consumer asserts an
  exact key set on that output before adding it.

## G10 — Harden the D2 coverage test's numbered-check discriminator against silent widening

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_check_coverage.py:55`
  (`_NUMBERED_CHECK_OPENER`) and `:65-78` (`_numbered_check_block`)
- **Evidence:** The block is `region[first_numbered_opener_match.start():]` — everything from the first
  `^\d+\.\s` line to the region end. Its docstring states the assumption openly: *"The numbered checks
  are the LAST thing in the Step-3 region before the dispatched-envelope output"*. That holds today
  (verified: openers `1.` through `17.`, contiguous, nothing earlier in the region opens with a digit,
  region terminates at `### Dispatched-envelope output`). Nothing pins it. A `####` subsection appended
  after check 17, or a numbered list inserted into the region's preamble (which currently spans
  `:235-280` and contains several `####` subsections), would widen the block — and the narrowing that
  `test_coverage_predicate_rejects_a_key_present_only_in_non_check_prose` exists to guarantee would stop
  applying to the real document while that synthetic test kept passing.
- **Why it matters:** The narrowing is the whole strength of the invariant: without it, a counted key
  mentioned anywhere in the Step-3 region reads as covered, which is the weaker predicate CodeRabbit
  finding 2 had already rejected once. Silent reversion to that predicate would leave a green test
  guarding nothing — the vacuous-guard shape this plan is about.
- **Action:** Add an assertion over the real document that the extracted block's numbered openers are
  exactly the contiguous run `1..N` with `N == len(_counted_lists())`-independent but non-zero, and that
  the block's last non-blank line belongs to the final numbered check (e.g. no `####` heading occurs
  inside the block).
- **Done when:** A test fails if a `####` heading appears inside the extracted numbered-check block, or
  if the block's ordinals are not a contiguous run starting at 1.
- **Effort:** S
- **Risk if fixed:** A structural assertion over prose can become brittle if the check list legitimately
  gains a sub-heading; scope the assertion to `####`-level headings only, which the numbered checks do
  not currently use.
