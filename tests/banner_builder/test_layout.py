from dataclasses import replace

from fontTools.ttLib import TTFont

from banner_builder.config import Config, Theme
from banner_builder.fonts import advance, cap_height, side_bearing
from banner_builder.layout import contrast_problems, plan, ratios


def test_starter_layout_rows(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(example, display, mono)
    assert layout.problems == ()
    assert layout.headline_size == 84
    assert layout.kicker_y == 92
    assert [line.y for line in layout.lines] == [180, 271]
    assert layout.rule_y == 311
    assert layout.footer_y == 357


def test_headline_is_the_largest_size_that_fits_the_width(example: Config, display: TTFont, mono: TTFont) -> None:
    text = "A much longer headline that has to shrink to fit"
    layout = plan(replace(example, lines=(text,)), display, mono)
    room = example.width - example.left - example.right
    size = layout.headline_size
    assert size < example.max_headline
    assert advance(display, text, size, example.headline_tracking) <= room
    assert advance(display, text, size + 1, example.headline_tracking) > room


def test_headline_shrinks_to_fit_the_height(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, lines=("One", "Two", "Three", "Four")), display, mono)
    assert layout.problems == ()
    assert layout.headline_size < example.max_headline
    assert layout.footer_y is not None
    assert layout.footer_y <= example.height - example.bottom


def test_without_a_kicker_the_headline_starts_at_top(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, kicker=""), display, mono)
    assert layout.kicker_y is None
    assert layout.lines[0].y == example.top + round(cap_height(display, layout.headline_size))


def test_without_a_footer_there_is_no_rule(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, footer_left="", footer_right=""), display, mono)
    assert layout.rule_y is None
    assert layout.footer_y is None


def test_one_footer_text_is_enough_for_a_footer(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, footer_left=""), display, mono)
    assert layout.footer_y == 357


def test_headline_ink_lines_up_with_the_left_margin(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(example, display, mono)
    first = layout.lines[0]
    assert first.x == round(example.left - side_bearing(display, "F", layout.headline_size), 2)
    assert first.x < example.left


def test_lines_keep_their_accent_runs(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(example, display, mono)
    assert layout.lines[1].runs == (("faster", True), (" deploys by day.", False))


def test_a_wide_kicker_is_a_problem(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, kicker="WIDE " * 40), display, mono)
    assert len(layout.problems) == 1
    assert "the kicker is" in layout.problems[0]


def test_a_wide_footer_is_a_problem(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, footer_left="Python · " * 8), display, mono)
    assert len(layout.problems) == 1
    assert "the footer needs" in layout.problems[0]


def test_a_missing_glyph_is_a_problem(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, lines=("Hello 漢",), footer_right="🙂"), display, mono)
    assert layout.problems == (
        "the display font has no glyph for '漢'",
        "the mono font has no glyph for '🙂'",
    )
    assert layout.lines == ()


def test_margins_wider_than_the_canvas_are_a_problem(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, left=800, right=800), display, mono)
    assert "leave no room" in layout.problems[0]


def test_a_headline_too_long_to_read_is_a_problem(example: Config, display: TTFont, mono: TTFont) -> None:
    layout = plan(replace(example, lines=("word " * 60,)), display, mono)
    assert layout.headline_size < 24
    assert "the headline only fits at" in layout.problems[0]


def test_default_themes_pass_wcag_aa(example: Config) -> None:
    assert contrast_problems(example, ("light", "dark")) == []


def test_low_contrast_is_a_problem(example: Config) -> None:
    pale = Theme(background="#ffffff", ink="#000000", soft="#cccccc", rule="#eeeeee", accent="#000000")
    config = replace(example, themes={**example.themes, "pale": pale})
    problems = contrast_problems(config, ("light", "pale"))
    assert len(problems) == 1
    assert problems[0].startswith("[themes.pale] soft #cccccc on #ffffff has a contrast ratio of 1.6")
    assert set(ratios(pale)) == {"ink", "soft", "accent"}
