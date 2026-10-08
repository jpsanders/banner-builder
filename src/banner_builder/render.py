"""
Draw the banner as SVG and rasterise it to PNG.

The SVG carries a subset of each font as woff2, so it looks the same in any browser. The PNG renderer, resvg, does not
read fonts embedded that way, so it gets the same fonts as files, renamed to the families the SVG asks for. Both outputs
draw with the same outlines, and the PNG is a picture of the SVG written beside it.
"""

import html
import tempfile
from collections.abc import Sequence
from pathlib import Path

import resvg_py
from fontTools.ttLib import TTFont

from banner_builder.config import Config, Theme, plain_text
from banner_builder.fonts import woff2_base64, write_renamed
from banner_builder.layout import Layout

DISPLAY_FAMILY = "Banner Display"
MONO_FAMILY = "Banner Mono"
RULE_WIDTH = 2


def font_faces(config: Config, display: TTFont, mono: TTFont) -> str:
    """
    Return the CSS rules that embed both fonts, cut down to the characters the banner uses.

    :param config: The banner config
    :param display: The headline font
    :param mono: The kicker and footer font
    :returns: One ``@font-face`` rule per font that draws something
    """
    rules = []
    for family, font, text in (
        (DISPLAY_FAMILY, display, "".join(plain_text(line) for line in config.lines)),
        (MONO_FAMILY, mono, config.kicker + config.footer_left + config.footer_right),
    ):
        if text:
            data = woff2_base64(font, text)
            rules.append(f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{data}) format("woff2")}}')
    return "".join(rules)


def svg(config: Config, layout: Layout, theme: Theme, faces: str) -> str:
    """
    Draw the banner in one theme.

    :param config: The banner config
    :param layout: Where everything goes
    :param theme: The colours to draw with
    :param faces: The ``@font-face`` rules from :func:`font_faces`
    :returns: A standalone SVG document
    """
    width, height, left, right = config.width, config.height, config.left, config.right
    mono = f"font-family=\"'{MONO_FAMILY}', ui-monospace, monospace\""
    display = f"font-family=\"'{DISPLAY_FAMILY}', ui-sans-serif, sans-serif\""
    keep = 'xml:space="preserve"'
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'role="img" aria-labelledby="title">',
        f'<title id="title">{_escape(title(config))}</title>',
        f"<style>{faces}</style>",
        f'<rect width="{width}" height="{height}" fill="{theme.background}"/>',
    ]
    if layout.kicker_y is not None:
        parts.append(
            f'<text x="{left}" y="{layout.kicker_y}" {mono} font-size="{config.kicker_size}" '
            f'letter-spacing="{config.kicker_tracking:g}em" fill="{theme.soft}" {keep}>{_escape(config.kicker)}</text>'
        )
    for line in layout.lines:
        spans = "".join(
            f'<tspan fill="{theme.accent if accent else theme.ink}">{_escape(text)}</tspan>'
            for text, accent in line.runs
        )
        parts.append(
            f'<text x="{line.x:g}" y="{line.y}" {display} font-size="{layout.headline_size}" '
            f'letter-spacing="{config.headline_tracking:g}em" {keep}>{spans}</text>'
        )
    if layout.rule_y is not None:
        parts.append(
            f'<line x1="{left}" y1="{layout.rule_y}" x2="{width - right}" y2="{layout.rule_y}" '
            f'stroke="{theme.rule}" stroke-width="{RULE_WIDTH}"/>'
        )
    if layout.footer_y is not None and config.footer_left:
        parts.append(
            f'<text x="{left}" y="{layout.footer_y}" {mono} font-size="{config.footer_size}" fill="{theme.ink}" '
            f"{keep}>{_escape(config.footer_left)}</text>"
        )
    if layout.footer_y is not None and config.footer_right:
        parts.append(
            f'<text x="{width - right}" y="{layout.footer_y}" {mono} font-size="{config.footer_size}" '
            f'text-anchor="end" fill="{theme.accent}" {keep}>{_escape(config.footer_right)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def title(config: Config) -> str:
    """
    Return the banner's words in reading order, for screen readers and file previews.

    :param config: The banner config
    :returns: The kicker, the headline and the footer as plain text
    """
    words = [config.kicker, *(plain_text(line) for line in config.lines), config.footer_left, config.footer_right]
    return " ".join(word.strip() for word in words if word.strip())


def png(document: str, scale: int, font_files: Sequence[Path]) -> bytes:
    """
    Rasterise an SVG with resvg.

    :param document: The SVG from :func:`svg`
    :param scale: 1 for the SVG's own size, 2 for twice as many pixels each way
    :param font_files: The renamed fonts from :func:`~banner_builder.fonts.write_renamed`
    :returns: The PNG file contents
    """
    return resvg_py.svg_to_bytes(
        svg_string=document,
        font_files=[str(path) for path in font_files],
        skip_system_fonts=True,
        zoom=scale,
    )


def build(
    config: Config,
    layout: Layout,
    fonts: tuple[TTFont, TTFont],
    out_dir: Path,
    themes: Sequence[str],
    formats: Sequence[str],
) -> list[Path]:
    """
    Write the banner files.

    Files are named ``<name>-<theme>.svg``, ``<name>-<theme>.png`` and ``<name>-<theme>@2x.png``. Existing files with
    those names are replaced.

    :param config: The banner config
    :param layout: Where everything goes
    :param fonts: The display and mono fonts
    :param out_dir: The folder to write into, created when missing
    :param themes: The themes to build
    :param formats: ``png``, ``svg`` or both
    :returns: The paths written, in order
    """
    display, mono = fonts
    out_dir.mkdir(parents=True, exist_ok=True)
    faces = font_faces(config, display, mono)
    written: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="banner-builder-") as scratch:
        font_files = [Path(scratch) / "display.ttf", Path(scratch) / "mono.ttf"]
        write_renamed(display, DISPLAY_FAMILY, font_files[0])
        write_renamed(mono, MONO_FAMILY, font_files[1])
        for name in themes:
            document = svg(config, layout, config.themes[name], faces)
            stem = f"{config.name}-{name}"
            if "svg" in formats:
                written.append(out_dir / f"{stem}.svg")
                written[-1].write_text(document, encoding="utf-8")
            if "png" in formats:
                for scale in config.scales:
                    written.append(out_dir / f"{stem}{'' if scale == 1 else f'@{scale}x'}.png")
                    written[-1].write_bytes(png(document, scale, font_files))
    return written


def _escape(text: str) -> str:
    return html.escape(text, quote=True)
