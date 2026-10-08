"""
Load and validate the banner config.

The config holds everything personal about a banner: the words, the colours and where the files go. It lives on the
user's machine, by default at ``~/.config/banner-builder/banner.toml``, and never inside this repository.
"""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from banner_builder.color import to_hex

ROLES = ("background", "ink", "soft", "rule", "accent")
FORMATS = ("png", "svg")

DEFAULT_THEMES: dict[str, dict[str, str]] = {
    "light": {
        "background": "oklch(0.973 0.008 78)",
        "ink": "oklch(0.205 0.014 62)",
        "soft": "oklch(0.505 0.020 66)",
        "rule": "oklch(0.878 0.012 74)",
        "accent": "oklch(0.545 0.128 52)",
    },
    "dark": {
        "background": "oklch(0.205 0.014 62)",
        "ink": "oklch(0.955 0.008 78)",
        "soft": "oklch(0.740 0.018 70)",
        "rule": "oklch(0.330 0.014 62)",
        "accent": "oklch(0.740 0.125 58)",
    },
}

_SECTIONS: dict[str, set[str]] = {
    "canvas": {"width", "height", "left", "right", "top", "bottom"},
    "text": {"kicker", "lines", "footer_left", "footer_right"},
    "type": {"max_headline", "kicker_size", "footer_size", "headline_tracking", "kicker_tracking"},
    "fonts": {"display", "mono"},
    "themes": set(),
    "output": {"dir", "name", "themes", "formats", "scales"},
}


@dataclass(frozen=True)
class Theme:
    """A palette of five ``#rrggbb`` colours."""

    background: str
    ink: str
    soft: str
    rule: str
    accent: str


@dataclass(frozen=True)
class FontSpec:
    """A font file, or ``None`` for the bundled one, and the weight to render it at."""

    file: Path | None
    weight: int


@dataclass(frozen=True)
class Config:
    """Everything needed to build one banner in one or more themes."""

    lines: tuple[str, ...]
    kicker: str = ""
    footer_left: str = ""
    footer_right: str = ""
    width: int = 1584
    height: int = 396
    left: int = 448
    right: int = 96
    top: int = 77
    bottom: int = 24
    max_headline: int = 84
    kicker_size: int = 20
    footer_size: int = 25
    headline_tracking: float = -0.025
    kicker_tracking: float = 0.14
    display: FontSpec = FontSpec(None, 500)
    mono: FontSpec = FontSpec(None, 400)
    themes: dict[str, Theme] = field(default_factory=dict)
    out_dir: Path = Path(".")
    name: str = "banner"
    build_themes: tuple[str, ...] = ("light", "dark")
    formats: tuple[str, ...] = FORMATS
    scales: tuple[int, ...] = (1, 2)


def default_path() -> Path:
    """
    Return where the config lives when no path is given.

    ``BANNER_BUILDER_CONFIG`` wins, then ``$XDG_CONFIG_HOME/banner-builder/banner.toml``, then
    ``~/.config/banner-builder/banner.toml``.

    :returns: The config path, which may not exist yet
    """
    explicit = os.environ.get("BANNER_BUILDER_CONFIG")
    if explicit:
        return Path(explicit).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base).expanduser() / "banner-builder" / "banner.toml"


def parse_markup(line: str) -> list[tuple[str, bool]]:
    r"""
    Split a headline line into runs of plain and accent text.

    Text between asterisks is drawn in the accent colour. ``\*`` is a literal asterisk.

    :param line: One headline line, such as ``"and the *result* it gets."``
    :returns: ``(text, is_accent)`` runs in order, without empty runs
    :raises ValueError: If an asterisk is left open
    """
    runs: list[tuple[str, bool]] = []
    current: list[str] = []
    accent = False
    chars = iter(line)
    for char in chars:
        if char == "\\":
            current.append(next(chars, "\\"))
        elif char == "*":
            if current:
                runs.append(("".join(current), accent))
                current = []
            accent = not accent
        else:
            current.append(char)
    if accent:
        raise ValueError(f"unclosed accent in {line!r}: every * needs a partner")
    if current:
        runs.append(("".join(current), accent))
    return runs


def plain_text(line: str) -> str:
    """
    Return a headline line without its accent markup.

    :param line: One headline line with optional ``*accent*`` markup
    :returns: The text a reader sees
    """
    return "".join(text for text, _ in parse_markup(line))


def load(path: Path) -> Config:
    """
    Read and validate a config file.

    :param path: The TOML file to read
    :returns: The validated config
    :raises FileNotFoundError: If the file does not exist
    :raises ValueError: If a key is unknown, a value has the wrong type or a colour does not parse
    """
    if not path.is_file():
        raise FileNotFoundError(f"no config at {path}: run `banner-builder init` to create one")
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return _from_dict(data, base=path.parent)


