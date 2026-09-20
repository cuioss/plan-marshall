envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:45:00Z

component=plan-marshall:workflow-integration-github
category=bug
created=2026-07-29
bundle=plan-marshall

# Doc/script flag-name drift: enabled-bots/settled-bots vs required/optional/participated-bots

Doc/script drift traced to PR #1041: the loaded `automatic-review` and `workflow-integration-github`
skill docs describe `--enabled-bots` / `--settled-bots` flags, while the live scripts implement
`--required-bots` / `--optional-bots` / `--participated-bots` instead. Two separate leaves in this
plan independently hit the mismatch — each had to rediscover the real flag surface from the script's
own `--help` rather than trust the doc.

## Solution

Regenerate/update the `automatic-review` and `workflow-integration-github` skill docs to describe the
actual `--required-bots` / `--optional-bots` / `--participated-bots` surface, and add this doc as a
tracked drift point so a future flag rename in the script updates the doc in the same commit.

## Impact

Matches the epic's recurring "doc-contract-divergence" archetype and the standing "enabled-bots vs
operative drift" note already carried in the epic's memory. This is a second, independently-hit live
instance of that exact drift, confirming it is still unresolved in main.
