# PLAN-LB-58: Verification truth — no confirmed result over a stale analysis, zero links, or an empty module population

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-58-verification-truth.md` and is queued as one row file,
> `queue/PLAN-LB-58.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-15 by operator instruction from the lessons ingest `lessons-routing-031` and
> `-037` (pm-mcp-core `-247`, `-253`, `-267`, graded high by the operator at that ingest), re-checked
> read-only at `d17ac5bef`. Priority: after the OpenCode plans. **Each deliverable is its own outline
> deliverable, and each Done-when is its own success criterion. Do not merge them.** A criterion
> that says "fails at `d17ac5bef`" is evidenced only by a run against that tree.

## Objective

Three verification steps report a result over evidence they never examined:

- Sonar's `fetch_findings` reports `count_status: confirmed` once the Compute Engine is idle,
  without checking that the analysis it read is of the PR head. A clean analysis of an older head
  reads as a confirmed zero.
- The link checker accepts a Markdown file, parses it with AsciiDoc rules, finds no links and
  reports success.
- On a Maven project the pre-push gate derives no per-module population and its module-tests arm
  runs degraded on every plan.

## Deliverables

1. **Sonar refuses to confirm an analysis of another head.**
   - `fetch_findings` reads the revision of the analysis it counts (the PR analysis's commit, as the
     Sonar API reports it) and compares it with the PR head. A mismatch yields
     `count_status: undecidable` with reason `stale_analysis` and both SHAs, never `confirmed`.
   - The attestation row (`sonar-scan-summary.jsonl`) records the analysis revision beside the
     `scanned_sha` it already records (`_resolve_scanned_sha`, L294-316, which is never compared).
   - A revision the API does not report is `undecidable`, never `confirmed`.

   *Done when:* tests with a stubbed Sonar API: an analysis revision equal to the head confirms; a
   different revision is `undecidable` / `stale_analysis`; a missing revision is `undecidable`. The
   second and third fail at `d17ac5bef`.

2. **The link checker cannot pass a file it cannot read.**
   - `verify-links` file mode refuses a non-AsciiDoc file with the same `no_files`-class error the
     directory mode already returns (`_cmd_verify_links.py` L192-197), or checks it with a Markdown
     link grammar. Choose at outline; either way a `.md` file never yields `total_links: 0,
     status: success`.

   *Done when:* a test runs file mode on a `.md` file containing one broken link and does not get
   `status: success` with `total_links: 0`. It fails at `d17ac5bef`.

3. **The pre-push gate derives a module population on non-marketplace projects.**
   - `derive_gate_bundles` resolves changed paths to modules through the architecture
     (`architecture which-module`) when the project is not a marketplace layout, instead of routing
     every path to `unresolved` (L127-139).
   - `build-maven` exposes `resolve-test-scope` for a module, so the module-tests divergence arm runs
     instead of taking the degraded path (`pre-push-quality-gate.md` L399-405).
   - A path that resolves to no module is still reported (rule 4), never dropped.

   *Done when:* a fixture Maven multi-module project with changes in two modules yields those two
   modules as the gate population and a `resolve-test-scope` answer for each; a path outside every
   module is reported unresolved. Both fail at `d17ac5bef`.

4. **A green scoped test run states what it did not cover, and the pre-push gate runs the root-level guards.** Added 2026-10-23 from `lessons-routing-053` item 3, graded **high** (three consumer plans: two pre-push failures on one rule, one stopped unmerged).
   - Guards at the root of `test/` (for example `test/test_harness_shape_guards.py`) sit outside every module, so `module-tests {module}` never runs them and the gate resolved `divergence_possible=false` and skipped its whole-tree run; CI then failed on rule R5.
   - The pre-push gate includes the root-level `test/*.py` guards whenever the plan adds or edits a test file, and a scoped green run reports the excluded population.

   *Done when:* a fixture diff that edits one test file inside a module yields a gate population that includes the root-level guards. A docs-only diff does not. The report of a scoped run names what it left out. At HEAD the population is module-scoped only (HYPOTHESIS, see Claim Labels).

Split guard: four deliverables, one theme (a verification result covers what it claims).

## Claim Labels

