# Menu Option: Display Timezone

Inspect and change the IANA zone plan-marshall renders operator-facing timestamps in. The setting is a
single top-level field in the run-configuration store, and it answers exactly one question: in which
zone should an already-recorded instant be *shown*.

The binding is **machine-local**. Which zone a timestamp reads best in is a property of the operator
sitting in front of the terminal, not of the project, so it persists to the git-ignored, main-anchored
`run-configuration.json` beside the `language_servers` and `derivation_resolvers` bindings rather than
in a version-controlled project file. Two developers on the same repository can legitimately render
the same artifact in different zones.

⛔ **This is a display-only setting — it changes nothing that is stored or compared.** Timestamps are
written and compared in UTC unconditionally, and a stored timestamp is byte-identical under any
`display_timezone` value. Changing the zone does not re-stamp, migrate, or rewrite a single artifact;
it changes how the next render reads. Never present it to the operator as "switching the project to
{zone}" — nothing moves.

An unconfigured project renders in `UTC`, which makes the unset behaviour byte-identical to the
pre-knob rendering.

See
[`../../manage-run-config/standards/run-config-standard.md`](../../manage-run-config/standards/run-config-standard.md)
§ "Display-Timezone Section" for the schema, the default-resolution rules, and the display-versus-storage
boundary (which a guard test enforces).

## Reachability

Reachable from the marshall-steward **Configuration** menu (Main Menu → "3. Configuration" → "More..."
→ "More..." → "More..." → "Display Timezone"). Like every other Configuration entry it is not gated
behind first-run setup.

---

## Step 1: Read the current value

Read the stored zone. This is the **only** source for what the menu displays — never report a zone
from memory, from the host's local time, or from a value written into a document:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config display-timezone get
```

The response carries `field: display_timezone` and `value` — the effective zone.

⚠ **`get` never reports "unset".** An absent field, a non-string value, and a stored zone that no
longer loads all resolve to `UTC`, so a `value` of `UTC` means *"UTC is what will be rendered"*, not
*"the operator chose UTC"*. Present it as the effective render zone; do not claim the operator picked
it.

## Step 2: Present the current value and offer the actions

Report the effective zone, and state alongside it what it governs — rendering only — so the operator
is not left to infer that changing it rewrites anything.

Then offer the actions:

```text
AskUserQuestion:
  question: "What would you like to do with the display timezone?"
  header: "Display Timezone"
  options:
    - label: "Set the timezone"
      description: "Render timestamps in a different IANA zone (display only)"
      value: "set"
    - label: "Reset to UTC"
      description: "Return rendering to the UTC default"
      value: "reset"
    - label: "Back"
      description: "Return to the Configuration menu"
      value: "back"
```

On `set`, ask for the zone as an IANA name (for example `UTC`, `Europe/Berlin`,
`America/New_York`). Pass whatever the operator supplies straight to the verb — the verb validates it.
Do NOT pre-screen the name against a list written here: a hand-maintained zone list would go stale
against the host's own zone database, and the verb already rejects a name that does not load.

## Step 3: Apply the change

| Selection | Command |
|-----------|---------|
| set | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config display-timezone set --value {zone}` |
| reset | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config display-timezone set --value UTC` |
| back | Do nothing → Return to the Configuration menu |

A `--value` that is not a loadable IANA zone returns the standard `invalid_value` error response and
**persists nothing**. Surface that error to the operator with the rejected name and re-ask; do not
fall back to a guessed zone and do not report the change as applied.

## Step 4: Confirm the round-trip

After a change, re-read the value (Step 1) and confirm it is what was just set. **Report the re-read
value, not the value that was written** — the write reporting success is a claim, and the re-read is
the outcome.

Then return to Step 2 so a further change can be made without leaving the menu.

---

## What this menu does NOT configure

- **What time anything happened.** The zone is applied at the render, so it moves the *label*, never
  the instant. Two renders of one artifact in two zones name the same moment.
- **How timestamps are stored or compared.** Record fields (`created`, `removed_at`, `set_at`),
  lesson identifier prefixes, retention and quiet-window cutoffs, CI/build durations, staleness
  checks, and every ordering key stay UTC unconditionally. A guard test scans the bundles and fails if
  any store-or-compare site consults `display_timezone`, so this boundary is enforced rather than
  merely intended.
- **The host's own clock or `TZ`.** The setting is read from the run-configuration store; it neither
  reads nor writes the operating system's timezone, and an operator who changes one has not changed
  the other.
- **Whether a converted timestamp is labelled.** It always is: a render in a non-UTC zone carries an
  unambiguous `ABBREV (UTC±HH:MM)` label so both the zone and the exact instant stay recoverable. An
  unlabelled converted timestamp is never emitted, and that is not switchable here.
