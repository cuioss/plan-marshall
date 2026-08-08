# Compiler Layout Specification

This is a reference document for the `compile-report.py` script. It specifies the ordered list of sections that the compiler must emit when assembling its markdown output, the heading style it must use, and the filename rules per invocation mode.

## Output Filename

In live modes the compiler writes `quality-verification-report.md` at the plan directory root, overwriting any existing copy. In archived mode the compiler writes `quality-verification-report-audit-{YYYYMMDDTHHMMSSZ}.md` inside the archived plan directory and never overwrites.

## Section List

The compiler must emit exactly these sections in this order:

1. Executive Summary — a 3-5 sentence narrative that synthesizes all aspects. It must lead with overall severity (all-green, N warnings, or errors) and the most important signals.
2. Goals vs Outcomes — renders the `request_result_alignment` aspect fragment as a table.
3. Artifact Consistency — renders the `artifact_consistency` aspect fragment as a check table plus a signal list.
4. Log Analysis — renders the `log_analysis` aspect fragment as counts, slowest scripts, and top error tags.
5. Phase Dispatch Boundaries — conditional. Emit only when the `dispatch_boundaries` fragment carries at least one phase entry reporting `present: true`. Renders a per-phase table plus the full fragment data.
6. Invariant Outcomes — renders the `invariant_summary` aspect fragment as a per-phase table plus a drift block.
7. Plan Efficiency — renders the `plan_efficiency` aspect fragment as totals plus ratios plus a per-phase breakdown.
8. LLM-to-Script Opportunities — renders the `llm_to_script_opportunities` aspect fragment as a candidate list.
9. Logging Gaps — renders the `logging_gap_analysis` aspect fragment as expected-vs-actual numbers and gap items.
10. Script Failure Analysis — conditional. Emit only when `log_analysis.counts.errors_script > 0`. Renders the `script_failure_analysis` aspect fragment.
11. Permission Prompt Analysis — conditional. Emit only when a session surfaced prompts, or the chat-history aspect detected them. Renders the `permission_prompt_analysis` aspect fragment.
12. Direct gh/glab Usage — always emitted; the aspect runs for every plan and emits zero findings on a clean trail. Renders the `direct-gh-glab-usage` aspect fragment.
13. Execution-Context Dispatch Audit — always emitted; the aspect runs for every plan and emits zero findings on a clean trail. Renders the `execution-context-dispatch-audit` aspect fragment.
14. Manifest Decisions — conditional. Emit only when the `manifest-decisions` fragment is present. Renders the manifest body plus the paired decision-log entries.
15. Routing Decisions — conditional. Emit only when the `routing-decisions` fragment is present. Renders the lane/recipe/posture verdict, the mis-prune checks, and the cost preview.
16. Chat History Analysis — conditional. Emit only when the `chat-history-analysis` fragment is present. A Tier-2 `status: skipped` fragment carrying a warning finding still renders — the warning is required to be visible.
17. Proposed Lessons — renders the `lessons_proposal` aspect fragment as a list of draft lesson blocks. In user-invocable mode, each draft that the user recorded is marked with a trailing `[recorded]` tag.

## Conditional Rule

Conditional sections are emitted only when their source fragment carries non-empty data. When a fragment is absent, has `status: skipped`, or carries only an empty list, the compiler must omit the entire section — it must not emit an empty heading. That is a benign omission and the compiler reports it under `sections_omitted`.

Chat History Analysis (item 16) is the sole documented exception: its own entry specifies that a `status: skipped` fragment carrying a warning finding still renders, because that warning is required to be visible. The override is keyed to that one section — every other conditional section still omits on `status: skipped` regardless of payload.

The counterpart holds too: a fragment that IS present and DOES carry payload but still does not render is a **drop**, not an omission, and must be reported as such — under `sections_dropped`, with the run's status raised to `warning`. A dropped section is content the aspect produced and the report lost, so it can never ride the same clean-run signal as an omission.

## Heading Style

The compiler uses `#` for the document title (which is `Plan Retrospective — {plan_id}`), `##` for each numbered section above, and `###` for any sub-table or sub-list inside a section.

## Header Block

The first lines of the document, directly below the title, must be a list containing these four keys: `mode`, `generated`, `plan_path`, and `session_id`. The value for `mode` is one of `finalize-step`, `user-invocable`, or `archived`. The value for `generated` is an ISO-8601 UTC timestamp. The value for `plan_path` is the live plan path or the archived plan path. The value for `session_id` is the provided identifier or the literal string `not provided`.

## Body Conventions

- Tables use pipe syntax (GitHub-flavored Markdown).
- Item lists use bullet entries prefixed with severity icons: `[ERROR]`, `[WARNING]`, `[INFO]`.
- When `metrics.md` exists, the compiler embeds a link to it at the top of the Plan Efficiency section.

## Compiler Boundaries

The compiler is an assembler only. It accepts an input bundle (a TOON file containing all aspect fragments keyed by `aspect`), validates fragment shapes (required top-level keys present), writes the markdown document at the correct path per mode, and returns TOON containing the absolute output path and the partitioned section outcome:

- `sections_written` — the sections the report carries.
- `sections_omitted` — sections whose trigger fragment was absent or carried nothing renderable. Benign: nothing was lost.
- `sections_dropped` — sections whose trigger fragment WAS present and carried payload, yet did not render. Loud: content the aspect produced never reached the report.

A non-empty `sections_dropped` raises the returned status to `warning` and adds a `message` naming the dropped headings. The process exit code stays `0` — the document was written, and the warning rides the TOON status so the caller cannot read a lossy run as a clean one.

The compiler still does NOT make judgement calls. The written/omitted/dropped partition is a mechanical probe over the fragment bundle — "did this fragment carry anything beyond its envelope keys?" — not an assessment of whether the content mattered. All interpretation remains the LLM's responsibility and happens in the pass that produces the fragments.
