envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T11:19:30Z

# oci-security: verify-then-run must use the verified digest, and the quick reference verifies a tag

Severity: medium. Domain content (security guidance), filed under RULING 2026-10-09 (operator-confirmed for this sweep).
Bundle: `pm-dev-oci` (oci-security).

## Source

API-Sheriff `2026-10-21-19-003` (PLAN-V02-47, PR #504; CodeRabbit finding), verbatim in `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-02/API-Sheriff/`.

## Observation

An operator recipe resolved and verified the image index digest, then started the container from the mutable version tag, leaving a window in which the tag can move. The fix: resolve `name@sha256` once, verify that exact reference, and run it unchanged.

## Ground truth (c431a8193)

`oci-security/standards/supply-chain-security.md:28-32` shows `cosign sign registry.example.com/myapp:v1.0` and `cosign verify registry.example.com/myapp:v1.0` — both on a mutable tag, with no digest-pinning or verify-what-you-run rule.

## What to consider

Change the quick commands to digest references. Add a checklist row: resolve the digest once, verify it, deploy that exact digest.
