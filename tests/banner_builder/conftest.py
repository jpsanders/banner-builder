from collections.abc import Callable
from importlib import resources
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from banner_builder import fonts
from banner_builder.config import Config, FontSpec, load

STARTER = resources.files("banner_builder").joinpath("example.toml").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def display() -> TTFont:
    return fonts.load(FontSpec(None, 500), "display")


@pytest.fixture(scope="session")
def mono() -> TTFont:
    return fonts.load(FontSpec(None, 400), "mono")


@pytest.fixture
def write_config(tmp_path: Path) -> Callable[[str], Path]:
    def write(text: str) -> Path:
        path = tmp_path / "banner.toml"
        path.write_text(text, encoding="utf-8")
        return path

    return write


@pytest.fixture
def example(write_config: Callable[[str], Path]) -> Config:
    return load(write_config(STARTER))