def _from_dict(data: dict[str, Any], base: Path) -> Config:
    unknown = sorted(set(data) - set(_SECTIONS))
    if unknown:
        raise ValueError(f"unknown section(s): {', '.join(unknown)}")
    for section, keys in _SECTIONS.items():
        table = _table(data, section)
        if keys:
            extra = sorted(set(table) - keys)
            if extra:
                raise ValueError(f"unknown key(s) in [{section}]: {', '.join(extra)}")

    canvas, text, type_, fonts, output = (_table(data, name) for name in ("canvas", "text", "type", "fonts", "output"))
    lines = tuple(_str_list(text, "lines", "text", default=None))
    if not lines:
        raise ValueError("[text] lines needs at least one line")
    for line in lines:
        if not plain_text(line).strip():
            raise ValueError("[text] lines must not be empty: remove the empty line")

    themes = {name: _theme(name, colours) for name, colours in DEFAULT_THEMES.items()}
    for name, colours in _table(data, "themes").items():
        if not isinstance(colours, dict):
            raise ValueError(f"[themes.{name}] must be a table of colours")
        merged = {**DEFAULT_THEMES.get(name, {}), **colours}
        themes[name] = _theme(name, merged)

    build_themes = tuple(_str_list(output, "themes", "output", default=["light", "dark"]))
    missing = [name for name in build_themes if name not in themes]
    if missing:
        raise ValueError(f"[output] themes names undefined theme(s): {', '.join(missing)}")
    formats = tuple(_str_list(output, "formats", "output", default=list(FORMATS)))
    bad_formats = [name for name in formats if name not in FORMATS]
    if bad_formats:
        raise ValueError(f"[output] formats must be png and/or svg, not {', '.join(bad_formats)}")
    scales = tuple(_int_list(output, "scales", "output", default=[1, 2]))
    if not scales or any(scale < 1 or scale > 4 for scale in scales):
        raise ValueError("[output] scales must be whole numbers from 1 to 4")

    name = _str(output, "name", "output", "banner")
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError("[output] name must be a plain file name, without folders")

    return Config(
        lines=lines,
        kicker=_str(text, "kicker", "text", ""),
        footer_left=_str(text, "footer_left", "text", ""),
        footer_right=_str(text, "footer_right", "text", ""),
        width=_int(canvas, "width", "canvas", 1584),
        height=_int(canvas, "height", "canvas", 396),
        left=_int(canvas, "left", "canvas", 448),
        right=_int(canvas, "right", "canvas", 96),
        top=_int(canvas, "top", "canvas", 77),
        bottom=_int(canvas, "bottom", "canvas", 24),
        max_headline=_int(type_, "max_headline", "type", 84),
        kicker_size=_int(type_, "kicker_size", "type", 20),
        footer_size=_int(type_, "footer_size", "type", 25),
        headline_tracking=_float(type_, "headline_tracking", "type", -0.025),
        kicker_tracking=_float(type_, "kicker_tracking", "type", 0.14),
        display=_font(fonts, "display", 500, base),
        mono=_font(fonts, "mono", 400, base),
        themes=themes,
        out_dir=Path(_str(output, "dir", "output", ".")).expanduser(),
        name=name,
        build_themes=build_themes,
        formats=formats,
        scales=scales,
    )


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"[{key}] must be a table")
    return value


def _str(table: dict[str, Any], key: str, section: str, default: str) -> str:
    value = table.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"[{section}] {key} must be a string")
    return value


def _int(table: dict[str, Any], key: str, section: str, default: int) -> int:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"[{section}] {key} must be a whole number of pixels")
    return value


def _float(table: dict[str, Any], key: str, section: str, default: float) -> float:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"[{section}] {key} must be a number")
    return float(value)


def _str_list(table: dict[str, Any], key: str, section: str, default: list[str] | None) -> list[str]:
    value = table.get(key, default)
    if value is None:
        raise ValueError(f"[{section}] {key} is required")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"[{section}] {key} must be a list of strings")
    return value


def _int_list(table: dict[str, Any], key: str, section: str, default: list[int]) -> list[int]:
    value = table.get(key, default)
    if not isinstance(value, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in value):
        raise ValueError(f"[{section}] {key} must be a list of whole numbers")
    return value


def _font(fonts: dict[str, Any], role: str, weight: int, base: Path) -> FontSpec:
    table = fonts.get(role, {})
    if not isinstance(table, dict):
        raise ValueError(f"[fonts.{role}] must be a table")
    extra = sorted(set(table) - {"file", "weight"})
    if extra:
        raise ValueError(f"unknown key(s) in [fonts.{role}]: {', '.join(extra)}")
    file_text = _str(table, "file", f"fonts.{role}", "")
    chosen = _int(table, "weight", f"fonts.{role}", weight)
    if not file_text:
        return FontSpec(None, chosen)
    file = Path(file_text).expanduser()
    return FontSpec(file if file.is_absolute() else base / file, chosen)


def _theme(name: str, colours: dict[str, Any]) -> Theme:
    extra = sorted(set(colours) - set(ROLES))
    if extra:
        raise ValueError(f"unknown colour(s) in [themes.{name}]: {', '.join(extra)}")
    missing = [role for role in ROLES if role not in colours]
    if missing:
        raise ValueError(f"[themes.{name}] is missing {', '.join(missing)}")
    values: dict[str, str] = {}
    for role in ROLES:
        raw = colours[role]
        if not isinstance(raw, str):
            raise ValueError(f"[themes.{name}] {role} must be a colour string")
        values[role] = to_hex(raw)
    return Theme(**values)
