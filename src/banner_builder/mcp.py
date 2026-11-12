"""
A Model Context Protocol server, so an AI agent can build a banner the same way a person does.

``banner-builder mcp`` speaks JSON-RPC 2.0 over stdio, one message per line, with no dependencies. The tools map one
to one onto the commands. None of them touches the network; ``build`` and ``init`` write files on this machine.
"""

import json
import sys
from collections.abc import Callable
from importlib import metadata
from typing import Any, TextIO

from banner_builder import api

PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

INSTRUCTIONS = (
    "banner-builder draws a profile banner (LinkedIn by default) from a TOML config on this machine. Start with "
    "config_path; if the config does not exist, init writes a starter. Edit the TOML file, then run check: it "
    "reports the layout and the contrast, and lists problems to fix. build writes the PNG and SVG files only when "
    "check passes. The config holds the user's own words: never copy it into a git repository."
)

_CONFIG = {"type": "string", "description": "config file path; omit for the default"}

TOOLS: dict[str, tuple[Callable[..., dict[str, Any]], str, dict[str, Any], bool, bool]] = {
    # name: (function, description, properties, read only, destructive)
    "config_path": (
        api.config_path,
        "Where the config is read from, and whether it exists.",
        {"config": _CONFIG},
        True,
        False,
    ),
    "init": (
        api.init,
        "Write the starter config. Refuses to replace an existing one unless force is true.",
        {"config": _CONFIG, "force": {"type": "boolean", "description": "replace an existing config"}},
        False,
        True,
    ),
    "check": (
        api.check,
        "Test the config, the layout and the colour contrast, and write nothing. Lists problems to fix.",
        {"config": _CONFIG},
        True,
        False,
    ),
    "build": (
        api.build,
        "Write the banner PNG and SVG files, replacing earlier ones of the same name. Writes nothing if a check fails.",
        {
            "config": _CONFIG,
            "out": {"type": "string", "description": "folder to write into; omit for the config's [output] dir"},
            "themes": {"type": "array", "items": {"type": "string"}, "description": "only these themes"},
            "formats": {"type": "array", "items": {"enum": ["png", "svg"]}, "description": "only these formats"},
            "scales": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 4}},
        },
        False,
        False,
    ),
}


def tools() -> list[dict[str, Any]]:
    """
    Describe the tools for ``tools/list``.

    :returns: MCP tool definitions
    """
    return [
        {
            "name": name,
            "description": about,
            "inputSchema": {"type": "object", "properties": props, "additionalProperties": False},
            "annotations": {
                "readOnlyHint": readonly,
                "destructiveHint": destructive,
                "idempotentHint": name != "init",
                "openWorldHint": False,
            },
        }
        for name, (_, about, props, readonly, destructive) in TOOLS.items()
    ]


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    """
    Answer one JSON-RPC message.

    :param message: The request or notification
    :returns: The response, or None for a notification
    """
    mid = message.get("id")
    if mid is None:
        return None
    method = str(message.get("method", ""))
    params = message.get("params") or {}
    if method == "initialize":
        asked = str(params.get("protocolVersion", ""))
        result: dict[str, Any] = {
            "protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "banner-builder", "title": "banner-builder", "version": _version()},
            "instructions": INSTRUCTIONS,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": tools()}
    elif method in ("resources/list", "prompts/list"):
        result = {method.split("/")[0]: []}
    elif method == "tools/call":
        result = _call(str(params.get("name", "")), params.get("arguments") or {})
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        return {"content": [{"type": "text", "text": f"Error: unknown tool {name!r}"}], "isError": True}
    function, _, props, _, _ = TOOLS[name]
    extra = set(arguments) - set(props)
    if extra:
        return {"content": [{"type": "text", "text": f"Error: unknown argument {sorted(extra)}"}], "isError": True}
    try:
        data = function(**arguments)
    except (FileNotFoundError, FileExistsError, ValueError, TypeError) as error:
        return {"content": [{"type": "text", "text": f"Error: {error}"}], "isError": True}
    failed = data.get("ok") is False
    return {
        "content": [{"type": "text", "text": json.dumps(data, indent=1)}],
        "structuredContent": data,
        "isError": failed,
    }


def serve_stdio(stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
    """
    Serve MCP over stdio until the input closes.

    :param stdin: Input stream, standard input by default
    :param stdout: Output stream, standard output by default
    """
    reader, writer = stdin or sys.stdin, stdout or sys.stdout
    for line in reader:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            reply: list[dict[str, Any]] = [
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            ]
        else:
            batch = message if isinstance(message, list) else [message]
            reply = [r for r in (handle(m) for m in batch if isinstance(m, dict)) if r is not None]
        for item in reply:
            writer.write(json.dumps(item) + "\n")
        writer.flush()


def _version() -> str:
    try:
        return metadata.version("banner-builder")
    except metadata.PackageNotFoundError:
        return "unknown"
