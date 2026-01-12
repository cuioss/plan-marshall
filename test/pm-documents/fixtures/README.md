# Test Fixtures

This directory contains test fixtures for pm-documents scripts.

## Purpose

Test files are created dynamically by test scripts and cleaned up after execution.

## Test Scripts

- `test-verify-links-false-positives.sh` - Tests link classification script
- `test-analyze-content-tone.sh` - Tests content tone analysis script

## Usage

```bash
# Run individual test
bash test/pm-documents/test-verify-links-false-positives.sh

# Run all tests
bash test/pm-documents/test-*.sh
```
