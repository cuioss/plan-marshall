# PLAN-LB-03: Self-review ends once on a diff no surfacer covers

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-03-self-review-consumer-repos.md` and is queued as one row file, `queue/PLAN-LB-03.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`default:pre-submission-self-review` ships default-on to consumer repositories, and its Step 1 runs the first
surfacing implementor whose script notation resolves. The only implementor is
`ext-self-review-plan-marshall`, whose detectors target Python, skill documents and Markdown; in a Java or
other consumer repository it resolves, runs, classifies the changed files as `other`, and surfaces nothing.
The verifier then declines to close a "clean" verdict that the analysis could not have reached, the step
records `loop_back`, and because no fix can change which surfacer exists the same round repeats until the
loop-back ceiling stops the push and an operator overrides it (about 28 minutes on one TokenSheriff PR, where
4 of 4 files were `other`; 19 of 20 on an API-Sheriff diff). Select the implementor by the content classes
it declares it covers instead of by "first that resolves", and give the step a terminal *not covered*
outcome, so a diff no surfacer covers ends the step in one round with a verdict that says exactly that.
Carries forward truthful-signals PLAN-TRUTH-181 deliverables D1–D3.

## Deliverables

1. **Implementors declare the content classes they cover, and selection uses the declaration.** A
   surfacing implementor states the content classes its detectors cover in a machine-readable declaration
   that `extension_discovery implementors` returns. `ext-self-review-plan-marshall` declares every class it
   has detectors for and does NOT declare the catch-all `other`. Step 1 classifies the live footprint into
   content classes, and an implementor is *applicable* only when its declared classes intersect the
   footprint's classes. A resolvable but inapplicable implementor is not run. Two implementors that declare
   the same class is a registration error reported by discovery, not a silent first-wins.
   Done when: the discovery verb's output for the surfacing ext-point carries the declared classes of
   `ext-self-review-plan-marshall`; a test with a footprint of only `.java` files shows the implementor
   resolved and not selected; a test with a footprint of `.py` and `SKILL.md` files shows it selected and
   its envelope identical to today's for the same fixture; a fixture with two implementors claiming one
   class makes discovery return an error naming both.
2. **A footprint no implementor covers closes the step once, as *not covered*.** When at least one
   implementor resolves and none is applicable, Step 1 skips the surface call, the author dispatch and the
   verifier dispatch, and Step 4 records `--outcome done` under a new non-finding verdict that is distinct
   from every existing one (for example `"self-review not covered: no surfacer covers this diff's
   content"` — at most 80 ASCII characters, no trailing period, not a prefix of another verdict, and
   without the substring `found`), with `work_performed=false` and facts carrying the uncovered file count
   and the footprint's class names. It is not the *not-run* verdict (no implementor resolved at all) and
   not the *zero-observation* verdict (a surfacer ran and observed nothing); the three stay separate
   records. A WARNING decision-log line names the uncovered classes. No `loop_back` is recorded and no
   iteration is spent.
   Done when: a test of the documented branch table shows the not-covered path reaching `done` with the
   new verdict and without a verifier answer; the verdict-vocabulary test accepts the new verdict beside
   the existing five and still proves no verdict is a prefix of another; `ext-point-self-review-surfacing.md` defines the outcome beside the not-run
   fallback.
3. **Uncovered files inside a covered diff are reported, and a refusal that no round can change does not
   loop.** When an applicable implementor runs over a footprint that also holds files of classes nobody
   declared, those files are reported as `not_covered` with their count in the round's published
   boundaries and are passed to the verifier as a stated boundary, so they are neither folded into a clean
   zero nor a ground for `may_close: no`. In addition, a round that would record `loop_back` with EMPTY
   author findings at the same HEAD as the previous round's `head_at_completion` (no fix landed in
   between, same non-closing verifier state) does not record a further `loop_back`: nothing a next round
   reads has changed, so the step records the gap once and ends, as Deliverable 2 does, with a verdict
   naming the unresolved verifier state. `verifier_unavailable` is excluded — a failed dispatch can
   succeed on retry.
   Done when: a test of a mixed footprint (Python plus Java) shows the Python slice surfaced, the Java
   files counted as `not_covered`, and the verifier prompt carrying that count; a test replays two
   consecutive empty-findings refused rounds at one HEAD and shows the second ending the step without
   incrementing the loop-back count; a round with findings, or with a moved HEAD, still records
   `loop_back`.
