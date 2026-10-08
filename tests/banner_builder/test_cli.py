from collections.abc import Callable
from importlib import resources
from pathlib import Path

import pytest

from banner_builder.cli import main

STARTER = resources.files("banner_builder").joinpath("example.toml").read_text(encoding="utf-8")


def test_init_writes_the_starter_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "deeper" / "banner.toml"
    assert main(["init", "--config", str(path)]) == 0
    assert path.read_text(encoding="utf-8") == STARTER
    assert f"wrote {path}" in capsys.readouterr().out


def test_init_keeps_an_existing_config(write_config: Callable[[str], Path], capsys: pytest.CaptureFixture[str]) -> None:
    path = write_config("mine")
    assert main(["init", "--config", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == "mine"
    assert "already exists" in capsys.readouterr().err


def test_init_force_replaces_the_config(write_config: Callable[[str], Path]) -> None:
    path = write_config("mine")
    assert main(["init", "--force", "--config", str(path)]) == 0
    assert path.read_text(encoding="utf-8") == STARTER


def test_path_prints_where_the_config_is_read_from(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BANNER_BUILDER_CONFIG", str(tmp_path / "env.toml"))
    assert main(["path"]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"{tmp_path / 'env.toml'}\n"
    assert "does not exist yet" in captured.err


def test_check_reports_the_layout(write_config: Callable[[str], Path], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--config", str(write_config(STARTER))]) == 0
    out = capsys.readouterr().out
    assert "headline  84px" in out
    assert "rows      kicker 92 · headline 180, 271 · rule 311 · footer 357" in out
    assert "dark: ink 15.75, soft 7.74, accent 7.53" in out
    assert out.endswith("ok\n")


def test_check_reports_problems(write_config: Callable[[str], Path], capsys: pytest.CaptureFixture[str]) -> None:
    path = write_config(STARTER.replace('kicker = "PLATFORM ENGINEER', 'kicker = "' + "VERY WIDE " * 20))
    assert main(["check", "--config", str(path)]) == 1
    err = capsys.readouterr().err
    assert "problem: the kicker is" in err
    assert "1 problem to fix. Nothing was written." in err


def test_check_counts_several_problems(write_config: Callable[[str], Path], capsys: pytest.CaptureFixture[str]) -> None:
    pale = STARTER.replace('soft = "oklch(0.505 0.020 66)"', 'soft = "#dddddd"')
    pale = pale.replace('accent = "oklch(0.545 0.128 52)"', 'accent = "#eeeeee"')
    assert main(["check", "--config", str(write_config(pale))]) == 1
    assert "2 problems to fix" in capsys.readouterr().err


def test_build_writes_the_files(
    write_config: Callable[[str], Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    args = ["build", "--config", str(write_config(STARTER)), "--out", str(out), "--format", "png", "--scale", "1"]
    assert main(args) == 0
    assert sorted(path.name for path in out.iterdir()) == ["banner-dark.png", "banner-light.png"]
    assert capsys.readouterr().out.splitlines() == [str(out / "banner-light.png"), str(out / "banner-dark.png")]


def test_build_one_theme_as_svg(write_config: Callable[[str], Path], tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert (
        main(["build", "--config", str(write_config(STARTER)), "--out", str(out), "--theme", "dark", "--format", "svg"])
        == 0
    )
    assert [path.name for path in out.iterdir()] == ["banner-dark.svg"]


def test_build_refuses_an_unknown_theme(
    write_config: Callable[[str], Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["build", "--config", str(write_config(STARTER)), "--out", str(tmp_path / "out"), "--theme", "neon"]) == 1
    )
    assert "no theme named neon" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_build_with_problems_writes_nothing(write_config: Callable[[str], Path], tmp_path: Path) -> None:
    path = write_config(STARTER.replace('footer_left = "Go', 'footer_left = "' + "Go · " * 30))
    assert main(["build", "--config", str(path), "--out", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out").exists()


def test_a_missing_config_is_explained(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--config", str(tmp_path / "missing.toml")]) == 1
    assert "banner-builder: error: no config at" in capsys.readouterr().err


def test_a_config_inside_a_repository_gets_a_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    path = tmp_path / "repo" / "banner.toml"
    path.write_text(STARTER, encoding="utf-8")
    assert main(["check", "--config", str(path)]) == 0
    assert "is inside the git repository at" in capsys.readouterr().err


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0
    assert capsys.readouterr().out.startswith("banner-builder ")
