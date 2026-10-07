envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:19:24Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# extract-chat-signal reports tier-1 success after dropping 99.75% of the transcript

## Observation

`extract-chat-signal run` on this plan's 806-turn session transcript returned:

```
reduced_turn_count: 2
raw_turn_count: 806
dropped_turn_count: 804
reduced_bytes: 687
no_signal: false
over_budget: false
```

Because `no_signal == false` and `over_budget == false`, the SKILL's two-tier degradation path takes **Tier 1** — "feed `reduced_transcript` to the LLM analysis prompt and synthesize the `status: success` fragment". No caveat, no skip-reason token. Downstream, the chat-history section of the report reads as a successful analysis of the session.

The two retained turns are the `/plan-marshall` slash-command invocation and one background task-notification ("Wait for PR to leave OPEN state completed"). Neither carries analytical content.

**Both operator interventions this plan actually had were invisible to the aspect** and had to be recovered from `decision.log` instead:

- 09:37:21Z — the operator chose **merge-anyway** at the 3/3 automatic-review loop-back ceiling, advancing an UNREVIEWED head.
- 09:52:02Z — the pre-merge comment barrier finding was **hand-suppressed** after it reproduced this plan's own target defect.

Those are the two highest-signal human decisions in a four-hour plan, and the aspect designed to surface human decisions saw neither.

## Second-order consequence

`permission-prompt-analysis` consumes the same reduction. It reported `prompts[]` empty — which reads as "no permission prompts occurred" when the truthful statement is "804 turns were never scanned for them". The aspect's own **severity floor** rule exists precisely to stop permission findings being silently dropped; an upstream reduction achieves the same silence by a route the floor cannot see.

## Corrective rule

The tier decision must not be a pure function of `no_signal` and `over_budget`. Add a **retention-ratio** dimension: when `reduced_turn_count / raw_turn_count` falls below a floor (or `reduced_bytes` below an absolute floor), either

- degrade to Tier 2 with a new skip-reason token (e.g. `transcript_over_reduced`), joining the existing `transcript_too_large` / `transcript_unavailable` pair; or
- proceed at Tier 1 but **stamp the retention ratio into the fragment** and emit a mandatory `warning` finding, so the report never presents a 687-byte sample as a transcript analysis.

Either way, `permission-prompt-analysis` must be told the scan did not happen rather than being handed an empty list.

## Evidence

- `extract-chat-signal run --transcript-path ~/.claude/projects/-Users-oliver-git-plan-marshall/4c734d17-afdb-4f06-9dca-401c84095ef9.jsonl` — output quoted above.
- `plan-retrospective/SKILL.md` Step 3, Aspect 14 two-tier degradation path; `references/chat-history-analysis.md` §§ "Two-Tier Degradation Path", "Skip-Reason Token Contract".
- `references/permission-prompt-analysis.md` § LLM Interpretation Rules, "Severity floor".
- `decision.log` 09:37:21Z and 09:52:02Z — the two operator interventions the aspect missed.
