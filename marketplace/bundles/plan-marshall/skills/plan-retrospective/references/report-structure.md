# Compiler Layout Specification

This is a reference document for the `compile-report.py` script. It specifies the ordered list of sections that the compiler must emit when assembling its markdown output, the heading style it must use, and the filename rules per invocation mode.

## Output Filename

In live modes the compiler writes `quality-verification-report.md` at the plan directory root, overwriting any existing copy. In archived mode the compiler writes `quality-verification-report-audit-{YYYYMMDDTHHMMSSZ}.md` inside the archived plan directory and never overwrites.

## Section List

The compiler must emit exactly these sections in this order:

1. Executive Summary — a 3-5 sentence narrative that synthesizes all aspects. It must lead with overall severity (all-green, N warnings, or errors) and the most important signals. Conditional on a body existing: when the `_executive-summary` fragment supplies no narrative the compiler emits NO heading at all, exactly as the Conditional Rule below requires — it never emits a placeholder body, and it never counts such a section as written.
2. Goals vs Outcomes — renders the `request_result_alignment` aspect fragment as a table.
3. Footprint Derivation Coverage — conditional, and injected by the compiler rather than registered by a producer. Emit only when the `_footprint-derivation` record was derived. Renders the plan-level aggregate over every aspect that consumes the shared footprint derivation: the producer roster with each member's own verdict and provenance, and the counts described under "Footprint Derivation Aggregate" below. It sits here, ahead of the four sections it aggregates, so a reader meets the plan-level caveat before reading any individual footprint-derived verdict at face value.
4. Artifact Consistency — renders the `artifact_consistency` aspect fragment as a check table plus a signal list.
5. Log Analysis — renders the `log_analysis` aspect fragment as counts, slowest scripts, the cumulative `script_cost_rollup` (read beside the per-call slowest/percentile fields), `context_position_cost` (cached-read tokens per tool use by phase — a different currency from the wall-clock roll-up), and top error tags. See `log-analysis.md` for how the per-call and cumulative views are read together.
6. Phase Dispatch Boundaries — conditional. Emit only when the `dispatch_boundaries` fragment carries at least one phase entry reporting `present: true`. Renders a per-phase table plus the full fragment data.
7. Invariant Outcomes — renders the `invariant_summary` aspect fragment as a per-phase table plus a drift block.
8. Plan Efficiency — renders the `plan_efficiency` aspect fragment as totals (including `total_build_seconds`, the ledger-derived total build time — a floor when suspect builds were seen) plus ratios plus a per-phase breakdown.
9. LLM-to-Script Opportunities — renders the `llm_to_script_opportunities` aspect fragment as a candidate list.
10. Logging Gaps — renders the `logging_gap_analysis` aspect fragment as expected-vs-actual numbers and gap items.
11. Script Failure Analysis — conditional. Emit only when `log_analysis.counts.errors_script > 0`. Renders the `script_failure_analysis` aspect fragment.
12. Permission Prompt Analysis — conditional. Emit only when a session surfaced prompts, or the chat-history aspect detected them. Renders the `permission_prompt_analysis` aspect fragment.
13. Direct gh/glab Usage — always emitted; the aspect runs for every plan and emits zero findings on a clean trail. Renders the `direct-gh-glab-usage` aspect fragment.
14. Execution-Context Dispatch Audit — always emitted; the aspect runs for every plan and emits zero findings on a clean trail. Renders the `execution-context-dispatch-audit` aspect fragment.
15. Manifest Decisions — conditional. Emit only when the `manifest-decisions` fragment is present. Renders the manifest body plus the paired decision-log entries.
16. Routing Decisions — conditional. Emit only when the `routing-decisions` fragment is present. Renders the lane/recipe/posture verdict, the mis-prune checks, and the cost preview.
17. Chat History Analysis — conditional. Emit only when the `chat-history-analysis` fragment is present. A Tier-2 `status: skipped` fragment carrying a warning finding still renders — the warning is required to be visible.
18. Proposed Lessons — renders the `lessons_proposal` aspect fragment as a list of draft lesson blocks. In user-invocable mode, each draft that the user recorded is marked with a trailing `[recorded]` tag.

