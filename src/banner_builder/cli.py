"""
The ``banner-builder`` command.

``init`` writes a starter config, ``check`` tests it without writing anything, ``build`` writes the banner files and
``path`` prints where the config is read from.
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import replace
from importlib import metadata, resources
from pathlib import Path

from fontTools.ttLib import TTFont

from banner_builder import fonts, layout, render
from banner_builder.config import Config, default_path, load


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the command line.

    :param argv: The arguments after the program name, or ``None`` to read them from ``sys.argv``
    :returns: The exit status: 0 on success, 1 when something has to be fixed first
    """
    args = _parser().parse_args(argv)
    path = args.config.expanduser() if args.config else default_path()
    try:
        return int(args.run(args, path))
    except (FileNotFoundError, ValueError) as error:
        _say(f"error: {error}")
        return 1


def _parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    default = str(default_path()).replace("%", "%%")
    shared.add_argument("--config", type=Path, metavar="PATH", help=f"the config file (default: {default})")

    parser = argparse.ArgumentParser(
        prog="banner-builder",
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
    return parser


def _init(args: argparse.Namespace, path: Path) -> int:
    if path.exists() and not args.force:
        _say(f"{path} already exists. Edit it, or pass --force to replace it with the starter config.")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    starter = resources.files("banner_builder").joinpath("example.toml").read_text(encoding="utf-8")
    path.write_text(starter, encoding="utf-8")
    print(f"wrote {path}")
    print("Edit it, then run `banner-builder check` and `banner-builder build`.")
    _warn_if_in_repository(path)
    return 0


def _check(args: argparse.Namespace, path: Path) -> int:
    config = load(path)
    _warn_if_in_repository(path)
    plan = layout.plan(config, *_fonts(config))
    problems = [*plan.problems, *layout.contrast_problems(config, config.build_themes)]
    if not plan.problems:
        _report(path, config, plan)
    if problems:
        return _fail(problems)
    print("ok")
    return 0


def _build(args: argparse.Namespace, path: Path) -> int:
    config = load(path)
    themes = tuple(args.theme or config.build_themes)
    unknown = [name for name in themes if name not in config.themes]
    if unknown:
        raise ValueError(f"no theme named {', '.join(unknown)}: define it as [themes.<name>] in the config")
    loaded = _fonts(config)
    plan = layout.plan(config, *loaded)
    problems = [*plan.problems, *layout.contrast_problems(config, themes)]
    if problems:
        return _fail(problems)
    if args.scale:
        config = replace(config, scales=tuple(args.scale))
    out_dir = args.out.expanduser() if args.out else config.out_dir
    for written in render.build(config, plan, loaded, out_dir, themes, tuple(args.format or config.formats)):
        print(written)
    return 0


def _path(args: argparse.Namespace, path: Path) -> int:
    print(path)
    if not path.is_file():
        _say("that file does not exist yet: run `banner-builder init` to create it")
    return 0


def _fonts(config: Config) -> tuple[TTFont, TTFont]:
    return fonts.load(config.display, "display"), fonts.load(config.mono, "mono")


def _report(path: Path, config: Config, plan: layout.Layout) -> None:
    rows = [] if plan.kicker_y is None else [f"kicker {plan.kicker_y}"]
    rows.append("headline " + ", ".join(str(line.y) for line in plan.lines))
    if plan.rule_y is not None:
        rows.append(f"rule {plan.rule_y}")
    if plan.footer_y is not None:
        rows.append(f"footer {plan.footer_y}")
    print(f"config    {path}")
    print(f"canvas    {config.width} x {config.height}, text from x {config.left} to x {config.width - config.right}")
    print(f"headline  {plan.headline_size}px")
    print(f"rows      {' · '.join(rows)}")
    for index, name in enumerate(config.build_themes):
        ratios = ", ".join(f"{role} {ratio:.2f}" for role, ratio in layout.ratios(config.themes[name]).items())
        print(f"{'contrast' if index == 0 else '':9} {name}: {ratios}")


def _fail(problems: Sequence[str]) -> int:
    for problem in problems:
        _say(f"problem: {problem}")
    count = len(problems)
    _say(f"{count} problem{'' if count == 1 else 's'} to fix. Nothing was written.")
    return 1


def _warn_if_in_repository(path: Path) -> None:
    for folder in path.resolve().parents:
        if (folder / ".git").exists():
            _say(f"warning: {path} is inside the git repository at {folder}, so your banner text could be committed")
            return


def _say(message: str) -> None:
    print(f"banner-builder: {message}", file=sys.stderr)


def _version() -> str:
    try:
        return metadata.version("banner-builder")
    except metadata.PackageNotFoundError:
        return "unknown"
