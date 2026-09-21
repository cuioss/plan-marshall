envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:18:55Z

component=plan-marshall:phase-1-init
category=improvement
confidence=medium
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# Domain detector scored zero narrative matches on an unambiguously Python plan

## Context

At init the domain detector returned `plan-marshall-plugin-dev` and nothing else. The
operator gate that surfaced it states the mechanism plainly:

> "The domain detector returned `plan-marshall-plugin-dev` only (zero narrative matches;
> resolved purely from the always_on leg). This plan's deliverables are Python
> production code (`github_pr.py`) plus pytest suites, and its Verification section
> mandates the repo Python build. Should `python` be added to the domain set?"

The operator answered "Add python (Recommended)". The final `references.json` records
`domains: ["plan-marshall-plugin-dev", "python"]`.

The plan's realized footprint is 10 files: three Python production modules
(`github_pr.py`, `github_ops.py`, `_github_ci.py`), four Python test modules, and three
markdown standards. Seven of ten files are Python. The request text names `github_pr.py`
throughout and mandates the repo Python build in its Verification section.

So the detector scored **zero** narrative matches against a request that is about as
Python-explicit as a request in this repository can be.

## Root cause

The `always_on` leg guarantees a non-empty domain set. That is a reasonable failsafe,
but it means a zero-narrative-match result and a confident single-domain result produce
the same output shape: one domain, no qualifier. The caller cannot distinguish "the
detector matched this domain" from "the detector matched nothing and the always_on leg
supplied a floor".

This is the same discriminator problem the codebase has closed elsewhere — a zero that
does not say which kind of zero it is. `manage-lessons list-stalled` publishes
`store_resolution` / `plans_root_state` / `scanned_plan_count` beside its count for
exactly this reason; the domain detector publishes no equivalent.

Had the operator not been prompted, the plan would have run with `python` absent from
its domain set, which governs skill resolution for the implementation profile.

## Proposed action

1. **Publish the match provenance.** Return `narrative_matches: N` alongside the domain
   set, and mark any domain contributed solely by the `always_on` leg (e.g.
   `source: always_on` vs `source: narrative`). A caller can then tell a floor from a
   finding without a human reading the prose.
2. **Escalate a zero-narrative-match result rather than presenting it as an answer.**
   When `narrative_matches == 0`, the gate should say so in the question — it did here,
   which is why the operator caught it, but that appears to be the prompt author's care
   rather than a guaranteed property.
3. **Check the narrative matcher against this case specifically.** A request naming a
   `.py` file repeatedly and mandating a Python build should not score zero. This may be
   a matcher-vocabulary gap rather than a reporting gap, and the two need different
   fixes.

## Evidence

- transcript: the init domain gate, quoted above, naming "zero narrative matches;
  resolved purely from the always_on leg".
- artifact: `references.json` — `domains: ["plan-marshall-plugin-dev", "python"]`
  (post-correction).
- footprint: `git diff 8025b2210^ 8025b2210` — 7 of 10 files are `.py`.
- aspect: chat_history_analysis — finding `DOMAIN_DETECTOR_NARRATIVE_MISS`.
