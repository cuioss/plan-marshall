envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:45:01Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# Phase Dispatch Boundaries renders on no plan - consumer key has no producer

## Context

`retro_sections.SECTION_SPEC` carries the row `('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries')`, and `compile-report.should_emit` gates it through `_dispatch_boundaries_has_present_phase(fragments.get('dispatch_boundaries'))` — a lookup on a **top-level bundle key**.

No producer writes that key. `analyze-logs.py` computes the whole `dispatch_boundaries` block and emits it **nested inside its own `log-analysis` fragment**, and the SKILL.md aspect table registers no `dispatch_boundaries` aspect — the workflow document does not mention the key at all.

Result: the section is omitted on every plan, forever, while its data sits one nesting level down.

## Root cause

Producer/consumer key placement drift: the consumer reads a top-level key, the producer nests the block, and nothing in the documented workflow bridges them.

Two things hide it:

1. The omission is classified **benign** — it lands in `sections_omitted` ("the trigger fragment was absent, so there was nothing to lose"), never in the loud `sections_dropped`. The report's own partition therefore reports *nothing was lost* about a block carrying 31 dispatch rows.
2. The tests **hand-construct** the missing key. `_compile_report_fixtures.py::_write_fragments_with_dispatch_boundaries` and `::_registry_render_fragment_lines` both synthesize a literal `dispatch_boundaries:` top-level block. The same file's `_FRAGMENT_TO_ASPECT` map — which records committed producer fragment filenames — has 10 entries and does **not** include it. The suite is green over a bundle shape production never emits.

## Proposed action

Pick one and make it structural:

- Have the workflow register the block as its own top-level aspect fragment (the key is already in `valid_aspect_keys()`), **or**
- Have `should_emit` reach into the `log-analysis` fragment for the nested block.

Then close the test gap: the registry round-trip guard should build its bundle from real producer output for at least one key, or assert that every `SECTION_SPEC` key has a named producer. A fixture that synthesizes the shape under test cannot detect a producer that never emits it.

## Evidence

- This run: `sections_omitted[3]` includes `Phase Dispatch Boundaries`, while the registered `log-analysis` fragment carries `dispatch_boundaries` with three phases all `present: true` and 31 rows total (4-plan 1, 5-execute 10, 6-finalize 20) — including the 5 `returned_with_findings` loop-backs and the whole finalize dispatch ledger.
- `sections_dropped[0]` — the loud half of the partition did not fire.
- `architecture search --content --pattern "dispatch_boundaries"`: 38 matches over 19 files, `files_scanned: 5264`, `truncated: false`, `unreadable[0]`, `elided[0]`. `plan-retrospective/SKILL.md` is **not** among them.
- The archetype is already in the corpus: a passing check over a synthesized fixture proves the grammar, not the existence.
