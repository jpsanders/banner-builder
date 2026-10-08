import base64
import shutil
from importlib import resources
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from banner_builder import fonts
from banner_builder.config import FontSpec


def test_bundled_fonts_are_pinned_to_their_weights(display: TTFont, mono: TTFont) -> None:
    assert "fvar" not in display
    assert "fvar" not in mono
    assert display["OS/2"].usWeightClass == 500
    assert mono["OS/2"].usWeightClass == 400


def test_a_weight_outside_the_font_is_refused() -> None:
    with pytest.raises(ValueError, match="outside its range"):
        fonts.load(FontSpec(None, 50), "display")


def test_a_configured_variable_font_is_pinned(tmp_path: Path) -> None:
    source = resources.files("banner_builder").joinpath("fonts", fonts.BUNDLED["display"])
    with resources.as_file(source) as bundled:
        mine = Path(shutil.copy(bundled, tmp_path / "Mine.ttf"))
    font = fonts.load(FontSpec(mine, 700), "display")
    assert "fvar" not in font
    assert font["OS/2"].usWeightClass == 700


def test_a_static_font_is_used_as_it_is(display: TTFont, tmp_path: Path) -> None:
    path = tmp_path / "Static.ttf"
    display.save(str(path))
    font = fonts.load(FontSpec(path, 900), "display")
    assert font["OS/2"].usWeightClass == 500


def test_a_missing_font_file_is_named(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Nope.ttf"):
        fonts.load(FontSpec(tmp_path / "Nope.ttf", 400), "mono")


def test_missing_glyphs_are_listed_once(display: TTFont) -> None:
    assert fonts.missing_glyphs(display, "Hello 漢 world 漢 🙂") == "漢🙂"
    assert fonts.missing_glyphs(display, "Hello, world.") == ""


def test_advance_adds_tracking_between_characters(mono: TTFont) -> None:
    plain = fonts.advance(mono, "abc", 10)
    assert plain == pytest.approx(3 * fonts.advance(mono, "a", 10))
    assert fonts.advance(mono, "abc", 10, 0.1) - plain == pytest.approx(2.0)
    assert fonts.advance(mono, "", 10, 0.1) == 0


def test_cap_height_comes_from_the_font(display: TTFont) -> None:
    assert fonts.cap_height(display, 100) == pytest.approx(70.0)
    assert fonts.cap_height({}, 100) == pytest.approx(70.0)


def test_side_bearing_scales_with_size(display: TTFont) -> None:
    assert fonts.side_bearing(display, "P", 1000) == pytest.approx(73.0)
    assert fonts.side_bearing(display, "P", 100) == pytest.approx(7.3)


def test_woff2_subset_leaves_the_font_whole(display: TTFont) -> None:
    glyphs = len(display.getGlyphOrder())
    data = base64.b64decode(fonts.woff2_base64(display, "Hello"))
    assert data.startswith(b"wOF2")
    assert len(display.getGlyphOrder()) == glyphs


def test_renamed_copy_answers_to_the_new_family(mono: TTFont, tmp_path: Path) -> None:
    path = tmp_path / "renamed.ttf"
    fonts.write_renamed(mono, "Banner Mono", path)
    names = TTFont(str(path))["name"]
    assert names.getDebugName(1) == "Banner Mono"
    assert names.getDebugName(6) == "BannerMono"
    assert names.getDebugName(16) is None
    assert mono["name"].getDebugName(1) != "Banner Mono"
