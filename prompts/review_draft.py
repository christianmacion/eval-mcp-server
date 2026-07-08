"""
prompts/review_draft.py — the MCP Prompt `review-draft`.

A reusable prompt template that wires the score_slop tool into a review
workflow: the client (e.g. Claude Desktop) is told to call score_slop on the
draft, read the SLOP INDEX + flagged rows, and produce a tightened revision.
"""

PROMPT_NAME = "review-draft"

PROMPT_DESCRIPTION = (
    "Run the AI-slop eval gate on a draft, then revise it. Calls the "
    "score_slop tool and turns its flags into concrete edits."
)

# MCP prompt argument schema (name, description, required).
PROMPT_ARGUMENTS = [
    {"name": "draft", "description": "The draft text to review.", "required": True},
    {"name": "target_tier",
     "description": "Desired verdict band: clean | minor (default: clean).",
     "required": False},
]

_TEMPLATE = """\
You are an editor enforcing an AI-slop quality gate before publication.

STEP 1 — Measure. Call the `score_slop` tool on the draft below. Read the
returned SLOP INDEX, verdict, and the per-rule rows whose status is "FLAG" or
"warn". Also fetch the `rubric://slop-rules` resource if you need thresholds.

STEP 2 — Diagnose. For each FLAG/warn row, name the offending span(s) from the
`hits` field (blocklist words, contrastive "not X, it's Y" reframes, intent
framing, finance vagueness, reader commands, assistant residue, etc.).

STEP 3 — Revise. Rewrite the draft to reach the **{target_tier}** band (lower
SLOP INDEX). Remove tells without inventing facts; preserve the author's claims,
structure, and voice. Vary sentence length (raise CV), cut bolded punch-lines,
delete announce-don't-assert framing.

STEP 4 — Verify. Re-run `score_slop` on your revision and report the
before/after SLOP INDEX and verdict.

Return: (a) the revised draft, (b) a short bullet list of the edits you made and
which flagged rule each one addresses, (c) before/after SLOP INDEX.

--- DRAFT ---
{draft}
--- END DRAFT ---
"""


def render(draft, target_tier="clean"):
    """Render the review-draft prompt to a single user-message string."""
    tier = (target_tier or "clean").strip().lower()
    if tier not in ("clean", "minor"):
        tier = "clean"
    return _TEMPLATE.format(draft=draft or "", target_tier=tier)