## Conditional Rule

Conditional sections are emitted only when their source fragment carries non-empty data. When a fragment is absent, has `status: skipped`, or carries only an empty list, the compiler must omit the entire section — it must not emit an empty heading. That is a benign omission and the compiler reports it under `sections_omitted`.

Chat History Analysis (item 17) is the sole documented exception: its own entry specifies that a `status: skipped` fragment carrying a warning finding still renders, because that warning is required to be visible. The override is keyed to that one section — no other conditional section renders on `status: skipped`.

⚠ **The implementation does not yet meet the omission requirement above for every `status: skipped` fragment, and this paragraph records the divergence rather than restating the rule as though it held.** A skipped fragment that carries any non-envelope field whose value is neither an empty sentinel nor `False` — a `skip_reason`, a `summary`, a `log_path` — is seen as payload by `_fragment_has_payload`, so the non-emit path classifies it as a **drop** and raises the run's status to `warning`. Two shapes are correctly omitted instead: an empty-valued field (`{'status': 'skipped', 'aspect': 'x', 'checks': []}`) and a `False` one (`{… 'manifest_present': False}`), which `_fragment_has_payload` skips by identity so a numeric zero is not swallowed with it. Measured on a plan with no `execution.toon`, where `check-manifest-consistency` and `check-routing-decisions` both return `status: skipped` with a reason: both land in `sections_dropped`. The same mechanism drops `script-failure-analysis` on any plan with no script failures — its clean-run fragment is `status: success` with an empty `findings` list and several non-envelope fields, the FIRST of which is `plan_id`, so removing the provenance paths would not change the verdict.

The requirement above is the intended behaviour. Closing the gap means deciding what `_fragment_has_payload` counts as content for a fragment whose own status already says it produced nothing — a decision that governs every conditional row, so it belongs to a change scoped to it rather than to a caller working around it here.

The counterpart holds too: a fragment that IS present and DOES carry payload but still does not render is a **drop**, not an omission, and must be reported as such — under `sections_dropped`, with the run's status raised to `warning`. A dropped section is content the aspect produced and the report lost, so it can never ride the same clean-run signal as an omission.

## Footprint Derivation Aggregate

Section 3 is the one section the compiler DERIVES rather than renders from a producer's fragment. Every aspect that consumes the shared footprint derivation degrades honestly on its own when that derivation cannot be resolved — `check-artifact-consistency` and `check-routing-decisions` report `inconclusive`, `analyze-logs` reports `ARTIFACT_COVERAGE_UNMEASURABLE`, and manifest compose-time reports `pre_push_quality_gate_inactive`. Each of those reports is correct and none of them is altered, rewritten, or replaced by this section.

Membership is decided by whether a producer publishes a degradation verdict, not by whether it names the resolver. `check-manifest-consistency` is the one consumer that mentions the resolver but publishes no such verdict, so it is not a roster member: a producer that can only ever read as `resolved` would suppress the record on every run, leaving the aggregate structurally unable to fire. The roster grows the moment that producer grows a verdict — the declaration in `scripts/retro_sections.py` is where that judgement lives, and it carries the measurement behind it. What the aggregate adds is the plan-level statement none of them can make alone: that N independent consumers went unmeasurable on the *same* missing derivation.

**The aggregate never edits a consumer's report.** It reads the fragment bundle and writes one additional record; no producer fragment is modified, and every producer's own section renders exactly as it would without this one.

**Roster provenance is published, not assumed.** The roster has two provenances and each member carries its own. The retrospective-time members are DERIVED from the aspect registry in `scripts/retro_sections.py` — walked in registry order and filtered to the aspects declared as footprint consumers — so an aspect added to the registry grows the roster with no change to the compiler. The single compose-time member has no registry entry and is therefore named explicitly, published under a distinct provenance so the derived half stays distinguishable from the declared one.

