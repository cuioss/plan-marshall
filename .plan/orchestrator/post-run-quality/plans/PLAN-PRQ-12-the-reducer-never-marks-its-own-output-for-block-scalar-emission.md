# PLAN-PRQ-12: The chat-signal reducer never marks its own output for block-scalar emission, so PRQ-02 D3's fix never reaches the value it was meant to protect

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-21 from `retrospective-aspects-publish-verdict-001.md` and `-002.md`, filed first-party
by `PLAN-PRQ-02`'s own retrospective (PR #1550, `c47f99c3c`) — the third independent report of this
symptom shape (the original corpus lesson, `PLAN-PRQ-02` D3, now this run). ⛔⛔ **`-001.md`'s STATED ROOT
CAUSE IS REFUTED by this orchestrator's own read-only verification and is corrected below — do not trust
the message's own diagnosis, only its symptom evidence.**

## Objective

**`PLAN-PRQ-02` D3 shipped a correct fix in the wrong place: the consumer (`extract-chat-signal.py`)
now wraps its own re-emitted `reduced_transcript` in `BlockScalar`, but the value it wraps was already
truncated to 69 of 725,532 bytes before it ever reached that code**, because the UPSTREAM producer —
`_chat_signal_reducer.reduce_chat_signal` — never marks `reduced_transcript` for block-scalar emission
when the runtime operation serializes its own success payload. The corruption happens one hop earlier
than D3 could reach, so the symptom D3 was built to fix (a transcript that reads as intact at the
`reduced_bytes` figure but delivers almost nothing) recurred, byte-for-byte the same shape, on the very
next plan that exercised it.

⛔⛔ **Root-cause correction, verified 2026-09-21 by direct code read (not trusted from the filing
message):** `-001.md` blames "the block-scalar emission path" generally and cites
`ref-toon-format/scripts/toon_parser.py`'s `BlockScalar` contract as unsatisfied. That contract IS
satisfied everywhere it is actually invoked:
- `toon_parser.py`'s `_serialize_block_scalar` (the shared writer) indents EVERY line of the body, not
  only the first — read directly, lines 761-765. Confirmed correct.
- `extract-chat-signal.py`'s own `_delivered_transcript` (D3's fix) correctly wraps its return value in
  `BlockScalar` before calling `output_toon` — confirmed correct, lines 66-87, 186-208.
