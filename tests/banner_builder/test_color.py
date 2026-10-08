import pytest

from banner_builder.color import contrast, to_hex

LIGHT = {
    "oklch(0.973 0.008 78)": "#f9f6f0",
    "oklch(0.205 0.014 62)": "#1c1611",
    "oklch(0.505 0.020 66)": "#6d6359",
    "oklch(0.878 0.012 74)": "#dcd6ce",
    "oklch(0.545 0.128 52)": "#a95719",
}
DARK = {
    "oklch(0.955 0.008 78)": "#f3f0ea",
    "oklch(0.740 0.018 70)": "#b2a99f",
    "oklch(0.330 0.014 62)": "#3b342e",
    "oklch(0.740 0.125 58)": "#e59656",
}


@pytest.mark.parametrize("oklch, expected", [*LIGHT.items(), *DARK.items()])
def test_oklch_converts_to_srgb_hex(oklch: str, expected: str) -> None:
    assert to_hex(oklch) == expected


def test_hex_passes_through_in_lowercase() -> None:
    assert to_hex(" #A95719 ") == "#a95719"


def test_oklch_accepts_extra_spaces_and_whole_numbers() -> None:
    assert to_hex("oklch( 1 0 0 )") == "#ffffff"
    assert to_hex("oklch(0 0 0)") == "#000000"


@pytest.mark.parametrize("value", ["red", "#fff", "#gggggg", "rgb(0, 0, 0)", "oklch(50% 0.1 20)", ""])
def test_other_colour_forms_are_refused(value: str) -> None:
    with pytest.raises(ValueError, match="unsupported colour"):
        to_hex(value)


def test_contrast_runs_from_1_to_21() -> None:
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast("#777777", "#777777") == pytest.approx(1.0)


def test_contrast_does_not_depend_on_order() -> None:
    assert contrast("#a95719", "#f9f6f0") == pytest.approx(contrast("#f9f6f0", "#a95719"))


def test_default_palettes_pass_wcag_aa() -> None:
    for text in ("#1c1611", "#6d6359", "#a95719"):
        assert contrast(text, "#f9f6f0") >= 4.5
    for text in ("#f3f0ea", "#b2a99f", "#e59656"):
        assert contrast(text, "#1c1611") >= 4.5
