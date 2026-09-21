envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:43:48Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# Documented aspect capture commands name work/footprint.txt, which no step creates

## Context

Two retrospective aspects document a capture command that passes `--diff-file work/footprint.txt`:

- `plan-retrospective/SKILL.md` § "Aspect 13 (routing-decisions, conditional)" — pre-existing, introduced in #811.
- `plan-retrospective/references/outline-vs-shipped.md` § "Persistence" — **shipped by this plan's D7**, a write-new file.

No step in the retrospective workflow creates `work/footprint.txt`. The plan-artifact manifest for this plan lists every file in `work/`; the file is absent.

Both scripts resolve a relative `--diff-file` plan-directory-first then cwd, and **raise** when neither candidate exists — a rule both documents state explicitly in the paragraph immediately below the command they document.

## Root cause

The new document copied the sibling's dangling artifact reference verbatim instead of using the resolver-recovery form the same paragraph goes on to describe. Nothing tests the documented invocation, so the divergence between "the command we publish" and "the command that works" is unobserved.

## Proposed action

Drop `--diff-file work/footprint.txt` from both capture commands. Absent the flag, both scripts recover the footprint through the shared resolver — which is what actually worked on this plan. If a capture artifact is wanted, a workflow step must create it first.

## Evidence

- Executed verbatim, aspect 13: `check-routing-decisions run --plan-id … --mode live --diff-file work/footprint.txt` → `exit 1`, `error: internal_error`, `Diff file does not exist: work/footprint.txt — tried: …/work/footprint.txt, …/plan-marshall/work/footprint.txt`
- Executed verbatim, aspect 15: `check-outline-vs-shipped run --plan-id … --mode live --diff-file work/footprint.txt` → identical `exit 1` failure.
- Both aspects produced fragments in this retrospective **only because the run deviated from the documented command** and omitted the flag.
- Corpus sweep: `architecture search --content --pattern "work/footprint.txt"` — 18 matches over 9 files, `files_scanned: 5264`, `truncated: false`, `unreadable[0]`, `elided[0]`. Three of the nine are documentation (`SKILL.md` ×3, `outline-vs-shipped.md` ×1, `routing-decision-verification.md` ×1); the rest are scripts and tests.
