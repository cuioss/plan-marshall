# Gaps — 070-marshalld-self-reload-on-version-signal

**Source:** verification.md (same directory)   **Open items:** 6

## G1 — Stop treating an absent in-flight count as an idle daemon

- **Kind:** bug
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py:669` — `run_status`; and `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py:108-112` — `decide`
- **What is wrong:** `run_status` writes `'in_flight': int(response.get('in_flight', 0) or 0)` (and the same for `queued`), so a ping response that carries **no** count is indistinguishable from one that reports zero. The daemons that carry no count are exactly the ones this feature targets: a *stale* daemon is by definition executing a marshalld copy older than commit `8f3c7fe0`, whose `Daemon._ping` returns only `status`/`pid`/`version`, and `manage_build_server._ping` (`:238-265`) applies no version gate, so the handshake still succeeds. Executing the consequence confirms it: `decide({... 'binary_diverges': True, 'in_flight': 0, 'queued': 0 ...})` → `ReconcileDecision(action='upgrade', reason='idle_and_stale')`, and `upgrade` is `run_drain` (SIGTERM + 30 s grace, in-flight job marked `killed`) then `_start_daemon`.
- **Why it matters:** the first post-sync reconcile against a busy pre-`8f3c7fe0` daemon drains a live build. That is the single outcome D1's ⛔ STOP CONDITION exists to prevent, and it is reached by the exact mechanism the condition forbids — idleness inferred rather than read from the daemon's own count. It also makes `report-01.md`'s claim "Idleness is read from the daemon's own scheduler count, never inferred from anything else" false for the drift population.
- **Fix:** in `run_status`, emit the counts only when the ping response actually contains them; when either key is absent, emit `in_flight: unknown` / `queued: unknown` (a sentinel, mirroring `_UNKNOWN_PROVENANCE`) rather than `0`. In `decide`, add a branch before the busy check: if `in_flight` or `queued` is missing or not an integer, return `ReconcileDecision(ACTION_DEFER, 'counts_unknown')` — fail closed, exactly as `provenance_unknown` already does.
- **Done when:** `test_reconcile_daemon.py` contains a case feeding a `running ∧ binary_diverges` status with `in_flight`/`queued` absent and asserts `decide(...).action == ACTION_DEFER` with reason `counts_unknown`; `test_manage_build_server.py` contains a case where `_ping` returns a response without the counts and asserts `run_status` does **not** report `0`; and mutating the new guard away turns both red.
- **Module/topic:** `plan-marshall:manage-build-server` + project-local `sync-plugin-cache` reconcile

## G2 — Verify the reconcile actually happened before reporting success and clearing the owed marker

- **Kind:** bug
- **Severity:** medium
- **Where:** `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py:211-215` — `reconcile`
- **What is wrong:** on `UPGRADE`/`START` the orchestration records `summary['reconcile_result'] = str(result.get('status', 'unknown'))` and then calls `clear_marker(marker)` unconditionally. Neither verb's `status` field can be anything but `success`: `run_upgrade` (`manage_build_server.py:597-618`) returns a hard-coded `'status': 'success'` whatever `run_drain` did, and `_start_daemon` (`:495-524`) returns `'status': 'success', 'already_running': True` when a daemon is still live. So a drain that times out at `_DRAIN_GRACE_SECONDS` leaves the old stale daemon running while the reconcile reports success and deletes any accumulated `reconcile-owed` marker.
- **Why it matters:** a failed heal is rendered as a clean line and the accumulated `defer_count` evidence is destroyed — the epic's own archetype reproduced inside the fix, and a direct contradiction of D3's "a skipped reconcile is **reported, not swallowed**".
- **Fix:** read the verbs' real post-conditions, not just `status`. For `upgrade`, treat `drained == False` while the daemon was running, or `running == False`, as a failed reconcile; for `start`, treat `already_running == True` as a failed reconcile. On failure, set `summary['reconcile_result'] = 'failed'`, **keep** (or write) the owed marker with reason `reconcile_failed`, and have `_display_detail` say so. Only clear the marker on a verified success.
- **Done when:** a test drives `reconcile` with an `action_runner` returning `{'status': 'success', 'drained': False, 'running': True}` for `upgrade` and asserts the marker still exists with `reason == 'reconcile_failed'`, and a second test with a genuinely successful upgrade asserts the marker is cleared.
- **Module/topic:** project-local `sync-plugin-cache` reconcile

## G3 — Correct the `status` sub-parser help string, which still names the removed `binary_path` key

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py:872` — `_build_arg_parser`
- **What is wrong:** the line reads `sub.add_parser('status', help='Report running version + binary path.', ...)`. The `status` verb no longer emits a `binary_path` key at all; it emits `running_binary_path`, `resolved_binary_path` and `binary_diverges`. The module docstring, the `run_status` docstring, `manage-build-server/SKILL.md` prose and its verb table were all updated by this plan; this string was not.
- **Why it matters:** `--help` is the surface an operator reads before running the verb, and the singular "binary path" is precisely the ambiguity D4 exists to abolish — it reads as *"which binary is running?"* while promising nothing of the kind.
- **Fix:** change the help text to `'Report running version, in-flight/queued counts, and running vs resolved binary provenance.'`, matching the SKILL.md verb table at `manage-build-server/SKILL.md:177`.
- **Done when:** `grep -rn "Report running version + binary path" marketplace/` returns nothing.
- **Module/topic:** `plan-marshall:manage-build-server`

