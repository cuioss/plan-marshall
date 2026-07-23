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
5. Invariant Outcomes — renders the `invariant_summary` aspect fragment as a per-phase table plus a drift block.
6. Plan Efficiency — renders the `plan_efficiency` aspect fragment as totals plus ratios plus a per-phase breakdown.
7. LLM-to-Script Opportunities — renders the `llm_to_script_opportunities` aspect fragment as a candidate list.
8. Logging Gaps — renders the `logging_gap_analysis` aspect fragment as expected-vs-actual numbers and gap items.
9. Script Failure Analysis — conditional. Emit only when `log_analysis.counts.errors_script > 0`. Renders the `script_failure_analysis` aspect fragment.
10. Permission Prompt Analysis — conditional. Emit only when a session surfaced prompts, or the chat-history aspect detected them. Renders the `permission_prompt_analysis` aspect fragment.
11. Proposed Lessons — renders the `lessons_proposal` aspect fragment as a list of draft lesson blocks. In user-invocable mode, each draft that the user recorded is marked with a trailing `[recorded]` tag.

## Conditional Rule

Sections 9 and 10 are emitted only when their source fragment carries non-empty data. When a fragment has `status: skipped` or an empty list, the compiler must omit the entire section — it must not emit an empty heading.

## Heading Style

The compiler uses `#` for the document title (which is `Plan Retrospective — {plan_id}`), `##` for each numbered section above, and `###` for any sub-table or sub-list inside a section.

## Header Block

The first lines of the document, directly below the title, must be a list containing these four keys: `mode`, `generated`, `plan_path`, and `session_id`. The value for `mode` is one of `finalize-step`, `user-invocable`, or `archived`. The value for `generated` is an ISO-8601 UTC timestamp. The value for `plan_path` is the live plan path or the archived plan path. The value for `session_id` is the provided identifier or the literal string `not provided`.

## Body Conventions

- Tables use pipe syntax (GitHub-flavored Markdown).
- Item lists use bullet entries prefixed with severity icons: `[ERROR]`, `[WARNING]`, `[INFO]`.
- When `metrics.md` exists, the compiler embeds a link to it at the top of the Plan Efficiency section.

## Compiler Boundaries

The compiler is an assembler only. It accepts an input bundle (a TOON file containing all aspect fragments keyed by `aspect`), validates fragment shapes (required top-level keys present), writes the markdown document at the correct path per mode, and returns TOON containing the absolute output path, the section count, and any omitted-section names.

The compiler does NOT make judgement calls. All interpretation is the LLM's responsibility and happens in the pass that produces the fragments.
