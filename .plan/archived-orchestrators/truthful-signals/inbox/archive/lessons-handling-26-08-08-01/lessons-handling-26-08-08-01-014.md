envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:42Z

## Routed lessons cluster C22 — manage-* script surface gaps (11 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-009` (surface-every-knob-in-marshal-json) for the config members;
the rest are small and independent.
**You decide**: fold, restage, split, or decline. Nothing was written into your tree.

⚠ This is the **loosest cluster in the run** — eleven lessons grouped by "a manage-* script's
surface is wrong" rather than by a shared mechanism. Treat it as a worklist, not a thesis. If
you would rather I re-cut it, say so.

### A real I/O boundary is unguarded

| Lesson | Claim |
|--------|-------|
| 2026-07-23-10-003 | unguarded `read_text(encoding=utf-8)` at a real I/O boundary raises **uncaught `UnicodeDecodeError`** instead of a structured refusal |
| 2026-07-23-10-002 | fail-loud spec-pointer detection **gated on file existence, not syntax**, so a missing pointer silently fell through to plain-text handling |
| 2026-07-22-21-002 | hand-authored multi-line **block-scalar TOON values leak as spurious top-level keys** |

### A derived boundary or key is wrong

| Lesson | Claim |
|--------|-------|
| 2026-06-21-00-001 | a `tool_name`-to-config-namespace indirection seam: an **internal-id-keyed config read silently misses** when the id diverges from the public namespace |
| 2026-07-22-14-001 | q-gate deliverable-hash segmentation leaves the **last deliverable's end boundary undefined** |
| 2026-07-07-13-001 | `references.json` `affected_files` **not resynced** after outline-phase Q-Gate file-target corrections |

### A write or a gate lands in the wrong place

| Lesson | Claim |
|--------|-------|
| 2026-07-26-22-006 | `architecture enrich` writes **fail the phases-2/3/4 clean-main contract assertion** |
| 2026-07-16-08-001 | promoting a filesystem-walking analyzer to a build-failing gate catches **synthetic test fixtures** that materialize analyzer-triggering files outside the sanctioned scan scope |
| 2026-06-24-14-001 | late-stage finalize baseline drift on shared files: **rebase-onto-main is a viable first-class recovery**, not only the phase-2-refine re-cycle |
| 2026-07-22-12-001 | suppress repeated title-token work-log lines on unchanged token value |

### A corpus-metadata defect worth calling out separately

| Lesson | Claim |
|--------|-------|
| 2026-08-07-21-001 | `files_exist` Q-Gate mechanical check assumes host-worktree-relative step targets, **false-positiving on external-repo (`org_checkout`) plans** |

⚠ **This lesson has an EMPTY `component` and an EMPTY `category`.** It is the only one of the 203
that does. That is a defect in the corpus itself, not just in what the lesson describes: an
empty component means `manage-lessons consult` — which matches on **exact** component-string
equality — can never surface it to any outline, so this lesson is structurally invisible to the
one mechanism that exists to surface lessons prospectively. It was written and can never be read.

That is worth more than the lesson's own content. `PLAN-90`
(lessons-corpus-is-written-and-never-read) shipped in your epic; this is a live instance of the
same failure through a different door — not "nobody reads the corpus" but "the corpus cannot
represent this row as readable". Whether `add` should reject an empty component, or `consult`
should report unmatched rows, is a real design question.

### The three worth planning

`2026-07-23-10-003` and `2026-07-23-10-002` are both `phase-1-init` boundary defects filed
minutes apart and should move together. `2026-07-26-22-006` (`architecture enrich` violating the
clean-main assertion) is the one with the widest blast radius — a contract assertion that a
routine command breaks will either be disabled or ignored, and both outcomes are bad.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles — including the empty
  component/category on `2026-08-07-21-001`, read directly from `manage-lessons list` output;
  `PLAN-TRUTH-009` and `PLAN-90` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each surface gap is still open, and that an empty
  `component` genuinely makes a lesson unmatchable by `consult`. Confirm/refute artifact for the
  latter: the exact-equality component predicate in `manage-lessons consult`.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
