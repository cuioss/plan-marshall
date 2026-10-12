# PLAN-LB-34: Self-review for every domain, part 1: several surfacers can coexist, and Java gets one

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-34-self-review-surfacing-foundation-and-java.md` and is queued as one row file, `queue/PLAN-LB-34.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on 2026-10-09 by operator instruction ("I meant the self-review surfacer. This is the most
> important one. For all domains"). It is the first of three plans: this one builds the foundation and
> the Java surfacer; PLAN-LB-35 adds JavaScript and Python; PLAN-LB-36 adds documents, containers and
> requirements. It revives the design of the retired `truthful-signals` specs PLAN-TRUTH-181 (foundation)
> and PLAN-TRUTH-182 (Java), re-read against HEAD `fcd54e6ef`, and takes over the four self-review
> deliverables PLAN-LB-28 carried from PLAN-LB-03 (tagged below), which were the reduced first third of
> the same foundation.

## Objective

The pre-submission self-review ships switched on to every repository that uses plan-marshall. Its
value comes from a *surfacer*: a script that reads the diff and lists the places worth a reviewer's
attention — changed functions, regular expressions, contract documents, paired operations, added I/O
without error handling — so the review reads those places and not just the diff top to bottom. Exactly
one surfacer exists, and it understands this repository's own material: Python scripts, skill documents
and Markdown. In a Java or JavaScript repository it runs, classes every changed file as `other`, and
lists nothing. The review then has nothing to look at, and before the change that shipped as #1726 it
looped to the round limit (19 of 20 files `other` on one API-Sheriff diff; 4 of 4 on a TokenSheriff
pull request, about 28 minutes). Since #1726 such a round closes — which means a Java change now passes
self-review without having been reviewed.

The extension point cannot host a second surfacer today: the workflow runs the first one that
resolves, the code that builds the result envelope is private to the one implementor, and the workflow
text and its findings are wired to that implementor by name. This plan makes the extension point host
several surfacers at once — each declares the kinds of file it covers, every applicable one runs over
its own slice, the results are merged, and whatever nobody covers is reported as not covered instead
of as clean — and it delivers the first real second surfacer, for Java, as the proof that the
foundation works on a repository that needs it.

## Deliverables

1. **[PLAN-LB-03 D1, widened]** **A surfacer declares what it covers, and selection follows the
   declaration.** Each implementor declares the content classes its detectors cover. The
   classification of a changed path into a content class is shared, so every implementor and the
   workflow see one partition of the footprint. An implementor is applicable when its declared
   classes intersect the footprint's; a resolvable but inapplicable implementor is not run. Two
   implementors declaring one class is a registration error that names both, never a silent
   first-wins. `ext-self-review-plan-marshall` declares every class it has detectors for and not
   the catch-all `other`. *Done when:* the discovery output carries each implementor's declared
   classes and its script notation; a footprint of only `.java` files shows the plan-marshall
   implementor resolved and not selected; a fixture with two implementors claiming one class
   returns the error naming both.

2. **Every applicable surfacer runs, and the results are merged.** Step 1 of the workflow runs
   each applicable implementor over its own class slice and merges the envelopes: candidate lists
   concatenate, counts and family counts sum, `delta_coverage.by_class` rows come from the
   implementor that owns the class, and each candidate keeps which implementor produced it. The
   candidate gate, the prose screening and the verifier prompt read the merged envelope. A finding
   is filed under the component of the implementor whose candidate it came from, not under one
   hard-coded name. *Done when:* a fixture with two implementors and a mixed footprint yields one
   merged envelope in which both classes appear in `by_class`, the totals equal the sum of the
   parts, and a finding from each side carries its own component; a plan-marshall-only footprint
   yields today's envelope byte for byte.

3. **[PLAN-LB-03 D2, D3]** **What nobody covers is reported as not covered, once.** When at least
   one implementor resolves and none is applicable, the step skips the surface call and both
   dispatches and records `done` under a new non-finding verdict that says no surfacer covers the
   diff, with the uncovered file count and class names as facts and a WARNING log line; no
   loop-back is recorded. When some classes are covered and some are not, the uncovered files are
   counted as `not_covered` in the round's published boundaries and passed to the verifier as a
   stated boundary, so they are neither folded into a clean zero nor a ground to refuse. The
   not-run verdict (no implementor resolved at all) and the zero-observation verdict stay separate
   records. *Done when:* the verdict-vocabulary test accepts the new verdict beside the six that
   exist and still proves none is a prefix of another; fixtures shaped like the two observed
   consumer diffs end in one round, the first as not covered, the second with its covered file
   reviewed and nineteen counted as not covered.

4. **The envelope code is shared.** Move the parts that do not depend on a language — reading the
   footprint and the diff, the since-ref scoping, the candidate-list registry with its families,
   the composition of counts, scope statement, structural limit and coverage, and the two
   detectors that work on any text (`touched_claims`, `keep_markers`) — into one module an
   implementor in any bundle imports. `ext-self-review-plan-marshall` becomes its first consumer.
   *Done when:* the plan-marshall implementor's existing test corpus passes with its output
   unchanged byte for byte; a minimal second implementor in a test fixture builds a valid envelope
   from the shared module in under fifty lines of its own code.

5. **The workflow and the contract stop assuming the one implementor.** The severity rubric the
   reviewer grades by lives in the plan-marshall implementor's skill document and the contract
   says it is "stated there and nowhere else"; move it to a domain-neutral home that every
   implementor's findings are graded by. The checks the reviewer runs are worded for Python and
   plan-marshall material (`output_toon`, argparse `help=`, `subprocess` with `check=True`, a
   `def` header, `SKILL.md` and `standards/*.md`): state each check by what it looks for, and let
   each implementor's skill document say how the check reads in its language. The contract
   documents the `--contract-radius` argument the workflow already forwards and the undocumented
   `local_base_behind_upstream` field, and says what `changed_code_units` means for a language
   that is not Python (the kinds of unit, and that an implementor without them emits the list
   empty and says so in its structural limit). *Done when:* a doc-contract test asserts the
   workflow names no implementor outside one "in this repository" example and no
   language-specific token in a check's statement; the contract lists every argument the workflow
   passes and every field the implementor emits.

6. **"Not covered" is a fact a consuming epic can read.** The landing facts a plan reports carry
   whether the self-review was not covered, with the file count, so an orchestrator can tell "no
   surfacer applied" from "reviewed clean" without parsing a verdict string. *Done when:* the
   landing-payload specification names the fact, the emitter writes it, and a test reads it back
   for the not-covered and the partly-covered case.

7. **An authoring guide and a conformance suite for a new surfacer.** The extension-point
   standard gains the guide: the shared module, the class declaration, the merge rules, what to
   emit where a language has no equivalent signal, and how to state an honest structural limit;
   its implementor list is derived, not hand-kept. One parametrised test suite runs against every
   discovered implementor and checks the contract: every registry key present, every declared
   class seeded, the class partition total over the scope, family counts summing to the total, a
   positive and a matched negative fixture per detector the implementor claims. *Done when:* the
   suite runs green over the plan-marshall implementor and the Java implementor of this plan, and
   fails for a fixture implementor that omits a registry key.

8. **[PLAN-LB-03 D4]** **Controls.** A plan-marshall-only diff gives today's envelope and
   today's verdicts unchanged. A project where no implementor resolves still records the not-run
   verdict. `test_self_review_unclassified_surface.py`, which pins "a wrong-domain implementor
   resolves, runs and observes nothing" as contract, is rewritten to pin the new routes with its
   matched negative control kept.

9. **The Java surfacer exists.** `ext-self-review-java` in `pm-dev-java`: a skill document with
   the declaration, the detection rules in Java terms and the Java reading of each check, and a
   `self_review` script exposing `surface` on the shared module. It covers Java sources and the
   build and configuration files the Java domain governs (`pom.xml`, `*.properties`,
   `module-info.java`); the verify-first clause settles the exact class list. *Done when:*
   discovery lists it with its classes; in a fixture shaped like a Java consumer repository it is
   selected for a `.java` footprint and the plan-marshall implementor is not.

10. **Java detectors that give the reviewer something to read.** Each emits into an existing
    registry key; none adds a key. At least: `changed_code_units` — the methods and constructors
    a diff touches, including one from which lines were only removed, so the behavioural check
    over changed code runs on Java; `symmetric_pairs` (encode/decode, serialize/deserialize,
    open/close, acquire/release, with whether a test exists in the module's test tree);
    `unguarded_boundaries` (added I/O, process or network calls outside try-with-resources or an
    enclosing `try`); `contract_sources` (changed interfaces, annotations, record components);
    `schema_bearing_files` (`*.xsd`, JSON schemas, OpenAPI documents, `module-info.java`);
    `regexes` (`Pattern.compile`, `String.matches`); `user_facing_strings` (log message
    templates, exception messages, JavaDoc summaries); `producer_consumer` (a message constant,
    configuration key or event type produced with no consumer in the diff); `flag_guard_pairs`;
    `source_of_truth` (one constant bound to different literals across files);
    `same_document_consistency` (normative sentences added in JavaDoc). Every other key is
    emitted empty. *Done when:* each detector has a positive and a matched negative fixture in the
    conformance suite; a fixture shaped like the API-Sheriff diff surfaces a non-empty, classified
    envelope.

11. **The Java surfacer states its limits, and the bundle documents it.** Its structural limit
    names what static surfacing of Java cannot see; a Java-domain file type with no detector is
    counted as not covered, never as clean; the bundle's README and the derived implementor list
    name it. *Done when:* a mixed Java and properties fixture reports each class on its own row,
    covered or not covered; the doc-contract test of deliverable 7 lists two implementors.

## Claim Labels

- OBSERVED: the contract names one way to implement — a skill `ext-self-review-{domain}` with a `self_review.py`, the `implements:` frontmatter line and the notation `{bundle}:ext-self-review-{domain}:self_review`; `surface` is the one required subcommand — `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md:19-22`, `:38-41`, `:47-52`
- OBSERVED: the contract says the consumer "invokes the first implementor whose `self_review` script notation resolves in the current executor", its header says "Implementations: 1", it invites consumer implementors (line 9) and says nothing on merging, per-domain selection or coexistence — `ext-point-self-review-surfacing.md:9`, `:24`
- OBSERVED: the envelope is fixed: ten scalars, `delta_coverage` with `by_class[C]{content_class,files,files_with_candidates,files_without_candidates}`, `counts` with `by_family{structural,prose_contract}` and `total`, and 24 candidate lists; every registry key must appear, extra lists are not permitted, and "the class vocabulary itself is the implementor's" — `ext-point-self-review-surfacing.md:76-199`, `:214-216`, `:227-228`, `:237`, `:268`, `:276`
- OBSERVED: the workflow forwards `--contract-radius` and the implementor defines it, but the contract does not mention it; the implementor emits `local_base_behind_upstream`, which the schema does not document — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:160-171`; `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py`
- OBSERVED: discovery reads seven frontmatter keys, none of them a content class or a domain, and its rows carry no script notation — `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` § `_IMPLEMENTOR_FRONTMATTER_KEYS` (894-902), `find_implementors` (1372-1426), `cmd_implementors` (1491-1529)
- OBSERVED: Step 1 selects one implementor by resolvability — "Select the first implementor whose notation **resolves in the current executor**" — and the zero-generator fallback records "self-review not run: no surfacer implementor resolved" — `pre-submission-self-review.md:118-122`, `:184-186`, `:735-740`
- OBSERVED: the workflow is wired to the one implementor: its notation is named at lines 42, 122 and 174; the detector-family registry and the severity rubric are links into its skill document (269, 273); `--component pm-plugin-development:ext-self-review-plan-marshall` is hard-coded on both `qgate add` calls (616, 779) — `pre-submission-self-review.md`
- OBSERVED: several checks are worded for Python and plan-marshall material — check 5 (`output_toon({...})`, argparse `help=`, line 399), check 10 (`subprocess.*`, `check=True`), check 11 ("`SKILL.md` or a `standards/*.md`", 415), check 19 ("whose `def` header is on `line`", 435) — `pre-submission-self-review.md:381-437`; the workflow hard-codes no content-class name and no file suffix
- OBSERVED: the severity rubric is at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md:25` and the contract says it is "stated there and nowhere else" — `ext-point-self-review-surfacing.md:272`
- OBSERVED: the one implementor is four scripts: `self_review.py` (694 lines), `_self_review_diff.py` (295), `_self_review_patterns.py` (574, with the `CANDIDATE_LISTS` / `CANDIDATE_FAMILIES` registry at 455-548) and `_self_review_detectors.py` (2753) — `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/`
- OBSERVED: its content classes are `python`, `skill_doc`, `standards_doc`, `markdown_other`, `structured_config` and `other`, and `_classify_content` sends every other shape — `.java`, `.js`, `.adoc`, `Dockerfile`, `.xml` — to `other` — `_self_review_detectors.py:2573-2610`
- OBSERVED: every detector but two is gated on `.py` or `.md`; `touched_claims` and `keep_markers` work on any text; `changed_code_units` is Python-only, filtered by `.py` and built with `ast.parse` — `_self_review_detectors.py:2315`, `:2394-2398`; SKILL.md § Detection Rules (282-372)
- OBSERVED: the language-independent parts are identifiable: all of `_self_review_diff.py`, `_compose_candidate_output` (`self_review.py:181-233`), `_format_scope_statement`, `_resolve_since_delta`, the argument and scope skeleton of `_cmd_surface`, and `_candidate_files` / `_compute_delta_coverage` given a classifier
- OBSERVED: the six non-finding and finding verdicts are listed at `pre-submission-self-review.md:466-477`; a test pins the wrong-domain route as contract — `test/plan-marshall/phase-6-finalize/test_self_review_unclassified_surface.py` (docstring, "Route 2")
- OBSERVED: each domain bundle declares the file globs it owns in `skills/plan-marshall-plugin/extension.py`; `pm-dev-java` declares `**/*.java` and `pm-dev-java-cui` declares the same glob; no function maps one file to one domain — `manage-config/scripts/_cmd_domain_detect.py` § `_glob_matched_domains` (194-213) returns the set of domains for a plan
- OBSERVED: the domain extension resolver knows three types, `outline`, `triage` and `marker-detect`; `self-review` is not one — `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py:234`, `:814`; `_cmd_skill_resolution.py:114-135`
- OBSERVED: no `ext-self-review-java` exists; `pm-dev-java` ships no analyzer script a surfacer could reuse (its one script manages Maven profiles) — a listing of `marketplace/bundles/*/skills/ext-self-review-*` finds the plan-marshall implementor only
- OBSERVED: the Java consumer repositories on this machine enable the `java`, `java-cui` and `documentation` domains, and their `workflow_skill_extensions` carry `triage` only — `/home/oliver/git/cui-http/.plan/marshal.json`, `/home/oliver/git/nifi-extensions/.plan/marshal.json`
- HYPOTHESIS: since #1726 (`d8b0284ef`) a round over a diff the surfacer classes entirely as `other` closes as clean instead of looping, so a Java change passes self-review unreviewed — read from the verifier rule ("the structural limit is not a reason to answer no"), not observed on a consumer run — confirm/refute by running the current workflow's documented branches over a 4-of-4 `other` fixture (verify-at-outline)
- HYPOTHESIS: the consumer figures (API-Sheriff 19 of 20 files `other`; TokenSheriff pull request #744, 4 of 4, about 28 minutes to the round limit) are reports from those repositories' runs before #1726, not re-run here — confirm/refute from those plans' archived step records (verify-at-outline)
- HYPOTHESIS: the shared module belongs in `plan-marshall:script-shared`, the place other cross-bundle helpers are imported from — confirm/refute at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` against how a script in another bundle imports from it, and against the executor's import path in a consumer repository where bundles come from the plugin cache (verify-at-outline)
- HYPOTHESIS: Java methods touched by a diff can be found reliably without a Java parser, from the hunk headers and a brace scan — confirm/refute on real diffs from `/home/oliver/git/cui-http`; if not, deliverable 10's `changed_code_units` states the cases it misses in the structural limit (verify-at-outline)
- Verify-first clause: **DECIDED by the operator on 2026-10-09: surfacers are routed per domain**, through the resolver triage uses, not through global frontmatter discovery alone. A domain bundle names its surfacer in its `extension.py`, the name is seeded into `.plan/marshal.json` under the domain's `workflow_skill_extensions` as a new type, and Step 1 asks the resolver for the surfacer of each domain the repository enabled. For deliverable 1 this means: the declared content classes are published where that resolver reads them; the new type is added to the resolver's vocabulary; an existing repository picks the surfacer up through the normal re-seeding of its domains, with no hand edit — confirm how `skill_domains` is refreshed for a repository configured before this plan, and name the command in the pull request. The background the decision was taken on follows. Two paths exist. Frontmatter discovery (`extension_discovery implementors`) is what the surfacer uses today; it is global and needs a new key and row field. The per-domain resolver (`resolve-workflow-skill-extension`, seeded into `.plan/marshal.json` from each bundle's `extension.py`) is what triage uses; it would need a new type, and it honours which domains a repository enabled. The rule to satisfy: a repository that has not enabled a domain does not run that domain's surfacer, and a repository that has enabled it does so without an edit to its `marshal.json` by hand. Record the choice and why.
- Verify-first clause: settle the class vocabulary before deliverable 1 — which classes exist, which implementor owns each, and how overlaps resolve. Known overlaps at HEAD: `.py` under `marketplace/bundles/` is claimed by both the Python domain and the plugin-development domain; `.md` is claimed by no domain by suffix; `.json`, `.yaml`, `.toml` and `.properties` are configuration that several domains could claim; the `-cui` bundles declare the same globs as their base domain. PLAN-LB-35 and PLAN-LB-36 build on this table, so publish it in the extension-point standard.
- Verify-first clause: **DECIDED by the operator on 2026-10-09: the `-cui` bundles contribute no detectors; their files are covered by the base domain's surfacer.** Build no contributor role. State in the extension-point standard that `java-cui` is covered by the Java surfacer and `javascript-cui` by the JavaScript one, and make the resolver return the base domain's surfacer for a repository that enabled the `-cui` domain. The question as it was put follows. Whether the `-cui` bundles (`pm-dev-java-cui`, `pm-dev-frontend-cui`) contribute detectors of their own. They cannot declare a class their base domain declares. If they are to add CUI-specific detectors (log-record conventions, for one), the merge rule needs a second role beside "owns a class" — a contributor to a class another implementor owns. If not, say so in the standard and build nothing.
- Verify-first clause: deliverable 4 must not change the plan-marshall implementor's output. Before moving code, freeze its envelope over the existing test corpus as a golden set, and move in steps that each keep the set identical.
- Verify-first clause: before deliverable 5, list every place the workflow's reviewer-facing text would read differently for a non-Python implementor, and have one cold reader run the reworded checks against a Java fixture; a check whose neutral wording loses the precision the Python wording had keeps its precision in the implementor's own skill document, not in the workflow.
- Verify-first clause: PLAN-LB-28's claims about this workflow were re-grounded on 2026-10-09 at `4ed67e228` and three were re-scoped (the verifier no longer refuses on structural grounds; an operator close exists; there are six verdicts). The same-HEAD rule of PLAN-LB-03 D3 is not carried: confirm on a fixture that no refusal that no round can change still occurs, and carry the rule only if one does.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — § "Domain-Aware Candidate Surfacing", § "Step 1" selection and merge, the verdict vocabulary, the check statements, the two `qgate add` calls, the verifier-prompt boundary lines, the not-covered branch (D1, D2, D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — declared coverage, applicability, merge rules, not-covered, the class table, the authoring guide (D1, D2, D3, D5, D7)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — the coverage declaration, the notation in the row, the duplicate-class error (D1)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` — the declaration; the rubric moves out (D1, D5)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py` — consumer of the shared module (D4)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_diff.py` — moved into the shared module (D4)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py` — the registry moves out (D4)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` — the classifier and coverage computation move out; `CONTENT_CLASSES` becomes the declaration's source (D1, D4)
- OBSERVED: `marketplace/bundles/pm-dev-java/.claude-plugin/plugin.json` — skill registration (D9)
- OBSERVED: `marketplace/bundles/pm-dev-java/README.md` — names the surfacer (D11)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_self_review_unclassified_surface.py` — rewritten route contract (D8)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_submission_self_review_verdict_verdict.py` — verdict vocabulary with the new verdict (D3)
- OBSERVED: `test/plan-marshall/extension-api/test_extension_discovery.py` — declaration and duplicate-class error (D1)
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_delta_coverage.py` — unchanged-envelope control and the not-covered count (D4, D8)
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_check_coverage.py` — registry, document and check parity after the move (D4, D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/self_review_surfacing.py` — the shared module; name and place settled at outline (D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/self-review-severity-rubric.md` — the rubric's domain-neutral home (D5) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/ext-self-review-java/SKILL.md` — new skill document (D9, D11) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/ext-self-review-java/scripts/self_review.py` — new script (D9, D10) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the not-covered landing fact (D6) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` — the new extension type in the resolver's vocabulary (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py` — seeding of the new type into `skill_domains` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_resolution.py` — resolving the surfacer, and the base domain's for a `-cui` domain (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py` — the hook a bundle uses to name its surfacer and its classes (D1)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/extension.py` — names the Java surfacer (D9)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py` — names the plan-marshall surfacer (D1)
- HYPOTHESIS: `test/plan-marshall/extension-api/test_self_review_surfacer_conformance.py` — the conformance suite (D7) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_self_review_multi_implementor_merge.py` — merge and not-covered controls (D2, D3) (verify-at-outline)
- HYPOTHESIS: `test/pm-dev-java/ext-self-review-java/test_self_review_java.py` — detector fixtures and the consumer-shaped diff (D10, D11) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Priority: the operator named this the most important subject of the epic. It is the head of a chain: PLAN-LB-35 and PLAN-LB-36 cannot start before it lands.
- Suggested order inside the plan: the three verify-first decisions (routing, class table, `-cui`); then deliverable 4 (the move, under the frozen golden set); then 1, 2 and 3; then 5; then 9 to 11 (Java) with 7 (guide and conformance suite) alongside; 6 and 8 last.
- Overlaps with: PLAN-LB-26 on `pre-submission-self-review.md` (that plan edits the evidence-resolution paragraph and one `qgate add` call — one of the two calls this plan changes; sequence the two, the second rebases); PLAN-LB-24 (running) on nothing declared; PLAN-LB-32 (running) on nothing declared.
- Takes over from PLAN-LB-28: its deliverables 5 to 8 (PLAN-LB-03 D1 to D4) and the ten surface entries that belonged to them. PLAN-LB-28 is the Maven plan only from now on.
- Blocks: PLAN-LB-35 and PLAN-LB-36.
- Adjacent to: the Open Defect "The self-review has no outcome for could-not-establish-coverage". Not covered (no surfacer for the class) is this plan's; could not establish coverage (a surfacer ran and the reviewer could not read everything) stays open.
- Left out on purpose: surfacers for the other domains (PLAN-LB-35, PLAN-LB-36); a Java parser dependency; changing the review's grading or its round loop, which shipped as #1726 and #1718; a surfacer for the general domain, which owns no file type (PLAN-LB-36 carries the decision on a last-resort surfacer).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-34-self-review-surfacing-foundation-and-java.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
