# Configuration Guide

Guide for configuring the component.

## Overview

This guide explains all configuration options.

## Configuration File

Create a `config.json` file with your settings:

```json
{
  "debug": false,
  "timeout": 5000,
  "retries": 3
}
```

## Options

### debug

Enable debug mode for verbose logging.

- **Type**: boolean
- **Default**: false

### timeout

Request timeout in milliseconds.

- **Type**: number
- **Default**: 5000

### retries

Number of retry attempts on failure.

- **Type**: number
- **Default**: 3

## Environment Variables

Override configuration with environment variables:

| Variable | Option |
|----------|--------|
| DEBUG | debug |
| TIMEOUT | timeout |
| RETRIES | retries |

Environment variables take precedence over config file values.
