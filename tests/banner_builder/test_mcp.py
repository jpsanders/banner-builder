import io
import json
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

from banner_builder import mcp

STARTER = resources.files("banner_builder").joinpath("example.toml").read_text(encoding="utf-8")


def ask(*messages: dict[str, Any]) -> list[dict[str, Any]]:
    out = io.StringIO()
    mcp.serve_stdio(io.StringIO("".join(json.dumps(m) + "\n" for m in messages)), out)
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_initialize_and_list() -> None:
    init, listed = ask(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert init["result"]["protocolVersion"] == "2025-06-18"
    assert init["result"]["serverInfo"]["name"] == "banner-builder"
    names = {tool["name"]: tool["annotations"] for tool in listed["result"]["tools"]}
    assert set(names) == {"config_path", "init", "check", "build"}
    assert names["check"]["readOnlyHint"] is True
    assert names["init"]["destructiveHint"] is True


def test_check_and_build(write_config: Callable[[str], Path], tmp_path: Path) -> None:
    config = str(write_config(STARTER))
    check, build = ask(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "check", "arguments": {"config": config}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "build",
                "arguments": {"config": config, "out": str(tmp_path / "out"), "formats": ["svg"], "themes": ["dark"]},
            },
        },
    )
    assert check["result"]["isError"] is False
    assert check["result"]["structuredContent"]["headline_size"] == 84
    assert build["result"]["structuredContent"]["written"] == [str(tmp_path / "out" / "banner-dark.svg")]


def test_errors_are_tool_errors(tmp_path: Path) -> None:
    (missing,) = ask(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "check", "arguments": {"config": str(tmp_path / "none.toml")}},
        }
    )
    assert missing["result"]["isError"] is True
    (unknown,) = ask({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "rm", "arguments": {}}})
    assert unknown["result"]["isError"] is True
    (bad,) = ask({"jsonrpc": "2.0", "id": 3, "method": "nope"})
    assert bad["error"]["code"] == -32601
