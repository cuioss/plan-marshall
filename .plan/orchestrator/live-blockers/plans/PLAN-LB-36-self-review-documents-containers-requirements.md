# PLAN-LB-36: Self-review for every domain, part 3: surfacers for documents, containers and requirements

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-36-self-review-documents-containers-requirements.md` and is queued as one row file, `queue/PLAN-LB-36.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on 2026-10-09 by operator instruction (self-review surfacers "for all domains"). Third of
> three plans; it CANNOT start before PLAN-LB-34 has landed. Its documents part revives the retired
> `truthful-signals` spec PLAN-TRUTH-185; the containers and requirements parts are new and had no
> earlier spec. Every OBSERVED claim was read at HEAD `fcd54e6ef`; the mechanism it builds on does
> not exist until PLAN-LB-34 ships, so its first deliverable re-reads that landing.

## Objective

After PLAN-LB-34 and PLAN-LB-35 the programming-language domains have surfacers. Three domains
that are not programming languages still have none: documentation (AsciiDoc, and Markdown outside
the skill tree), containers (Dockerfiles, compose files and their lint and scan configuration)
and requirements. A documentation change in a consumer project surfaces nothing today — the
recorded case is 76 added lines in a configuration guide and zero candidates — and nearly every
plan in every repository touches documentation, so this is the surfacer most diffs will meet.
This plan adds the three, and settles what happens to a file no domain claims at all, so that
"for all domains" ends with a stated answer for every file type and not with a silent remainder.

## Deliverables

1. **Gate: read what PLAN-LB-34 landed.** Read its merge commit, the authoring guide and the
   published class table, and re-scope this spec where the mechanism differs. *Done when:* the
   outline records the landed mechanism in three lines and lists every deliverable below whose
   wording changed because of it.

2. **The documents surfacer exists, with a clear boundary to this repository's own.**
   `ext-self-review-documents` in `pm-documents`, covering AsciiDoc (`*.adoc`, `*.asciidoc`)
   everywhere and Markdown outside the trees the plan-marshall surfacer owns. Markdown is claimed
   by no domain by suffix today; the class table of PLAN-LB-34 decides the boundary and this
   deliverable implements it. *Done when:* an `.adoc` footprint selects it; a `README.md` in a
   consumer-shaped fixture selects it; a `SKILL.md` under `marketplace/bundles/` in a fixture
   shaped like this repository selects the plan-marshall surfacer and not both.

3. **Document detectors, reusing the analyzers the bundle already ships.** Each emits into an
   existing registry key. At least: `contract_sources` (the `include::` targets and `xref:`
   anchors a changed document depends on; a dangling target is a candidate) — built on the
   bundle's existing reference extraction and link verification, not on new parsing;
   `same_document_consistency` (added normative sentences, for contradiction review);
   `count_prose` (cardinality claims such as "three steps"); `ordinal_references` (`step N`
   references into a list the same diff touched); `markdown_sections` (sections duplicated
   across changed documents, AsciiDoc and Markdown headings alike); `description_vs_body`
   (header attributes against the changed body); `touched_claims` and `keep_markers` from the
   shared module. Where the plan-marshall surfacer has a prose detector that is not tied to skill
   documents, take it from one place as PLAN-LB-35 does for Python. *Done when:* each detector
   has a positive and a matched negative fixture; the 76-line configuration-guide shape surfaces
   a non-empty envelope; the plan-marshall surfacer's golden envelope set is unchanged.

4. **The containers surfacer exists.** `ext-self-review-oci` in `pm-dev-oci`, covering the files
   the domain already declares (Dockerfile and Containerfile variants, compose files, ignore
   files, hadolint and trivy configuration). Detectors, each into an existing key:
   `unguarded_boundaries` (a download piped to a shell, a fetch without checksum or pinned
   digest, a `RUN` chain without failure propagation); `source_of_truth` (one base image or one
   version pinned to different values across stages or files); `contract_sources` (the build
   arguments, exposed ports, volumes and entry point a changed file declares, which compose
   files and documentation depend on); `producer_consumer` (a build argument or environment
   variable declared and never used, or used and never declared, within the diff);
   `flag_guard_pairs` where a build argument gates stages. Every other key is emitted empty,
   `changed_code_units` among them, and the structural limit says so. *Done when:* each detector
   has a positive and a matched negative fixture; a Dockerfile-plus-compose fixture reports each
   class on its own row.

5. **The requirements surfacer exists, once it is settled which files are requirements.** The
   requirements domain declares no file globs on purpose, so nothing identifies its documents by
   path today. Settle the identification first (the verify-first clause below), then ship
   `ext-self-review-reqs` in `pm-requirements`. Detectors: `source_of_truth` (one requirement
   identifier defined twice, or defined with diverging text); `producer_consumer` (an identifier
   referenced and never defined, or defined and referenced by no specification, within the
   changed set); `same_document_consistency` (normative keywords added or changed);
   `contract_sources` (the requirement a changed specification section traces to);
   `touched_claims`. *Done when:* a fixture with a requirements document and a specification
   that traces to it surfaces the trace as a contract source and a dangling identifier as a
   candidate; a plain AsciiDoc document in the same fixture goes to the documents surfacer and
   not to this one.

