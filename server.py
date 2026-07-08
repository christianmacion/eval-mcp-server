"""
server.py — MCP server exposing the eval gate over stdio.

THIN WRAPPER. All tool/resource/prompt LOGIC lives in stdlib-only modules
(tools.logic, resources.rubric, prompts.review_draft) that import ONLY
slop_engine. This file just registers those functions with the official MCP
Python SDK (`mcp`) and runs them over the stdio transport.

Run:   python -m server      (or: python server.py)
Register in Claude Desktop:  see claude_desktop_config.snippet.json

If `mcp` is not installed, importing this module fails with a clear message;
the logic itself is fully exercised by tests/test_conformance.py and
test_client.py, neither of which require `mcp`.
"""

import asyncio
import json
import sys

try:
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError as e:  # pragma: no cover - environment-dependent
    sys.stderr.write(
        "ERROR: the 'mcp' package is required to run the MCP server.\n"
        "       Install it with:  pip install -r requirements.txt\n"
        "       (The eval logic itself runs without mcp — see test_client.py\n"
        "        and tests/test_conformance.py.)\n"
    )
    raise

from tools import logic

app = Server("eval-mcp-server")


# --- Tools ------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["input_schema"],
        )
        for t in logic.TOOLS
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    result = logic.call_tool(name, arguments or {})
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


# --- Resources --------------------------------------------------------------

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=r["uri"],
            name=r["name"],
            description=r["description"],
            mimeType=r["mime_type"],
        )
        for r in logic.RESOURCES
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    for r in logic.RESOURCES:
        if str(uri) == r["uri"]:
            return r["fn"]()
    raise ValueError(f"unknown resource: {uri}")


# --- Prompts ----------------------------------------------------------------

@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name=p["name"],
            description=p["description"],
            arguments=[
                types.PromptArgument(
                    name=a["name"],
                    description=a["description"],
                    required=a["required"],
                )
                for a in p["arguments"]
            ],
        )
        for p in logic.PROMPTS
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None) -> types.GetPromptResult:
    if name != logic.REVIEW_PROMPT_NAME:
        raise ValueError(f"unknown prompt: {name}")
    arguments = arguments or {}
    rendered = logic.render_review_prompt(
        draft=arguments.get("draft", ""),
        target_tier=arguments.get("target_tier", "clean"),
    )
    return types.GetPromptResult(
        description=logic.REVIEW_PROMPT_DESCRIPTION,
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=rendered),
            )
        ],
    )


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