- OBSERVED: `workflow-integration-sonar/scripts/sonar.py` L26-33: `count_status` is `confirmed | undecidable`, decided by CE readiness (`_wait_for_ce_ready`, L250-286); a content search for `head_sha|revision|analysis_sha|stale` in the Sonar scripts finds no comparison; `_resolve_scanned_sha` (L294-316) records the local HEAD only — orchestrator-read at `d17ac5bef`.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Behaviour holds; lines moved +13 because e40f50aa1 (#1839) added read_open_issues: count_status docstring now L38-45, _wait_for_ce_ready L263, _resolve_scanned_sha L307 (spot-read); no head_sha/revision/analysis_sha/stale comparison anywhere in the Sonar scripts, scanned_sha is written and never compared (dispatched read-only corroboration).
- OBSERVED: pm-mcp-core `-253` (2026-10-13..15): `fetch_findings` reported `confirmed` on a stale PR analysis; a manual check caught it (`lessons-routing-037`).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: A consumer-project lesson (pm-mcp-core -253, lessons-routing-037) outside this repository; the code path that permits it (confirmed on CE readiness alone) is corroborated by claim 0.
- OBSERVED: `pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` L185-186 file mode accepts any existing file; L70-106 are AsciiDoc-only regexes; directory mode refuses on no `.adoc` (L192-197) — orchestrator-read.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_verify_links.py L185-186, L70-106 and L192-197 match the cited lines exactly; the file has no commits since d17ac5bef (dispatched read-only corroboration).
- OBSERVED: `phase-6-finalize/scripts/derive_gate_bundles.py` L127-139 resolves only `marketplace/bundles/<b>/…` and `test/<b>/…`; everything else goes to `unresolved` — orchestrator-read. Only `build-pyproject` exposes `resolve-test-scope` (delegated agent).
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: derive_gate_bundles.py L127-139 as cited (no commits since d17ac5bef); resolve-test-scope exists only in pyproject_build.py L389-430, build-maven/scripts/maven.py has none (dispatched read-only corroboration).
- OBSERVED: pm-mcp-core `-205`, `-216`, `-229`, `-237`, `-250`, `-267`: 0 bundles, module-tests DEGRADED on every Maven plan; the whole-tree arms ran (`lessons-routing-031`).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Consumer-project lessons (lessons-routing-031) outside this repository. The code is consistent with them: with no Maven resolve-test-scope verb the gate takes the DEGRADED path (pre-push-quality-gate.md now L406-422, moved from the cited L399-405 by 215f5095e).
- HYPOTHESIS: the Sonar API exposes the analysed revision for a PR analysis (`/api/project_analyses/search` `revision`, or the CE task's `analysisId` → analysis) — confirm against the provider before choosing the call (verify-at-outline).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: An external Sonar API fact. No repository code calls project_analyses or reads an analysisId, so nothing at HEAD settles it; the plan must confirm it against the provider before choosing the call, as it already says.
- HYPOTHESIS: `architecture which-module` answers for Maven layouts in a consumer project — confirm with the Maven extension's discovery (verify-at-outline).
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Code-level only, no run: the Maven discovery emits paths.module/sources/tests (_maven_cmd_discover.py L385-391) and cmd_which_module (_cmd_client_handlers.py L1198-1221) resolves by those prefixes regardless of layout (dispatched read-only corroboration).
- HYPOTHESIS (D4): the pre-push gate's module-scoped population omits root-level `test/*.py` guards, so a plan that edits only module tests skips them — confirm at `derive_gate_bundles.py` and `pre-push-quality-gate.md` (verify-at-outline). The sender's three occurrences (`lessons-routing-053`) were not re-verified at HEAD. Re-grounded at `ee00687b8`: D4 does NOT land in the files D3 declares; the population logic is `script-shared/scripts/build/_test_scope_divergence.py` (`resolve_test_scope`), now declared below.
  - verdict: contradicted | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: yes | evidence: The hypothesis holds (_test_scope_divergence.py L483-504: a single-module test edit gives divergence_possible=false and a scoped recommended_target, so no root test/*.py guard runs) but the clause that D4 adds no file surface is false: the population logic is script-shared/scripts/build/_test_scope_divergence.py (resolve_test_scope) with test_test_scope_divergence.py. Also pre-push-quality-gate.md L92-97 says root-level guards run whenever test files are edited yet its mechanism escalates only for a footprint touching root test/*.py, so the doc and the code disagree. Spec surface corrected.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md` — `count_status` reasons (D1)
- OBSERVED: `test/plan-marshall/workflow-integration-sonar/` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` — the `sonar-scan-summary` row (L279) the analysis-revision field joins (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md` — lists the row fields (L106) and gates on `count_status == confirmed`; may need the `stale_analysis` reason (D1)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` (D2)
- OBSERVED: `test/pm-documents/ref-asciidoc/` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/derive_gate_bundles.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/` — `resolve-test-scope`, absent today (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md` — the canonical-invocations section the gate doc points to (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md` — lists `resolve-test-scope` (D3)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_derive_gate_bundles.py` (D3)
- OBSERVED: `test/plan-marshall/build-maven/` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_test_scope_divergence.py` — `resolve_test_scope` (L483-504): a single-module test edit gives `divergence_possible=false` and a scoped target, so no root `test/*.py` guard runs (D4)
- OBSERVED: `test/plan-marshall/build-pyproject/test_test_scope_divergence.py` — the population tests (D4)

Re-grounding notes (`ee00687b8`): D1's scope also covers `cmd_read_open_issues` (`sonar.py` L738-822, added by #1839), which gates on the same CE readiness and returns `count_status: confirmed` with no head check; the runbook lane consumes it. D3's `derive_gate_bundles` CLI takes only `--files`, `--files-file`, `--globs` and `--marketplace-root`, so routing through `which-module` needs a new input and a change to the gate doc's derive call. D4: `pre-push-quality-gate.md` L92-97 states the root-guard behaviour the code does not implement; the plan reconciles the two. Cited line anchors have moved: `sonar.py` L26-33 / L250-286 / L294-316 are now L38-45 / L263-299 / L307-327, and the gate doc's degraded-path L399-405 is now L406-422.

## Dependencies and Sequencing

- Depends on: none. Priority: after the OpenCode plans (operator instruction, 2026-10-15).
- Overlaps with: PLAN-LB-55 (staged) on `pre-push-quality-gate.md` (D1 push refusal vs D3 population —
  different sections); PLAN-LB-44 (staged) on Sonar routing in `verification-feedback.md` (not
  edited here). The gate will ask.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-58-verification-truth.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
