"""
Load fonts, measure text and prepare font files for the SVG and the PNG renderer.

A variable font is pinned to one weight first, so measuring and drawing use the same outlines.
"""

import base64
import io
from importlib import resources
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from banner_builder.config import FontSpec

BUNDLED = {
    "display": "SpaceGrotesk-Variable.ttf",
    "mono": "JetBrainsMono-Variable.ttf",
}


def load(spec: FontSpec, role: str) -> TTFont:
    """
    Open a font and pin it to the configured weight.

    :param spec: The configured file and weight
    :param role: ``display`` or ``mono``, which picks the bundled font when no file is set
    :returns: A static font at the configured weight
    :raises FileNotFoundError: If a configured font file does not exist
    :raises ValueError: If the weight is outside the range a variable font supports
    """
    if spec.file is None:
        data = resources.files("banner_builder").joinpath("fonts", BUNDLED[role]).read_bytes()
    elif spec.file.is_file():
        data = spec.file.read_bytes()
    else:
        raise FileNotFoundError(f"font file {spec.file} does not exist")
    font = TTFont(io.BytesIO(data))
    if "fvar" not in font:
        return font
    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    if "wght" in axes:
        lowest, highest = axes["wght"].minValue, axes["wght"].maxValue
        if not lowest <= spec.weight <= highest:
            raise ValueError(f"{role} font weight {spec.weight} is outside its range of {lowest:g} to {highest:g}")
    pins = {tag: spec.weight if tag == "wght" else axis.defaultValue for tag, axis in axes.items()}
    return instancer.instantiateVariableFont(font, pins)


def missing_glyphs(font: TTFont, text: str) -> str:
    """
    Return the characters a font cannot draw.

    :param font: The font to check
    :param text: The text it has to draw
    :returns: Each missing character once, in order of appearance
    """
    cmap = font.getBestCmap()
    return "".join(dict.fromkeys(char for char in text if ord(char) not in cmap))


def advance(font: TTFont, text: str, size: float, tracking: float = 0.0) -> float:
    """
    Measure how far a line of text advances, without kerning.

    :param font: A static font
    :param text: The text, which must contain only characters the font has
    :param size: The font size in pixels
    :param tracking: Letter spacing in ems, added between characters
    :returns: The width in pixels
    """
    cmap, metrics = font.getBestCmap(), font["hmtx"]
    units = float(sum(metrics[cmap[ord(char)]][0] for char in text))
    return units * size / float(font["head"].unitsPerEm) + tracking * size * max(len(text) - 1, 0)


def cap_height(font: TTFont, size: float) -> float:
    """
    Return the height of a font's capital letters.

    :param font: A static font
    :param size: The font size in pixels
    :returns: The cap height in pixels, or 70 percent of the size when the font does not record one
    """
    units = getattr(font["OS/2"], "sCapHeight", 0) if "OS/2" in font else 0
    if not units:
        return 0.7 * size
    return float(units) * size / float(font["head"].unitsPerEm)


def side_bearing(font: TTFont, char: str, size: float) -> float:
    """
    Return the gap between a glyph's origin and its left edge.

    Large type shifted left by this amount lines up with the smaller text above and below it.

    :param font: A static font
    :param char: The first character of a line
    :param size: The font size in pixels
    :returns: The left side bearing in pixels
    """
    glyph = font.getBestCmap()[ord(char)]
    return float(font["hmtx"][glyph][1]) * size / float(font["head"].unitsPerEm)


def woff2_base64(font: TTFont, text: str) -> str:
    """
    Cut a font down to the glyphs a text needs and encode it for an SVG ``@font-face`` rule.

    :param font: A static font, which is left unchanged
    :param text: Every character the font has to draw
    :returns: A base64 encoded woff2 font
    """
    subset = _copy(font)
    options = Options()
    options.flavor = "woff2"
    options.layout_features = ["kern", "liga"]
    subsetter = Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(subset)
    buffer = io.BytesIO()
    subset.flavor = "woff2"
    subset.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def write_renamed(font: TTFont, family: str, path: Path) -> None:
    """
    Save a copy of a font under a new family name, so a renderer finds exactly this font by name.

    :param font: A static font, which is left unchanged
    :param family: The family name to give the copy
    :param path: Where to write the copy
    """
    renamed = _copy(font)
    names = renamed["name"]
    for name_id in (1, 2, 4, 6, 16, 17):
        names.removeNames(nameID=name_id)
    for name_id, value in ((1, family), (2, "Regular"), (4, family), (6, family.replace(" ", ""))):
        names.setName(value, name_id, 3, 1, 0x409)
    renamed.save(str(path))


def _copy(font: TTFont) -> TTFont:
    buffer = io.BytesIO()
    font.save(buffer)
    buffer.seek(0)
    return TTFont(buffer)