4. **Controls.** (a) A plan-marshall-only diff produces today's envelope and today's verdicts unchanged.
   (b) A project where no implementor resolves still records the not-run verdict, not the new one.
   (c) Fixtures shaped like the two observed consumer diffs — 4 of 4 files `other`, and 19 of 20 `other`
   with one covered file — end in one round: the first as not covered, the second with the one file
   reviewed and 19 reported `not_covered`. (d) `test_self_review_unclassified_surface.py`, which today
   pins the "wrong-domain implementor resolves, runs, and observes nothing" route as contract, is rewritten
   to pin the new routes with its matched negative control kept.

## Claim Labels

- OBSERVED: Step 1 selects exactly one implementor, by resolvability — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:119` ("Select the first implementor whose notation **resolves in the current executor**"); § "Domain-Aware Candidate Surfacing" (:39) states the step ships `default_on: true` to consumer projects.
- OBSERVED: exactly one surfacing implementor exists — `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` (frontmatter `implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing`); a listing of `marketplace/bundles/*/skills/ext-self-review-*` finds this skill and one stale directory holding only an untracked `__pycache__` (`marketplace/bundles/plan-marshall/skills/ext-self-review-plan-marshall/`), which is not a skill.
- OBSERVED: the implementor's class vocabulary is private to it and every unanticipated file shape lands in `other` — `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` § `CONTENT_CLASSES` (:2463-2470: `python`, `skill_doc`, `standards_doc`, `markdown_other`, `structured_config`, `other`) and § `_classify_content` (:2476-2500, final `return 'other'`).
- OBSERVED: discovery reads no content-class key from implementor frontmatter — `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` § `_IMPLEMENTOR_FRONTMATTER_KEYS` (:894-902: `name`, `order`, `default_on`, `presets`, `description`, `canonicals`, `verification_profile`).
- OBSERVED: every non-closing verifier state records `loop_back` — `pre-submission-self-review.md:505-511` (table) and `:520` ("Every non-closing state above records `loop_back`, never `done` and never `failed`").
- OBSERVED: the verifier is told to refuse "a clean verdict that reads as a reviewed diff where the structural limit says this analysis class could not reach the question", and to answer `may_close: no` when anything "suggests a further round would find something this one did not look for" — `pre-submission-self-review.md` § "Step 3b" verifier prompt (the two numbered questions).
- OBSERVED: a round that surfaced nothing over a non-empty scope is routed to a Branch A close under the zero-observation verdict, but Branch A still requires the verifier's `acceptance: accepted` and `may_close: yes` — `pre-submission-self-review.md` § "A clean verdict states what the round observed" (:314) and § "Step 4" stop-path confirmation gate (:540-547). No branch exists for "the verifier will never say yes for a reason no fix changes".
- OBSERVED: the only path that closes without a verifier answer is the zero-generator fallback, reached when NO implementor resolves — `pre-submission-self-review.md:181-183` and `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md:24-26`.
- OBSERVED: the existing non-finding verdict set is four strings plus the findings verdict, with a stated disjointness rule — `pre-submission-self-review.md` § "Dispatched-envelope output" (:399-407).
- OBSERVED: the surfacer already publishes a per-class partition of its file set — `ext-point-self-review-surfacing.md` § `delta_coverage` (`by_class[C]{content_class,files,files_with_candidates,files_without_candidates}` at :95; "the class vocabulary itself is the implementor's" at :224).
- OBSERVED: a test pins the wrong-domain route as contract — `test/plan-marshall/phase-6-finalize/test_self_review_unclassified_surface.py` module docstring ("Route 2 — a wrong-domain implementor resolves, runs, and observes nothing").
- OBSERVED: in consumer repositories the plan-marshall implementor's notation resolves, which is why Step 1 selects it instead of taking the zero-generator fallback — the generated executors of the local consumer checkouts `/Users/oliver/git/TokenSheriff/.plan/execute-script.py` and `/Users/oliver/git/API-Sheriff/.plan/execute-script.py` each carry `ext-self-review-plan-marshall` entries (3 matches each).
- HYPOTHESIS: on the observed consumer diffs the loop was driven by the verifier refusing or answering `may_close: no` over a zero-observation clean verdict, round after round at an unchanged HEAD — reported by two runs (TokenSheriff PR #744, API-Sheriff), not reproduced here; confirm from those plans' archived `metadata.phase_steps` and decision logs, or by replaying a 4-of-4 `other` fixture through the documented branches (verify-at-outline).
- HYPOTHESIS: Step 1 can classify the footprint before choosing an implementor without a shared envelope module — either by a cheap applicability subcommand on the implementor script, or by a small path classifier owned by `extension-api`; confirm which at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py` § the `surface` subcommand's footprint derivation (verify-at-outline).
- Verify-first clause: decide where footprint classification lives for this plan (implementor-side applicability call versus an `extension-api` classifier) before scoping Deliverable 1; the shared envelope is out of scope, so the choice must not require moving `CONTENT_CLASSES` out of the implementor.
- Verify-first clause: enumerate the verifier-refusal grounds that cannot change between rounds at an unchanged HEAD (surfacer domain, content class, zero detectors) and confirm the same-HEAD rule in Deliverable 3 catches each; if a ground exists that the rule misses, add it or report it.
- Verify-first clause: the terminal outcome in Deliverables 2 and 3 is `done` with a not-covered verdict and a WARNING. If the operator wants an unattended run to halt and ask instead, that is a one-line change of the recorded outcome; settle it at outline and record the choice.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — § "Domain-Aware Candidate Surfacing", § "Step 1" selection, § "Dispatched-envelope output" verdict vocabulary, Step 3b verifier-prompt boundary lines, new not-covered branch in § "Step 4"
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — declared coverage, applicability, the not-covered outcome beside the not-run fallback
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — parse and return the coverage declaration; duplicate-class registration error
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` — the coverage declaration
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py` — applicability / `not_covered` reporting
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` — `CONTENT_CLASSES` as the source of the declaration (read; edited only if the declaration is derived from it in code)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_self_review_unclassified_surface.py` — rewritten route contract (D4d)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_submission_self_review_verdict_verdict.py` — verdict-vocabulary disjointness with the new verdict
- OBSERVED: `test/plan-marshall/extension-api/test_extension_discovery.py` — coverage declaration and duplicate-class error
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_delta_coverage.py` — unchanged-envelope control and `not_covered` count

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-02 (`PLAN-LB-02-self-review-convergence.md`) — both edit `phase-6-finalize/workflow/pre-submission-self-review.md`. Section ownership: THIS plan owns § "Domain-Aware Candidate Surfacing", § "Step 1" (implementor selection and the zero-generator fallback), the non-finding verdict vocabulary in § "Dispatched-envelope output", the boundary lines of the Step 3b verifier prompt, and the new not-covered branch in § "Step 4". PLAN-LB-02 owns § "Step 3b" from the non-closing state table through the `qgate add` block and the unverified-dispatch paragraph, § "Step 4" Branch B and the paragraph that closes Step 4, and § "Round-loop termination". Neither plan edits the other's sections. Sequence the two, never run them together; the second to start rebases onto the first. This plan is the smaller one and is suggested first.
- Adjacent to: the per-source loop-back budget and the operator close that PLAN-LB-02 adds. Deliverable 3's same-HEAD rule ends a round before it asks for a loop-back, so it does not read or write the loop-back counter in either its current or its per-source form.
- Left out on purpose: truthful-signals PLAN-TRUTH-181 D4–D7 — the shared surfacing envelope module, the machine-readable `not_covered` landing fact for orchestrator epics, the implementor authoring guide, and the multi-implementor merge controls. With one implementor there is nothing to merge; Deliverable 1 selects at most one applicable implementor and reports the duplicate-class case as an error.
- Left out on purpose: surfacers for other domains (Java, consumer Python, JavaScript, documents — truthful-signals PLAN-TRUTH-182 to -185). After this plan a consumer diff is honestly reported as not covered; it is still not reviewed. A consumer diff of `.py` or `.md` files continues to be surfaced by the plan-marshall-domain detectors, because those classes are declared.
- Foreign-repo work: none. The consumer repositories receive the fix through the normal bundle sync.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-03-self-review-consumer-repos.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
