# Security

## Reporting a vulnerability

Please report security problems privately, through GitHub's
[private vulnerability reporting](https://github.com/jpsanders/banner-builder/security/advisories/new), not in a
public issue. You will get an answer within a week.

## What banner-builder does on your machine

It reads one TOML file and the fonts it names, and writes SVG and PNG files into the output folder, replacing earlier
files of the same name. `init` writes the starter config and refuses to replace one unless `--force` is given.
`man --install` writes one file into your per user man folder. It makes no network requests and runs no other
program, except `man` to show the man page.

The MCP server offers the same four actions and nothing else. It runs with your permissions, so an agent that calls
`build` with an `out` folder writes there.
