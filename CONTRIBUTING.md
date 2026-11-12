# Contributing

Issues and pull requests are welcome.

## Set up

```sh
git clone https://github.com/jpsanders/banner-builder && cd banner-builder
python3.15 -m venv .venv && . .venv/bin/activate
make init-dev
```

## Before a pull request

```sh
make format      # black and isort
make checks      # every check CI runs, in the same order
```

`make checks` runs isort, black, editorconfig-checker, darglint, flake8, mypy in strict mode, bandit, the man page
check and pytest with coverage. CI runs the same on Linux and macOS with Python 3.14 and 3.15, then installs the built
package on its own, builds a banner from the starter config and asks the MCP server to check it.

## Changing things

- **Behaviour** lives in `api.py`, which returns data. The CLI and the MCP server only present it.
- **The manual** is `docs/MANUAL.md`; `make man` rebuilds the packaged copy and the man page.
- **Test text** is placeholder text. Never a real person's banner.
