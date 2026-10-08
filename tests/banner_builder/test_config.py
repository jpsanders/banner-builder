import re
from collections.abc import Callable
from dataclasses import replace
from importlib import resources
from pathlib import Path

import pytest

from banner_builder.config import Config, FontSpec, default_path, load, parse_markup, plain_text

STARTER = resources.files("banner_builder").joinpath("example.toml").read_text(encoding="utf-8")
MINIMAL = '[text]\nlines = ["Hello, world."]\n'


def test_starter_config_loads(example: Config) -> None:
    assert example.kicker == "PLATFORM ENGINEER · OPEN TO NEW ROLES"
    assert example.lines == ("Fewer alerts at night,", "*faster* deploys by day.")
    assert example.footer_right == "example.com"
    assert example.themes["light"].background == "#f9f6f0"
    assert example.themes["dark"].accent == "#e59656"


def test_starter_config_states_the_defaults(example: Config, write_config: Callable[[str], Path]) -> None:
    text_only = load(write_config(MINIMAL))
    same_words = replace(
        text_only,
        lines=example.lines,
        kicker=example.kicker,
        footer_left=example.footer_left,
        footer_right=example.footer_right,
    )
    assert example == same_words


def test_only_lines_are_required(write_config: Callable[[str], Path]) -> None:
    config = load(write_config(MINIMAL))
    assert config.lines == ("Hello, world.",)
    assert config.kicker == config.footer_left == config.footer_right == ""
    assert config.display == FontSpec(None, 500)
    assert set(config.themes) == {"light", "dark"}


def test_missing_file_explains_how_to_start(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="banner-builder init"):
        load(tmp_path / "nowhere.toml")


def test_broken_toml_is_a_value_error(write_config: Callable[[str], Path]) -> None:
    with pytest.raises(ValueError):
        load(write_config("[text\n"))


