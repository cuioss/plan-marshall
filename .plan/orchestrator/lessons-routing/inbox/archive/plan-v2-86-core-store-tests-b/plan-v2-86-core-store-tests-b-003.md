envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:29Z

# git-workflow commit verb returns an opaque 'git commit failed: exit 1' when nothing is staged

- component: plan-marshall:workflow-integration-git
- category: improvement
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

The commit verb commits only what is already staged. When nothing is staged, it returns only 'git commit failed: exit 1', without git's own 'nothing to commit' text and without suggesting to stage files. The verb should check whether the index is empty and return a structured error such as nothing_staged.

Evidence: git-workflow commit --plan-id ... --message-file ... --step functional-review, with the changed file unstaged, answered error 'git commit failed: exit 1' / error_code FETCH_FAILURE; after git add of the one file the same call succeeded.
