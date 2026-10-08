"""
Place every line of the banner and check that it fits.

The headline is drawn as large as the canvas allows, up to ``max_headline``. The kicker and the footer keep their
configured sizes. Anything that would overflow the canvas, use a glyph the font lacks or fall under the WCAG AA contrast
ratio is reported as a problem, and nothing is written until every problem is fixed.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from fontTools.ttLib import TTFont

from banner_builder.color import contrast
from banner_builder.config import Config, Theme, parse_markup, plain_text
from banner_builder.fonts import advance, cap_height, missing_glyphs, side_bearing

MIN_CONTRAST = 4.5
MIN_HEADLINE = 24
LINE_HEIGHT = 1.08  # headline baseline to baseline, in headline sizes
KICKER_GAP = 1.45  # kicker baseline to the top of the headline capitals, in kicker sizes
RULE_GAP = 1.6  # last headline baseline to the rule, in footer sizes
FOOTER_GAP = 1.84  # rule to the footer baseline, in footer sizes
FOOTER_SPACE = 3.2  # least space between the two footer texts, in footer sizes


@dataclass(frozen=True)
class Line:
    """One headline line: its runs of plain and accent text, and where it starts."""

    runs: tuple[tuple[str, bool], ...]
    x: float
    y: int


@dataclass(frozen=True)
class Layout:
    """Where everything goes, and every reason it cannot be drawn yet."""

    headline_size: int
    kicker_y: int | None
    lines: tuple[Line, ...]
    rule_y: int | None
    footer_y: int | None
    problems: tuple[str, ...]


def plan(config: Config, display: TTFont, mono: TTFont) -> Layout:
    """
    Size the headline and place every row.

    :param config: The banner config
    :param display: The headline font, pinned to its weight
    :param mono: The kicker and footer font, pinned to its weight
    :returns: The layout, with a problem for everything that does not fit
    """
    available = config.width - config.left - config.right
    if available <= 0:
        return _failed(f"[canvas] left and right leave no room on a canvas {config.width}px wide")
    headline = [plain_text(line) for line in config.lines]
    small = config.kicker + config.footer_left + config.footer_right
    gaps = [
        f"the {role} font has no glyph for {', '.join(repr(char) for char in missing)}"
        for role, missing in (
            ("display", missing_glyphs(display, "".join(headline))),
            ("mono", missing_glyphs(mono, small)),
        )
        if missing
    ]
    if gaps:
        return _failed(*gaps)

    problems: list[str] = []
    widest = max(advance(display, text, 1, config.headline_tracking) for text in headline)
    size = min(config.max_headline, math.floor(available / widest))
    while size > 1 and _rows(config, display, mono, size)[-1] > config.height - config.bottom:
        size -= 1
    if size < min(MIN_HEADLINE, config.max_headline):
        problems.append(
            f"the headline only fits at {size}px: shorten the longest line, split it, or make the canvas larger"
        )

    kicker_width = advance(mono, config.kicker, config.kicker_size, config.kicker_tracking)
    if kicker_width > available:
        problems.append(
            f"the kicker is {kicker_width:.0f}px wide and the text area is {available}px: "
            "shorten it or lower [type] kicker_size"
        )
    footer = [advance(mono, text, config.footer_size) for text in (config.footer_left, config.footer_right) if text]
    footer_width = sum(footer) + (FOOTER_SPACE * config.footer_size if len(footer) == 2 else 0)
    if footer_width > available:
        problems.append(
            f"the footer needs {footer_width:.0f}px and the text area is {available}px: "
            "shorten footer_left or footer_right, or lower [type] footer_size"
        )

    kicker_y, line_ys, rule_y, footer_y = _split(config, _rows(config, display, mono, size))
    lines = tuple(
        Line(
            runs=tuple(parse_markup(line)),
            x=round(config.left - side_bearing(display, text[0], size), 2),
            y=y,
        )
        for line, text, y in zip(config.lines, headline, line_ys)
    )
    return Layout(size, kicker_y, lines, rule_y, footer_y, tuple(problems))


def ratios(theme: Theme) -> dict[str, float]:
    """
    Return the contrast of each text colour against the background.

    :param theme: The palette to measure
    :returns: The WCAG contrast ratio for ink, soft and accent
    """
    return {
        "ink": contrast(theme.ink, theme.background),
        "soft": contrast(theme.soft, theme.background),
        "accent": contrast(theme.accent, theme.background),
    }


def contrast_problems(config: Config, themes: Iterable[str]) -> list[str]:
    """
    List every text colour that fails WCAG AA against its background.

    :param config: The banner config
    :param themes: The names of the themes being built
    :returns: One message per failing colour
    """
    problems = []
    for name in themes:
        theme = config.themes[name]
        for role, ratio in ratios(theme).items():
            if ratio < MIN_CONTRAST:
                problems.append(
                    f"[themes.{name}] {role} {getattr(theme, role)} on {theme.background} has a contrast ratio of "
                    f"{ratio:.2f}, under the WCAG AA minimum of {MIN_CONTRAST}"
                )
    return problems


def _rows(config: Config, display: TTFont, mono: TTFont, size: int) -> list[int]:
    rows: list[int] = []
    if config.kicker:
        rows.append(config.top + round(cap_height(mono, config.kicker_size)))
        cap_top = rows[-1] + round(KICKER_GAP * config.kicker_size)
    else:
        cap_top = config.top
    first = cap_top + round(cap_height(display, size))
    rows.extend(first + index * round(LINE_HEIGHT * size) for index in range(len(config.lines)))
    if config.footer_left or config.footer_right:
        rows.append(rows[-1] + round(RULE_GAP * config.footer_size))
        rows.append(rows[-1] + round(FOOTER_GAP * config.footer_size))
    return rows


def _split(config: Config, rows: list[int]) -> tuple[int | None, list[int], int | None, int | None]:
    kicker_y = rows.pop(0) if config.kicker else None
    footer_y = rows.pop() if config.footer_left or config.footer_right else None
    rule_y = rows.pop() if footer_y is not None else None
    return kicker_y, rows, rule_y, footer_y


def _failed(*problems: str) -> Layout:
    return Layout(0, None, (), None, None, problems)
