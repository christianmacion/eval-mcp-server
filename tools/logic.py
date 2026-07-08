"""
tools/logic.py — the single, stdlib-only source of truth for every MCP primitive.

This module imports ONLY slop_engine (stdlib) plus the sibling logic modules.
It deliberately knows NOTHING about the `mcp` package, so it is fully testable
and runnable without MCP installed. The MCP server (`server.py`) is a thin
wrapper that registers these functions; the test client falls back to them when
`mcp` is absent.

Exposed primitives:
    score_slop(text)                  -> Tool
    grade_rag(question, answer, ctx)  -> Tool
    rubric_resource()                 -> Resource (rubric://slop-rules)
    render_review_prompt(draft, tier) -> Prompt  (review-draft)

Each returns a plain JSON-serializable dict / str.
"""

import slop_engine
from resources.rubric import RUBRIC_URI, build_rubric, rubric_text
from prompts.review_draft import (
    PROMPT_NAME, PROMPT_DESCRIPTION, PROMPT_ARGUMENTS, render as _render_prompt,
)
from tools.grade_rag import grade_rag as _grade_rag


# --- Tool 1: score_slop -----------------------------------------------------

def score_slop(text):
    """
    MCP Tool. Score a text for AI-slop tells via the vendored slop_engine.
    Returns slop_engine.score_text(text) UNCHANGED — round-trip parity with the
    sibling slop-scanner is a tested invariant.
    """
    return slop_engine.score_text(text or "")


SCORE_SLOP_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Draft / prose to score."},
    },
    "required": ["text"],
}


# --- Tool 2: grade_rag ------------------------------------------------------

def grade_rag(question, answer, context, live=False):
    """
    MCP Tool. Deterministic RAG grounding/faithfulness score: fraction of the
    answer's content tokens supported by the context. Optional live=True uses
    Claude IF ANTHROPIC_API_KEY is set; default is stdlib-only.
    """
    return _grade_rag(question, answer, context, live=live)


GRADE_RAG_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "description": "The user question."},
        "answer": {"type": "string", "description": "The RAG answer to grade."},
        "context": {"type": "string", "description": "Retrieved context the answer must be grounded in."},
        "live": {"type": "boolean", "description": "Use Claude live faithfulness check (needs ANTHROPIC_API_KEY). Default false."},
    },
    "required": ["question", "answer", "context"],
}


# --- Resource: rubric://slop-rules ------------------------------------------

def rubric_resource():
    """
    MCP Resource body for rubric://slop-rules. Returns the pretty-printed JSON
    rubric (rules + thresholds + weights), derived from slop_engine.
    """
    return rubric_text()


RUBRIC_RESOURCE_URI = RUBRIC_URI
RUBRIC_RESOURCE_MIME = "application/json"


# --- Prompt: review-draft ---------------------------------------------------

def render_review_prompt(draft, target_tier="clean"):
    """MCP Prompt body for review-draft. Returns the rendered prompt string."""
    return _render_prompt(draft, target_tier)


REVIEW_PROMPT_NAME = PROMPT_NAME
REVIEW_PROMPT_DESCRIPTION = PROMPT_DESCRIPTION
REVIEW_PROMPT_ARGUMENTS = PROMPT_ARGUMENTS


# --- Registry: a single declarative manifest of all primitives --------------
# server.py iterates this; tests assert against it.

TOOLS = [
    {
        "name": "score_slop",
        "description": "Score text for AI-slop tells (SLOP INDEX, verdict, per-rule rows, flagged spans).",
        "input_schema": SCORE_SLOP_SCHEMA,
        "fn": score_slop,
    },
    {
        "name": "grade_rag",
        "description": "Deterministic RAG grounding/faithfulness score: fraction of answer tokens supported by context.",
        "input_schema": GRADE_RAG_SCHEMA,
        "fn": grade_rag,
    },
]

RESOURCES = [
    {
        "uri": RUBRIC_RESOURCE_URI,
        "name": "slop-rules",
        "description": "AI-slop rubric: rules, thresholds, scoring weights, verdict bands.",
        "mime_type": RUBRIC_RESOURCE_MIME,
        "fn": rubric_resource,
    },
]

PROMPTS = [
    {
        "name": REVIEW_PROMPT_NAME,
        "description": REVIEW_PROMPT_DESCRIPTION,
        "arguments": REVIEW_PROMPT_ARGUMENTS,
        "fn": render_review_prompt,
    },
]


def call_tool(name, arguments):
    """Dispatch a tool by name with a kwargs dict (used by server + test client)."""
    for t in TOOLS:
        if t["name"] == name:
            return t["fn"](**arguments)
    raise KeyError(f"unknown tool: {name}")
