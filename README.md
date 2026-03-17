# datasette-debug-gotham

[![PyPI](https://img.shields.io/pypi/v/datasette-debug-gotham.svg)](https://pypi.org/project/datasette-debug-gotham/)
[![Changelog](https://img.shields.io/github/v/release/datasette/datasette-debug-gotham?include_prereleases&label=changelog)](https://github.com/datasette/datasette-debug-gotham/releases)
[![Tests](https://github.com/datasette/datasette-debug-gotham/actions/workflows/test.yml/badge.svg)](https://github.com/datasette/datasette-debug-gotham/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/datasette/datasette-debug-gotham/blob/main/LICENSE)

A debugging utility for testing actor permissions/actions with DC Superheros (superman, Batman, Daily Planet, etc.)

## Installation

Install this plugin in the same environment as Datasette.
```bash
datasette install datasette-debug-gotham
```
## Usage

Usage instructions go here.

## Development

To set up this plugin locally, first checkout the code. You can confirm it is available like this:
```bash
cd datasette-debug-gotham
# Confirm the plugin is visible
uv run datasette plugins
```
To run the tests:
```bash
uv run pytest
```
