envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:57:15Z

# terminal-title ruling (d) claims an edit to hook-authoring-guide.md that never landed

component=plan-marshall:manage-terminal-title
category=bug
confidence=high
source_plan=hook-timeout-unit-confusion
source_pr=1131

## Context

`manage-terminal-title/standards/terminal-title-architecture.md` is the normative contract for the
render-trigger set. Its Component Map states:

> Render triggers wired by `project install-hook`: `SessionStart:matcher-less`, `SessionStart:clear`
> (the entry that routes the session teardown …), `UserPromptSubmit`, `Notification`, `Stop`,
> `PreToolUse:AskUserQuestion`, `PreToolUse:Bash`, `PostToolUse:AskUserQuestion`, and
> `PostToolUse:Bash`. … **Nine render-trigger labels in total**, plus `statusLine`.

Ruling (d) additionally records that `_DISPLAY_RENDER_ENTRIES` was converged to include "the
installed `SessionStart:clear` entry — previously absent from the expected set, so its removal would
have gone unreported", and that the `display` health check is fail-closed against it.

`plan-marshall/references/hook-authoring-guide.md` — the human-facing authoring contract for anyone
adding a hook-driven script — still says the opposite:

> The terminal-title bundle installs **eight** render-trigger entries (plus `statusLine`):
> `SessionStart` (**ONE matcher-less entry** — it fires for every source, and the renderer turns
> `source == "clear"` into a session teardown rather than a render), `UserPromptSubmit`,
> `Notification`, `Stop`, `PreToolUse:AskUserQuestion`, `PreToolUse:Bash`, `PostToolUse:Bash`, and
> `PostToolUse:AskUserQuestion`.

It enumerates exactly eight and explicitly **denies** a separate `SessionStart:clear` entry. An
inventory content sweep for the literal `SessionStart:clear` finds it in eight other artifacts — the
architecture standard (8 hits), `marshall-steward/references/menu-terminal-title.md` (5),
`platform-runtime/SKILL.md`, `platform-runtime/standards/contract.md`,
`manage-status/scripts/_cmd_lifecycle.py`, `_claude_runtime_impl.py` (3), `claude_runtime.py` (4),
`runtime_base.py`, plus two test modules — and **absent** from `hook-authoring-guide.md`. The code is
authoritative and correct; the guide is the sole artifact teaching the wrong shape.

## The aggravating half

Ruling (d) closes with its own edit manifest:

> Artifacts this ruling edits: `platform-runtime/scripts/_claude_runtime_impl.py`
> (`_DISPLAY_RENDER_ENTRIES`, `_prune_matcher_scoped_render_entries`),
> **`plan-marshall/references/hook-authoring-guide.md`**,
> `marshall-steward/references/menu-terminal-title.md`, and this document.

That edit was never made. And ruling **(a)** in the *same document* names the *same artifact* in its
own edits list — and that one **did** land: `hook-authoring-guide.md` lines 16 and 28 carry the
`/dev/tty` deletion faithfully, including the "a path that provably never lands is worse than none"
rationale.

So one document holds two edit claims about one file with opposite truth values, and nothing inside
the document distinguishes them. An "artifacts this ruling edits" list is an assertion about the
world that no check verifies; a reader auditing ruling (d) against its claimed artifact set finds the
claim, reads it as discharged, and stops.

## Root cause

The edits list is authored at ruling time as an intent, and read afterwards as a record. Nothing
converts it from the first to the second — no test, no plugin-doctor rule, and no finalize step
compares a ruling's named artifacts against the commit that implemented it. Ruling (a)'s claim being
true is what makes ruling (d)'s claim credible.

## Proposed action

1. Correct `hook-authoring-guide.md` § "Installed render-trigger hook entries": nine entries, both
   `SessionStart` rows enumerated, and the `source == "clear"` behaviour described as what the
   dedicated entry routes rather than as what a single matcher-less entry branches on internally.
2. Treat the divergence class structurally. An edits list that names concrete repo-relative paths is
   machine-checkable: a rule could require every path named in an "Artifacts this ruling edits" list
   to appear in the diff of the commit that introduced the ruling, or to carry a marker showing which
   change discharged it. The `ext-self-review-plan-marshall` surfacer already enumerates
   contract-source and source-of-truth-duplicate candidates; a named-artifact-vs-diff check fits the
   same family.
3. Note that this plan touched both `platform-runtime/standards/contract.md` and
   `marshall-steward/references/menu-terminal-title.md` — two of the three docs ruling (d) named —
   without reconciling the third. The affected-files set was derived from the *code* change, not
   from the set of artifacts making claims *about* that code.

## Evidence

- `plan-marshall/references/hook-authoring-guide.md` line 22 (eight, SessionStart as ONE entry);
  lines 16 and 28 (ruling (a) landed).
- `manage-terminal-title/standards/terminal-title-architecture.md` line 284 ("Nine render-trigger
  labels in total"); lines 208–210 (ruling (d) on `_DISPLAY_RENDER_ENTRIES`); line 229 (ruling (d)
  edits list); line 82 (ruling (a) edits list).
- `architecture search --content --pattern "SessionStart:clear"` → 20 results across 10 distinct
  files; `hook-authoring-guide.md` is not among them.
- aspect `request_result_alignment` — findings `DOC_CONTRACT_DIVERGENCE_HOOK_AUTHORING_GUIDE` and
  `RULING_EDIT_CLAIM_UNHONOURED`.

## Why this belongs to truthful-signals

A canonical contract asserting an edit that was never made is the purest form of the theme: the
artifact that exists to be trusted is the one carrying the false claim, and the claim is phrased as a
completed action. The `display` health check being fail-closed makes it worse, not better — the
machine-checked surface is right, so nothing ever fails, and only a human reading the guide is
misled.
