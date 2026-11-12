# Changelog

Versions follow [semantic versioning](https://semver.org). Tags carry the bare version, such as `1.0.0`.

## 1.0.0 (2026-11-12)

- Every command takes `--json` and prints one object: the layout, the rows, each theme's contrast ratios, problems
  and warnings from `check`; the written paths from `build`.
- An MCP server, `banner-builder mcp`, so an AI agent can find, write, check and build a banner. No new dependency.
- A Claude Code plugin with a skill, and the MCP server registered through uvx, so nothing needs installing first.
- A full manual: `banner-builder guide` prints it, `banner-builder man` shows it as a man page, and
  `banner-builder man --install` makes `man banner-builder` work.
- Python 3.14 or later; CI tests 3.14 and 3.15 on Linux and macOS and builds a banner from the installed wheel.
- A release workflow that attaches the wheel and the sdist, Dependabot, issue forms, a security policy and a code of
  conduct.
- The release tag is now `0.1.0` for the first version, without the v.

## 0.1.0 (2026-10-08)

The first version: `init`, `check`, `build` and `path`, light and dark themes, SVG with embedded font subsets and PNG
through resvg, fit, glyph and WCAG AA contrast checks.
