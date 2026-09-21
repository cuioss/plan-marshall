envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:16:38Z

kind=candidate-lesson
module=plan-marshall
enrich_verb=insight
source_plan=implement-plan-09-interaction-mode
disposition=taken_into_account
recurrence_count=6

# Owed architecture hint: CI wait-deadline transients

Target: `--module plan-marshall` via `enrich insight`.

Hint text: The project treats CI wait-deadline transients as a standing
consideration in plan-marshall: when CI reports in-progress at the wait
deadline with no failing conclusion, re-wait the gate rather than opening
fix tasks.
