envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=live-blockers
kind=finding
created=2026-11-02T14:27:42Z

# Make the three-layer analysis of a runbook-lane landing, read by a sub-agent, part of `plan-orchestrator analyze` — the epic `pm-mcp-core-m2-m4-v2` carries it as custom rules today

Severity: **highest (operator: "add it as highest issue … in order not to have this custom rules anymore")**. Bundle: `plan-marshall`, skill `plan-orchestrator`. Kind: missing capability; the epic works around it with standing rules.
Source: the orchestrator session of the epic `pm-mcp-core-m2-m4-v2` in `pm-mcp-core` (plugin 0.1.2041), 2026-11-01 to 2026-11-02, five landings analyzed on the three layers (PLAN-V2-05, 01, 12, 11, 08). Checked against the installed plugin cache 0.1.2041 (`plan-orchestrator/workflow/analyze.md`, `templates/landing-analysis.md`); not re-verified at the `plan-marshall` HEAD.

## What the epic had to add as its own rules

The verb `analyze` corroborates a full ship against the merge diff and the PR checks and writes `landings/PLAN-NN.md` from `templates/landing-analysis.md` (fidelity table, metrics, routing). It does not read the merged code. Two operator decisions closed that gap in this epic's `standing-rules.md` only:

1. **R21, r5 (2026-11-01): a landing is analyzed on three layers, by reading, never by building.** (1) Specified: is the spec sound, are its premises and Done-when conditions consistent with each other and with `main`. (2) Implemented: each deliverable traced to code and to a test that can fail; a file the diff touched that no deliverable explains; a claim of the lane's report the diff does not bear out. (3) Implementation correctness: the merged code read for defects (invariants, boundaries, error paths, concurrency, resource handling, the project's code rules), each with the line, the triggering input and the effect. The result is a `## Three-Layer Analysis` section of the landing report with a verdict per layer; what only a run could show is reported as "not shown by reading". Layer-3 defects go to the operator at once and become a staged fix-plan spec only on the operator's word. First application, PLAN-V2-05: the fidelity check had passed a landing whose spec premise was wrong (the lock order is asserted per transaction, so a refresh in a scope transaction is never order-checked) and whose deleted watch item was not covered by the tests that replaced it.
2. **R21 amended, r6 (2026-11-02): the reading is always done by a read-only sub-agent.** The brief names the merge commit, the spec path, the three layers, the project's code rules and the limits; its report is a lead, the orchestrator re-reads every point it records as "checked", and keeps the verdicts, the landing report and every ledger write. Today's `analyze.md` makes the corroboration dispatchable only "when the read burden is large" and returns `corroborations[N]{claim,verdict,evidence}`, which has no place for a layer, a severity or a "not shown by reading" tag.

Evidence that the practice earns its cost: PLAN-V2-12 (a real defect, `GitLabCiProvider.java:116-137` answers `REJECTED` for a missing issue when a merge request with that number exists), PLAN-V2-11 (swapped format arguments at `LessonFrontMatter.java:150-152`; a lossy R05 reduction that dropped a normative sentence), PLAN-V2-05 and PLAN-V2-08 (spec contradictions the lane had to resolve). The lane's own report passed the fidelity check in every case.

## What is asked

1. `workflow/analyze.md` Step 4 (full ship): add the three-layer analysis as a step of the verb, with the layer definitions above, the "by reading, no build, no test, no write" limit and the "not shown by reading" tag; and add `## Three-Layer Analysis` (Layer 1, 2, 3, CLAUDE.md/code-rule conformance, verdict) to `templates/landing-analysis.md`.
2. Dispatch it **always** (not "when large"): one `execution-context-{level}` leaf per landing on the `orchestrator.analyze` surface, return shape `findings[N]{layer,severity,file,line,claim,verdict}` with `verdict` one of `checked` / `not_shown_by_reading`, plus the conformance list; the orchestrator re-reads each `checked` point before recording it. Verdicts, the report and every ledger write stay inline.
3. Layer-3 findings: report to the operator, never an inline fix; a staged fix-plan spec only on the operator's word; layer-1/2 findings name the spec or specification part to correct and an owner (the epic keeps an owner register for this; consider a verb or a field for it).
4. When this is native, the epic drops R21 from its `standing-rules.md`; the rule is "custom" only because the verb lacks it.

## Related gaps seen in the same landings (same verb, smaller)

- **`landing-check` reports `complete: false` on every runbook-lane landing**: `missing_keys` is `total_tokens` and `plugin_version` each time (nine recurrences, recorded as an Open Defect in the epic). The lane writes `unknown`. Either the lane fills them or `landing-check` stops treating them as required for a lane that cannot measure them.
- **A partial landing** (`merge_state=open`, `deliverables_done` below `deliverables_total`, as PLAN-V2-110's landing message of 2026-11-02) has no named path in `analyze`: the epic observes it, keeps the row `running`, and writes no ship semantics. A documented "observe, do not ship" branch would remove the judgment call. Eight recurrences of an incomplete landing are in the epic's Open Defects.
- **A downstream spec has no field for "read this landing's findings at your outline"**: the epic adds a Standing Constraints bullet by hand to each staged spec whose surface a finding touches (PLAN-V2-16, 62, 36, 28 so far). A `corpus` verb that lists the staged specs whose Expected Surface a landing's findings name would make that mechanical.

## Not asked

No change to the lane, to the disjointness gate, or to who decides: the operator still owns every fix-plan decision.
