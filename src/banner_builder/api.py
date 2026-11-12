"""
What the command line and the MCP server both call.

Each function takes plain arguments and returns plain data, so ``--json``, the MCP tools and the human output all
come from one place. Nothing here prints.
"""

from dataclasses import replace
from importlib import resources
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont

from banner_builder import fonts, layout, render
from banner_builder.config import Config, default_path, load


def resolve(config: str | Path | None) -> Path:
    """
    Turn an optional config path into the path that will be read.

    :param config: A path, or None for the default (``BANNER_BUILDER_CONFIG``, then the XDG config folder)
    :returns: The expanded path
    """
    return Path(config).expanduser() if config else default_path()


def repository_warning(path: Path) -> str | None:
    """
    Warn when a config sits inside a git repository, where a commit would publish its words.

    :param path: The config path
    :returns: The warning, or None
    """
    for folder in path.resolve().parents:
        if (folder / ".git").exists():
            return f"{path} is inside the git repository at {folder}, so your banner text could be committed"
    return None


def config_path(config: str | Path | None = None) -> dict[str, Any]:
    """
    Say where the config is read from and whether it exists.

    :param config: An explicit path, or None for the default
    :returns: ``{"path", "exists"}``
    """
    path = resolve(config)
    return {"path": str(path), "exists": path.is_file()}


def init(config: str | Path | None = None, force: bool = False) -> dict[str, Any]:
    """
    Write the starter config.

    :param config: Where to write it, or None for the default
    :param force: Replace an existing config
    :returns: ``{"wrote", "warnings"}``
    :raises FileExistsError: When a config is already there and ``force`` is not set
    """
    path = resolve(config)
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Edit it, or pass --force to replace it with the starter config.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(starter(), encoding="utf-8")
    warning = repository_warning(path)
    return {"wrote": str(path), "warnings": [warning] if warning else []}


def starter() -> str:
    """
    Return the starter config, with every key documented next to its default.

    :returns: TOML text
    """
    return resources.files("banner_builder").joinpath("example.toml").read_text(encoding="utf-8")


def load_fonts(config: Config) -> tuple[TTFont, TTFont]:
    """
    Load the display and mono fonts the config names.

    :param config: The loaded config
    :returns: The display font and the mono font
    """
    return fonts.load(config.display, "display"), fonts.load(config.mono, "mono")


def check(config: str | Path | None = None) -> dict[str, Any]:
    """
    Test the config, the layout and the colours, and write nothing.

    :param config: The config path, or None for the default
    :returns: The layout, the contrast ratios, problems and warnings; ``ok`` is true when there are no problems
    """
    path = resolve(config)
    loaded = load(path)
    plan = layout.plan(loaded, *load_fonts(loaded))
    problems = [*plan.problems, *layout.contrast_problems(loaded, loaded.build_themes)]
    warning = repository_warning(path)
    report: dict[str, Any] = {
        "ok": not problems,
        "config": str(path),
        "problems": problems,
        "warnings": [warning] if warning else [],
        "canvas": {
            "width": loaded.width,
            "height": loaded.height,
            "text_from": loaded.left,
            "text_to": loaded.width - loaded.right,
        },
    }
    if not plan.problems:
        report["headline_size"] = plan.headline_size
        report["rows"] = {
            "kicker": plan.kicker_y,
            "headline": [line.y for line in plan.lines],
            "rule": plan.rule_y,
            "footer": plan.footer_y,
        }
        report["contrast"] = {
            name: {role: round(ratio, 2) for role, ratio in layout.ratios(loaded.themes[name]).items()}
            for name in loaded.build_themes
        }
    return report


def build(
    config: str | Path | None = None,
    out: str | Path | None = None,
    themes: list[str] | None = None,
    formats: list[str] | None = None,
    scales: list[int] | None = None,
) -> dict[str, Any]:
    """
    Write the banner files, unless a check fails first, in which case nothing is written.

    :param config: The config path, or None for the default
    :param out: The folder to write into, or None for the config's ``[output] dir``
    :param themes: Only these themes, or None for the config's list
    :param formats: Only these formats (``png``, ``svg``), or None for the config's list
    :param scales: Only these PNG scales (1 to 4), or None for the config's list
    :returns: ``{"ok", "written", "problems"}``
    :raises ValueError: When a theme is unknown or an argument is out of range
    """
    loaded = load(resolve(config))
    names = tuple(themes or loaded.build_themes)
    unknown = [name for name in names if name not in loaded.themes]
    if unknown:
        raise ValueError(f"no theme named {', '.join(unknown)}: define it as [themes.<name>] in the config")
    wrong = [f for f in formats or [] if f not in ("png", "svg")] + [
        str(s) for s in scales or [] if s not in range(1, 5)
    ]
    if wrong:
        raise ValueError(f"not a format (png, svg) or a scale (1 to 4): {', '.join(wrong)}")
    font_pair = load_fonts(loaded)
    plan = layout.plan(loaded, *font_pair)
    problems = [*plan.problems, *layout.contrast_problems(loaded, names)]
    if problems:
        return {"ok": False, "written": [], "problems": problems}
    if scales:
        loaded = replace(loaded, scales=tuple(scales))
    out_dir = Path(out).expanduser() if out else loaded.out_dir
    written = render.build(loaded, plan, font_pair, out_dir, names, tuple(formats or loaded.formats))
    return {"ok": True, "written": [str(p) for p in written], "problems": []}
