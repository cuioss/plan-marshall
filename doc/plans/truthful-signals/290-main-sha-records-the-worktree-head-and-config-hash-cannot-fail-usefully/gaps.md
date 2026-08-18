# Gaps — 290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully

**Source:** verification.md (same directory)   **Open items:** 4

## G1 — Remove the refuted "the capture was dead / exit 2" claim from the production docstring and the test comment

- **Kind:** stale-statement
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:1514-1518` — `_capture_config_hash` docstring; and `test/plan-marshall/plan-marshall/test_invariants_behavior.py:203-206` — the `_capture_config_hash` section comment.
- **What is wrong:** Both assert that the pre-fix capture "passed `--audit-plan-id`, which the `plan` noun does not accept, so the subprocess exited non-zero and the capture was silently `None` at every boundary — a signal that never fired at all." That is false. `_capture_config_hash` reached the script through `_run_script` (`_invariants.py:467-487`), which invokes `.plan/execute-script.py`, and the executor **strips** `--audit-plan-id` before the target parser runs — `execute-script.py.template:11` ("stripped before passing to script"), `extract_audit_plan_id` at `:1222-1254`, applied at `:1417`, and independently stated in `argparse_surface.py:213-215`. The stripping is present at `b2982e75^`, so it held during the run. Executed at HEAD: `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-5-execute get --audit-plan-id X` exits **0** with a parseable TOON payload, while the same call made **directly** against `manage-config.py` exits **2**. The report's "empirically verified … with the marketplace PYTHONPATH" measured the direct path, which the capture never used. The claim is also self-contradicted by the plan's own evidence: four *distinct* recorded hash values cannot come from a capture returning `None`.
- **Why it matters:** A false diagnosis is shipped in production code documentation of a skill whose epic exists to remove false signals. Worse, it is actionably misleading: `--audit-plan-id` appears on dozens of documented calls to nouns that do not declare it (e.g. `plan-marshall/workflow/planning.md:117`, `planning-outline.md:183`, `:342`, `:591`, `q-gate-validation.md:57`), all of which work through the executor. A reader trusting this docstring would conclude they are broken and "fix" them.
- **Fix:** Rewrite the docstring's defect-(2) sentence to state what is true: the old capture ran `manage-config plan phase-{phase} get` through the executor and returned a **phase-scoped** hash — a different config subtree at every boundary — so the cross-phase scan flagged a spurious drift by construction. Delete the "does not accept / exited non-zero / never fired at all" clause entirely (it was never the mechanism). Apply the same correction to the test-file section comment. Optionally add a one-line correction note to `report-01.md` § D0 recording that defect #1 was refuted on re-verification, so a later audit does not re-inherit it.
- **Done when:** `grep -rn "audit-plan-id" marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py test/plan-marshall/plan-marshall/test_invariants_behavior.py` returns no hit asserting that the `plan` noun's rejection made the capture `None`, and the surviving prose names phase-scoping as the sole pre-fix defect.
- **Module/topic:** `plan-marshall:plan-marshall` — phase-handshake invariants (`_invariants.py` + `test_invariants_behavior.py`).

## G2 — Add the missing non-dict `marshal.json` test, or stop claiming it

- **Kind:** missing-test
- **Severity:** medium
- **Where:** `test/plan-marshall/plan-marshall/test_invariants_behavior.py:17` — module docstring; guard at `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:1535-1536`.
- **What is wrong:** The module docstring states the suite covers "`_capture_config_hash` — the absent / unreadable / non-dict / plan-section branches". Three tests exist (`:219` absent, `:231` unparseable JSON, `:240` plan-section) but **none** exercises the `if not isinstance(config, dict): return None` guard. `grep -n "non_dict\|non-dict\|not_dict"` over the file returns only `test_hash_dict_handles_non_dict_payload` (`:103`), which tests `_hash_dict`, not the capture. This bullet was rewritten by this very run as the "Fixed" disposition of sub-agent finding D2-1, so the correction shipped a new inaccuracy.
- **Why it matters:** An untested guard on a `blocking_at_every_boundary` invariant, advertised as tested. A refactor that dropped the `isinstance` check would hash `{}` from a list-shaped `marshal.json` — a stable but meaningless fingerprint — with the whole suite still green.
- **Fix:** Add `test_capture_config_hash_none_when_marshal_not_a_dict`: write `marshal.json` containing a top-level JSON array (e.g. `json.dumps([1, 2])`), monkeypatch `inv.get_marshal_path` at it as the sibling tests do, and assert `inv._capture_config_hash('p', {}, '5-execute') is None`. Also rename `test_capture_config_hash_none_when_marshal_unreadable` or its docstring so "unreadable" is not used for what is in fact unparseable JSON.
- **Done when:** the new test exists, passes, and goes RED when `_invariants.py:1535-1536` is deleted.
- **Module/topic:** `plan-marshall:plan-marshall` — phase-handshake invariant tests.

## G3 — Stop calling the `None` return "fail-closed"

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:1524-1526` — `_capture_config_hash` docstring; echoed in `test/plan-marshall/plan-marshall/test_invariants_behavior.py:232`.
- **What is wrong:** The docstring calls returning `None` on an absent / unreadable / non-dict `marshal.json` "fail-closed". At capture time it is the opposite: `capture_all` (`_invariants.py:1893-1894`) skips any invariant whose capture returns `None`, so the `config_hash` column is written empty and `_diffs` (`_handshake_commands.py:495-498`) then skips it — the invariant simply disappears with no diagnostic. Closed behaviour only holds in the verify direction, where a captured value versus an observed `''` does raise a blocking diff.
- **Why it matters:** A reader auditing this epic's "signal absent" archetype would read "fail-closed" and stop looking, when a `marshal.json` that is unreadable at capture time produces exactly the silent-absence outcome the epic targets.
- **Fix:** Replace "fail-closed" with an accurate statement of both directions: at capture the invariant is recorded as not-applicable (empty column, no signal) rather than as a false "config emptied" drift; at verify a value that becomes unreadable diffs against the captured hash and blocks. Mirror the wording in the test docstring.
- **Done when:** neither file describes the `None` return as "fail-closed", and the capture-side silent-absence behaviour is stated explicitly.
- **Module/topic:** `plan-marshall:plan-marshall` — phase-handshake invariants.

## G4 — Correct the `build-map` misattribution in the run report

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully/report-01.md` § D0, defect 1.
- **What is wrong:** The report states `--audit-plan-id` "exists only on the `build-decision` / `build-map` nouns". In `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` the flag is declared exactly twice — `:389` under `build-decision` and `:420` under `sync-defaults`. `build-map` declares none. `git show b2982e75:…/manage-config.py | grep -n audit-plan-id` returns the same two lines, so the report was wrong at the moment it was written. The same sentence appears in the landed commit body of `b2982e75`.
- **Why it matters:** Retrospective audits mine these reports for surface facts; a wrong noun sends the next reader to the wrong parser. It also compounds G1 — the whole defect-1 paragraph is unreliable.
- **Fix:** Amend the § D0 sentence to name `build-decision` and `sync-defaults`, and fold it into the G1 correction note so the paragraph is repaired once.
- **Done when:** `report-01.md` names no noun that does not declare `--audit-plan-id`, verifiable against `manage-config.py:389` / `:420`.
- **Module/topic:** `doc/plans/truthful-signals/290-…` run report (and, by reference, `plan-marshall:manage-config` CLI surface documentation).
