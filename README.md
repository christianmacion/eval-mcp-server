# eval-mcp-server — expose your eval gate to any AI client via MCP

**TL;DR.** A Model Context Protocol (MCP) server that exposes my own AI-slop
scanner (and a RAG grounding grader) as MCP **Tools**, a **Resource**, and a
**Prompt** — so any MCP client (e.g. Claude Desktop) can call my eval gate as a
first-class capability. Most MCP demos ship Tools only; this one demonstrates
**all three primitives**.

**Headline metric:** **3 MCP primitives** exposed (2 Tools · 1 Resource ·
1 Prompt) — **100% tool-schema-validity (10/10)** and **100% round-trip parity
(4/4)** on the conformance suite (20/20 total checks). `score_slop` output is
byte-for-byte identical to the underlying engine's `score_text`.

### What is MCP, in two sentences
MCP is an open protocol that lets AI clients call external capabilities through
three primitives — **Tools** (callable functions), **Resources** (readable
context), and **Prompts** (reusable templates). Think of it as "USB-C for AI":
one standard plug, and any host can drive any server.

### How a reviewer clicks it
Run `python3 test_client.py "<text>"` — it prints a SLOP INDEX, a grade_rag
score, the rubric resource, and the rendered prompt. No MCP host, no API key
needed (it falls back to calling the logic directly if `mcp` isn't installed).
Register the snippet in Claude Desktop and the same tools/resource/prompt appear
in the client.

---

## The three primitives

| Primitive | Name | What it does |
|---|---|---|
| **Tool** | `score_slop(text)` | Scores prose for AI-slop tells → `slop_index`, `verdict`, per-rule `rows`, flagged `hits`. Wraps the vendored `slop_engine.score_text`. |
| **Tool** | `grade_rag(question, answer, context)` | Deterministic RAG grounding/faithfulness score: fraction of the answer's content tokens supported by the context → score + verdict (`GROUNDED` / `PARTIALLY GROUNDED` / `UNSUPPORTED`). |
| **Resource** | `rubric://slop-rules` | Serves the rule list, thresholds, scoring weights, and verdict bands — derived from the engine so it never drifts. |
| **Prompt** | `review-draft` | Reusable template that wires `score_slop` into a measure → diagnose → revise → re-measure editing workflow. |

---

## Run it

### 1. Reproduce the metric (one command, no key, no mcp)
```bash
python3 tests/test_conformance.py
```
Tests the stdlib logic module directly. Prints **tool-schema-validity %** and
**round-trip-parity %**. Exits non-zero on any failure.

### 2. Call the gate (the reviewer path)
```bash
python3 test_client.py "In today's fast-paced world, let's delve into this robust, transformative paradigm."
```
If `mcp` is installed it does a real stdio round-trip against `server.py`;
otherwise it calls the logic directly. Either way you get JSON back.

### 3. Run the MCP server over stdio
```bash
pip install -r requirements.txt   # installs the official `mcp` SDK
python3 -m server                 # serves Tools/Resources/Prompts over stdio
```

### 4. Register in Claude Desktop
See `claude_desktop_config.snippet.json` — merge the `eval-gate` entry into your
`claude_desktop_config.json`, fix the absolute path, restart, and the
tools/resource/prompt show up in the client.

---

## Architecture (why it's testable without `mcp`)

The **logic** lives in stdlib-only modules that import only `slop_engine`:

```
slop_engine.py            vendored scoring core (stdlib-only; copy of the sibling slop-scanner engine)
tools/logic.py            single source of truth: registers every primitive
tools/grade_rag.py        deterministic grounding grader (+ optional Anthropic live mode)
resources/rubric.py       builds the rubric://slop-rules payload from the engine
prompts/review_draft.py   the review-draft prompt template
server.py                 THIN MCP wrapper — imports `mcp`, registers the above over stdio
test_client.py            stdio round-trip if mcp present, else direct-logic fallback
tests/test_conformance.py runnable as plain python3; tests logic, not mcp
claude_desktop_config.snippet.json
requirements.txt
```

`server.py` is a thin adapter; all behaviour is in the logic modules. That's why
the conformance suite and the test-client fallback run with zero dependencies.

---

## The four-part contract

1. **TL;DR + headline metric + run steps + reviewer line** — above.
2. **Reproducible metric** — `python3 tests/test_conformance.py` (one command).
3. **Offline / no-key path** — everything here runs with **no API key**; the
   tools are fully deterministic. `grade_rag` has an *optional* Anthropic live
   mode (`live=True`), lazy-imported and gated on `ANTHROPIC_API_KEY`; it
   **defaults to the stdlib check** and never touches the network otherwise.
4. **Honest scope** — this project is about **protocol/integration rigor**: it
   exposes deterministic eval tools over MCP correctly, with all three
   primitives and tested round-trip parity. It is **not** a claim about model
   quality — `score_slop` is a heuristic linter (flags mean "go look," not
   "delete"), and `grade_rag` is a token-overlap grounding proxy, not a semantic
   judge. Cross-link: this makes the sibling **slop-scanner** a *callable
   capability* for any agent — register it once and any MCP host can gate its
   own output on it.

---

*Christian Macion — AI / Agent Engineer*
