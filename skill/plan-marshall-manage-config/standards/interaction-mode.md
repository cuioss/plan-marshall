# Interaction Mode

How much plan-marshall tells the operator and asks the operator while work runs. The mode is a persisted top-level `marshal.json` scalar (`interaction_mode`: `basic` | `advanced` | `expert`, default `advanced`), chosen at first run (marshall-steward wizard-flow Step 6b) and re-selectable from the Configuration submenu ("Configuration: Interaction Mode"). Read via `manage-config interaction-mode get --field interaction_mode`; write via `manage-config interaction-mode set --field interaction_mode --value {mode}`.

Modes are described by **user experience**, never by system behaviour: what the operator sees and when they are interrupted. The mode never changes what gets built, which checks run, which model tier runs them (`effort`), or how branches land. Every behaviour below binds to a landed mechanism — the cited standard or verb is the authority, this mapping only selects among the postures those authorities already permit.

## Modes

| Mode | How it feels |
|------|--------------|
| `basic` | Short check-ins at the important moments. The operator reads phase-boundary status lines and is asked only when nothing can proceed without them. |
| `advanced` (default) | The full standard surface. Context where it matters, a question whenever a decision is genuinely the operator's. This is the behaviour every workflow doc describes today. |
| `expert` | Terse output for operators who drive with explicit overrides. The run assumes the operator already stated their intent up front and never circles back to re-ask it. |

## Prompt context volume

Prompt context is what the run carries into each decision — gathered answers, resolved defaults, and explicitly supplied overrides.

- `basic`: the run carries the minimum needed to proceed. Optional questionnaires resolve to their computed projection without asking (the `auto` posture of the init `lane_selection` gate: take the computed projection silently rather than surfacing the minimal/standard/full dialogue).
- `advanced`: the run gathers through the standard bounded escalations — the phase-2-refine iterate-to-confidence loop, the init posture dialogue, per-invocation coverage cells — exactly as each workflow doc describes.
- `expert`: the run carries operator-supplied overrides as authoritative input and does not re-derive them. The landed form is `manage-config domain-detect --domain-override`: an explicit domain bypasses the narrative scan entirely, so a run launched with its overrides stated never opens the question those overrides answer.

## Phase-boundary output volume

Phase-boundary output is what the operator reads when a phase starts, ends, or yields. Its lower bound is the completeness floor in [`persona-plan-marshall-agent/standards/user-communication.md`](../../persona-plan-marshall-agent/standards/user-communication.md): a boundary line states what the next decision needs — no less — and brevity applies only above that floor. No mode may print below the floor.

- `basic`: output sits on the floor — the canonical `[STATUS]` lines (phase entry, per-deliverable `[OUTCOME]`, terminal verdict) with no elaboration.
- `advanced`: the full standard surface — the same lines plus the context each workflow doc emits around them (what was decided, what is pending, what to run next).
- `expert`: floor-minimum prose plus the machine-readable payload where the surface already produces one (the terminal TOON blocks each phase returns), so an operator driving from scripts reads the structure, not the sentences.

## Borderline-gate ask-vs-proceed behaviour

A borderline gate is a point where the run could either ask the operator or proceed on a safe default: the planning gates (`deep_lane` / `escalation` / `revalidation`), the scope-deviation escalation (Hold the line / Accept with rationale / Split into follow-up plan), and the verification-feedback triage (FIX / SUPPRESS / ACCEPT).

- `basic`: gates that can proceed safely do — auto-continue where the contract permits it (`finalize_without_asking` / `loop_back_without_asking` posture), and a borderline finding resolves to its safe default without opening a question. The operator is asked only on a hard block: an `error`, a `blocked` task, or a triage signal no default can absorb.
- `advanced`: the standard bounded escalation — the operator is asked exactly where the workflow doc says a decision is genuinely theirs, and the run proceeds everywhere else.
- `expert`: gates resolve without asking by construction — the run requires the deciding input up front as an explicit override and fails closed when it is absent rather than opening a prompt. Ambiguity is an error naming the missing override, never a question.

## The retired domain prompt stays retired

Domain selection was once a prompt; it is now detection (`domain-detect` over the clarified narrative, the `always_on` leg, and the `file_globs` leg) with an explicit override (`--domain-override`) and a narrowing pass (`domain-narrow`). No mode restores the prompt: under `expert`, an ambiguous detection fails closed to the override demand above instead of asking which domain was meant. The mapping a mode selects is therefore always "detect, override, or fail closed" — never "ask".