6. **Each of the three states its limits, and the bundles document them.** A structural limit
   per surfacer; a file type of the domain with no detector counted as not covered; the three
   bundle READMEs name their surfacer. *Done when:* the conformance suite of PLAN-LB-34 runs
   green over all three.

7. **A file no domain claims stays not covered, and the standard says which.** After the six
   domain surfacers exist, some changed files still belong to no class: configuration formats
   several domains could claim, shell scripts, CI workflow files, binary assets. Decided by the
   operator on 2026-10-09: no last-resort surfacer for now; the domain surfacers come first.
   Such files are reported not covered by name and count, as PLAN-LB-34 built it, and the
   extension-point standard lists the file types deliberately left without a surfacer, with the
   note that a last-resort surfacer is deferred and not rejected. So that the later decision
   has figures, record in the pull request how many files of the last twenty landed plans in
   this repository would have been not covered once all six surfacers exist, by type. *Done
   when:* a doc-contract test pins the list of deliberately uncovered types against the class
   table; the pull request carries the count by type.

8. **The three run on a real repository.** Run the documents surfacer over a recent
   documentation commit of this repository and of one consumer repository, the containers
   surfacer over a repository that has a Dockerfile, and the requirements surfacer over a
   repository that has requirements documents, if one is checked out. Record in the pull request
   the candidate counts per list, the class rows, and three candidates per surfacer read by hand
   with a judgement on whether a reviewer would want them. *Done when:* the pull request carries
   those figures; a detector whose sampled candidates are all noise is tightened or removed
   before merge.

9. **Every domain is accounted for.** One table in the extension-point standard lists every
   domain key the bundles declare and what covers it: its own surfacer, its base domain's
   surfacer (the `-cui` variants), the last-resort surfacer, or "none, on purpose" with the
   reason. A test derives the domain keys from the bundles and fails when a key has no row.
   *Done when:* the test is green, and adding a fixture bundle with a new domain key and no row
   makes it fail.

## Claim Labels