- The actual gap: `platform-runtime/scripts/_chat_signal_reducer.py:378` returns
  `'reduced_transcript': reduced_text` as a PLAIN `str`, with no `BlockScalar` import anywhere in that
  file. `_claude_runtime_impl.py`'s `chat_extract_signal` (line ~1853) forwards that record verbatim
  into `toon_success(...)`, so the RUNTIME OPERATION's own stdout — what `extract-chat-signal.py` then
  calls `parse_toon(result.stdout)` on (line 128) — is the corrupted document. `extract-chat-signal.py`'s
  own docstring (lines 29-37) already names the exact corruption mechanism ("every line after the first
  lands at column zero and `parse_toon` reads it as a sibling top-level key") — it simply names it as a
  contract the CONSUMER satisfies, not realising the PRODUCER one hop upstream does not.
- Scope: only the Claude Code runtime implementation (`_claude_runtime_impl.py` +
  `_chat_signal_reducer.py`) has a real transcript-reduction body. `antigravity_runtime.py`'s
  `chat_extract_signal` is a `toon_noop` stub; `opencode_runtime.py`'s returns an empty transcript by
  design. Neither is affected in practice, but neither should be assumed clean without a one-line check
  at outline (verify-at-outline).

## Deliverables

Three deliverables. D0 is a gate.

**D0 — GATE: confirm the fix site and its population.** Read `_chat_signal_reducer.py`'s
`reduce_chat_signal` in full and confirm `reduced_transcript` is the ONLY field in the seven-field
normalized record (`reduced_transcript`, `raw_turn_count`, `kept_raw_count`, `operator_turn_count`,
`gate_decision_count`, `reduced_bytes`, `no_signal`) that is multi-line text requiring block-scalar
treatment — the other six are scalars. Also confirm `antigravity_runtime.py`'s and `opencode_runtime.py`'s
`chat_extract_signal` implementations genuinely cannot emit a non-trivial multi-line `reduced_transcript`
today, so this fix is complete without touching them (or fix them too if they can).

**D1 — `_chat_signal_reducer.reduce_chat_signal` marks `reduced_transcript` as a `BlockScalar` before
returning it.** One-line fix at `_chat_signal_reducer.py:378`, mirroring the exact pattern
`extract-chat-signal.py`'s own `_delivered_transcript` already uses. Add a regression test that
round-trips a MULTI-LINE transcript (not the single-line/first-line-only fixtures that let this ship
broken through D3) through the FULL hop — reducer → `toon_success` serialization → `parse_toon` →
`extract-chat-signal.py`'s own re-emission — and asserts `reduced_transcript_delivered_bytes ==
reduced_bytes` end to end. The existing per-file unit tests for `extract-chat-signal.py` and
`_chat_signal_reducer.py` evidently do not exercise this hop together, which is why three independent
reports of the same symptom did not converge on this file until now.

**D2 — The chat-history tier gate stops selecting Tier 1 on an under-delivered payload, and gains the
skip-reason token the contract is missing.** (Folded from `-002.md`, same run, same subsystem.) The
two-tier gate selects Tier 1 whenever `no_signal == false AND over_budget == false` — an UPPER-bound-only
test that cannot detect a payload too SMALL to be useful, exactly the failure D1 fixes but which any
future partial-delivery bug in this same hop would reproduce. Add a delivery-integrity condition: when
`reduced_transcript_delivered_bytes` is materially below `reduced_bytes`, Tier 1 MUST NOT be selected.
The current skip-reason contract is a CLOSED two-member set (`transcript_too_large`,
`transcript_unavailable`); neither fits an under-delivered-but-present transcript. Add a third token,
`transcript_undelivered`, and update every aggregation consumer per the contract's own amendment rule.
This deliverable is independently valuable even after D1 lands — it is the control that catches the NEXT
instance of this failure shape, wherever it originates.

## Claim Labels

- OBSERVED: `_serialize_block_scalar` (`toon_parser.py:742-765`) indents every body line, not only the
  first — read directly 2026-09-21, contradicting `-001.md`'s stated root cause.
- OBSERVED: `extract-chat-signal.py`'s `_delivered_transcript` (lines 66-87) and its call sites (lines
  186, 208) correctly wrap the re-emitted transcript in `BlockScalar` — D3's fix, confirmed still present
  and correct at HEAD.
- OBSERVED: `_chat_signal_reducer.py` (platform-runtime) has no `BlockScalar` import and returns
  `reduced_transcript` as a plain `str` at line 378 — the actual gap.
- OBSERVED: on this run, `reduced_bytes: 725532` vs `reduced_transcript_delivered_bytes: 69` —
  0.01% delivered; a second aspect (`permission_prompt_analysis`) was consequently forced to report 121 of
  123 operator turns and 7 of 7 gate-decision bodies as undelivered.
- ⚠ HYPOTHESIS: `antigravity_runtime.py` and `opencode_runtime.py` cannot currently emit a non-trivial
  multi-line `reduced_transcript` (stub / empty-by-design) and so need no fix — D0 owns confirming this
  (verify-at-outline).
- Verify-first clause: D0 must re-read `_chat_signal_reducer.py` in full at outline HEAD before D1 is
  implemented — this spec's root-cause correction was derived from a partial read (the function signature
  and the one returning line), not a full-file audit.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_chat_signal_reducer.py` — D0, D1 (the actual fix site)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py` — D0 (the caller that serializes the reducer's record)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py` — D1 (the end-to-end round-trip test target), D2 (the tier gate)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/chat-history-analysis.md` — D2 (the skip-reason token contract)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py` — D0 (confirmed correct, cited for the record; no change expected)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` — D0, only if the stub needs hardening (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — D0, only if the empty-transcript path needs hardening (verify-at-outline)
- OBSERVED: `test/plan-marshall/plan-retrospective/test_extract_chat_signal.py` — D1's regression test
- OBSERVED: `test/plan-marshall/platform-runtime/` — D1's reducer-side test (exact file TBD at outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ Shares `plan-retrospective/scripts/` and `plan-retrospective/references/` with `PLAN-PRQ-01`,
  `PLAN-PRQ-08`, `PLAN-PRQ-09`, `PLAN-PRQ-11` — automatic at `parallelization_scope: 1`.
- Does NOT share surface with any currently-staged spec outside `plan-retrospective/**` — the
  `platform-runtime/**` half is new territory for this epic.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-12-the-reducer-never-marks-its-own-output-for-block-scalar-emission.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