@pytest.mark.parametrize(
    "text, message",
    [
        ('[colours]\nink = "#000000"\n', "unknown section"),
        ('[text]\nlines = ["a"]\ntitle = "x"\n', r"unknown key\(s\) in \[text\]"),
        ('text = "x"\n', r"\[text\] must be a table"),
        ("[text]\n", "lines is required"),
        ("[text]\nlines = []\n", "at least one line"),
        ("[text]\nlines = [1]\n", "list of strings"),
        ('[text]\nlines = ["a", " "]\n', "must not be empty"),
        ('[text]\nlines = ["an *open accent"]\n', "unclosed accent"),
        ('[text]\nlines = ["a"]\nkicker = 3\n', "kicker must be a string"),
        ('[text]\nlines = ["a"]\n[canvas]\nwidth = "wide"\n', "whole number"),
        ('[text]\nlines = ["a"]\n[canvas]\nwidth = -1\n', "whole number"),
        ('[text]\nlines = ["a"]\n[canvas]\nwidth = true\n', "whole number"),
        ('[text]\nlines = ["a"]\n[type]\nheadline_tracking = "tight"\n', "must be a number"),
        ('[text]\nlines = ["a"]\n[themes]\ndark = "black"\n', "table of colours"),
        ('[text]\nlines = ["a"]\n[themes.dark]\nshadow = "#000000"\n', "unknown colour"),
        ('[text]\nlines = ["a"]\n[themes.dark]\nink = 0\n', "colour string"),
        ('[text]\nlines = ["a"]\n[themes.dark]\nink = "black"\n', "unsupported colour"),
        ('[text]\nlines = ["a"]\n[themes.forest]\nink = "#ffffff"\n', "missing background"),
        ('[text]\nlines = ["a"]\n[output]\nthemes = ["forest"]\n', "undefined theme"),
        ('[text]\nlines = ["a"]\n[output]\nformats = ["jpg"]\n', "png and/or svg"),
        ('[text]\nlines = ["a"]\n[output]\nscales = [0]\n', "from 1 to 4"),
        ('[text]\nlines = ["a"]\n[output]\nscales = []\n', "from 1 to 4"),
        ('[text]\nlines = ["a"]\n[output]\nscales = ["2"]\n', "whole numbers"),
        ('[text]\nlines = ["a"]\n[output]\nname = "../banner"\n', "plain file name"),
        ('[text]\nlines = ["a"]\n[fonts]\ndisplay = "Inter"\n', r"\[fonts.display\] must be a table"),
        ('[text]\nlines = ["a"]\n[fonts]\nmono = { size = 3 }\n', r"unknown key\(s\) in \[fonts.mono\]"),
    ],
)
def test_mistakes_are_named(write_config: Callable[[str], Path], text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load(write_config(text))


def test_a_theme_override_keeps_the_other_defaults(write_config: Callable[[str], Path]) -> None:
    config = load(write_config(MINIMAL + '[themes.dark]\naccent = "#FF8800"\n'))
    assert config.themes["dark"].accent == "#ff8800"
    assert config.themes["dark"].background == "#1c1611"


def test_a_new_theme_can_be_built(write_config: Callable[[str], Path]) -> None:
    theme = """
[themes.mono]
background = "#000000"
ink = "#ffffff"
soft = "#cccccc"
rule = "#333333"
accent = "#eeeeee"

[output]
themes = ["mono"]
"""
    config = load(write_config(MINIMAL + theme))
    assert config.build_themes == ("mono",)
    assert config.themes["mono"].ink == "#ffffff"


def test_font_paths_resolve_from_the_config_folder(write_config: Callable[[str], Path], tmp_path: Path) -> None:
    config = load(
        write_config(
            MINIMAL + '[fonts]\ndisplay = { file = "fonts/Mine.ttf", weight = 700 }\nmono = { file = "/x/y.otf" }\n'
        )
    )
    assert config.display == FontSpec(tmp_path / "fonts" / "Mine.ttf", 700)
    assert config.mono == FontSpec(Path("/x/y.otf"), 400)


def test_output_folder_expands_the_home_folder(write_config: Callable[[str], Path]) -> None:
    config = load(write_config(MINIMAL + '[output]\ndir = "~/banners"\nscales = [1]\nformats = ["svg"]\n'))
    assert config.out_dir == Path.home() / "banners"
    assert config.scales == (1,)
    assert config.formats == ("svg",)


@pytest.mark.parametrize(
    "line, runs",
    [
        ("plain words", [("plain words", False)]),
        ("the *result* it gets", [("the ", False), ("result", True), (" it gets", False)]),
        ("*all of it*", [("all of it", True)]),
        ("*one**two*", [("one", True), ("two", True)]),
        ("5 \\* 3", [("5 * 3", False)]),
        ("ends with \\", [("ends with \\", False)]),
        ("**", []),
    ],
)
def test_markup_splits_accent_runs(line: str, runs: list[tuple[str, bool]]) -> None:
    assert parse_markup(line) == runs


def test_plain_text_drops_the_markup() -> None:
    assert plain_text("and the *result* it gets.") == "and the result it gets."


def test_unclosed_accent_is_refused() -> None:
    with pytest.raises(ValueError, match="unclosed accent"):
        parse_markup("an *open accent")


def test_config_path_prefers_the_environment_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BANNER_BUILDER_CONFIG", str(tmp_path / "mine.toml"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert default_path() == tmp_path / "mine.toml"


def test_config_path_follows_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("BANNER_BUILDER_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert default_path() == tmp_path / "xdg" / "banner-builder" / "banner.toml"


def test_config_path_falls_back_to_dot_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("BANNER_BUILDER_CONFIG", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert default_path() == tmp_path / ".config" / "banner-builder" / "banner.toml"


def test_starter_config_holds_no_personal_details() -> None:
    assert 'footer_right = "example.com"' in STARTER
    assert re.search(r"[\w.]+@[\w-]+\.\w+", STARTER) is None
