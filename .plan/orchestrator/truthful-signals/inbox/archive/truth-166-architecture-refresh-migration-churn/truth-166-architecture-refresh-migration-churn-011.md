envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:36:47Z

component=plan-marshall:manage-architecture
category=bug
confidence=high
rank=11
source_plan=truth-166-architecture-refresh-migration-churn

# A tolerant read is void when a stricter read of the same artifact runs first on the same path

## Context

`_read_pre_state` deliberately tolerates an unparseable `enriched.json`: it records the
document's bytes so the delta classifier can return `CLASS_UNCLASSIFIED`, and the selective
`--apply` modes can then report `undecidable` and write nothing — a documented,
deliberately honest outcome.

The regeneration loop then re-reads the same file through
`load_module_enriched_or_empty`, whose `_read_json` is a bare `json.load`. It raises before
`classify_delta` is ever called. So the tolerant recording is never consumed for a
malformed document, the documented `undecidable` / write-nothing outcome is unreachable,
and `classify_delta`'s `pre.unreadable_documents` branch is a guard no production input can
enter.

Fixed in-run as TASK-10, after CodeRabbit reported it (`e87384`, Major).

## Root cause

The tolerance and the strictness are two reads of ONE artifact on ONE path, and the order
decides. The tolerant read is first in the file and reads as the component's policy; the
strict read is downstream and is the policy that actually applies. Nothing in the tolerant
read's own vicinity reveals that it is void — the recorded bytes, the dedicated
`CLASS_UNCLASSIFIED` class, and the documented `undecidable` verdict all look live.

The same file's classification vocabulary carried a second outcome that production cannot
act on, which is corroborating rather than the same defect: a module with a readable
document but no `_project.json.modules` entry also lands in `CLASS_UNCLASSIFIED`, so
`--apply plan` refuses on `undecidable` and the missing entry can never be repaired —
reachable through the sanctioned path where `sync_module_index` no-ops on an absent
`_project.json` (finding `8afb08`, Major, fixed as TASK-11). Two of the vocabulary's
outcomes were authored without a pass asking which production input reaches them.

## Proposed action

For any artifact a component reads more than once on one path, assert that the reads agree
on strictness — or that the tolerant read's recorded state is consumed before the strict
read can raise. The detector is cheap and mechanical: enumerate the read sites for one
artifact within a code path and compare their failure modes. A tolerant site upstream of a
strict site is the signature.

Pair it with the reachability pass the second instance argues for: for every documented
outcome in a classification vocabulary, name the production input that produces it. An
outcome with no such input is either dead or a missing repair path.

## Evidence

- finding `e87384` — `_cmd_manage.py:843`; "`load_module_enriched_or_empty`, whose strict
  `_read_json` raises before `classify_delta` runs".
- finding `8afb08` — `_descriptor_delta.py:325`; the second unreachable-in-effect outcome
  in the same vocabulary, reachable via a sanctioned path and unrepairable once reached.
- Both were Major, both confirmed against the code rather than the phrasing, and both were
  missed by four in-house self-review rounds, a clean whole-tree `plugin-doctor` and a
  green `verify`.

## Relationship to message 001

Message 001 reports the INVERSE pole of the same failure: a could-not-look branch that
fires on every invocation because the field it tests for has no writer. Its detector is
"a reader-only field". This one's detector is "a tolerant read preempted by a strict read
of the same artifact". Both are branch-reachability never checked against production
inputs — 001 always-fires, this one never-fires — so the epic may prefer to hold them as
one archetype with two detectors. Filed separately because the detectors share no
mechanism and each is independently runnable.

## Generalizes

Honesty machinery is only as live as the path that reaches it. A component can carry a
recorded error state, a dedicated classification for it, and a documented write-nothing
verdict, and still be unable to enter any of the three — and every one of those artifacts
reads as evidence that the case was handled.
