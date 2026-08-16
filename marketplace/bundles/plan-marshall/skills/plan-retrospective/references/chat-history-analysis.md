# Aspect: Chat History Analysis

**Conditional**: only dispatched when `--session-id` is present.

Complements log-analysis with conversational context — user pivots, mid-plan clarifications, permission prompts, and loop-backs. Hybrid: the deterministic `extract-chat-signal.py` pre-pass reduces the raw transcript to its signal-bearing turns (a fact), and the LLM then synthesizes the analysis fragment from that reduced transcript.

## Input Resolution

Claude Code session transcripts live under `~/.claude/projects/{slug}/{session_id}.jsonl`, where `{slug}` is the absolute project cwd with each `/` replaced by `-` (path-slug). The orchestrator resolves the absolute path by constructing the canonical pattern `~/.claude/projects/{cwd-slug}/{session_id}.jsonl` (see `SKILL.md` Step 3, Aspect 14 dispatch instructions) and falling back to a parent-directory glob under `~/.claude/projects/` for cross-cwd recovery. The LLM does **not** manually construct the path or perform any file discovery — it receives `transcript_path` as a concrete absolute path from the orchestrator and reads it directly via the Read tool.

Raw session transcripts are routinely multi-megabyte JSONL. Feeding the raw file to the LLM analysis prompt would blow the read budget on tool-output noise. The orchestrator therefore runs the `extract-chat-signal.py` signal-extraction pre-pass against the resolved `transcript_path` BEFORE deciding which tier applies — see [Two-Tier Degradation Path](#two-tier-degradation-path) below. The pre-pass reduces the transcript to its signal-bearing turns and returns the flags (`no_signal`, `over_budget`) that select Tier 1 (full analysis) vs Tier 2 (graceful skip).

## Two-Tier Degradation Path

The aspect resolves to exactly one of two tiers, gated by the `extract-chat-signal.py` pre-pass output:

| Tier | Trigger | Aspect behaviour |
|------|---------|------------------|
| **Tier 1 — full analysis** | The transcript carried operator-authored signal AND the reduced text fits the read budget: `no_signal == false` AND `over_budget == false`. | Feed the reduced transcript (`reduced_transcript`) to the LLM analysis prompt and synthesize the `chat_history_analysis` fragment with `status: success` per the [TOON Fragment Shape](#toon-fragment-shape) below. |
| **Tier 2 — graceful skip** | The transcript is missing, carried no operator-authored signal, OR the reduced transcript still exceeds the read budget (default 2 MiB / `2 * 1024 * 1024` bytes). | Do NOT feed any transcript to the LLM. Emit a fragment with `status: skipped` and the canonical skip-reason token per the [Skip-Reason Token Contract](#skip-reason-token-contract), plus a `severity: warning` finding so the skip is visible in the compiled report. |

The pre-pass is the single decision source — the orchestrator never inspects raw file size directly. The `extract-chat-signal.py run --transcript-path {abs} [--read-budget-bytes N]` invocation returns:

- `no_signal` — `true` when the transcript carried **no operator-authored signal of either kind**: `operator_turn_count == 0` AND `gate_decision_count == 0`. It is deliberately **not** a count of survivors — see [Why the verdict is not a survivor count](#why-the-verdict-is-not-a-survivor-count).
- `over_budget` — `true` when the reduced text still exceeds `--read-budget-bytes` (default 2 MiB).
- `reduced_transcript` — the Tier-1 input. It is fed to the LLM only when both flags are `false`; it is **not** empty whenever they are not. A transcript with no operator signal can still retain marker-bearing `assistant` turns, so a Tier-2 skip may carry a non-empty reduction. The flags decide the tier — never the emptiness of this field.
- `raw_turn_count` / `reduced_turn_count` / `dropped_turn_count` — the parseable-turn count before reduction, the raw turns kept, and how many the reduction removed, so the caller can see how much was boilerplate. `reduced_turn_count + dropped_turn_count == raw_turn_count` holds; recovered gate decisions were never raw turns, so they appear as extra entries in `reduced_transcript` and are counted by `gate_decision_count` alone.
- `operator_turn_count` / `gate_decision_count` — the two operator-signal counters, reported separately from the survivor count so a caller can tell *"kept 200 turns, 3 operator-authored"* from *"kept 200 operator turns"*. `operator_turn_count` counts free-form operator corrections; `gate_decision_count` counts operator decisions recovered from the tool-result channel.

### The reduction identifies provenance positively

A `user` turn is kept only when it is **operator-authored**. The harness injects synthetic turns under the `user` role that carry no operator signal, and a role-only filter cannot tell them apart from a real utterance.

The predicate does **not** enumerate the synthetic shapes it knows about. It asks the opposite question: **does operator prose remain once every harness envelope is stripped?** A turn is dropped when the residue is empty.

- an **empty or whitespace-only** turn (a tool-result placeholder that carried no text block) — no residue;
- a turn that is **wholly a harness envelope** — one or more XML-ish tag blocks with nothing outside them. The match is generic over the tag *name*, so an envelope introduced after this document was written is recognised without editing anything;
- a **synthetic skill-load** turn — a loaded skill's body injected into the conversation, recognized by a `Base directory for this skill:` line followed by a markdown heading — or an **envelope-less harness notice** (session re-entry, the local-command caveat, stop-hook feedback), matched as a literal prefix because it carries no tag to key on. The notice is matched against the **residue**, not the raw turn, so an envelope attached ahead of it does not hide it. That prefix list is a sample, not a closed set — see [The residual gap](#the-residual-gap--envelope-less-injections).

Three rules keep the residue trustworthy:

- **Only a matched open/close pair is an envelope.** Stray markup in operator prose (`List<Integer>`, a stray `</error>`) stays in the residue rather than swallowing the rest of the turn.
- **Only the outermost pair is stripped.** An unmatched tag earlier in a turn therefore cannot suppress the stripping of a well-formed envelope that follows it — that would be a fail-toward-*operator* path, the direction this design exists to avoid.
- **Some envelopes carry the operator's own words.** A slash command's `<command-args>` is the harness's wrapper around the operator's instruction, and it is this project's primary channel for driving a run; its inner text is kept as residue rather than dropped with the envelope. This allow-list is safe in the only direction an allow-list can be: an operator-bearing envelope nobody listed reads as synthetic, never the reverse.

**Precedence — recovered operator text wins over the notice backstop.** When a turn yields text from an operator-bearing envelope, it is operator-authored, *even if the rest of the turn opens with a listed notice*. The harness attaches its notices to whatever turn follows them, so a stop-hook or local-command notice can sit in front of a command the operator typed; letting the notice veto the command would discard the instruction along with the wrapper. The skill-load check still runs **first**, so an injected skill body that merely quotes a command block stays synthetic.

The precedence applies only to text recovered from an operator-bearing envelope — never to ordinary prose residue, which the notice backstop still vetoes.

An envelope *attached to* an operator turn is not a drop either: the harness routinely annotates a genuine utterance, and the residue then still holds the operator's prose.

**The direction of failure is the design.** An enumeration of synthetic shapes fails toward *"operator"* for any wrapper nobody listed — the direction that inflates the survivor count and manufactures a falsely healthy verdict. Residue-based classification fails toward *"synthetic"* instead, **for any injection that carries an envelope**; an envelope-less notice is outside that guarantee and is covered only by the literal-prefix backstop (see [The residual gap](#the-residual-gap--envelope-less-injections)). The accepted cost is that an operator turn consisting of nothing but a matched tag block is misread as synthetic.

### The harness-injection marker inventory

The classes below were derived by running the reducer over real session transcripts and classifying the survivors. **The inventory is evidence for the positive predicate, not a list the predicate consults** — no code keys on it.

| Injected class | Reaches the reducer as | Recognised by |
|---|---|---|
| Skill body injected as a `user` turn | A `text` block | The `Base directory for this skill:` + heading signature |
| Tool-result placeholder carrying no text | A `user` turn with empty text | Empty residue |
| Tag-wrapped instruction blocks (`<system-reminder>`, `<task-notification>`, `<wake>`/`<event>`) | A `text` block, on harness surfaces that persist them inline | Empty residue after envelope stripping |
| Slash-command expansions (`<command-name>` / `<command-message>` / `<command-args>`) | A `text` block | **Kept, not dropped** — `<command-args>` is operator-bearing, so its inner text is the residue. An expansion with no arguments leaves no residue and is dropped |
| Harness metadata (tool/agent/skill listings, permission and mode notices) | `attachment` events carrying **no `message`** | Never parsed as a turn at all |
| Verbatim envelope-less notices (re-entry, local-command caveat, stop-hook feedback) | A `text` block with **no tag at all** | Literal prefix match — a **sample**, see the gap below |

⚠ **The decisive finding is that this inventory cannot be completed by enumeration.** The same logical injection is persisted differently by different harness surfaces and versions — a block rendered inline in one surface arrives as an `attachment` in another — so any list keyed on the shapes one transcript happens to contain is a sample. That is why the predicate is residue-based: it needs no entry here to classify a wrapper correctly.

#### The residual gap — envelope-less injections

**The structural guarantee covers tag-wrapped injections only.** A harness turn that carries *no envelope* — the stop-hook feedback notice is the observed case — leaves full residue and is counted as an operator turn unless its exact wording is listed in `HARNESS_NOTICE_PREFIXES`. For that class the filter is back to an enumeration, and therefore back to being a sample. Listing a notice is necessary but **not sufficient** for the turn to be dropped: a turn that also yields operator-bearing text is kept, per the precedence rule above.

This is published rather than papered over because the plan's own thesis is that a named list is a sample: an inventory that hid an observed miss would repeat the defect it documents. A new envelope-less notice is a false *operator* — the direction that inflates the verdict — so this list is the one part of the mechanism that needs updating when the harness adds a shape.

### Why the verdict is not a survivor count

`no_signal` is derived from `operator_turn_count` and `gate_decision_count`, never from how many turns survived.

A survivor count answers *"did the reduction keep anything?"* — and that number **rises** with every class of injected instruction text the filter fails to recognise. Signal quality and the reported verdict then move in opposite directions: the more boilerplate leaks through, the healthier the transcript is reported to be. Keying the flag on operator-authored counts breaks that coupling, so retaining more framework boilerplate can no longer move the verdict.

This is why the surviving set must never be described as operator-authored *by construction*. It is not: the reduction keeps marker-bearing `assistant` turns for context, and those are not operator signal. The counters are what carry the claim, and the flag reads only them.

### The gated-decision channel

On a gated run the operator's decisions arrive as **tool results, not user turns** — a permission grant or refusal, or an `AskUserQuestion` selection. A reducer that keeps only free-form turns therefore measures only the channel the operator did not use, and a run with zero corrections and many gate decisions reads as silent when it is in fact well-instrumented.

Such results are recovered into the reduced transcript under the `operator-decision` role and counted in `gate_decision_count`. Both tests are deliberately narrow — the answering tool-use id, or a verbatim operator-refusal notice — so a counter of operator signal fails toward *not* counting and ordinary tool output is never mistaken for a decision.

**The generalizable rule**: when a channel's producer injects synthetic entries under the same structural label real entries use, a filter keyed on that label measures the label, not the content. Identify provenance positively, so an unrecognised producer shape fails toward *synthetic*; and derive any downstream sufficiency flag from what the surviving set **is**, never from how much of it there is.

Either flag being `true` is the Tier-2 trigger. When BOTH are `false`, `reduced_transcript` is the Tier-1 input to the LLM prompt. The 2 MiB read budget is the canonical threshold and is owned by the script (`DEFAULT_READ_BUDGET_BYTES`); this document references it, it does not re-declare it.

## Skip-Reason Token Contract

Tier 2 emits a `reason` token that downstream retrospective aggregation MUST key on to distinguish *why* the aspect was skipped. The two canonical tokens carry distinct semantics — a **deliberate, size-driven skip** (`transcript_too_large`) versus a **genuine absence of session data** (`transcript_unavailable`) — and aggregation MUST NOT collapse them into one bucket. Two canonical tokens exist:

| Token | Emitted when | Semantics for aggregation |
|-------|--------------|---------------------------|
| `transcript_too_large` | The pre-pass returned `status: success` AND (`over_budget == true` OR `no_signal == true`) — a transcript was present and read, but the reduced signal was empty or still over budget. | The chat-history aspect was **intentionally skipped** because the session was too large to analyse within budget. Aggregation MUST treat this as "analysis withheld by design", NOT as "this plan had no conversational signal". A retrospective corpus scan counting plans-with-chat-analysis MUST exclude `transcript_too_large` skips from the denominator of "plans that genuinely lacked a session", and MUST NOT infer a quiet/uneventful session from the skip. |
| `transcript_unavailable` | The pre-pass returned `status: skipped` with `reason: transcript_unavailable` — the transcript file could not be resolved or read (missing file; `read_transcript_lines` raised `FileNotFoundError`). | The session JSONL was **absent** — a genuine data absence, not a size-driven skip. Aggregation treats this as "no transcript existed for this plan" (e.g. a plan run without a captured session id, or an archived plan whose transcript was not retained). |

**Discriminator (normative, checkable)**: the orchestrator MUST key the token on the pre-pass's own `status` field, NOT on the `no_signal` flag alone. The missing-file path returns `status: skipped, reason: transcript_unavailable` while ALSO setting `no_signal: true` (no bytes were read, so it recorded no operator signal), so `no_signal == true` is NOT sufficient to select `transcript_too_large`. The rule is: when the pre-pass returns `status: skipped`, forward its emitted `reason` verbatim (`transcript_unavailable`); only when it returns `status: success` does the orchestrator apply the `over_budget == true OR no_signal == true` → `transcript_too_large` mapping. Equivalently: `transcript_unavailable` means no bytes were read; `transcript_too_large` means bytes were read and deliberately set aside. Cross-plan aggregation (e.g. the `audit-archived-plan-retrospectives` corpus checks) MUST key on the token, never on the bare `status: skipped`, so the two causes never collapse into one bucket. A `status: skipped` fragment without a recognised `reason` token is a contract violation and MUST be surfaced as an error during aggregation rather than silently bucketed.

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

(`reason: transcript_unavailable` when the transcript file was absent rather than too large.)

## LLM Interpretation Rules

- Pivots AFTER `3-outline` completion indicate a missed clarification in refine — surface as `warning`.
- Any permission prompt within the plan SHOULD have a corresponding entry in the permission-prompt-analysis aspect.
- Loop-backs from `6-finalize` to `5-execute` are normal; loop-backs from later phases to `2-refine` are strong signals of an under-refined request.
- Fragment bodies MUST NOT use `|` block scalars. Multi-line narrative content (e.g. `summary`) MUST be a quoted scalar (`"line1\nline2"`) so the fragment round-trips deterministically through `serialize_toon`/`parse_toon`. Rationale: `serialize_toon` never emits block scalars, so a `|` block scalar is a parse-only, hand-authored construct; any continuation line that sits flush at column 0 and contains a colon is re-parsed by `parse_toon` as a phantom sibling top-level key, leaking a spurious aspect into the bundle.

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

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-chat-history-analysis.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect chat-history-analysis --fragment-file work/fragment-chat-history-analysis.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
