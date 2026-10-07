envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:13:15Z

component=plan-marshall:plan-retrospective:check-artifact-consistency
category=bug

# Pass declared flags to retrospective consistency checks

Source: work-log script_failure 2026-09-16T15:58:50Z, notation plan-marshall:plan-retrospective:check-artifact-consistency exit 2, detail naming declared flags archived-plan-path, mode, plan-id.

Defect: retrospective invoked the consistency check without its required flags, so argparse rejected before any artifact was examined.

Rule: run --help first when invoking a retrospective helper whose surface recently changed; quote the declared flag names verbatim.

Evidence: the rejection detail lists the accepted flag set, making the correction mechanical.
