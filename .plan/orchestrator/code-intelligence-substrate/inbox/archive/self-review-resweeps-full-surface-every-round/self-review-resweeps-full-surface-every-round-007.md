envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:23:05Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_aspects=routing-decisions,llm-to-script-opportunities

# check-routing-decisions reports a vacuous SKIP on the --diff-file invocation its own SKILL.md documents

`plan-retrospective/SKILL.md` § Aspect 13 documents the capture pattern with a **plan-relative** `--diff-file`:

```bash
check-routing-decisions run --plan-id {plan_id} --mode live --diff-file work/footprint.txt
```

Run verbatim, that produces:

```toon
mis_prune_checks[2]{check,status,predicate,removal_cause,detail}:
  "mis_prune:sonar-roundtrip",skip,no_code_delta,not_evaluated,no realized footprint
```

The **identical file** passed as an absolute path produces:

```toon
  "mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
```

Same file, same content, same run. The documented form silently degrades to "no realized footprint" and reports `skip`; the undocumented form finds a real mis-prune violation.

## Root cause

An unresolvable `--diff-file` path is treated as *absent* rather than as *supplied-and-unreadable*. A could-not-look is reported with the same token as a nothing-to-look-at, and `skip` reads as benign in every downstream summary (`summary.skipped`, the compiled report section, any cross-plan audit counting evaluated predicates).

## Solution

Either resolve a plan-relative `--diff-file` against the plan directory (matching the SKILL.md capture pattern and the sibling `collect-fragments --fragment-file` flag, which DOES accept `work/...`), or **fail loudly** on a supplied-but-unresolvable path. Do not report `skip`.

Whichever is chosen, the SKILL.md capture pattern and the script must agree — today they do not, and the disagreement is silent in the direction of a clean result.

## Impact

On this retrospective the vacuous skip hid a genuine `mis_prune:sonar-roundtrip` failure: the lane dropped `sonar-roundtrip` as `no_code_delta` while the realized 19-path footprint touched production code. The check that exists to catch a mis-prune reported `skip` for a reason that had nothing to do with the prune.

Note the asymmetry that makes this hard to notice: `collect-fragments add --fragment-file work/fragment-X.toon` accepts the relative form, so a caller who successfully used the relative form on one flag in the same workflow has every reason to expect it on the next.
