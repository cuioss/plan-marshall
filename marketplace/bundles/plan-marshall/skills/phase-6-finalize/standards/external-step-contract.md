# External Finalize Step — Input & Termination Contract

The mechanics an external (`project:` / fully-qualified `bundle:skill`) finalize step honours: `--session-id` forwarding opt-in and the mandatory `manage-status mark-step-done` termination call. The phase-6-finalize `SKILL.md` § "Interface Contract for External Steps" points here for the full detail; the two step-type invocation templates (INLINE `Skill:` / DISPATCHED `Task:`) stay inline in the SKILL.

## Session-id forwarding

`--session-id {session_id}` is forwarded ONLY to external steps on the per-step opt-in whitelist below. The forwarding is opt-in (rather than universal) because some external steps may reject unknown flags; opting in keeps the contract additive for new dependencies without breaking existing steps.

| Whitelisted external step | Why it needs `--session-id` |
|---------------------------|------------------------------|
| `plan-marshall:plan-retrospective` | Aspect 12 (chat-history-analysis) is conditional on `--session-id`. Without it, the aspect is silently skipped and the retrospective report omits the chat-history section. See `plan-retrospective/SKILL.md` → "Input Contract" for the consumer-side declaration. |

`default:record-metrics` is intentionally NOT on this whitelist: it is a built-in step, dispatched via `standards/record-metrics.md`, which already consumes `--session-id` inline. The whitelist scope is project- and skill-type external steps only.

**How to apply** — when defining a new external step that consumes session-scoped state:

1. Declare `--session-id` as an input in the step's authoritative document (project step `SKILL.md` or fully-qualified skill `SKILL.md`/standards).
2. Add the fully-qualified step name to the whitelist table above.
3. Verify by running a finalize end-to-end and confirming the step does not hit a "session_id missing" code path.

The orchestrator is responsible for resolving `session_id` (see the SKILL "How to obtain session_id" section). This skill receives the resolved value via its Input Parameters and forwards it verbatim to whitelisted steps; it does not re-resolve.

## Required termination

Every external step (project and fully-qualified skill) MUST terminate with a `manage-status mark-step-done` call that carries `--display-detail "{one-line summary}"`. This is REQUIRED, not optional — a missing or empty `display_detail` causes renderer failure in Step 4 (the literal placeholder `<missing display_detail>` will surface to the user and contribute to a `[FAILED]` headline). The detail string is authored by the step itself; the renderer NEVER invents content on the step's behalf.

The full command template (use verbatim, substituting the placeholders):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step {step_name} --outcome {done|skipped|failed} \
  --display-detail "{one-line summary}"
```

MANDATORY annotations for every argument:

- `--phase` — MANDATORY. Always the literal string `6-finalize` for steps dispatched under this operation. This anchors the step record to the finalize phase; any other value routes the record into the wrong phase bucket and breaks the Step 4 renderer grouping.
- `--outcome` — MANDATORY. Must be exactly one of `done`, `skipped`, or `failed`. Any other value (including misspellings or capitalized variants) is rejected by `manage-status`. The choice determines the headline classification and CANNOT be inferred from `display_detail` alone.
- `--step` — MANDATORY. Pass the step's **composed manifest catalog key** — the key exactly as `manifest.phase_6.steps` catalogs it, NOT a name read off `marshal.json`. The `default:` prefix is normalised on write by the canonical step-key seam, so a built-in step lands on the same record whether authored bare (`push`) or prefixed (`default:push`). A `bundle:skill` id (e.g. `plan-marshall:automatic-review`) is **preserved verbatim** by that seam and therefore MUST be authored exactly as the manifest catalogs it — the normalisation cannot rescue a mis-authored bundle-prefixed key. A key the seam cannot reconcile creates an orphan status record that the renderer cannot pair with the dispatched step, which the dispatcher-side guard surfaces as `step_record_mismatched_key`.
- `--display-detail` — MANDATORY. Single-line summary of what the step actually did, authored by the step itself. Subject to the constraints listed below. A missing, empty, or whitespace-only value triggers the `<missing display_detail>` placeholder and contributes a `[FAILED]` headline regardless of the `--outcome` value.

**Notation:** the canonical 3-part notation is `plan-marshall:manage-status:manage-status` — every segment is kebab-case.

### Ordering invariant — record before returning

**The record-before-return invariant is NOT external-step-specific and is not owned here.** It binds every dispatched leaf, and its governing statement — the leaf-side obligation to record before composing the return, the dispatcher-side rule that a `status: success` return failing `assert-step-recorded --require-terminal` is a leaf-attributable contract violation rather than a reconcilable condition, and the `escalate_ask` carve-out as the single sanctioned non-terminal return — lives in [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md) § "Leaf must record its terminal outcome BEFORE composing its return". Read the invariant there; it is deliberately not restated in this document.

What remains external-step-specific is the **mechanics** of the call this document already specifies above: the `--step` composed-manifest-catalog-key contract and the `--display-detail` constraints. Those are the two places an external step's terminal call goes wrong in a way the shared invariant does not cover, and the dispatcher-side guard reports them distinctly — `step_record_missing` (no record at all: the shared invariant was violated) versus `step_record_mismatched_key` (a record exists under a key the canonical step-key seam could not reconcile: the `--step` contract above was violated).

**`display_detail` constraints:**

- ≤80 characters
- No trailing period
- No embedded newlines (single line only)
- Plain ASCII — no unicode glyphs
- Concrete and user-facing (describe what the step did, not how)

See [`output-template.md`](output-template.md#display_detail-contract-for-step-authors) for the full detail-string convention, ASCII icon rules, and concrete examples per built-in step.
