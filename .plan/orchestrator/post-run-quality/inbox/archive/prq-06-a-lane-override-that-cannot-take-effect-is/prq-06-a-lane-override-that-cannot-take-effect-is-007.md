envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:41Z

component=plan-marshall:manage-architecture
category=improvement
confidence=medium
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=script_failure_analysis

# architecture search has no path scoping, and callers keep inventing it

## Context

`script-failure-analysis` recorded 26 argparse rejections across 16 unique signatures in this plan. The single most repeated one, by a wide margin, is:

```
anti-pattern, invented_flag, plan-marshall:manage-architecture:architecture,
  search, exit 2, occurrence_count: 8
```

Eight rejections of one verb in one plan. The verb's actual flag surface is narrow:

```
architecture search [-h] --content --pattern PATTERN
                    [--category CATEGORY] [--literal] [--ignore-case]
```

There is no way to say *where*. A caller who wants "find this string under `marketplace/bundles/plan-marshall/skills/manage-config`" can express the string and not the location, so it reaches for `--module`, `--path`, or `--glob` — none of which exist — and is rejected.

## Root cause

`architecture search --content` is the project's mandated first choice for content search (hard rule: "Structured queries first"), and in a dispatched leaf `Grep`/`Glob` may not even be granted, so there is frequently no fallback. A first-choice tool that cannot scope its own search is going to be called with an invented scoping flag, repeatedly, by every caller that needs one.

`--category` exists but is a taxonomy filter, not a path filter, so it does not answer the question callers are actually asking.

## Proposed action

Add a path-scoping flag — `--path-prefix` or `--under` — restricting the content sweep to inventory entries beneath a given path, and name it in the `search` help text so the discoverable surface matches the need. Reusing the `--pattern` spelling from `architecture find` (`--path-pattern`) would keep the two verbs' vocabularies aligned.

Until that lands, the `search` help output should name the absent capability explicitly ("no path scoping; combine with `architecture find` or filter the result set"), so the eighth caller does not rediscover it by rejection.

## Evidence

- aspect: script_failure_analysis — `invented_flag` against `architecture search`, `occurrence_count: 8`, first at `2026-09-18T15:20:41Z`
- live `architecture search --help` — flag set is `--content --pattern [--category] [--literal] [--ignore-case]`
- `script_cost_rollup` — `manage-architecture:architecture` is the 4th-costliest script in the plan at 116 calls / 948,790 ms
