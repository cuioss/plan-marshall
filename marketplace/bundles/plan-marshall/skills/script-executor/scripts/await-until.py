#!/usr/bin/env python3
"""Poll until condition is satisfied. Uses run-config for adaptive timeouts."""

import argparse
import subprocess
import sys
import time

from run_config import timeout_get, timeout_set  # type: ignore[import-not-found]

# Direct imports - PYTHONPATH set by executor
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

DEFAULT_TIMEOUT = 300
DEFAULT_INTERVAL = 30


def match(parsed, pattern):
    """Check if parsed TOON matches field=value pattern."""
    if '=' in pattern:
        field, expected = pattern.split('=', 1)
        return str(parsed.get(field, '')).lower() == expected.lower()
    return bool(parsed.get(pattern))


def finish(status, start, polls, command_key, error=None):
    """Save timeout and output result."""
    duration = int(time.time() - start)
    timeout_set(command_key, duration)

    output = {'status': status, 'duration_seconds': duration, 'polls': polls, 'command_key': command_key}
    if error:
        output['error'] = error

    print(serialize_toon(output))
    sys.exit(0 if status == 'success' else 1)


def main():
    parser = argparse.ArgumentParser(description='Poll until condition is satisfied')
    parser.add_argument('--check-cmd', required=True)
    parser.add_argument('--success-field', required=True)
    parser.add_argument('--failure-field')
    parser.add_argument('--command-key', required=True)
    parser.add_argument('--interval', type=int, default=DEFAULT_INTERVAL)
    args = parser.parse_args()

    timeout = timeout_get(args.command_key, DEFAULT_TIMEOUT)
    start = time.time()
    polls = 0

    while time.time() - start < timeout:
        polls += 1
        result = subprocess.run(args.check_cmd, shell=True, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            parsed = parse_toon(result.stdout)
            if args.failure_field and match(parsed, args.failure_field):
                finish('failure', start, polls, args.command_key, 'Permanent failure')
            if match(parsed, args.success_field):
                finish('success', start, polls, args.command_key)

        time.sleep(args.interval)

    finish('timeout', start, polls, args.command_key, f'Timeout after {timeout}s')


if __name__ == '__main__':
    main()
