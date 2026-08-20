"""
case.py
--------------------
RAG engine specifically for Case Outcome Predictor.
Uses case.csv — no Ollama, no external dependencies beyond stdlib.

Place this file in the same directory as app.py, named case.py
(app.py does `from case import search_case_outcome, format_outcome_html`).
Make sure case.csv is also in the same directory.
"""

import csv
import os
import re

# ── Path to dataset ────────────────────────────────────────────────────────────
DATASET_PATH = os.path.join(os.path.dirname(__file__), "case.csv")

# ── In-memory store loaded once at startup ─────────────────────────────────────
_RECORDS: list[dict] = []
_LOADED = False


def _safe_str(value) -> str:
    """csv.DictReader can hand back None for missing/ragged fields.
    Every downstream .strip()/.lower() call assumes a string, so normalize here."""
    return "" if value is None else str(value)


def _load_dataset() -> None:
    """Load CSV into memory once."""
    global _RECORDS, _LOADED
    if _LOADED:
        return

    if not os.path.exists(DATASET_PATH):
        print(f"[case.py] ERROR: Dataset not found at {DATASET_PATH}")
        _LOADED = True
        return

    try:
        with open(DATASET_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize every field to a string up front so nothing
                # downstream has to guard against None individually.
                row = {k: _safe_str(v) for k, v in row.items()}

                raw_kw = row.get("keywords", "").strip().strip('"')
                row["_keyword_list"] = [k.strip().lower() for k in raw_kw.split(",") if k.strip()]
                _RECORDS.append(row)
    except Exception as e:
        print(f"[case.py] ERROR loading dataset: {e}")
        _RECORDS = []

    print(f"[case.py] Loaded {len(_RECORDS)} entries from dataset.")
    _LOADED = True


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, return tokens of length >= 2."""
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 2]


def _score_record(record: dict, query_tokens: list[str]) -> float:
    """
    Score a record against query tokens.

    Scoring rules (higher = better match):
      +3  exact keyword phrase found in query string
      +2  query token found in keyword list as substring
      +1  query token found in crime_type
      +1  query token found in title
      +0.5 query token found in description
    """
    score = 0.0
    query_str = " ".join(query_tokens)

    kw_list   = record.get("_keyword_list", [])
    crime     = _safe_str(record.get("crime_type", "")).lower()
    title     = _safe_str(record.get("title", "")).lower()
    desc      = _safe_str(record.get("description", "")).lower()

    for kw in kw_list:
        if kw in query_str:
            score += 3.0           # exact keyword phrase in query

    for token in query_tokens:
        for kw in kw_list:
            if token in kw or kw in token:
                score += 2.0
                break

        if token in crime:
            score += 1.0
        if token in title:
            score += 1.0
        if token in desc:
            score += 0.5

    return score


def search_case_outcome(query: str, top_n: int = 5) -> list[dict]:
    """
    Search the dataset for relevant IPC sections given a plain-language query.

    Returns empty list if nothing matches, or if the dataset failed to load,
    or if the query is empty -- never raises for those cases.
    """
    _load_dataset()

    if not query or not query.strip():
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored = []
    for record in _RECORDS:
        try:
            s = _score_record(record, query_tokens)
        except Exception as e:
            # One malformed row should never take down the whole search.
            print(f"[case.py] Skipping malformed record: {e}")
            continue
        if s > 0:
            scored.append((s, record))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    # De-duplicate: keep only the highest-scored entry per section number
    seen_sections = set()
    results = []
    for score, rec in scored:
        sec_key = f"{rec.get('act','')}_{rec.get('section','')}"
        if sec_key not in seen_sections:
            seen_sections.add(sec_key)
            results.append({
                "section":          rec.get("section", ""),
                "act":              rec.get("act", "IPC") or "IPC",
                "title":            rec.get("title", ""),
                "description":      rec.get("description", ""),
                "punishment":       rec.get("punishment", ""),
                "bns_equivalent":   rec.get("bns_equivalent", ""),
                "sentencing_range": rec.get("sentencing_range", ""),
                "cognizable":       rec.get("cognizable", ""),
                "bailable":         rec.get("bailable", ""),
                "outcome_note":     rec.get("outcome_note", ""),
                "score":            round(score, 2),
            })

        if len(results) >= top_n:
            break

    return results


def format_outcome_html(results: list[dict]) -> str:
    """
    Convert search results into ready-to-display HTML for the frontend.
    Never raises -- falls back to an empty-state message on any bad data.
    """
    if not results:
        return (
            "<div class='text-slate-500 text-sm p-3'>"
            "❌ No relevant legal sections found. Try describing the incident in more detail."
            "</div>"
        )

    html = "<div class='space-y-3'>"
    html += "<p class='font-bold text-purple-800 text-sm mb-2'>⚖️ Relevant Legal Sections Found:</p>"

    for r in results:
        act_label = r.get("act") or "IPC"

        cognizable_val = _safe_str(r.get("cognizable")).strip().lower()
        bailable_val   = _safe_str(r.get("bailable")).strip().lower()

        cognizable_badge = (
            "<span class='text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-semibold'>Cognizable</span>"
            if cognizable_val == "yes"
            else "<span class='text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-semibold'>Non-Cognizable</span>"
        )
        bailable_badge = (
            "<span class='text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-semibold'>Bailable</span>"
            if bailable_val == "yes"
            else "<span class='text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-semibold'>Non-Bailable</span>"
        )

        description = _safe_str(r.get("description"))
        desc_short = description[:250] + ("…" if len(description) > 250 else "")
        bns = _safe_str(r.get("bns_equivalent"))
        bns_line = f"<p class='text-xs text-blue-600 mt-1'>🔄 New Law: {bns}</p>" if bns else ""

        html += f"""
        <div class='border border-purple-200 rounded-lg p-3 bg-purple-50'>
            <div class='flex items-center gap-2 flex-wrap mb-1'>
                <span class='font-bold text-purple-900 text-sm'>📘 {act_label} § {r.get('section','')}</span>
                {cognizable_badge}
                {bailable_badge}
            </div>
            <p class='font-semibold text-slate-800 text-sm'>{r.get('title','')}</p>
            <p class='text-xs text-slate-600 mt-1 leading-relaxed'>{desc_short}</p>
            <div class='mt-2 bg-white border border-purple-100 rounded p-2 text-xs'>
                <span class='font-semibold text-purple-700'>⚖️ Punishment: </span>
                <span class='text-slate-700'>{r.get('punishment','')}</span>
            </div>
            <div class='mt-1 text-xs text-slate-500'>
                <span class='font-semibold'>📅 Sentencing Range: </span>{r.get('sentencing_range','')}
            </div>
            {bns_line}
        </div>
        """

    if results and results[0].get("outcome_note"):
        html += f"""
        <div class='bg-blue-50 border border-blue-200 rounded-lg p-3 mt-2 text-xs text-blue-800'>
            <span class='font-bold'>📋 Legal Note: </span>{results[0]['outcome_note']}
        </div>
        """

    html += """
    <p class='text-xs text-red-500 mt-3 font-semibold border-t pt-2'>
        ⚠️ Disclaimer: This is an AI-assisted legal reference only.
        Actual outcome depends on evidence, court discretion and facts of the case.
        Consult a qualified lawyer for legal advice.
    </p>
    </div>
    """

    return html


if __name__ == "__main__":
    test_queries = [
        "bike stolen from parking",
        "my wife was beaten by husband",
        "cheque bounced bank returned",
        "hacked my bank account otp fraud",
        "murdered stabbed",
        "landlord entered my house illegally",
        "bribe demanded by government officer",
    ]
    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        results = search_case_outcome(q, top_n=3)
        if results:
            for r in results:
                print(f"  [{r['score']}] {r['act']} §{r['section']} — {r['title']}")
                print(f"        Punishment: {r['punishment']}")
        else:
            print("  No results found.")