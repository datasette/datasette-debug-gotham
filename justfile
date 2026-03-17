# Formatting
format *flags:
    uv run ruff format {{flags}}

format-check *flags:
    uv run ruff format --check {{flags}}

# Type checking
check:
    uvx ty check

# Development
dev *flags:
    DATASETTE_SECRET=abc123 uv run datasette {{flags}}
