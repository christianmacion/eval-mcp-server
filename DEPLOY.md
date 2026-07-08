# Deploy — eval-mcp-server (MCP)

An MCP server is **not** a web app — it runs over **stdio** and is registered inside an MCP client (e.g. Claude Desktop). "Deploying" it means making it callable from a client and/or publishing the repo. Three paths below.

## 0. Prerequisites
```bash
cd "06_projects/eval-mcp-server"
pip install -r requirements.txt      # installs the `mcp` SDK
python3 tests/test_conformance.py    # confirm 20/20 conformance, 100% round-trip parity
```

## A. Use it in Claude Desktop (primary)
1. Find your absolute paths:
   - the server: `.../06_projects/eval-mcp-server/server.py`
   - your python: `which python3`
2. Open the Claude Desktop config file (create it if missing):
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
3. Merge in the snippet from `claude_desktop_config.snippet.json`, using **absolute paths**:
   ```json
   {
     "mcpServers": {
       "eval-gate": {
         "command": "/absolute/path/to/python3",
         "args": ["/absolute/path/to/eval-mcp-server/server.py"]
       }
     }
   }
   ```
4. **Fully quit and reopen Claude Desktop.** The server's tools (`score_slop`, `grade_rag`), the `rubric://slop-rules` resource, and the `review-draft` prompt now appear. Try: *"Use the eval-gate tool to score this draft for slop: …"*

## B. No MCP host? Use the bundled test client
```bash
python3 test_client.py "In today's fast-paced world, let's delve into this robust paradigm."
# does a real stdio round-trip if `mcp` is installed; otherwise falls back to calling the logic directly
```

## C. Publish it
- Push to its own public GitHub repo:
  ```bash
  git init && git add . && git commit -m "eval-mcp-server: MCP server exposing an eval gate (3 primitives)"
  gh repo create eval-mcp-server --public --source=. --push
  ```
- *(Optional)* list it on an MCP registry (e.g. Smithery / the public MCP registry) so others can install it by name.
- *(Stretch)* wrap `server.py` in an HTTP/SSE transport to host it as a remote MCP server.

## What a reviewer sees
The README's headline — **3 MCP primitives (2 Tools · 1 Resource · 1 Prompt), 20/20 conformance, 100% round-trip parity** — and, in Claude Desktop, your slop-evaluation gate callable as a first-class tool from any chat.

---
*Christian Macion — AI / Agent Engineer.*