- OBSERVED: no surfacer exists for documents, containers or requirements — a listing of `marketplace/bundles/*/skills/ext-self-review-*` finds `pm-plugin-development/skills/ext-self-review-plan-marshall` only
- OBSERVED: `pm-documents` declares the domain key `documentation` with the globs `**/*.adoc`, `**/*.asciidoc` and `doc/**`; Markdown is claimed by no domain by suffix — `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/extension.py`
- OBSERVED: `pm-documents` already ships deterministic analyzers a surfacer can call: AsciiDoc validation, link verification and link classification, a documentation review and tone analysis, an ASCII-diagram check, and an extractor of xref, link and include references — `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/` (`asciidoc.py`, `_cmd_validate.py`, `_cmd_verify_links.py`, `_cmd_classify_links.py`), `ref-documentation/scripts/` (`docs.py`, `_cmd_review.py`, `_cmd_analyze_tone.py`), `ref-ascii-diagrams/scripts/ascii_diagrams.py`, `plan-marshall-plugin/scripts/doc_references.py`
- OBSERVED: the plan-marshall surfacer classes `.adoc` as `other`, and its prose detectors are gated on `.md`; `count_prose` and `contract_sources` read the nearest `SKILL.md` and `standards/*.md` — `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py:2573-2610`; skill document § Detection Rules (282-372)
- OBSERVED: `pm-dev-oci` declares the domain key `oci-containers` with eleven globs (Dockerfile and Containerfile variants, compose files, ignore files, hadolint and trivy configuration) and ships no script outside its `extension.py` — `marketplace/bundles/pm-dev-oci/skills/plan-marshall-plugin/extension.py`
- OBSERVED: `pm-requirements` declares the domain key `requirements` with an empty glob list, deliberately, and ships no script outside its `extension.py` — `marketplace/bundles/pm-requirements/skills/plan-marshall-plugin/extension.py`
- OBSERVED: the base bundle's `general-dev` domain also declares no globs, deliberately; the two `-cui` bundles declare the globs of their base domain — `marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/extension.py`, `marketplace/bundles/pm-dev-java-cui/skills/plan-marshall-plugin/extension.py`, `marketplace/bundles/pm-dev-frontend-cui/skills/plan-marshall-plugin/extension.py`
- OBSERVED: both consumer repositories read on this machine enable the `documentation` domain — `/home/oliver/git/cui-http/.plan/marshal.json`, `/home/oliver/git/nifi-extensions/.plan/marshal.json`
- HYPOTHESIS: the recorded case of a documentation change surfacing nothing (76 added lines of `doc/user/configuration.adoc`, zero candidates) reproduces at HEAD — it follows from `.adoc` being classed `other`; confirm/refute by running the current surfacer over a commit that adds lines to that file (verify-at-outline)
- HYPOTHESIS: the plan-marshall surfacer's prose detectors (`count_prose`, `ordinal_references`, `same_document_consistency`, `markdown_sections`) can serve AsciiDoc once their Markdown-specific line shapes (heading and bullet syntax) are parameterised — confirm/refute at `_self_review_detectors.py` § each `_detect_*` function (verify-at-outline)
- HYPOTHESIS: a repository with a Dockerfile, and one with requirements documents, are checked out on the machine that runs this plan — confirm/refute by listing sibling checkouts whose `marshal.json` enables `oci-containers` or `requirements`; where none is, deliverable 8 uses a synthetic fixture for that surfacer and says so (verify-at-outline)
- Verify-first clause: settle how a requirements document is identified before deliverable 5. Read the requirements bundle's skill documents for the conventions it prescribes — file names, a document header attribute, the shape of a requirement identifier — and choose a rule a script can evaluate. If the only reliable signal is content (an identifier pattern), the classifier needs to read the file and not just its path: check that the shared classification of PLAN-LB-34 allows that, and if it does not, raise it with the operator before building a path-only approximation.
- Verify-first clause: the Markdown boundary of deliverable 2 must be a rule a script can evaluate from the path and the repository. Take it from PLAN-LB-34's class table; if that table left it open, settle it here and add it. The plan-marshall surfacer keeps `SKILL.md`, `standards/*.md` and the other Markdown it classes today in this repository.
- Verify-first clause: decided by the operator on 2026-10-09 — no last-resort surfacer for now ("not for now, we start with the others"); deliverable 7 builds the stated list and the count only. Also decided the same day: surfacers are routed per domain, so each bundle names its surfacer in its `extension.py`; and the `-cui` bundles contribute no detectors.
- Verify-first clause: calling the bundle's existing analyzers from the documents surfacer (deliverable 3) must not make a self-review round slow or dependent on tools a consumer repository lacks. Measure the surface call on a 50-file documentation diff and state the time in the pull request; an analyzer that needs an external tool is optional and its absence is named in the structural limit.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-documents/.claude-plugin/plugin.json` — skill registration (D2)
- OBSERVED: `marketplace/bundles/pm-documents/README.md` — names the surfacer (D6)
- OBSERVED: `marketplace/bundles/pm-dev-oci/.claude-plugin/plugin.json` — skill registration (D4)
- OBSERVED: `marketplace/bundles/pm-dev-oci/README.md` — names the surfacer (D6)
- OBSERVED: `marketplace/bundles/pm-requirements/.claude-plugin/plugin.json` — skill registration (D5)
- OBSERVED: `marketplace/bundles/pm-requirements/README.md` — names the surfacer (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — class table rows, the deliberately uncovered types or the last-resort surfacer, the domain coverage table (D2, D4, D5, D7, D9)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` — the reusable prose detectors move out (D3)
- HYPOTHESIS: `marketplace/bundles/pm-documents/skills/ext-self-review-documents/SKILL.md` — new skill document (D2, D6) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-documents/skills/ext-self-review-documents/scripts/self_review.py` — new script (D2, D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-oci/skills/ext-self-review-oci/SKILL.md` — new skill document (D4, D6) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-oci/skills/ext-self-review-oci/scripts/self_review.py` — new script (D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-requirements/skills/ext-self-review-reqs/SKILL.md` — new skill document (D5, D6) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-requirements/skills/ext-self-review-reqs/scripts/self_review.py` — new script (D5) (verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/extension.py` — names the documents surfacer (D2)
- OBSERVED: `marketplace/bundles/pm-dev-oci/skills/plan-marshall-plugin/extension.py` — names the containers surfacer (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/self_review_surfacing.py` — the shared module of PLAN-LB-34, receiving the moved prose detectors; name as landed (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-requirements/skills/plan-marshall-plugin/extension.py` — the requirements-document identification, if it is declared there (D5) (verify-at-outline)
- HYPOTHESIS: `test/pm-documents/ext-self-review-documents/test_self_review_documents.py` — detector fixtures and the Markdown boundary (D2, D3) (verify-at-outline)
- HYPOTHESIS: `test/pm-dev-oci/ext-self-review-oci/test_self_review_oci.py` — detector fixtures (D4) (verify-at-outline)
- HYPOTHESIS: `test/pm-requirements/ext-self-review-reqs/test_self_review_reqs.py` — detector fixtures and the identification rule (D5) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/extension-api/test_self_review_domain_coverage.py` — every domain key has a row (D9) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-34 (the shared module, the class declaration and table, the merge, the conformance suite). It must have landed.
- Priority: third in the self-review chain by number, not by weight: the documents surfacer is the one most diffs will meet. It may run together with PLAN-LB-35.
- Suggested order inside the plan: the gate; then the documents surfacer (2, 3) first; the containers surfacer (4) and the requirements surfacer (5) side by side with it — the three share no file; then 6 and 8; 7 as soon as the operator has answered; 9 last.
- Overlaps with: PLAN-LB-35 on `ext-point-self-review-surfacing.md` (own rows only) and on `_self_review_detectors.py` and the shared module if both move detectors out — the second to merge rebases; PLAN-LB-34 on everything it declares, which is why this plan waits for it.
- Left out on purpose: surfacers of their own for the `-cui` bundles unless PLAN-LB-34 decided for them; a renderer or external linter as a hard dependency; reviewing binary assets.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-36-self-review-documents-containers-requirements.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
