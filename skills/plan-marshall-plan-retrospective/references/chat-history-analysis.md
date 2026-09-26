# Aspect: Chat History Analysis

**Conditional**: only dispatched when `--session-id` is present.

Complements log-analysis with conversational context — user pivots, mid-plan clarifications, permission prompts, and loop-backs. Hybrid: the deterministic `extract-chat-signal.py` pre-pass reduces the raw transcript to its signal-bearing turns (a fact), and the LLM then synthesizes the analysis fragment from that reduced transcript.

The session transcript itself, its resolution, and its format are owned by the platform-runtime `chat extract-signal` operation — that op's record schema and the reduction's operator-provenance and gated-decision contracts are specified in `platform-runtime/standards/contract.md` § `chat extract-signal`, and are NOT restated here. This skill never resolves or reads a session JSONL; it passes a `session_id` to the op and routes on the op's normalized record.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

**Documented step-level exception — `extract-chat-signal.py run`.** That standard's general
disposition for a zero exit with a non-`success` status is to STOP. This document's pre-pass is
an explicit exception to it, and the exception is the whole Tier-2 mechanism: `extract-chat-signal.py`
returns `status: skipped` with `reason: transcript_unavailable` at exit 0 when the runtime op
declines to reduce, and the orchestrator MUST **continue** on that return and route it into
[Tier 2 — graceful skip](#two-tier-degradation-path), forwarding the emitted `reason` verbatim per
the [Skip-Reason Token Contract](#skip-reason-token-contract). Treating it as a STOP would abort the
retrospective on the one input the two-tier path exists to degrade over. The exception covers
`status: skipped` from this one call ONLY — a `status: error` from it, and any non-`success` status
from any other call in this document, keeps the standard's STOP disposition unchanged.

## Input Resolution

This skill does **not** construct a transcript path and does **not** perform file discovery. Raw session transcripts are routinely multi-megabyte JSONL, and feeding the raw file to the LLM analysis prompt would blow the read budget on tool-output noise; the runtime op owns the reduction. The orchestrator therefore runs the `extract-chat-signal.py` signal-extraction pre-pass against the recorded `session_id` BEFORE deciding which tier applies — see [Two-Tier Degradation Path](#two-tier-degradation-path) below. The pre-pass forwards the runtime's reduction and returns the flags (`no_signal`, `over_budget`) that select Tier 1 (full analysis) vs Tier 2 (graceful skip).

## Two-Tier Degradation Path

The aspect resolves to exactly one of two tiers, gated by the `extract-chat-signal.py` pre-pass output:

| Tier | Trigger | Aspect behaviour |
|------|---------|------------------|
| **Tier 1 — full analysis** | The transcript carried operator-authored signal AND the reduced text fits the read budget: `no_signal == false` AND `over_budget == false`. | Feed the reduced transcript (`reduced_transcript`) to the LLM analysis prompt and synthesize the `chat_history_analysis` fragment with `status: success` per the [TOON Fragment Shape](#toon-fragment-shape) below. |
| **Tier 2 — graceful skip** | The transcript is missing, carried no operator-authored signal, OR the reduced transcript still exceeds the read budget (default 2 MiB / `2 * 1024 * 1024` bytes). | Do NOT feed any transcript to the LLM. Emit a fragment with `status: skipped` and the canonical skip-reason token per the [Skip-Reason Token Contract](#skip-reason-token-contract), plus a `severity: warning` finding so the skip is visible in the compiled report. |

The pre-pass is the single decision source — the orchestrator never inspects a raw file size directly. The `extract-chat-signal.py run --session-id {id} [--read-budget-bytes N]` invocation returns:

- `no_signal` — `true` when the transcript carried **no operator-authored signal of either kind**: `operator_turn_count == 0` AND `gate_decision_count == 0`. It is deliberately **not** a count of survivors (the runtime derives it from operator-authored counts; see the contract's § "The operator-provenance predicate").
- `over_budget` — `true` when the **delivered** text exceeds `--read-budget-bytes` (default 2 MiB). This is derived by the **consumer**, and ⛔ it is derived from `reduced_transcript_delivered_bytes`, **never** from the forwarded `reduced_bytes`. The budget governs what will actually be read, and only the delivered figure measures that.
- `reduced_bytes` / `reduced_transcript_delivered_bytes` — two figures describing **different things**, published side by side so neither can stand in for the other. `reduced_bytes` is forwarded verbatim from the runtime and describes the bytes its reduction PRODUCED; `reduced_transcript_delivered_bytes` is the UTF-8 size of the `reduced_transcript` the pre-pass actually EMITS. They agree in the ordinary case — a block scalar round-trips verbatim — and the gap between them is itself the signal when they do not. A budget decision taken on the forwarded figure is a verdict about a payload the consumer never received, which is exactly what it used to be.
- `reduced_transcript` — the Tier-1 input, emitted as a `key: |` block scalar (see [Multi-line serialization](#multi-line-serialization-binds-producers-and-fragment-authors-alike)). It is fed to the LLM only when both flags are `false`; it is **not** empty whenever they are not. A transcript with no operator signal can still retain marker-bearing `assistant` turns, so a Tier-2 skip may carry a non-empty reduction. The flags decide the tier — never the emptiness of this field.
- `raw_turn_count` / `reduced_turn_count` / `dropped_turn_count` — the parseable-turn count before reduction, the raw turns kept, and how many the reduction removed, so the caller can see how much was boilerplate. `reduced_turn_count + dropped_turn_count == raw_turn_count` holds; recovered gate decisions were never raw turns, so they appear as extra entries in `reduced_transcript` and are counted by `gate_decision_count` alone.
- `operator_turn_count` / `gate_decision_count` — the two operator-signal counters, reported separately from the survivor count so a caller can tell *"kept 200 turns, 3 operator-authored"* from *"kept 200 operator turns"*. `operator_turn_count` counts free-form operator corrections; `gate_decision_count` counts operator decisions recovered from the tool-result channel.

Either flag being `true` is the Tier-2 trigger. When BOTH are `false`, `reduced_transcript` is the Tier-1 input to the LLM prompt. The 2 MiB read budget is the canonical threshold and is owned by this skill's script (`DEFAULT_READ_BUDGET_BYTES`); this document references it, it does not re-declare it.

## Skip-Reason Token Contract

Tier 2 emits a `reason` token that downstream retrospective aggregation MUST key on to distinguish *why* the aspect was skipped. The two canonical tokens carry distinct semantics — a **deliberate, size-driven skip** (`transcript_too_large`) versus a **genuine absence of session data** (`transcript_unavailable`) — and aggregation MUST NOT collapse them into one bucket. Two canonical tokens exist:

| Token | Emitted when | Semantics for aggregation |
|-------|--------------|---------------------------|
| `transcript_too_large` | The pre-pass returned `status: success` AND (`over_budget == true` OR `no_signal == true`) — a transcript was present and read, but the reduced signal was empty or still over budget. | The chat-history aspect was **intentionally skipped** because the session was too large to analyse within budget. Aggregation MUST treat this as "analysis withheld by design", NOT as "this plan had no conversational signal". A retrospective corpus scan counting plans-with-chat-analysis MUST exclude `transcript_too_large` skips from the denominator of "plans that genuinely lacked a session", and MUST NOT infer a quiet/uneventful session from the skip. |
| `transcript_unavailable` | The pre-pass returned `status: skipped` with `reason: transcript_unavailable` — the runtime op declined to reduce (its `transcript_not_found` no-op, forwarded as this token) or returned an error. | The session JSONL was **absent** — a genuine data absence, not a size-driven skip. Aggregation treats this as "no transcript existed for this plan" (e.g. a plan run without a captured session id, or an archived plan whose transcript was not retained). |

**Discriminator (normative, checkable)**: the orchestrator MUST key the token on the pre-pass's own `status` field, NOT on the `no_signal` flag alone. The unavailable path returns `status: skipped, reason: transcript_unavailable` while ALSO setting `no_signal: true` (no signal was measured, so it recorded none), so `no_signal == true` is NOT sufficient to select `transcript_too_large`. The rule is: when the pre-pass returns `status: skipped`, forward its emitted `reason` verbatim (`transcript_unavailable`); only when it returns `status: success` does the orchestrator apply the `over_budget == true OR no_signal == true` → `transcript_too_large` mapping. Equivalently: `transcript_unavailable` means no bytes were read; `transcript_too_large` means bytes were read and deliberately set aside. Cross-plan aggregation (e.g. the `audit-archived-plan-retrospectives` corpus checks) MUST key on the token, never on the bare `status: skipped`, so the two causes never collapse into one bucket. A `status: skipped` fragment without a recognised `reason` token is a contract violation and MUST be surfaced as an error during aggregation rather than silently bucketed.

The token shape is a flat scalar `reason: {token}` on the skipped fragment — never a nested object, never a free-text sentence. The two tokens above are the closed set; introducing a third token requires updating this contract and every aggregation consumer.

## TOON Fragment Shape

**Tier 1 (`status: success`)** — full analysis fragment:

```toon
aspect: chat_history_analysis
status: success
session_id: {session_id}
summary: "{3-5 sentence narrative of the session arc}"
pivots[*]{turn_index,reason}:
  42,"user clarified compatibility strategy"
permission_prompts[*]{tool,resource,cause}:
  ...
loop_backs[*]{from_phase,reason}:
  ...
findings[*]{severity,message}:
  info,"User clarified requirement mid-refine — consider refine-phase prompt tuning"
```

**Tier 2 (`status: skipped`)** — graceful-skip fragment. The `reason` field carries the canonical skip-reason token (see [Skip-Reason Token Contract](#skip-reason-token-contract)); a `warning` finding makes the skip visible in the compiled report:

```toon
aspect: chat_history_analysis
status: skipped
session_id: {session_id}
reason: transcript_too_large
findings[*]{severity,message}:
  warning,"Chat-history analysis skipped: session transcript exceeded the 2 MiB read budget"
```

(`reason: transcript_unavailable` when the transcript was absent rather than too large.)

## Multi-line serialization (binds PRODUCERS and fragment authors alike)

⛔ **No line of a multi-line value may reach column 0 of the emitted document.** `parse_toon` reads a flush-left line containing a colon as a *sibling top-level key*, so a transcript line reading `status: blocked` does not merely get lost — it OVERWRITES the envelope's own `status` and truncates everything after it. This rule is stated here, outside [LLM Interpretation Rules](#llm-interpretation-rules), because it binds **both** parties to a fragment and the interpretation rules bind only one: the script that PRODUCES a payload is subject to it exactly as the LLM that AUTHORS a fragment is. Siting it under the interpretation rules is what let `extract-chat-signal.py` emit a raw multi-line `reduced_transcript` for as long as it did.

Which form satisfies the rule depends on who is writing:

| Writer | Form | Why |
|--------|------|-----|
| A **script** emitting opaque foreign text (a transcript, a captured log, a PR body) | Mark the value `BlockScalar` before handing it to `serialize_toon`; it is then emitted as `key: \|` with the body indented two spaces past the header. | The indent is exactly what `parse_toon` strips back off, so the body round-trips verbatim and is inert — no payload line can reach column 0. A plain multi-line `str` is quoted but **not** escaped, which is the corruption above. |
| An **LLM** hand-authoring a fragment body (e.g. `summary`) | A quoted scalar with escaped newlines (`"line1\nline2"`). | A hand-authored body is short and under the author's control; the escaped form keeps it on one physical line, so the question of a flush-left continuation never arises. |

`serialize_toon` emits a block scalar **only** for a value the producer explicitly marked `BlockScalar` — the marking is deliberate and is not inferred from the presence of a newline, because `value_needs_quoting` is the published predicate for what the serializer quotes and changing it would be wrong for every existing caller. The boundary contract, including which edges round-trip and which do not, is owned by the `BlockScalar` docstring in `ref-toon-format/scripts/toon_parser.py` and is not restated here.

## LLM Interpretation Rules

- Pivots AFTER `3-outline` completion indicate a missed clarification in refine — surface as `warning`.
- Any permission prompt within the plan SHOULD have a corresponding entry in the permission-prompt-analysis aspect.
- Loop-backs from `6-finalize` to `5-execute` are normal; loop-backs from later phases to `2-refine` are strong signals of an under-refined request.
- Multi-line narrative content you author by hand (e.g. `summary`) MUST be a quoted scalar (`"line1\nline2"`). See [Multi-line serialization](#multi-line-serialization-binds-producers-and-fragment-authors-alike) for the rule this follows from and for the different form a producing SCRIPT must use.

## Finding Shape

```toon
aspect: chat_history_analysis
severity: info|warning|error
message: "{one-line}"
evidence: "turn_index={n}"
```

## Out of Scope

- Log-level quantitative counts — those belong to log-analysis.
- Root-cause of specific script failures surfaced in chat — those belong to script-failure-analysis.
- Transcript format and reduction mechanics — those belong to the platform-runtime `chat extract-signal` operation and its contract.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-chat-history-analysis.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect chat-history-analysis --fragment-file work/fragment-chat-history-analysis.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.