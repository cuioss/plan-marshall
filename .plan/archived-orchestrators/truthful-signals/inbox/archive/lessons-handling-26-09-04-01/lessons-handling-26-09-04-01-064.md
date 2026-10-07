envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T16:13:40Z

component=plan-marshall:manage-config
category=bug

# sync-defaults back-fills a verify step the operator removed: keyed step maps cannot record a deliberate removal

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-15 (PR cuioss/TokenSheriff#745,
merged `833cbf09`, 2026-09-15). The orchestrator checked the mechanism against plan-marshall source
before relaying.

## Observation

Token-Sheriff decided that module-wide coverage belongs to the central SonarCloud new-code gate and
not local builds. It removed `default:verify:coverage` from `plan.phase-5-execute.verification_steps`
using the sanctioned verb:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-5-execute remove-step \
  --step default:verify:coverage
```

A subsequent `manage-config sync-defaults` (plan-marshall 0.1.1670) reported
`added: plan.phase-5-execute.verification_steps.default:verify:coverage` (added_count 1), and
`.plan/marshal.json` reverted byte-for-byte to its pre-removal state.

## Mechanism (read in source)

- `skills/manage-config/scripts/_config_defaults.py:747` `_seed_verify_steps()` seeds every
  discovered built-in verify-step id, `coverage` included.
- `skills/manage-config/scripts/_cmd_sync_defaults.py:255` `_deep_merge_missing` recurses into
  dicts and back-fills every key absent from live config. `verification_steps` is a dict (keyed
  step map), so an absent step id counts as "missing default", never as "removed on purpose".

So `remove-step` and `sync-defaults` contradict each other: the first verb's result is undone by the
second, and `/marshall-steward upgrade` runs the second.

## Why it matters

- A deliberate operator decision is silently reverted by routine maintenance. The only trace is a
  `.plan/marshal.json` diff inside a steward-refresh PR, where it is easy to approve unread.
- The same shape applies to phase-6-finalize `steps` (also a keyed step map with a seed), so any
  finalize step an operator removes has the same problem.
- Related class, different field: a known Token-Sheriff gotcha where the steward upgrade silently
  discarded legacy `enabled_bots` because `sync-defaults` runs first. That is two instances of
  `sync-defaults` overriding operator intent on a list or map field.

## Candidate direction

- Do not deep-merge into keyed step maps. Treat `verification_steps` / `steps` as atomic once
  present, like lists, and seed them only when the whole map is absent; **or**
- Have `remove-step` record a tombstone or opt-out (e.g. `"default:verify:coverage": false`, or a
  sibling `removed_steps` list) that `_deep_merge_missing` honours; **and**
- Add a regression test: `remove-step X` → `sync-defaults` → X still absent.
