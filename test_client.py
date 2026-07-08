"""
test_client.py — call the eval gate and print JSON, with or without MCP.

Usage:
    python3 test_client.py "some text to score for slop"
    python3 test_client.py            # uses a built-in slop-heavy sample

Behaviour:
    * If the `mcp` package is installed, spins up server.py over stdio, does a
      real MCP round-trip (initialize -> list_tools -> call_tool score_slop ->
      read_resource rubric -> get_prompt review-draft), and prints what came
      back over the wire.
    * If `mcp` is NOT installed (this sandbox), falls back to calling the
      stdlib logic module directly, so a reviewer always sees a result.

Either way you get a SLOP INDEX printed.
"""

import asyncio
import json
import sys

SAMPLE = ("In today's fast-paced world, let's delve into this robust, "
          "transformative paradigm.")


def _print_header(mode):
    print("=" * 64)
    print(f"  eval-mcp-server test client   [mode: {mode}]")
    print("=" * 64)


def _print_slop(result):
    print(f"\nSLOP INDEX: {result['slop_index']}   ->   {result['verdict']}")
    print(f"words={result['n_words']}  sentences={result['n_sentences']}")
    flagged = [r for r in result["rows"] if r["status"] in ("FLAG", "warn")]
    if flagged:
        print("flagged rows:")
        for r in flagged:
            print(f"  [{r['status']:>4}] {r['metric']}: {r['value']}")


# --------------------------------------------------------------------------
# Fallback path: call the stdlib logic directly (no mcp required)
# --------------------------------------------------------------------------

def run_direct(text):
    from tools import logic

    _print_header("direct logic (mcp not installed)")

    print("\n--- TOOL score_slop ---")
    slop = logic.score_slop(text)
    _print_slop(slop)

    print("\n--- TOOL grade_rag (demo) ---")
    rag = logic.grade_rag(
        question="What is the capital of France?",
        answer="The capital of France is Paris.",
        context="France is a country in Europe. Its capital city is Paris.",
    )
    print(json.dumps({k: rag[k] for k in ("grounding_score", "verdict", "mode")},
                     indent=2))

    print("\n--- RESOURCE rubric://slop-rules (first 240 chars) ---")
    print(logic.rubric_resource()[:240] + " ...")

    print("\n--- PROMPT review-draft (first 200 chars) ---")
    print(logic.render_review_prompt(text)[:200] + " ...")


# --------------------------------------------------------------------------
# Real path: stdio round-trip against server.py via the mcp client
# --------------------------------------------------------------------------

async def run_mcp(text):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _print_header("real MCP stdio round-trip")

    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("\ntools:", [t.name for t in tools.tools])

            print("\n--- TOOL score_slop ---")
            res = await session.call_tool("score_slop", {"text": text})
            slop = json.loads(res.content[0].text)
            _print_slop(slop)

            print("\n--- TOOL grade_rag (demo) ---")
            res = await session.call_tool("grade_rag", {
                "question": "What is the capital of France?",
                "answer": "The capital of France is Paris.",
                "context": "France is a country in Europe. Its capital is Paris.",
            })
            rag = json.loads(res.content[0].text)
            print(json.dumps({k: rag[k] for k in ("grounding_score", "verdict",
                                                   "mode")}, indent=2))

            print("\n--- RESOURCE rubric://slop-rules (first 240 chars) ---")
            rub = await session.read_resource("rubric://slop-rules")
            print(rub.contents[0].text[:240] + " ...")

            print("\n--- PROMPT review-draft (first 200 chars) ---")
            pr = await session.get_prompt("review-draft", {"draft": text})
            print(pr.messages[0].content.text[:200] + " ...")


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else SAMPLE
    try:
        import mcp  # noqa: F401
        has_mcp = True
    except ImportError:
        has_mcp = False

    if has_mcp:
        try:
            asyncio.run(run_mcp(text))
            return
        except Exception as e:  # pragma: no cover - falls back on any wire error
            print(f"[mcp round-trip failed: {e!r}; falling back to direct logic]\n")

    run_direct(text)


if __name__ == "__main__":
    main()
