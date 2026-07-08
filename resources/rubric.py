"""
resources/rubric.py — the MCP Resource payload for `rubric://slop-rules`.

Builds a machine-readable rubric (rule list + thresholds + scoring weights +
verdict bands) directly from the vendored slop_engine's metric definitions, so
the resource never drifts from the actual scoring logic.
"""

import json

import slop_engine

RUBRIC_URI = "rubric://slop-rules"


def build_rubric():
    """Return the rubric as a JSON-serializable dict, derived from slop_engine."""
    # Run the engine on empty text purely to harvest the canonical row schema
    # (metric name + note), then attach thresholds/weights from the engine.
    rows = slop_engine._rows(slop_engine.analyze_text(""))

    rules = []
    for r in rows:
        rules.append({
            "metric": r[0],
            "note": r[3],          # human-readable threshold guidance
        })

    return {
        "name": "AI-Slop Scanner rubric",
        "uri": RUBRIC_URI,
        "description": (
            "Density/co-occurrence rules for detecting AI-generated prose. "
            "No single metric proves AI authorship — flags mean 'go look,' not "
            "'delete on sight.' The human reader is the judge."
        ),
        "verdict_bands": [
            {"tier": "clean",    "label": "CLEAN",                 "slop_index": "< 15"},
            {"tier": "minor",    "label": "MINOR TELLS",           "slop_index": "15–39"},
            {"tier": "reads_ai", "label": "READS AI — revise",     "slop_index": "40–79"},
            {"tier": "heavy",    "label": "HEAVY SLOP — rewrite",  "slop_index": "≥ 80"},
        ],
        "rules": rules,
        "scoring_weights": {
            "emdash_per1k_over_5":     "x1.2 per unit over 5/1k",
            "contrastive_reframe":     "x4 per hit",
            "low_cv_under_0.4":        "+12 flat",
            "monotony_run_over_3":     "x3 per sentence over 3",
            "ing_openers_over_6pct":   "x2 per point over 6%",
            "bold_per1k_over_5":       "x1.0 per unit over 5/1k",
            "blocklist_words":         "x3 per hit",
            "blocklist_phrases":       "x4 per hit",
            "intent_framing":          "x6 per hit",
            "finance_vagueness":       "x6 per hit",
            "reader_commands":         "x3 per hit",
            "assistant_residue":       "x25 per hit",
            "title_colon_formula":     "+15 flat",
        },
        "blocklist_words": list(slop_engine.BLOCKLIST),
        "blocklist_phrases": list(slop_engine.BLOCK_PHRASES),
    }


def rubric_text():
    """Pretty-printed JSON string — the Resource body served over MCP."""
    return json.dumps(build_rubric(), indent=2, ensure_ascii=False)
