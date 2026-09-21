envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T17:07:40Z

# The hunk that widens a set is also the hunk that plants the next stale count

component: pm-plugin-development:ext-self-review-plan-marshall
category: anti-pattern
confidence: high
source_signal: signal_qgate_pending_count

## Context

The stale-restated-set archetype fired **four times in one plan, across two phases**, on a change whose entire subject was widening two sets (`TARGET_REGISTRY` gained `pr-agent`; `_INFRA_CONFIG_BASENAME_GLOBS` gained the review-bot descriptor family):

| Phase | Finding | Restatement | Truth |
|-------|---------|-------------|-------|
| 3-outline | `6a64fc` | D2 Design notes: "adds **two** rows" | Change per file and Success Criteria both enumerate **three** |
| 6-finalize | `fc0706` | AGENTS.md + CLAUDE.md: `--target [claude,opencode,all]` | argparse choices are now `claude, opencode, pr-agent, all` |
| 6-finalize | `d66dea` | "The **two** surviving lowercase tokens are the upstream spec's own address" | the file carries **four**, and one of them is not an address — the universal is false, not merely miscounted |
| 6-finalize | `d7c9f8` | grouping comment: "grouped by the tool that resolves them: container orchestration, container lint/scan, and review bots" | the tuple also holds `.gitlab-ci.yml`/`.yaml` — a fourth group |

Three sharpening details make this more than a tally.

**1. The widening hunk plants its own successors.** In `d66dea`, *both* uncounted tokens were introduced by the same hunk that wrote the count. The sentence was stale on arrival — it could never have been correct, at any moment, in any tree. The fix for that finding then added further legacy-name tokens, so any corrected fixed count would have gone stale a second time before landing.

**2. The correct remedy was deletion every time, never correction.** All four were resolved by removing the number or opening the enumeration — "widens the tuple by one family, described by its RULE"; "Every surviving lowercase token is protected, and none of them names the file this command emits"; "the groups present **include** …, stated openly because the family grows"; "name `TARGET_REGISTRY` as the source of truth and describe `--target {name}` by the rule". Correcting `two` to `three` was available in every case and was the wrong move in every case.

**3. A sibling document already had it right, and was not copied.** `standards/decision-rules.md:311` writes "Tool groups recognized under it **include** …" — open language, in the same skill, describing the same tuple. The closed restatement in `_manifest_core.py` sat beside a correct model and still drifted.

**4. The consulted lesson did not prevent the recurrence.** This plan consulted lesson `2026-08-08-21-003` (*when a set is widened, the restated counts are the blast radius and the fix is DELETION not correction*) at outline time, cited it by id inside D2 — **and then reproduced the archetype inside the deliverable that cites it** (`6a64fc`). The lesson supplied the correct remedy after the gate caught each instance; it prevented none of them. A prospective lesson that is read, understood, cited, and then violated in the same document is evidence that the corpus's prospective arm is not where this class gets caught.

## Why this belongs to the review apparatus

`fc0706` is not an ordinary doc-drift finding. **The same change that made `AGENTS.md` stale also made it load-bearing as the PR-Agent reviewer's `repo_context_files` source.** The reviewer this epic exists to improve was pointed at a repo-root instruction file that denies the existence of the very generator target the plan added — and it denies it in *brace notation*, which reads as a closed choice set to an agent that this project's own hard rules instruct to quote verbatim. So the failure mode is not "a reader is under-informed"; it is "a reviewer is authoritatively misinformed, in the format most likely to be copied".

## Proposed action

1. **Make set-widening carry a mandatory blast-radius sweep.** When a change adds a member to an enumerated set, every restatement of that set — prose counts, docstrings, grouping comments, brace-notation choice lists, repo-root instruction files — is in scope by construction. The deterministic seam exists: a content sweep for the old enumeration string. In this run it was run *after the fact* by self-review and found four sites; the same sweep at outline time would have produced the same list.
2. **Detect the plant, not only the drift.** Three of the four sites were *written by the widening hunk itself*. A check that only compares restated counts against the current tree catches drift over time; it does not catch a count that was wrong the moment it was authored. The self-review candidate class should flag any count or closed enumeration appearing **in added lines** of a hunk that also modifies a set literal.
3. **Prefer the sibling's phrasing over a new one.** When one document in a skill describes a set openly and another closes it, that is a cheap, deterministic pair to detect and the correct resolution is always to copy the open form.

## Relation to the epic

Sharpens the retained lesson `2026-08-08-21-003` from a new direction: the existing lesson names the blast radius and prescribes deletion, but assumes the restatements pre-exist the widening. This run shows the widening hunk **manufactures** them, and shows the lesson being cited and violated in the same paragraph. Also relevant to **PLAN-PR-011**: all four were caught by in-house self-review, on a run where no external reviewer produced content — so this is one of the few first-party data points on what self-review does catch, namely inconsistencies between statements inside the diff.

## Evidence

- Q-Gate `fc0706`, `d66dea`, `d7c9f8` (6-finalize, source `pm-plugin-development:ext-self-review-plan-marshall`) and `6a64fc` (3-outline) — all `resolution: fixed`, resolution details record the deletion-not-correction remedy verbatim
- `d66dea` resolution detail — "my own Step 2 rewrite added further legacy-name tokens, which any fixed count would have made stale on arrival for the second time"
- `standards/decision-rules.md:311` — the correct open phrasing in the same skill
- `6a64fc` detail — "This is the stale-count-prose archetype the plan's own consulted lesson 2026-08-08-21-003 names, reproduced inside the deliverable that cites it"
- retained lesson `2026-08-08-21-003`
