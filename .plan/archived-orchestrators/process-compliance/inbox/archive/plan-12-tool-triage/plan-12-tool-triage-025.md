envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:59Z

# Four smaller observations from plan-12-tool-triage (not filed individually)

1. **Self-review candidate payload too large to inline.** A full-scope `self_review surface` returns ~91–93 KB (183 candidates over 50 files). The dispatch contract passes `candidates` in the prompt body, so the orchestrator had to hand the author a path to the persisted tool-results file instead ("read that file in full and treat it as the candidates field"). The workflow has no documented by-reference channel for the candidate set.
2. **`detect-artifacts` false positives on test fixtures.** During commit steps the artifact scan offered committed test-fixture files as artifacts; they had to be dismissed by hand. The artifact patterns do not distinguish tracked fixtures under `test/` from generated residue.
3. **The simplify standards doc embeds its own dispatch.** `finalize-step-simplify.md` Step 3 instructs a dispatch, but the step already runs inside a dispatched `execution-context` leaf, which cannot dispatch. The leaf therefore ran Step 3 in-context and reported the deviation every round ("I'm a leaf and can't start sub-agents").
4. **Correction to message plan-12-tool-triage-005 (`session_ids` never captured).** At finalize, `manage-status metadata --get --field session_ids` returned `[bf78eae8-48cc-4369-ac15-823fb9dfab66]` with `resolved_from: current`, and `manage-metrics enrich` succeeded with it. The absence 005 reported was therefore not permanent for this plan — the id was present by finalize. 005's claim should be re-verified before it drives a fix (whether capture happened late or 005's probe read the wrong source).