**Counts.** The record publishes `producer_count`, `degraded_count`, `resolved_count`, `unread_count` and `roster_source`, plus a `producers` list carrying each member's name, verdict and provenance.

**When it fires.** The record exists only when every roster member that could be READ degraded:

- `state: unmeasurable` — the roster was fully read and every member degraded. The verdict fires.
- `state: partial_coverage` — every member that could be read degraded, but at least one could not be read at all. The verdict is SUPPRESSED and the coverage gap reported in its place; an aggregate computed over a roster that was not fully read would assert more than it measured.

A run in which any member resolved yields no record and no section at all, because the signal is that the consumers failed *together* — a mixed roster is not that signal, and reporting one would make the section fire on runs it exists to stay silent for.

## Heading Style

The compiler uses `#` for the document title (which is `Plan Retrospective — {plan_id}`), `##` for each numbered section above, and `###` for any sub-table or sub-list inside a section.

## Header Block

The first lines of the document, directly below the title, must be a list containing these four keys: `mode`, `generated`, `plan_path`, and `session_id`. The value for `mode` is one of `finalize-step`, `user-invocable`, or `archived`. The value for `generated` is the report-generation time rendered through the display-only timezone: an ISO-8601 UTC timestamp when `display_timezone` is unset or `UTC` (the default), or the converted, zone-labelled form (e.g. `2026-08-11T20:00:45 IST (UTC+05:30)`) when a non-UTC `display_timezone` is configured — see [`manage-run-config`](../../manage-run-config/standards/run-config-standard.md) § "Display-Timezone Section". The value for `plan_path` is the live plan path or the archived plan path. The value for `session_id` is the provided identifier or the literal string `not provided`.

## Body Conventions

- Tables use pipe syntax (GitHub-flavored Markdown).
- Item lists use bullet entries prefixed with severity icons: `[ERROR]`, `[WARNING]`, `[INFO]`.
- When `metrics.md` exists, the compiler embeds a link to it at the top of the Plan Efficiency section.

## Compiler Boundaries

The compiler is an assembler only. It accepts an input bundle (a TOON file containing all aspect fragments keyed by `aspect`), validates fragment shapes (required top-level keys present), writes the markdown document at the correct path per mode, and returns TOON containing the absolute output path and the partitioned section outcome:

- `sections_written` — the sections the report carries. **The partition's invariant is *written implies non-empty*.** A section listed here has a body; a section whose body would be empty or a placeholder is not written, it is omitted or dropped. Without that invariant the partition reads as precision it does not have — an empty headline section riding the clean half while the loud half fires on something harmless.
- `sections_omitted` — sections whose trigger fragment was absent or carried nothing renderable. Benign: nothing was lost.
- `sections_dropped` — sections whose trigger fragment WAS present and carried payload, yet did not render. Loud: content the aspect produced never reached the report.

Beside the partition — and NOT a member of it — the compiler returns `sections_unattributed_zero`: written sections whose `findings: []` cannot be told apart from *this section could not look*. Those sections are written and do carry a body, and nothing was lost, so this list never changes the returned `status`; it is reported so a reader can see which zeros are unqualified. A section clears it by declaring that it could not look (a status in `ZERO_DECLARED_UNMEASURED_STATUSES`) or by publishing the population it examined (a field in `ZERO_ATTRIBUTION_FIELDS`). Both vocabularies are declared in `scripts/retro_sections.py` — the shared producer/consumer registry — and are read from there rather than restated here.

A non-empty `sections_dropped` raises the returned status to `warning` and adds a `message` naming the dropped headings. The process exit code stays `0` — the document was written, and the warning rides the TOON status so the caller cannot read a lossy run as a clean one.

The compiler still does NOT make judgement calls. The written/omitted/dropped partition is a mechanical probe over the fragment bundle — "did this fragment carry anything beyond its envelope keys?" — not an assessment of whether the content mattered. All interpretation remains the LLM's responsibility and happens in the pass that produces the fragments.
