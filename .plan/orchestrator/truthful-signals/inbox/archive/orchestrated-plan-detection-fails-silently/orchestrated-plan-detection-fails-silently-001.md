envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=landing
created=2026-07-29T15:41:09Z

## What landed

**PLAN-114 / WS-01 — PR #1057** `fix(marshall-orchestrator): accept slug-scoped plan ids and surface unrecognised pointers`

3 commits, 5 files, +281/-40.

### The defect

`orchestrator inbox detect` recognised only a `PLAN-{DIGITS}` id segment. Any other id shape under `.plan/local/orchestrator/{slug}/plans/` returned `orchestrated: false` — **bit-for-bit indistinguishable from "this is not an orchestrator pointer at all"**. An orchestrated plan whose spec was named e.g. `CIS-01-content-search-seam.md` therefore finalized down the non-orchestrated path and wrote NO inbox message. The epic silently lost the landing, and nothing anywhere reported a reclassification.

This is the epic's theme in its purest form: a confident boolean (`orchestrated: false`) that hides the caveat "…or I simply did not recognise this."

### The fix

- **Widened grammar — three accepted forms** for the id segment: `PLAN-{DIGITS}`, `PLAN-{SLUG}-{DIGITS}`, `{SLUG}-{DIGITS}`. `{SLUG}` is a 2–8-character uppercase-alphanumeric token with mandatory trailing digits, so `01-foo.md`, lowercase `cis-01-foo.md`, and a nine-character token all stay outside the grammar.
- **New `detection` return field** over a closed four-token vocabulary: `orchestrated`, `not_orchestrator_pointer`, `unrecognised_id`, `unsafe_slug`. `unrecognised_id` is precisely the previously-invisible class — the path IS an orchestrator plan-spec path but its id segment matched nothing.
- **`phase-6-finalize` SKILL.md Step 3 item 4b.a0** now emits a work-log `WARNING` naming the pointer when `detection == unrecognised_id`. **The WARNING changes the SILENCE, not the branch** — the verdict stays `orchestrated: false` and the run proceeds down the non-orchestrated path exactly as before. `detection` is read at the dispatcher and is deliberately NOT added to the two forwarded consumers' runtime inputs (`default:lessons-capture`, `plan-retrospective` Step 5b), which keep receiving `orchestrated` + `epic` unchanged.
- **Docs**: both `marshall-orchestrator/SKILL.md` and `phase-6-finalize/SKILL.md` now state the grammar table and the detection-vocabulary table.
- **Tests**: `test_inbox_envelope.py` (+128), `test_finalize_orchestration_routing.py` (+50).

### Verification

whole-tree quality-gate green · module-tests green · plugin-doctor clean (2 skills gated) · pre-submission self-review clean (7 candidates) · simplify 0 edits · `ci-verify: all checks green`.

## Residue the epic should track

1. **⛔ Reviewer participation on #1057 was THIN — do the post-merge revisit.** `automatic-review` found exactly **1** comment and `review-retrospective` compared exactly **1** reviewer: pr-agent's informational "PR Reviewer Guide" summary (`PR contains tests / No security concerns / No major issues`), triaged `accepted` with zero actionable content. **No CodeRabbit comment and no Sourcery comment** were present at finalize time. Per the epic's own standing rule, a green `automatic-review` outcome is not evidence the bots saw the diff — `ci pr comments --pr-number 1057` is the only evidence of participation, and it should be re-run post-merge.

2. **This plan's own `status.json` is internally inconsistent**: `current_phase: 6-finalize` while `phases[].2-refine` is still `in_progress`. The light lane collapsed the refine envelope and never closed the phase row. Same root cause as candidate-lesson #1 below.

3. **Five orchestrator-observed process signals** from this run ride as separate `candidate-lesson` messages: light-lane `pr_title` producerless-consumer, light-lane `references.json` missing `track`/`affected_files`, vacuous `--help` freshness evidence, `enabled_bots` manifest-field doc drift, and the wrong compose-time `execution_tier` stamp. All five are the same family the epic already tracks (producer/consumer mismatch, vacuous guard, derived-value-as-authority) and none of them is specific to this plan's own change — they are infrastructure defects this run merely surfaced.
