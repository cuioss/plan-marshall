"""
Phase-based plan command handler for plan-marshall-config.

Handles plan sub-nouns: phase-1-init, phase-2-refine, phase-5-execute,
phase-6-finalize.

All phases read/write from config['plan'][phase_section].
"""

from _config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    error_exit,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)

# Valid phase sections
PHASE_SECTIONS = {
    'phase-1-init',
    'phase-2-refine',
    'phase-3-outline',
    'phase-4-plan',
    'phase-5-execute',
    'phase-6-finalize',
}

# Phases that have max_iterations and boolean steps
PIPELINE_PHASES = {'phase-5-execute', 'phase-6-finalize'}

# Phases with simple scalar fields only
SCALAR_PHASES = {'phase-1-init', 'phase-2-refine', 'phase-3-outline', 'phase-4-plan'}


def _coerce_value(value: str) -> str | bool | int:
    """Coerce string value to appropriate Python type."""
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    elif value.isdigit():
        return int(value)
    return value


def cmd_phase(args, phase_section: str) -> int:
    """Handle phase-based plan sub-nouns.

    Args:
        args: Parsed arguments with verb and optional parameters
        phase_section: Phase key (e.g., 'phase-5-execute')
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    plan_config = config.get('plan', {})
    section = plan_config.get(phase_section, {})

    if args.verb == 'get':
        field = getattr(args, 'field', None)
        if field:
            if field not in section:
                return error_exit(f"Unknown field '{field}' in {phase_section}")
            return success_exit({'phase': phase_section, 'field': field, 'value': section[field]})
        return success_exit({'phase': phase_section, **section})

    elif args.verb == 'set' and phase_section in (SCALAR_PHASES | {'phase-5-execute'}):
        field = args.field
        value = _coerce_value(args.value)
        section[field] = value
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'field': field, 'value': value})

    elif args.verb == 'set-max-iterations' and phase_section in PIPELINE_PHASES:
        value = int(args.value)
        key = 'verification_max_iterations' if phase_section == 'phase-5-execute' else 'max_iterations'
        section[key] = value
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, key: value})

    elif args.verb == 'set-step' and phase_section in PIPELINE_PHASES:
        step = args.step
        enabled = args.enabled.lower() == 'true'

        # Validate step exists as a numbered boolean key
        if step not in section:
            return error_exit(f"Unknown step '{step}' in {phase_section}")

        section[step] = enabled
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'step': step, 'enabled': enabled})

    elif args.verb == 'set-domain-step' and phase_section == 'phase-5-execute':
        domain = args.domain
        step = args.step
        enabled = args.enabled.lower() == 'true'

        domain_steps = section.get('verification_domain_steps', {})
        if domain not in domain_steps:
            return error_exit(f"Unknown domain '{domain}' in verification_domain_steps")

        domain_step_config = domain_steps[domain]
        if step not in domain_step_config:
            return error_exit(f"Unknown step '{step}' in verification_domain_steps.{domain}")

        # When disabling, set to false; when enabling, caller must provide agent reference
        if not enabled:
            domain_step_config[step] = False
        else:
            # Re-enable requires the original agent reference
            # If currently false, we can't restore it - caller should use set-domain-step-agent
            if domain_step_config[step] is False:
                return error_exit(
                    f"Cannot re-enable step '{step}' without agent reference. "
                    f'Use set-domain-step-agent to set the agent.'
                )

        domain_steps[domain] = domain_step_config
        section['verification_domain_steps'] = domain_steps
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'domain': domain, 'step': step, 'enabled': enabled})

    elif args.verb == 'set-domain-step-agent' and phase_section == 'phase-5-execute':
        domain = args.domain
        step = args.step
        agent = args.agent

        domain_steps = section.get('verification_domain_steps', {})
        if domain not in domain_steps:
            domain_steps[domain] = {}

        domain_steps[domain][step] = agent
        section['verification_domain_steps'] = domain_steps
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'domain': domain, 'step': step, 'agent': agent})

    return EXIT_ERROR
