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

Split guard: three deliverables, one theme (a verification result covers what it claims).

## Claim Labels

- OBSERVED: `workflow-integration-sonar/scripts/sonar.py` L26-33: `count_status` is `confirmed | undecidable`, decided by CE readiness (`_wait_for_ce_ready`, L250-286); a content search for `head_sha|revision|analysis_sha|stale` in the Sonar scripts finds no comparison; `_resolve_scanned_sha` (L294-316) records the local HEAD only — orchestrator-read at `d17ac5bef`.
- OBSERVED: pm-mcp-core `-253` (2026-10-13..15): `fetch_findings` reported `confirmed` on a stale PR analysis; a manual check caught it (`lessons-routing-037`).
- OBSERVED: `pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` L185-186 file mode accepts any existing file; L70-106 are AsciiDoc-only regexes; directory mode refuses on no `.adoc` (L192-197) — orchestrator-read.
- OBSERVED: `phase-6-finalize/scripts/derive_gate_bundles.py` L127-139 resolves only `marketplace/bundles/<b>/…` and `test/<b>/…`; everything else goes to `unresolved` — orchestrator-read. Only `build-pyproject` exposes `resolve-test-scope` (delegated agent).
- OBSERVED: pm-mcp-core `-205`, `-216`, `-229`, `-237`, `-250`, `-267`: 0 bundles, module-tests DEGRADED on every Maven plan; the whole-tree arms ran (`lessons-routing-031`).
- HYPOTHESIS: the Sonar API exposes the analysed revision for a PR analysis (`/api/project_analyses/search` `revision`, or the CE task's `analysisId` → analysis) — confirm against the provider before choosing the call (verify-at-outline).
- HYPOTHESIS: `architecture which-module` answers for Maven layouts in a consumer project — confirm with the Maven extension's discovery (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md` — `count_status` reasons (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-sonar/` (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` (D2)
- HYPOTHESIS: `test/pm-documents/ref-asciidoc/` (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/derive_gate_bundles.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/` — `resolve-test-scope` (verify-at-outline) (D3)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_derive_gate_bundles.py` (verify-at-outline) (D3)
- HYPOTHESIS: `test/plan-marshall/build-maven/` (verify-at-outline) (D3)

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
