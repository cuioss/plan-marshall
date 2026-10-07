envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:41:10Z

component=plan-marshall:manage-status
category=bug
title=planning-lane routed deep on S7:risk_prose, a signal the documented S1-S6 table omits
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing

# planning-lane routed deep on S7:risk_prose, a signal the documented S1-S6 table omits

## Context

`decision.log` 33be14 records this plan's lane routing:

```
Routed planning_lane=deep (predicate=signal_set, fired=['S7:risk_prose'], ceremony.deep_lane=auto,
execution_profile=minimal, signals={'plan_source': None, 'scope_estimate': 'surgical',
'change_type': None, 'compatibility': None, 'request_concrete': True, 'risk_prose': True,
'planning_lane_override': None})
```

`manage-status/SKILL.md` § `planning-lane` documents the signal set as exactly six rows: S1 `plan_source`, S2 `scope_estimate`, S3 `change_type`, S4 `compatibility`, S5 request concreteness, S6 explicit override. There is no S7 and no mention of `risk_prose` anywhere in the documented table.

`S7:risk_prose` was the **sole** fired signal. Every documented signal evaluated to light: `scope_estimate` was `surgical` (→ light), `change_type` and `compatibility` were unset, `request_concrete` was `True` (→ light), and there was no override. So this plan's entire deep-lane routing — and the `complex` track, the level-5 dispatch tier, and the deep-lane discovery cost that followed from it — rests on a signal that no reader of the documentation knows exists.

## Root cause

A signal was added to `_cmd_planning_lane.py`'s scoring without a corresponding row in the SKILL.md signal table. The table is presented as the complete enumeration of the predicate's inputs ("the signal set (`deep` IFF any deep-precondition fires)"), so its incompleteness is invisible at the point of reading — an operator reasoning about why a plan went deep would work through S1-S6, find all six pointing light, and conclude the router misfired.

The routing itself was arguably correct: the request narrative does carry risk prose. The defect is that the decision is unauditable against the published contract.

## Proposed action

- Add the S7 `risk_prose` row to the `manage-status/SKILL.md` planning-lane signal table with its source, its trigger condition, and its light/deep polarity — matching the format of S1-S6.
- Add a derivation guard asserting set equality between the documented signal rows and the signal keys the router actually scores, so the next added signal fails the gate until documented.
- Re-check the same table's claim that the projection is over "the SAME signals" for `execution_profile` — the projected posture was `minimal` while the lane went `deep`, which is consistent with the documented independence but is worth confirming against S7's participation.

## Evidence

- aspect: routing-decisions — `planning_lane: deep`, `posture: standard`, lane recorded with `fired=['S7:risk_prose']`
- aspect: log_analysis — `decision.log` 33be14 carries the full signals dict including the undocumented `risk_prose` key
- source: `manage-status/SKILL.md` § planning-lane signal table documents S1-S6 only
