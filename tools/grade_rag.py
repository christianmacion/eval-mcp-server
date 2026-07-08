"""
tools/grade_rag.py — deterministic, stdlib-only RAG grounding / faithfulness grader.

The question: of the answer's *content* tokens (after stopword removal), what
fraction are supported by the supplied context? This is a cheap, fully
deterministic proxy for "faithfulness" — it does NOT judge correctness or
fluency, only whether the answer is grounded in the retrieved context.

Public API:
    grade_rag(question, answer, context, *, live=False) -> dict

Optional live mode: if `live=True` AND ANTHROPIC_API_KEY is set, lazily import
the Anthropic SDK and ask Claude for a faithfulness judgement. Defaults OFF —
the stdlib check runs with no key, no network, fully reproducible.
"""

import os
import re

# A small, generic English stopword set. Kept inline (stdlib-only, no nltk).
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "he", "her", "here", "him", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "may", "might", "must", "no", "not", "of", "on", "or", "our",
    "out", "over", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "to", "up", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "why",
    "will", "with", "would", "you", "your",
}


def _content_tokens(text):
    """Lowercase alphanumeric tokens, stopwords and 1-char tokens removed."""
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in toks if t not in STOPWORDS and len(t) > 1]


def _verdict(coverage):
    if coverage >= 0.80:
        return "GROUNDED", "grounded"
    if coverage >= 0.50:
        return "PARTIALLY GROUNDED", "partial"
    return "UNSUPPORTED — likely hallucinated", "unsupported"


def grade_rag(question, answer, context, *, live=False):
    """
    Deterministic grounding score for a (question, answer, context) triple.

    Returns a JSON-serializable dict:
        grounding_score  float 0..1  (fraction of answer content tokens in context)
        verdict          str
        tier             str
        supported        [tokens found in context]
        unsupported      [tokens NOT found in context]
        n_answer_tokens  int
        mode             "stdlib" | "anthropic-live"
    """
    answer_toks = _content_tokens(answer)
    context_set = set(_content_tokens(context))

    if not answer_toks:
        result = {
            "grounding_score": 0.0,
            "verdict": "EMPTY ANSWER",
            "tier": "empty",
            "supported": [],
            "unsupported": [],
            "n_answer_tokens": 0,
            "mode": "stdlib",
        }
    else:
        # Dedup while preserving order for stable, readable output.
        seen = set()
        unique_toks = [t for t in answer_toks if not (t in seen or seen.add(t))]
        supported = [t for t in unique_toks if t in context_set]
        unsupported = [t for t in unique_toks if t not in context_set]
        # Score over ALL answer tokens (token frequency weighted), not unique,
        # so repeated unsupported claims are penalised proportionally.
        n_supported = sum(1 for t in answer_toks if t in context_set)
        coverage = round(n_supported / len(answer_toks), 4)
        label, tier = _verdict(coverage)
        result = {
            "grounding_score": coverage,
            "verdict": label,
            "tier": tier,
            "supported": supported,
            "unsupported": unsupported,
            "n_answer_tokens": len(answer_toks),
            "mode": "stdlib",
        }

    if live and os.environ.get("ANTHROPIC_API_KEY"):
        live_judgement = _grade_rag_live(question, answer, context)
        if live_judgement is not None:
            result["anthropic_live"] = live_judgement
            result["mode"] = "anthropic-live"

    return result


def _grade_rag_live(question, answer, context):
    """
    Optional live faithfulness judgement via Claude. Lazy-imported and gated on
    ANTHROPIC_API_KEY so the default path stays stdlib-only and key-free.
    Returns a dict or None on any failure (never raises into the caller).
    """
    try:
        import json as _json
        from anthropic import Anthropic  # lazy import — only if live mode used
    except Exception:
        return None

    try:
        client = Anthropic()
        prompt = (
            "You are a strict RAG faithfulness grader. Decide whether the ANSWER "
            "is fully supported by the CONTEXT (no claims beyond it). Reply with "
            "ONLY a JSON object: {\"faithful\": true|false, \"reason\": \"...\"}.\n\n"
            f"QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nANSWER:\n{answer}\n"
        )
        msg = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return _json.loads(raw.strip())
    except Exception as e:  # network / parse / auth — degrade gracefully
        return {"error": str(e)}
