# Extension Point: Verify

> **Type**: Findings-Pipeline Stage Extension | **Hook Method**: producer `verification_profile` declaration | **Implementations**: 4 | **Status**: Active

## Overview

A verify extension declares a **finding-validity-verification** stage that runs in the [findings pipeline](../../ref-workflow-architecture/standards/findings-pipeline.md) BEFORE the domain-keyed [triage](ext-point-triage.md) stage. It is an optional, producer-declared, adversarial-refute pass: each finding a participating producer emits is challenged to confirm it is a genuine defect before triage ever sees it. Findings that survive refutation flow on to domain triage unchanged; findings the verify stage refutes as invalid (false positives) close with the new terminal resolution `rejected` — a non-pending state that never reaches triage and never blocks an invariant gate.

The stage is **opt-in per producer**: it runs only when a producer declares a `verification_profile`. A producer that declares no `verification_profile` keeps the legacy `producer → store → triage → gate` flow with no verify hop. When a producer declares one, the pipeline becomes `producer → store → VERIFY (ext-point-verify) → triage → gate`.

```text
                            BEFORE
  producer ──▶ store ──▶ triage (ext-triage-{domain}) ──▶ invariant gate

                            AFTER (when producer declares verification_profile)
  producer ──▶ store ──▶ VERIFY (ext-point-verify) ──▶ triage ──▶ invariant gate
                              │
                              └─▶ refuted finding ──▶ resolve --resolution rejected
                                  (non-pending; never reaches triage)
```

> **Not to be confused with [`ext-point-build-verify-step`](ext-point-build-verify-step.md)**, the phase-5 build/verify command step (`quality-gate`, `module-tests`, `coverage`). That extension point governs which build/verify *commands* run during phase-5-execute; this one governs validity-verification of *findings* before triage. They are unrelated concerns.

## Implementor Requirements

A verify implementor has two halves: a **producer** that declares it participates (the `verification_profile` declaration) and a **verify skill** that documents the adversarial-refute methodology the stage applies for that profile.

### Producer Declaration

A producer opts into the verify stage by declaring a `verification_profile`. The value is a profile key (e.g. `security`) that resolves to the verify skill applied to that producer's findings (see [Resolution](#resolution)).

Because the skill frontmatter schema is closed (see [`frontmatter-standards.md`](../../../../pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md)), a producer SKILL.md carries the declaration under the supported `metadata:` escape hatch:

```yaml
metadata:
  verification_profile: security
```

