"""Colour parsing and the WCAG contrast check."""

import math
import re

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_OKLCH = re.compile(r"^oklch\(\s*([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s*\)$")


def to_hex(value: str) -> str:
    """
    Convert a CSS colour to a lowercase ``#rrggbb`` string.

    :param value: ``#rrggbb``, or ``oklch(L C H)`` with lightness from 0 to 1
    :returns: The colour as ``#rrggbb``
    :raises ValueError: If the colour is in neither form
    """
    text = value.strip()
    if _HEX.match(text):
        return text.lower()
    match = _OKLCH.match(text)
    if not match:
        raise ValueError(f"unsupported colour {value!r}: use #rrggbb or oklch(L C H)")
    lightness, chroma, hue = (float(group) for group in match.groups())
    return _oklch_to_hex(lightness, chroma, hue)


def contrast(foreground: str, background: str) -> float:
    """
    Return the WCAG contrast ratio of two ``#rrggbb`` colours.

    :param foreground: The text colour
    :param background: The colour behind it
    :returns: A ratio from 1.0 to 21.0
    """
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _oklch_to_hex(lightness: float, chroma: float, hue: float) -> str:
    a = chroma * math.cos(math.radians(hue))
    b = chroma * math.sin(math.radians(hue))
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )
    return "#" + "".join(f"{round(_encode(channel) * 255):02x}" for channel in linear)


def _encode(channel: float) -> float:
    channel = min(max(channel, 0.0), 1.0)
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def _luminance(hex_colour: str) -> float:
    red, green, blue = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (red, green, blue)]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