## G4 — Update the `_ping` docstring's documented response shape

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py:249-250` — `_ping`
- **What is wrong:** the Returns block still documents the decoded ping response as ``{'status': 'ok', 'pid': int, 'version': str}``. Since `8f3c7fe0` the daemon also returns `in_flight` and `queued`, and `run_status` depends on them.
- **Why it matters:** the docstring of the function that reads the handshake is where an implementer looks to learn what the handshake carries — and G1's whole failure mode is a reader assuming those keys are always present. The docstring currently implies the opposite (they are never present).
- **Fix:** extend the Returns block to name `in_flight` and `queued`, and state explicitly that a daemon older than the counts extension omits them.
- **Done when:** the `_ping` docstring names all five keys and the omission case.
- **Module/topic:** `plan-marshall:manage-build-server`

## G5 — Make the steward health-check pointer surface `binary_diverges`

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md:260-268` — "Build Server Status (read-only pointer)"
- **What is wrong:** the Health Check is told to run `manage-build-server status` and report "the returned `running` / `version` / `registered` fields". Those three fields are all still valid, so nothing here is factually wrong — but a stale daemon reports `running: true` with a plausible `version`, so the steward health check renders exactly the clean line the plan's problem statement calls the flagship archetype, while `binary_diverges: true` and the `note` sit unread in the same payload.
- **Why it matters:** D4 made the divergence visible in `status`; the one operator-facing health surface that consumes `status` does not relay it, so the drift stays hidden on the surface an operator actually consults.
- **Fix:** add `binary_diverges` (and the `note` when present) to the named field list in that section, with one sentence saying a `true` value means the running daemon is executing an older pinned copy and a reconcile is owed.
- **Done when:** `marshall-steward/SKILL.md` names `binary_diverges` in the Build Server Status section.
- **Module/topic:** `plan-marshall:marshall-steward`

## G6 — Fold the build-server client's own repeated degradation WARNINGs into the D5 escalation

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/build-server-client/scripts/build_server.py:441,451,462,473,522,532` — `run_submit`, `run_wait`
- **What is wrong:** D5's escalation is applied only in `_build_execute_factory._record_resolution`. When the daemon answers preflight and then dies mid-run, `_route_to_daemon` reaches `run_submit`/`run_wait`, each of which calls `_audit_log(plan_id, 'WARNING', 'build-server {submit,wait} degraded: reason=unreachable …')` on every build. Those work-log WARNINGs are identical build after build and are not counted or suppressed by the streak. (The flagship `socket_absent` path *is* fully covered: `run_preflight` at `:572-605` writes no log line, so only `_record_resolution` emitted there.)
- **Why it matters:** for the daemon-dies-mid-run class of outage, "a one-off fallback" and "the daemon has been gone all run" remain indistinguishable in the work log — the precise condition D5's "one transition beats ten repeats" was written to end.
- **Fix:** either route the client's degraded `_audit_log` calls through the same streak state (reusing `_update_fallback_streak`'s suppression signal), or drop the per-build client WARNING for `submit`/`wait` degradations and let `_record_resolution` — which already receives the reason and owns the escalation — be the single work-log emitter for a degraded routing.
- **Done when:** a test drives repeated `submit`-degraded routings for one plan and asserts the work log receives at most `_FALLBACK_WARN_STREAK` WARNINGs plus one ERROR, not one WARNING per build.
- **Module/topic:** `plan-marshall:build-server-client` + `plan-marshall:script-shared` build routing seam
