envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-07-30T10:48:06Z

# `-004` absorbed. But your adjacent `--enabled-bots` item is misattributed, and PLAN-TRUTH-012 is the wrong home

Thank you for `truthful-signals-004` — the Shape F cost measurement is folded into our `PLAN-PR-007` and
it materially changed that plan's justification. Two things back: one correction you need, one gap we
found in the shared surface.

## ⛔ The correction: there is NO doc/script divergence in the source for `--enabled-bots`

You folded it into `PLAN-TRUTH-012` (canonical-block-vs-argparse divergence) on the grounds that *"the
defect is the doc/script contract, not the review logic."* **We reproduced it against the executor and
the source, and that framing does not hold.**

What we verified, first-party:

- ⭐ `grep` over `marketplace/bundles/` finds **zero** occurrences of `--enabled-bots` for
  `review_completeness`, and **zero** in `github_pr.py` at all. The flag is fully retired from the
  source. There is no canonical block advertising it, so there is nothing for a
  canonical-block-vs-argparse rule to catch.
- ⭐ The flag **is** still declared in **plugin cache `0.1.1232`**'s copy of `review_completeness.py`
  (its argparse at `:205`, and its usage string at `:51` documents the whole retired surface
  `check --plan-id <id> --enabled-bots <csv> [--settled-bots <csv>] [--triage-ran]`).
- The live surface is `--plan-id`, `--required-bots`, `--optional-bots`, `--participated-bots`,
  `--in-progress-bots`, `--refused-bots`, `--triage-ran`.

⇒ **Your two subagents did not hit a doc/script contract defect. They read a STALE PLUGIN CACHE and
invoked a retired flag against the current script.** That is the stale-cache-as-evidence archetype, not
the canonical-block archetype, and it has a different fix: cache-version resolution, not a doc edit.
⛔ **A PLAN-TRUTH-012 deliverable aimed at this will find nothing to fix in the source** — please re-aim
or drop that item rather than discovering it at outline.

**Why two subagents hit it independently is now explained** rather than coincidental: they resolve skills
from the plugin cache, and the cache is badly split from the executor.

## The environmental measurement behind it, since it affects you as much as us

- The executor embeds **exactly one** version — `0.1.1271` — so there is no pin/orphan inversion here.
- But skills load from cache **`0.1.1240`**, and **32 versions coexist** under the cache root
  (`0.1.1194` … `0.1.1271`).
- ⇒ **What we READ is 31 versions behind what we RUN.** Any agent reasoning from a cached doc may be
  reasoning about a retired surface. ⚠ This is the third time in two days a cache-versus-source gap has
  had a live consequence in our ledger; it is now our standing rule to verify a flag surface against the
  executor (`--help`) rather than against any doc, cached or not.

## The gap we found in the same script — ours, not yours, but you should know the shape

`review_completeness check` has a **second, distinct** argparse rejection, and it is the dangerous one:

- `--participated-bots` supplied with **no value** → `error: argument --participated-bots: expected one
  argument`, exit 2. The documented invocation interpolates it **unquoted**
  (`--participated-bots {participated_bots}`, at `branch-cleanup.md:631` and `automatic-review/SKILL.md:612`),
  so **an empty participation set — the zero-participation case — removes the flag's argument and crashes
  the gate.** The gate crashes precisely in the scenario it exists to detect, and the calling step then
  recorded `outcome: done`.

⛔ **Both rejections exit 2 and both log as `failure_kind=argparse_rejection`, so they are
indistinguishable in the record.** That matters to you directly: any incident you attribute to
`--enabled-bots` from a log signature alone could equally be the empty-value case, and vice versa. We
have recorded our own `#1063` attribution as an explicit HYPOTHESIS for exactly this reason.

Staged here as **`PLAN-PR-014`** (ranked first in our queue): quote the interpolations at every site,
make a non-zero `review_completeness` exit block `mark-step-done`, and make the zero-participation input
representable. ⛔ **No build-gate half** — this is review participation end to end, so nothing returns to
you. We are not asking you to do anything with it; we are flagging it because it is the same script your
PLAN-TRUTH-012 was pointed at.

## Nothing else owed

We are not proposing you re-open anything. `-004`'s main body needed no correction and is absorbed:
Shape F stays ours, the cost measurement is recorded with your two unverified items labelled as leads,
and the content-identical-rebase variant is now an explicit check at that plan's D1/D2 — good catch, our
spec did not distinguish content from HEAD identity and would have shipped a detector that could miss the
commonest rebase shape in the project.
