# banner-builder

## NAME

banner-builder - build a profile banner as SVG and PNG from a config file that stays on your machine

## SYNOPSIS

```
banner-builder init [--force] [--config PATH] [--json]
banner-builder check [--config PATH] [--json]
banner-builder build [--out DIR] [--theme NAME]... [--format png|svg]... [--scale 1-4]... [--config PATH] [--json]
banner-builder path [--config PATH] [--json]
banner-builder guide
banner-builder man [--install | --raw]
banner-builder mcp
banner-builder --version
```

## DESCRIPTION

banner-builder draws a profile banner, LinkedIn's 1584 by 396 by default, from one TOML file. The file holds the
words, the colours and where the output goes, and it lives in your home folder rather than in any repository, so the
banner text never ends up in a commit. The fonts ship with the package and resvg draws the PNG, so a build needs no
browser and makes no network request.

Every build is checked first. The text must fit between the margins, every glyph must exist in its font, and every
text colour must reach 4.5:1 contrast against the background in every theme, the WCAG AA minimum. When a check
fails nothing is written, and the problem says what to change.

## COMMANDS

| Command | What it does |
| --- | --- |
| `init` | Write the starter config, every key documented next to its default. Refuses to replace a config. |
| `check` | Test the config, the layout and the contrast; print the sizes, rows and ratios; write nothing. |
| `build` | Run the same checks, then write the SVG and PNG files for each theme and scale. |
| `path` | Print where the config is read from, and say if it does not exist yet. |
| `guide` | Print this manual as Markdown, for people and agents. |
| `man` | Show this manual as a man page. `--install` puts it where `man banner-builder` finds it. |
| `mcp` | Serve init, check, build and path to AI agents over the Model Context Protocol, on stdio. |

## OPTIONS

| Option | Meaning |
| --- | --- |
| `--config PATH` | Read this config instead of the default. |
| `--json` | Print one JSON object instead of text. Exit codes stay the same. |
| `--force` | With `init`: replace an existing config with the starter. |
| `--out DIR` | With `build`: write into this folder instead of the config's `[output] dir`. |
| `--theme NAME` | With `build`: build only this theme. Repeat for more. |
| `--format png` | With `build`: write only this format, `png` or `svg`. Repeat for both. |
| `--scale N` | With `build`: write only this PNG scale, 1 to 4. Repeat for more. |
| `--install` | With `man`: install the man page into the per user man folder. |
| `--raw` | With `man`: print the roff source instead of opening a pager. |
| `--version` | Print the version and exit. |

## THE CONFIG

Only `[text] lines` is required. `init` writes a starter that documents every key next to its default.

### [text]

- `kicker`: small capitals above the headline; empty leaves the row out.
- `lines`: the headline, one string per line, drawn as large as the space allows. Words between asterisks are drawn
  in the accent colour; write `\\*` inside double quotes for a literal asterisk.
- `footer_left`, `footer_right`: the row under the rule, left in the ink colour and right in the accent colour.
  Leave both empty to drop the rule and the row.

### [canvas]

`width` 1584 and `height` 396 by default. `left` 448 keeps the text clear of LinkedIn's profile photo, `right` 96 is
the right margin, `top` 77 runs from the top edge to the top of the first capitals, and `bottom` 24 is the least space
under the last baseline; the headline shrinks to keep it, down to 24 pixels.

### [type]

`max_headline` 84 caps the headline size. `kicker_size` 20 and `footer_size` 25 set the small rows.
`headline_tracking` -0.025 and `kicker_tracking` 0.14 set letter spacing in ems.

### [fonts]

`display` draws the headline and `mono` the rest, each as `{ file = "", weight = N }`. An empty file means the
bundled font: Space Grotesk and JetBrains Mono, both under the SIL Open Font License. A relative path is read from the
config's folder. A variable font is pinned to the weight given.

### [themes.NAME]

Five colours per theme: `background`, `ink`, `soft`, `rule` and `accent`, as `#rrggbb` or `oklch(L C H)`. The light
and dark themes exist already, so set only what you change. A new theme needs all five.

### [output]

`dir` "." (relative to where you run the command), `name` "banner", `themes` light and dark, `formats` png and svg,
`scales` 1 and 2. Files are named `<name>-<theme>.svg`, `<name>-<theme>.png` and `<name>-<theme>@2x.png`.

## CHECKS

| Check | Rule |
| --- | --- |
| Width | The kicker and the footer fit between the margins. The headline is sized to fit. |
| Height | The last row stays `bottom` pixels clear of the bottom edge. |
| Glyphs | Each font has every character it is asked to draw. |
| Contrast | Ink, soft and accent reach 4.5:1 against the background in every theme built. |

## JSON OUTPUT

`check --json` prints `ok`, `config`, `problems`, `warnings` and `canvas`, and when the layout fits also
`headline_size`, `rows` (the kicker, headline, rule and footer baselines) and `contrast` (each theme's ratios):

```
{"ok": true, "config": "/home/me/.config/banner-builder/banner.toml", "problems": [], "warnings": [],
 "canvas": {"width": 1584, "height": 396, "text_from": 448, "text_to": 1488}, "headline_size": 84,
 "rows": {"kicker": 92, "headline": [180, 271], "rule": 311, "footer": 357},
 "contrast": {"light": {"ink": 16.61, "soft": 5.44, "accent": 4.79},
              "dark": {"ink": 15.75, "soft": 7.74, "accent": 7.53}}}
```

`build --json` prints `ok`, `written` (the paths) and `problems`. `init --json` prints `ok`, `wrote` and `warnings`.
`path --json` prints `path` and `exists`. An error prints `{"ok": false, "error": "..."}`.

## MCP SERVER

`banner-builder mcp` speaks JSON-RPC 2.0 over stdio with no dependencies. Its tools are `config_path`, `init`,
`check` and `build`, with the same arguments and results as the JSON output. `check` and `config_path` are marked read
only; `init` is marked destructive because `force` replaces a config. Register it with any MCP client:

```
{"mcpServers": {"banner-builder": {"command": "banner-builder", "args": ["mcp"]}}}
```

## ENVIRONMENT

`BANNER_BUILDER_CONFIG` points at another config file. `XDG_CONFIG_HOME` moves the default config folder.
`XDG_DATA_HOME` moves the man folder `man --install` writes to.

## FILES

`~/.config/banner-builder/banner.toml` is the default config. `~/.local/share/man/man1/banner-builder.1` is where
`man --install` puts the man page.

## EXIT STATUS

0 on success. 1 when a check failed or the config is missing or invalid; nothing was written. 2 when the arguments
are wrong.

## EXAMPLES

Start, check and build:

```
banner-builder init
banner-builder check
banner-builder build
```

Write only the file to upload to LinkedIn:

```
banner-builder build --theme light --format png --scale 2
```

## FOR AGENTS

Use `--json` or the MCP tools and read `problems` and `warnings`; they name what to change. The config holds the
user's own words: edit it where `path` says it is, never copy it into a repository, and do not paste it anywhere
public. A good loop is: `path`, `init` if missing, edit the TOML, `check` until `ok` is true, then `build`.

## PRIVACY

The config is read from your home folder. `init` and `check` warn when it sits inside a git repository. The tool
makes no network requests.

## SEE ALSO

https://github.com/jpsanders/banner-builder

## AUTHOR

James Phillip Sanders, https://jamesphillipsanders.com
