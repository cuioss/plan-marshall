envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:57:30Z

component=plan-marshall:phase-3-outline
category=bug
created=2026-07-29

# Light lane skips phase-2-refine Step 13, so phase-3-outline hard-fails on pr_title_missing

The `light` planning lane skips `phase-2-refine` Step 13, which is the step that authors `metadata.pr_title`. When a request is routed `light`, `metadata.pr_title` is therefore never written during refine. `phase-3-outline`'s `phase_handshake` capture then hard-fails with `pr_title_missing` because it expects that field to already be populated by the time outline runs.

## Impact

Either `phase-3-outline`'s `phase_handshake` must tolerate an absent `pr_title` on the light lane and author it itself (mirroring what Step 13 does on the deep lane), or the light lane needs its own lightweight `pr_title`-authoring step before outline's handshake capture runs. As implemented, every light-lane plan is exposed to this hard-fail unless some other step happens to backfill `metadata.pr_title` first — this plan hit it directly at `phase-3-outline`'s `phase_handshake` capture.
