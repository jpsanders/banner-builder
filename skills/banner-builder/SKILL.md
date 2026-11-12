---
name: banner-builder
description: Make or update a profile banner (LinkedIn's 1584 by 396 by default, or any size) as PNG and SVG with banner-builder, from a TOML config that stays on the user's machine. Use when the user asks for a LinkedIn banner, a profile header or cover image, or to change the words, colours or size of their banner.
---

# Build a profile banner with banner-builder

banner-builder draws the banner from one config file in the user's home folder. It checks the layout and the colour
contrast (WCAG AA, 4.5:1) before it writes anything, and it makes no network requests.

## Get the tool

If `banner-builder` is not on the PATH, install it, or run it through uvx without installing:

```sh
uv tool install git+https://github.com/jpsanders/banner-builder@1.0.0
uvx --from git+https://github.com/jpsanders/banner-builder@1.0.0 banner-builder --version
```

When this skill came with the Claude Code plugin, the `banner-builder` MCP server is already registered and its tools
(`config_path`, `init`, `check`, `build`) do the same as the commands below.

## Steps

1. Find the config: `banner-builder path --json`. If `exists` is false, write the starter with `banner-builder init`.
2. Ask the user for the words if you do not have them: a kicker (small capitals, optional), the headline lines, and
   the footer row. Words between asterisks are drawn in the accent colour.
3. Edit the TOML file at that path. Only `[text] lines` is required; change only what the user asked for.
4. Run `banner-builder check --json`. Fix every entry in `problems` (text too wide, missing glyphs, low contrast)
   and run it again until `ok` is true.
5. Run `banner-builder build --json` and report the paths in `written`. For LinkedIn the file to upload is
   `banner-light@2x.png` (or the dark one).

## Rules

- The config holds the user's own words. Never copy it into a git repository or paste it anywhere public;
  `check` warns when it sits inside one.
- Do not lower the contrast rule to make a colour pass; pick a darker or lighter colour instead.
- `banner-builder guide` prints the full manual, every config key included.
