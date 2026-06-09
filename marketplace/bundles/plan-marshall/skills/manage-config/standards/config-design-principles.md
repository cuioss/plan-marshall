# Config Design Principles

Governance rules for what belongs in `marshal.json` and how config fields change.
These rules govern every addition, removal, relocation, and rename of a config
field across `manage-config` defaults, the CLI accessor surface, and the committed
`.plan/marshal.json`.

## Framing — plan-marshall has two roles

Most config defects are a confusion between the two roles plan-marshall plays:

1. **The tool that seeds every consumer project's config.** `DEFAULT_PROJECT`,
   built from the `DEFAULT_*` constants in shipped marketplace code, is
   materialised into each consumer's `marshal.json` at `init`. Anything seeded
   here ships to every consumer.
2. **One consumer itself**, with its own committed `.plan/marshal.json` tracked in
   git.

Rules 1 and 2 are the two ownership-boundary failure modes (foreign-system config
vs the meta-project's own convention). Rule 5 is placement; Rule 6 is
anti-speculation; Rule 3 is the change mechanics. The new-input-shape validator
mechanic (formerly "Rule 4") lives with the script-authoring standards — see
[`pm-plugin-development:plugin-script-architecture`](../../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md)
§ "New get/set input shape must pass its own validator".

## Rule 1 — Tool vs foreign system: store a foreign value only if the user may legitimately diverge from it

A field belongs in `marshal.json` only if it encodes a decision plan-marshall (or
its operator) actually **owns**. Two escalating failure modes make a field a
violation:

1. **Derivable mirror.** The stored value is computable from a real choice already
   held elsewhere. Storing it redundantly is a pure drift surface.
2. **Foreign-owned config (the deeper defect).** The value belongs to another
   system entirely — copying it drags that system's config into plan-marshall's,
   a scope-ownership leak.

**The test is whether divergence is valid, not whether it is a mirror.** A field
that *seeds* from a foreign system but that the user may legitimately set to a
different value is a valid overridable knob — keep it, seeded from the foreign
source as a default. The defect is a mirror the user may NOT diverge from: where
the only valid value *equals* the foreign source, so it is a fake choice and a
pure drift surface.

When divergence is invalid, encode your *narrow constraint* against the foreign
system, never a copy of its config, and never the foreign system's own entries.
When divergence is valid, seed-and-allow-override is the correct, legitimate
pattern.

| Outcome | Test result | Action |
|---------|-------------|--------|
| Overridable seed | A user can legitimately set a different value AND a consumer reads the override (e.g. `providers[].verify_command`, a CI wait-timeout) | Keep as config, seeded from the foreign source as a default |
| Fake choice | A structural rule enforces *equality* with the foreign source, so no independent value is valid | Remove the stored copy; derive the narrow constraint instead |
| Refactor litter | Looks overridable but has no read-path | Remove as dead data — a "kept because adaptable" field with no reader is dead, not adaptable |

**Caveat — retired keys linger.** Retiring a config key drops it from defaults and
code, but nothing prunes the orphan from already-written instance `marshal.json`
files (`sync-defaults` only adds keys). Retired keys survive as stale data until
deleted in-place.

## Rule 2 — Tool vs the meta-project's own convention: never ship your house rules to consumers

Because plan-marshall seeds every consumer's config (and ships every consumer's
skills), a value or rule that is really *plan-marshall's own convention* leaks into
every consumer the moment it is shipped — whether as a `DEFAULT_*` constant, a
runtime behaviour, or a "universal" invariant.

Two distinct defects compound when a house rule is shipped:

1. **The default leaks the meta-project's layout.** A path or value specific to
   plan-marshall's own repo seeds every consumer's config, so every consumer
   inherits plan-marshall's layout.
2. **The RULE itself is plan-marshall's opinion, not a universal truth.** A
   convention plan-marshall adopts for its own repo is shipped as if it were a
   mechanical fact of the underlying tool.

**Three tiers, do not conflate them:**

| Tier | Definition | Shipping policy |
|------|------------|-----------------|
| 1 — Universal truth | A mechanical fact of the underlying tool | Ship freely |
| 2 — Meta-project's own convention | A house rule plan-marshall adopts for its own repo | Ship only as advisory prose; enforce only in the meta-project's own non-shipped tests |
| 3 — Consumer's own choice | A consumer's project-specific decision | Let the consumer own it — never seed or enforce it |

The recurring defect is **tier 2 masquerading as tier 1 or 3**: a house rule
shipped as a `DEFAULT_*` seed or a runtime invariant, imposed on every consumer.

## Rule 3 — A field migration moves BOTH the read-path AND the values, losslessly

When a plan relocates, renames, or removes a config field, the deliverable surface
is not just the writer that moves the data — it is every CLI accessor and runtime
consumer that reads it.

Apply, in the SAME task that deletes the old field:

1. Ship the `get` read-path for the NEW location.
2. Grep the codebase for the OLD field names to find every read-site before
   deleting them.
3. Migrate the VALUES, not just the schema. When the committed `marshal.json`
   overrides a default, carry that override forward — a move-block operation that
   resets to the default instead of preserving the committed override is a silent
   value-flip.
4. Add a read-back assertion (call the new accessor, compare the result against the
   original value) to the migration task's success criteria.

## Rule 5 — Placement: a tool's intrinsic property vs workflow policy about using the tool

- **A tool's intrinsic property** — lives with the tool's provider/skill.
- **Workflow policy about using the tool** — lives with the phase/step that applies
  it.

A wait-timeout consumed by the finalize step is a finalize wait-policy, not the
CI provider's config: it belongs under the owning phase (`plan.phase-6-finalize`),
while the low-level tool stays dumb (honours a `--timeout` flag plus a hard
fallback) and the phase reads the policy and *passes* it down.

## Rule 6 — Don't ship a generalization before its second concrete case

A generalization built before a second case exists is YAGNI: it ships unused,
carries validation/test/doc surface, and is **removal-worthy by default**. A
condition-scoped policy engine or override layer introduced empty — with no
populated case driving it — is the worked example of this defect.

## Related

- [`pm-plugin-development:plugin-script-architecture`](../../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md)
  § "New get/set input shape must pass its own validator" — the change-mechanics
  companion governing the validator boundary for a new get/set input shape.
- [`data-model.md`](data-model.md) — the `marshal.json` field inventory these
  principles govern.
- `recipe-marshal-json-config-audit` — the audit recipe that enforces these
  principles across a live `marshal.json`.
