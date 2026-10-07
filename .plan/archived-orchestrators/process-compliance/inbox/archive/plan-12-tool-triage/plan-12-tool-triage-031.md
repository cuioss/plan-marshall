envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:44:02Z

# A routed whole-tree verify was killed at 783 s while the learned budget is 1434 s

**Observed (plan-12-tool-triage, 5-execute loop-back, 2026-09-29):** a whole-tree `verify` routed to marshalld (`resolved=routed, mechanism=daemon_longpoll`) returned `status: timeout, error: timeout, timeout_used_seconds: 784`. The daemon's job log confirms the build itself (`./pw verify`) was stopped at 783 s — not the client's wait, not the harness Bash ceiling. `run_config timeout measured --command python:verify` reports `measured: true, timeout_seconds: 1434`, and whole-tree verifies on this branch took 917–1078 s. An identical re-run minutes later completed green in 994 s, so it ran under a budget ≥ 994 s.

**The defect:** the budget the daemon enforced on the first run was neither the learned `python:verify` value nor derivable from anything the caller saw. The resolver's own `bash_timeout_seconds` for the same canonical varied across this run (1958, then later values), and nothing in the result TOON names the budget's source. A non-finish caused by an unexplained short budget reads identically to a genuinely slow build, costs a full ~13-minute re-run, and — without the operator asking — would have prompted a budget change aimed at the wrong knob.

**Suggested fix:** have the daemon echo the budget's provenance (`timeout_source: learned|default|explicit|...`, command key) in the result TOON, and establish why a routed build received 783 s when the learned key held 1434 s.
