envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:27:55Z

# Candidate lesson: self-review findings go stale against a moving HEAD and cost no-op finalize loops

## Signal source

Q-Gate `6-finalize` findings `087589`, `a79fd5`, `4f314a`, `67f697`, `934b8d` — five findings, all resolved `taken_into_account` with the resolution detail "cited passage no longer present".

## Observation

Five self-review findings were triaged against a HEAD at which the cited defect **had already been fixed**. In four of the five, the live text already read exactly the wording the finding prescribed:

- `087589` — `inbox-envelope.md:77/79` already read "the directory the message is written to".
- `a79fd5` — `_orchestrator_inbox.py:1037` already read "The directory the message is allocated in (created when absent)".
- `4f314a` — `plan-orchestrator/SKILL.md:450` already stated the trailing digits are "mandatory AND terminal" with the letter-suffix exclusion.
- `6bc7d4`/`e9862b` family — `orchestration-model.md:173/175` already read "three sanctioned in-place edits".
- `67f697` — the `test_inbox_delivery.py` comment already stated the corrected rationale.

Each was resolved without a fix task, with the triager explicitly noting the goal of avoiding "a no-op finalize loop". The cost is visible in the step record: `pre-submission-self-review` fired **13 times with 10 loop-backs**, and the plan reached `loop_back_iteration: 11`.

## Corrective rule

1. **Re-ground a self-review finding against current HEAD before triage raises a loop_back.** A finding carries a file and a line; verifying the cited passage still says what the finding claims is cheap relative to a full execute/finalize loop.
2. **Findings surfaced against commit X must record X**, so a triager reading them at commit Y can tell staleness from disagreement. The `pr-comment` findings in this plan do carry `reviewed_commit_sha`; the Q-Gate findings do not carry an equivalent, which is why staleness could only be detected by re-reading each file.
3. A round that returns only stale findings should close the loop, not open another one.

## Instrument gap

There is no automated staleness check on a Q-Gate finding. The `resolve-evidenced` verb exists for the case where a landed fix touched the finding's file, but these five were resolved by hand after a manual re-read. A finding-level "still present at HEAD?" probe would have closed all five without a triage pass.