A producer that is a script (not a skill) declares the profile at its dispatch site / engine prose; the discovery record surfaces `verification_profile` whenever the field is present (see [Hook API](#hook-api)).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `verification_profile` | str | No | The verify-profile key the producer's findings are routed through. Absent → the producer does not participate in the verify stage. Present → every pending finding the producer emits passes through the resolved verify skill's adversarial-refute pass before triage. |

### Verify Skill

The skill that `verification_profile` resolves to MUST document the adversarial-refute methodology applied to candidate findings. The required sections:

| Section | Purpose | Content |
|---------|---------|---------|
| `## Refute Procedure` (or a `standards/adversarial-refute.md`) | How to challenge a candidate finding | The per-finding refutation steps: is the defect real and reachable, or a false positive? |
| `## Confirm vs Reject` | The decision rule | When a finding survives refutation (→ flows to triage) vs is refuted (→ `rejected`) |
| Cross-reference to `ext-point-verify.md` | Contract linkage | The verify skill names this contract as the interface it implements as a verify profile |

The verify skill is loaded in-context by the orchestrator's verify pre-stage; it is LLM-driven knowledge, not a Python hook.

## Runtime Invocation Contract

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `finding` | dict | Yes | The pending finding under verification (`type`, `file`, `line`, `message`, `severity`, `hash_id`) |
| `verification_profile` | str | Yes | The producer-declared profile key driving the verify-skill resolution |
| resolved verify skill | skill | Yes | The verify skill `verification_profile` resolves to, loaded in-context for the refute pass |

### Pre-Conditions

- The finding's producer declared a `verification_profile` (producers without it skip the stage)
- The verify skill resolves and is loadable from the `verification_profile` value
- The producer-side stage has run: findings are stored and `pending` in `manage-findings`

### Post-Conditions

- Each finding gets a verify verdict: **confirmed** (flows to triage unchanged) or **refuted** (closed `rejected`)
- A refuted finding is resolved via `manage-findings resolve --resolution rejected` (and its Q-Gate twin via `manage-findings qgate resolve --resolution rejected`) — terminal and non-blocking; it does not contribute to the invariant gate's blocking count and never reaches triage
- A confirmed finding is left `pending` so the existing triage stage picks it up unchanged
- Decisions are logged to `decision.log`

### Lifecycle

```text
1. Producer stage: producer emits findings via manage-findings add; producer
   declares verification_profile (under metadata:) when it participates.
2. Verify pre-stage (gated on verification_profile being present on the producer):
   a. Query pending findings for the producer (manage-findings list --resolution pending)
   b. Resolve the verify skill from verification_profile
   c. Load Skill: {resolved verify skill}
   d. For each pending finding: run the adversarial-refute pass
   e. Refuted → manage-findings resolve --resolution rejected (never reaches triage)
      Confirmed → leave pending (falls through to step 3)
3. Triage stage (ext-triage-{domain}): decides FIX / SUPPRESS / ACCEPT on the
   surviving confirmed findings — unchanged by the verify stage.
4. Invariant gate: rejected findings are non-pending and do not block.
```

The verify pre-stage is inserted by the orchestrator's [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) workflow between the producer query and the ext-triage handoff; [`triage.md`](../../plan-marshall/workflow/triage.md) gains only a cross-reference noting refuted findings may already be closed `rejected` before the FIX/SUPPRESS/ACCEPT loop runs. See [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) for the full producer→store→verify→triage→gate flow.

## Hook API

A verify participation is not a Python hook method on `ExtensionBase` — it IS the `verification_profile` field on the producer. Discovery flows through the reusable `extension_discovery.find_implementors()` / record-parse machinery: the implementor-record builder surfaces `verification_profile` in the parsed record when the producer declares it, so a consumer can enumerate which producers participate and with which profile.

```python
# find_implementors / record parse surfaces verification_profile when declared:
{
    'name': ...,
    'verification_profile': 'security',   # present only when the producer declared it
    'source': ...,
    'path': ...,
}
```

A producer that omits `verification_profile` yields a record without the key — the absence is the signal that the producer does not participate in the verify stage.

## Resolution

The `verification_profile` value resolves to the verify skill applied to the producer's findings. Resolution is performed by the orchestrator's verify pre-stage when it loads the verify skill: the profile key names the methodology to apply (e.g. `security` → the `persona-security-expert` adversarial-refute standard).

```text
verification_profile: security
        │
        ▼
  persona-security-expert/standards/adversarial-refute.md  (the verify skill)

verification_profile: quality
        │
        ▼
  persona-code-reviewer/standards/adversarial-refute.md    (the verify skill)
```

The `quality` profile is the code-review counterpart to `security`: it resolves to the `persona-code-reviewer` adversarial-refute standard, which refutes candidate quality/structural/documentation findings with quality lenses (defect vs preference, surplus vs load-bearing, drift vs already-correct) in place of the security lenses.

Unlike triage's `resolve-workflow-skill-extension` config lookup, the verify-profile resolution is a knowledge resolution carried out in the LLM-driven verify pre-stage: the profile key selects the verify skill the orchestrator loads in-context. There is no separate config-registration step for the profile beyond the producer's `verification_profile` declaration and the verify skill's existence.

## Current Implementations

| Producer | verification_profile | Verify Skill |
|----------|----------------------|--------------|
| `recipe-security-audit` | `security` | `persona-security-expert` (adversarial-refute) |
| `recipe-code-review` | `quality` | `persona-code-reviewer` (adversarial-refute) |
| `recipe-simplify-codebase` | `quality` | `persona-code-reviewer` (adversarial-refute) |
| `pm-documents:recipe-doc-verify` | `quality` | `persona-code-reviewer` (adversarial-refute) |

Security-audit is the pilot consumer: its engine declares the `security` verification_profile, and findings it emits pass through the `persona-security-expert` adversarial-refute pass before domain triage. The three `quality`-profile producers — `recipe-code-review`, `recipe-simplify-codebase`, and `pm-documents:recipe-doc-verify` — are the LLM-reasoning quality/structural/documentation finding producers; each declares `verification_profile: quality` so the findings it emits pass through the `persona-code-reviewer` adversarial-refute pass before domain triage. Findings the refute pass invalidates close `rejected`; confirmed findings flow to `ext-triage-*` unchanged.

## Related Specifications

- [ext-point-triage.md](ext-point-triage.md) — Triage extension point; the consumer-side stage the verify stage runs BEFORE
- [ext-point-build-verify-step.md](ext-point-build-verify-step.md) — Phase-5 build/verify command step (a distinct, unrelated extension point)
- [findings-pipeline.md](../../ref-workflow-architecture/standards/findings-pipeline.md) — The producer→store→verify→triage→gate pipeline this stage extends
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference
