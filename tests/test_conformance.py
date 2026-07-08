"""
tests/test_conformance.py — conformance + round-trip parity for the eval gate.

Runs as plain `python3 tests/test_conformance.py` — tests the stdlib logic
module directly. Does NOT require the `mcp` package (the MCP wrapper is verified
separately by `python3 -m py_compile server.py`).

Asserts:
  1. Each declared tool returns schema-valid JSON for sample inputs.
  2. score_slop output EXACTLY matches slop_engine.score_text (round-trip parity).
  3. The rubric resource is non-empty and valid JSON.
  4. The review-draft prompt template renders (and embeds the draft).

Reports tool-schema-validity % and round-trip-parity %.
"""

import json
import os
import sys

# Make the repo root importable when run as `python3 tests/test_conformance.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import slop_engine
from tools import logic


# --------------------------------------------------------------------------
# Minimal JSON-Schema validator (stdlib only) — enough for our flat schemas:
# type object/string/boolean, properties, required.
# --------------------------------------------------------------------------

_PY_TYPES = {
    "object": dict, "string": str, "boolean": bool,
    "number": (int, float), "integer": int, "array": list,
}


def schema_valid(value, schema):
    t = schema.get("type")
    if t and not isinstance(value, _PY_TYPES[t]):
        # bool is a subclass of int — guard number/integer against bool
        if t in ("number", "integer") and isinstance(value, bool):
            return False
        return False
    if t == "object":
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                return False
        for k, v in value.items():
            if k in props and not schema_valid(v, props[k]):
                return False
    return True


# A result schema each tool's output must conform to (separate from the
# input_schema the MCP server advertises).
SCORE_SLOP_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "slop_index": {"type": "number"},
        "verdict": {"type": "string"},
        "tier": {"type": "string"},
        "n_words": {"type": "integer"},
        "rows": {"type": "array"},
        "hits": {"type": "object"},
    },
    "required": ["slop_index", "verdict", "tier", "rows"],
}

GRADE_RAG_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "grounding_score": {"type": "number"},
        "verdict": {"type": "string"},
        "tier": {"type": "string"},
        "supported": {"type": "array"},
        "unsupported": {"type": "array"},
        "mode": {"type": "string"},
    },
    "required": ["grounding_score", "verdict", "mode"],
}


# --------------------------------------------------------------------------
# Test inputs
# --------------------------------------------------------------------------

SLOP_SAMPLES = [
    "In today's fast-paced world, let's delve into this robust, transformative paradigm.",
    "The cat sat on the mat. It was a quiet afternoon and nothing much happened.",
    "Moreover, this comprehensive guide will explore the nuanced, multifaceted ecosystem.",
    "",  # edge case: empty input must not crash
]

RAG_SAMPLES = [
    # (question, answer, context)
    ("What is the capital of France?",
     "The capital of France is Paris.",
     "France is a country in Europe. Its capital city is Paris."),
    ("When was the company founded?",
     "The company was founded by aliens in 1850 on Mars.",
     "The company was founded in 1850 as a small textile workshop."),
    ("Empty?", "", "some context here"),  # empty answer edge case
]


def main():
    checks = []          # (name, passed)
    parity_checks = []   # (name, passed)

    def check(name, passed):
        checks.append((name, bool(passed)))
        flag = "PASS" if passed else "FAIL"
        print(f"  [{flag}] {name}")

    print("Tool schema validity")
    print("-" * 50)

    # 1a. score_slop must be JSON-serializable AND schema-valid.
    for i, text in enumerate(SLOP_SAMPLES):
        out = logic.score_slop(text)
        roundtripped = json.loads(json.dumps(out))  # serializable?
        check(f"score_slop[{i}] schema-valid",
              schema_valid(roundtripped, SCORE_SLOP_RESULT_SCHEMA))

    # 1b. grade_rag must be JSON-serializable AND schema-valid.
    for i, (q, a, c) in enumerate(RAG_SAMPLES):
        out = logic.grade_rag(q, a, c)
        roundtripped = json.loads(json.dumps(out))
        check(f"grade_rag[{i}] schema-valid",
              schema_valid(roundtripped, GRADE_RAG_RESULT_SCHEMA))
        # grounding_score must be a fraction in [0, 1]
        check(f"grade_rag[{i}] score in [0,1]",
              0.0 <= out["grounding_score"] <= 1.0)

    schema_total = len(checks)
    schema_passed = sum(1 for _, p in checks if p)

    print("\nRound-trip parity (score_slop == slop_engine.score_text)")
    print("-" * 50)

    # 2. Exact parity with the vendored engine on every sample.
    for i, text in enumerate(SLOP_SAMPLES):
        direct = slop_engine.score_text(text)
        via_tool = logic.score_slop(text)
        passed = direct == via_tool
        parity_checks.append((f"parity[{i}]", passed))
        check(f"score_slop[{i}] == score_text[{i}]", passed)

    print("\nResource + Prompt")
    print("-" * 50)

    # 3. Rubric resource non-empty + valid JSON + contains expected keys.
    rub = logic.rubric_resource()
    check("rubric resource non-empty", bool(rub and rub.strip()))
    rub_obj = json.loads(rub)
    check("rubric resource has rules", len(rub_obj.get("rules", [])) > 0)
    check("rubric resource has verdict_bands",
          len(rub_obj.get("verdict_bands", [])) == 4)

    # 4. Prompt template renders and embeds the draft text.
    draft = "delve into the robust paradigm"
    rendered = logic.render_review_prompt(draft)
    check("prompt renders non-empty", bool(rendered.strip()))
    check("prompt embeds the draft", draft in rendered)
    check("prompt names score_slop", "score_slop" in rendered)

    # --- Report ---
    total = len(checks)
    passed = sum(1 for _, p in checks if p)
    schema_pct = round(100 * schema_passed / schema_total, 1) if schema_total else 0.0
    parity_passed = sum(1 for _, p in parity_checks if p)
    parity_pct = round(100 * parity_passed / len(parity_checks), 1) if parity_checks else 0.0

    print("\n" + "=" * 50)
    print("CONFORMANCE REPORT")
    print("=" * 50)
    print(f"  tool-schema-validity : {schema_passed}/{schema_total}  ({schema_pct}%)")
    print(f"  round-trip-parity    : {parity_passed}/{len(parity_checks)}  ({parity_pct}%)")
    print(f"  total checks         : {passed}/{total}")
    print("=" * 50)

    failed = [n for n, p in checks if not p]
    if failed:
        print("FAILED:", ", ".join(failed))
        sys.exit(1)
    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
