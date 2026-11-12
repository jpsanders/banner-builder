"""
The ``banner-builder`` command.

``init`` writes a starter config, ``check`` tests it without writing anything, ``build`` writes the banner files and
``path`` prints where the config is read from. Each takes ``--json``. ``guide`` prints the full manual, ``man`` shows
the man page and ``mcp`` serves the same commands to AI agents over the Model Context Protocol.
"""

import argparse
import json
import os
import shutil
import subprocess  # nosec B404: runs man with fixed arguments only
import sys
from collections.abc import Sequence
from importlib import metadata, resources
from pathlib import Path
from typing import Any

from banner_builder import api
from banner_builder.config import default_path

PROG = "banner-builder"


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the command line.

    :param argv: The arguments after the program name, or ``None`` to read them from ``sys.argv``
    :returns: The exit status: 0 on success, 1 when something has to be fixed first
    """
    args = _parser().parse_args(argv)
    try:
        return int(args.run(args))
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(error)}))
        else:
            _say(str(error) if isinstance(error, FileExistsError) else f"error: {error}")
        return 1


def _parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    default = str(default_path()).replace("%", "%%")
    shared.add_argument("--config", type=Path, metavar="PATH", help=f"the config file (default: {default})")
    shared.add_argument("--json", action="store_true", help="print one JSON object instead of text")

    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Build a profile banner from a config file that stays on your machine.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    commands = parser.add_subparsers(title="commands", metavar="COMMAND", required=True)

    init = commands.add_parser("init", parents=[shared], help="write a starter config to edit")
    init.add_argument("--force", action="store_true", help="replace an existing config with the starter")
    init.set_defaults(run=_init)

    check = commands.add_parser("check", parents=[shared], help="test the config and the layout, write nothing")
    check.set_defaults(run=_check)

    build = commands.add_parser("build", parents=[shared], help="write the banner files")
    build.add_argument("--out", type=Path, metavar="DIR", help="the folder to write into (default: [output] dir)")
    build.add_argument("--theme", action="append", metavar="NAME", help="build only this theme, repeat for more")
    build.add_argument("--format", action="append", choices=("png", "svg"), help="write only this format")
    build.add_argument("--scale", action="append", type=int, choices=(1, 2, 3, 4), help="write only this PNG scale")
    build.set_defaults(run=_build)

    where = commands.add_parser("path", parents=[shared], help="print where the config is read from")
    where.set_defaults(run=_path)

    guide = commands.add_parser("guide", help="print the full manual, for people and agents")
    guide.set_defaults(run=_guide)

    man = commands.add_parser("man", help="show the man page")
    man.add_argument("--install", action="store_true", help=f"install it so `man {PROG}` works")
    man.add_argument("--raw", action="store_true", help="print the roff source")
    man.set_defaults(run=_man)

    mcp = commands.add_parser("mcp", help="serve the commands to AI agents over MCP, on stdio")
    mcp.set_defaults(run=_mcp)
    return parser


def _init(args: argparse.Namespace) -> int:
    result = api.init(args.config, force=args.force)
    if args.json:
        return _json({"ok": True, **result})
    print(f"wrote {result['wrote']}")
    print("Edit it, then run `banner-builder check` and `banner-builder build`.")
    for warning in result["warnings"]:
        _say(f"warning: {warning}")
    return 0


def _check(args: argparse.Namespace) -> int:
    report = api.check(args.config)
    if args.json:
        return _json(report, 0 if report["ok"] else 1)
    for warning in report["warnings"]:
        _say(f"warning: {warning}")
    if "rows" in report:
        _report(report)
    if report["problems"]:
        return _fail(report["problems"])
    print("ok")
    return 0


def _build(args: argparse.Namespace) -> int:
    result = api.build(args.config, args.out, args.theme, args.format, args.scale)
    if args.json:
        return _json(result, 0 if result["ok"] else 1)
    if result["problems"]:
        return _fail(result["problems"])
    for written in result["written"]:
        print(written)
    return 0


def _path(args: argparse.Namespace) -> int:
    result = api.config_path(args.config)
    if args.json:
        return _json(result)
    print(result["path"])
    if not result["exists"]:
        _say("that file does not exist yet: run `banner-builder init` to create it")
    return 0


def _data(name: str) -> str:
    return (resources.files("banner_builder") / "data" / name).read_text(encoding="utf-8")


def _guide(args: argparse.Namespace) -> int:
    print(_data("MANUAL.md"), end="")
    return 0


def _man(args: argparse.Namespace) -> int:
    page = _data(f"{PROG}.1")
    if args.install:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        target = Path(base) / "man" / "man1" / f"{PROG}.1"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        print(f"installed {target}; open it with: man {PROG}")
        return 0
    man = shutil.which("man")
    if man and sys.stdout.isatty() and not args.raw:
        with resources.as_file(resources.files("banner_builder") / "data" / f"{PROG}.1") as path:
            return subprocess.call([man, "-l", str(path)])  # nosec B603: man, fixed arguments
    print(page, end="")
    return 0


def _mcp(args: argparse.Namespace) -> int:
    from banner_builder import mcp

    mcp.serve_stdio()
    return 0


def _report(report: dict[str, Any]) -> None:
    rows = report["rows"]
    parts = [] if rows["kicker"] is None else [f"kicker {rows['kicker']}"]
    parts.append("headline " + ", ".join(str(y) for y in rows["headline"]))
    if rows["rule"] is not None:
        parts.append(f"rule {rows['rule']}")
    if rows["footer"] is not None:
        parts.append(f"footer {rows['footer']}")
    canvas = report["canvas"]
    print(f"config    {report['config']}")
    print(
        f"canvas    {canvas['width']} x {canvas['height']}, text from x {canvas['text_from']} to x {canvas['text_to']}"
    )
    print(f"headline  {report['headline_size']}px")
    print(f"rows      {' · '.join(parts)}")
    for index, (name, ratios) in enumerate(report["contrast"].items()):
        shown = ", ".join(f"{role} {ratio:.2f}" for role, ratio in ratios.items())
        print(f"{'contrast' if index == 0 else '':9} {name}: {shown}")


def _fail(problems: Sequence[str]) -> int:
    for problem in problems:
        _say(f"problem: {problem}")
    count = len(problems)
    _say(f"{count} problem{'' if count == 1 else 's'} to fix. Nothing was written.")
    return 1


def _json(data: dict[str, Any], code: int = 0) -> int:
    print(json.dumps(data))
    return code


def _say(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)


def _version() -> str:
    try:
        return metadata.version(PROG)
    except metadata.PackageNotFoundError:
        return "unknown"
