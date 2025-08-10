# Contributing

Thanks for your interest in contributing! Please follow these steps:

- Fork the repo and create a feature branch.
- Run linters and tests before committing.
- Submit a PR with a clear description and checklist.

## Development setup

- Python 3.11+
- Install dependencies:
  ```bash
  pip3 install -r requirements.txt
  ```
- Optional dev tools:
  ```bash
  pip3 install ruff pre-commit pytest
  pre-commit install
  ```

## Code style
- Use Ruff for lint/format: `ruff check .` and `ruff format .`
- Prefer clear naming and small functions.

## Commit messages
- Use concise, imperative style: "Add X", "Fix Y".

## Pull Requests
- Link related issues.
- Include screenshots/gifs for UX changes.
- Ensure CI is green.