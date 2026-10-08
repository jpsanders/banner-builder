import struct
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

from fontTools.ttLib import TTFont

from banner_builder.config import Config
from banner_builder.fonts import write_renamed
from banner_builder.layout import plan
from banner_builder.render import DISPLAY_FAMILY, MONO_FAMILY, build, font_faces, png, svg, title

SVG = "{http://www.w3.org/2000/svg}"


def _size(path: Path) -> tuple[int, int]:
    width, height = struct.unpack(">II", path.read_bytes()[16:24])
    return width, height


def test_svg_escapes_the_words(example: Config, display: TTFont, mono: TTFont) -> None:
    config = replace(example, kicker="R&D <TEAM>", lines=('Tom & "Jerry"',), footer_left="a < b")
    document = svg(config, plan(config, display, mono), config.themes["light"], "")
    root = ElementTree.fromstring(document)
    texts = ["".join(node.itertext()) for node in root.iter(f"{SVG}text")]
    assert texts == ["R&D <TEAM>", 'Tom & "Jerry"', "a < b", "example.com"]
    assert root.findtext(f"{SVG}title") == 'R&D <TEAM> Tom & "Jerry" a < b example.com'


def test_svg_draws_the_accent_in_the_accent_colour(example: Config, display: TTFont, mono: TTFont) -> None:
    theme = example.themes["light"]
    document = svg(example, plan(example, display, mono), theme, "")
    assert f'<tspan fill="{theme.accent}">faster</tspan>' in document
    assert f'<tspan fill="{theme.ink}"> deploys by day.</tspan>' in document


def test_title_reads_in_order(example: Config) -> None:
    assert title(example) == (
        "PLATFORM ENGINEER · OPEN TO NEW ROLES Fewer alerts at night, faster deploys by day. "
        "Go · Kubernetes · Terraform example.com"
    )


def test_font_faces_embed_only_fonts_in_use(example: Config, display: TTFont, mono: TTFont) -> None:
    both = font_faces(example, display, mono)
    assert both.count("@font-face") == 2
    assert f'font-family:"{DISPLAY_FAMILY}"' in both
    assert f'font-family:"{MONO_FAMILY}"' in both
    headline_only = font_faces(replace(example, kicker="", footer_left="", footer_right=""), display, mono)
    assert headline_only.count("@font-face") == 1


def test_png_draws_text_with_the_renamed_fonts(example: Config, display: TTFont, mono: TTFont, tmp_path: Path) -> None:
    files = [tmp_path / "display.ttf", tmp_path / "mono.ttf"]
    write_renamed(display, DISPLAY_FAMILY, files[0])
    write_renamed(mono, MONO_FAMILY, files[1])
    document = svg(example, plan(example, display, mono), example.themes["dark"], "")
    with_text = png(document, 1, files)
    without_fonts = png(document, 1, [])
    assert with_text.startswith(b"\x89PNG")
    assert len(with_text) > 5 * len(without_fonts)


def test_build_writes_every_theme_format_and_scale(
    example: Config, display: TTFont, mono: TTFont, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    written = build(example, plan(example, display, mono), (display, mono), out, ("light", "dark"), ("png", "svg"))
    assert [path.name for path in written] == [
        "banner-light.svg",
        "banner-light.png",
        "banner-light@2x.png",
        "banner-dark.svg",
        "banner-dark.png",
        "banner-dark@2x.png",
    ]
    assert _size(out / "banner-light.png") == (1584, 396)
    assert _size(out / "banner-dark@2x.png") == (3168, 792)
    assert ElementTree.parse(out / "banner-dark.svg").getroot().get("viewBox") == "0 0 1584 396"


def test_build_writes_only_what_is_asked(example: Config, display: TTFont, mono: TTFont, tmp_path: Path) -> None:
    config = replace(example, name="profile", scales=(3,))
    written = build(config, plan(config, display, mono), (display, mono), tmp_path, ("dark",), ("png",))
    assert [path.name for path in written] == ["profile-dark@3x.png"]
    assert _size(written[0]) == (4752, 1188)
