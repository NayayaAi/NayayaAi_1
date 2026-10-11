"""Act/section suggestion for the FIR form.

WHY THIS EXISTS SEPARATELY FROM `ai_engine.analyze_complaint_for_sections`
--------------------------------------------------------------------------
`/generate_fir` already calls that matcher, but only when the officer left the
Act(s)/Section(s) field empty, and it never shows its working: the sections
appear on the filed record and the officer finds out afterwards what they were
charged under. There is no preview, no reason given, and nothing to reject.

This module is the same question asked out loud. It returns candidates *with a
reason each*, so the form can put them in front of the officer before the FIR is
filed and let them accept the ones that fit. The record is still written by
`/generate_fir` from whatever the officer ended up with -- nothing here writes
anything.

PROPOSE, THEN VERIFY
--------------------
Groq is asked for the sections that apply, from its own knowledge of Indian law.
Every section it names is then looked up in `IndiaLaw.db` (1,968 sections across
eight acts) and **dropped if it does not exist**. What survives carries the real
statutory title read out of the database, not the model's paraphrase of it.

The obvious safer-looking design -- retrieve candidate sections by keyword and
let the model only pick from that list -- was tried first and abandoned. Statute
titles do not share vocabulary with the way a complainant describes an incident:
a chain-snatching narrative retrieved `Vehicles with left hand control` (the
complainant "injured her hand") while IPC 379 never surfaced, because the word
"theft" appears nowhere in the narrative and the word "snatched" appears nowhere
in the statute. Constraining the model to that list would have made it worse than
the keyword matcher it is meant to improve on.

Verifying afterwards gives the same guarantee for less: the model may propose
anything, and nothing an officer sees is a section that does not exist.

WHAT HAPPENS WHEN GROQ IS DOWN
------------------------------
`analyze_complaint_for_sections` runs instead, and the reply says `source:
"keyword"`. That is exactly what `/generate_fir` would have filed on its own, so
a station with no internet is no worse off than before this endpoint existed.
"""

import json
import os
import re
import sqlite3

from ai_engine import analyze_complaint_for_sections

# The eight tables in IndiaLaw.db, which are also the eight act codes
# `/api/acts` returns and the app's act picker offers. A suggestion outside this
# set cannot be verified and so is not offered as a chip -- see `note` in
# `suggest_sections` for how those are surfaced instead.
ACTS = ["IPC", "CRPC", "NIA", "IEA", "HMA", "CPC", "IDA", "MVA"]

# Spellings a model reaches for that mean one of our eight tables.
_ACT_ALIASES = {
    "IPC": "IPC", "INDIANPENALCODE": "IPC",
    "CRPC": "CRPC", "CODEOFCRIMINALPROCEDURE": "CRPC", "CRPC1973": "CRPC",
    "IEA": "IEA", "INDIANEVIDENCEACT": "IEA", "EVIDENCEACT": "IEA",
    "CPC": "CPC", "CODEOFCIVILPROCEDURE": "CPC",
    "NIA": "NIA", "NEGOTIABLEINSTRUMENTSACT": "NIA",
    "HMA": "HMA", "HINDUMARRIAGEACT": "HMA",
    "IDA": "IDA", "INDUSTRIALDISPUTESACT": "IDA",
    "MVA": "MVA", "MOTORVEHICLESACT": "MVA", "MV": "MVA",
}

# "IPC Section 379" -> ("IPC", "379"). The section group stops at the first
# bracket or comma so `IPC Section 323 (General Investigation)`, which the
# keyword matcher really does return, yields "323" and not the parenthetical.
_PAIR = re.compile(r"^\s*(.+?)\s+Section\s+([0-9]+[A-Za-z]?)", re.I)

_INDEX_CACHE = None


def _db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "IndiaLaw.db")


def _columns(conn, act):
    """(section, title, description) column names for one act table.

    The eight tables do not share a schema -- five use `section_title` /
    `section_desc`, three use `title` / `description`. Read from PRAGMA rather
    than from a hardcoded map, so this module cannot drift out of step with
    `app.act_columns` and so importing it does not mean importing `app.py`
    (which imports this).
    """
    names = {row[1].lower(): row[1] for row in
             conn.execute(f'PRAGMA table_info("{act}")')}
    section = names.get("section")
    title = names.get("section_title") or names.get("title")
    desc = names.get("section_desc") or names.get("description")
    if not (section and title and desc):
        return None
    return section, title, desc


def _index():
    """`(ACT, SECTION) -> title`, for every section in the database, once.

    Held in memory rather than queried per suggestion: it is under a megabyte,
    it never changes at runtime, and a verification step that costs eight SQL
    round trips per answer is a verification step someone will later be tempted
    to skip.
    """
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE

    index = {}
    try:
        conn = sqlite3.connect(_db_path())
        for act in ACTS:
            columns = _columns(conn, act)
            if not columns:
                print(f"sections_ai: {act} has no recognisable columns, skipped")
                continue
            section_col, title_col, _ = columns
            try:
                rows = conn.execute(
                    f'SELECT "{section_col}", "{title_col}" FROM "{act}"'
                ).fetchall()
            except sqlite3.Error as e:
                print(f"sections_ai: cannot read {act}: {e}")
                continue
            for section, title in rows:
                key = (act, str(section).strip().upper())
                index[key] = (title or "").strip()
        conn.close()
    except sqlite3.Error as e:
        print(f"sections_ai: cannot open IndiaLaw.db: {e}")

    _INDEX_CACHE = index
    return index


def normalise_act(act):
    """An act code as one of [ACTS], or None if it is not one of ours."""
    key = re.sub(r"[^A-Za-z0-9]", "", str(act or "")).upper()
    return _ACT_ALIASES.get(key)


def verify(act, section):
    """The statutory title if this section exists, else None.

    The lookup is exact on the section number as text. `376A` and `376` are
    different sections and must not be folded together; a model that answers
    `376A` for a section stored as `376` is answering about a provision the
    database does not have, and dropping it is the right outcome.
    """
    code = normalise_act(act)
    if not code:
        return None
    number = str(section or "").strip().upper()
    if not number:
        return None
    return _index().get((code, number))


def find_section(number, act=None):
    """Every act that has a section with this number, with its full text.

    Exists because `rag_engine.search_law` answers exact-section questions out of
    `law_data.csv`, which holds 84 IPC sections. Anything outside those 84 --
    "what does CrPC 154 say", "IPC 376A" -- fell through to a semantic search
    over the same 84 rows and came back with whatever was nearest. The database
    beside it has 1,968 sections across eight acts, so the answer usually exists;
    nothing was looking in it.

    Returns a list because a bare section number is genuinely ambiguous: there is
    a section 154 in IPC, CrPC, CPC and MVA. Pass `act` when the question names
    one.
    """
    number = str(number or "").strip().upper()
    if not number:
        return []

    wanted = normalise_act(act) if act else None
    acts = [wanted] if wanted else ACTS

    found = []
    try:
        conn = sqlite3.connect(_db_path())
        for code in acts:
            columns = _columns(conn, code)
            if not columns:
                continue
            section_col, title_col, desc_col = columns
            try:
                row = conn.execute(
                    f'SELECT "{section_col}", "{title_col}", "{desc_col}" '
                    f'FROM "{code}" WHERE upper(trim("{section_col}")) = ? LIMIT 1',
                    (number,)
                ).fetchone()
            except sqlite3.Error as e:
                print(f"sections_ai: cannot search {code}: {e}")
                continue
            if row:
                found.append({
                    "act": code,
                    "section": str(row[0]).strip(),
                    "title": (row[1] or "").strip(),
                    "description": (row[2] or "").strip(),
                })
        conn.close()
    except sqlite3.Error as e:
        print(f"sections_ai: cannot open IndiaLaw.db: {e}")

    return found


def split_pair(text):
    """`"IPC Section 379"` -> `{"act": "IPC", "section": "379"}`, else None.

    `analyze_complaint_for_sections` also returns prose for its no-match cases
    ("Non-criminal matter (lost/stolen documents) - Administrative Report"),
    which has no act and no section and must never become a chip on an FIR.
    Those return None and are dropped.
    """
    match = _PAIR.match(text or "")
    if not match:
        return None
    act = match.group(1).strip()
    section = match.group(2).strip()
    if not act or not section:
        return None
    return {"act": act, "section": section}


def _keyword_suggestions(narrative, limit=5):
    """The existing matcher's answer, in this module's output shape.

    Acts are left exactly as the matcher spells them -- "POCSO Act", "IT Act",
    "Motor Vehicles Act" -- rather than normalised to the eight table names.
    Those are the acts a station charges under most and the database does not
    carry them; renaming them to fit would be worse than passing them through.
    """
    out = []
    for entry in analyze_complaint_for_sections(narrative, top_n=3) or []:
        pair = split_pair(entry)
        if not pair:
            continue
        code = normalise_act(pair["act"])
        out.append({
            "act": code or pair["act"],
            "section": pair["section"],
            "title": verify(pair["act"], pair["section"]) or "",
            "reason": "",
            "confidence": "low",
        })
        if len(out) >= limit:
            break
    return out


def _prompt(narrative, hints):
    hint_line = ""
    if hints:
        hint_line = (
            "\nA keyword matcher on the same text suggested: "
            + ", ".join(f'{h["act"]} {h["section"]}' for h in hints)
            + ". Treat that as a hint, not an answer -- it matches words, not "
              "meaning, and it is often wrong.\n"
        )

    return (
        "An Indian police officer is registering an FIR. Read the complaint "
        "narrative and identify the offences it discloses.\n\n"
        f"NARRATIVE:\n{narrative}\n{hint_line}\n"
        "Reply with the sections that apply. Rules:\n"
        f"- Use ONLY these acts: {', '.join(ACTS)}. Give the act code exactly as "
        "written here.\n"
        "- Give the section number alone: 379, 304A, 498A. No sub-clauses in "
        "brackets.\n"
        "- At most 5 sections, most serious first.\n"
        "- 'reason' is one short clause, under 15 words, naming the fact in the "
        "narrative that triggers the section.\n"
        "- 'confidence' is high, medium or low.\n"
        "- If the narrative also discloses an offence under an act NOT in the "
        "list above (POCSO, NDPS, IT Act, Dowry Prohibition, Prevention of "
        "Corruption), name it in 'note' in one sentence. Otherwise 'note' is an "
        "empty string.\n"
        "- If the narrative discloses no offence at all, return an empty "
        "sections array.\n\n"
        "Reply with JSON only, no prose and no code fence:\n"
        '{"sections": [{"act": "IPC", "section": "379", "reason": "...", '
        '"confidence": "high"}], "note": ""}'
    )


def _parse(answer):
    """Groq's JSON -> (raw suggestions, note). No verification yet."""
    if not answer:
        return [], ""

    text = answer.strip()
    # Models fence JSON even when told not to.
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text, flags=re.I).strip()

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return [], ""

    try:
        parsed = json.loads(text[start:end + 1])
    except (ValueError, TypeError) as e:
        print(f"sections_ai: could not parse Groq reply: {e}")
        return [], ""
    if not isinstance(parsed, dict):
        return [], ""

    raw = []
    for item in (parsed.get("sections") or [])[:5]:
        if isinstance(item, dict):
            raw.append(item)
    return raw, str(parsed.get("note", "") or "").strip()[:300]


def suggest_sections(narrative, ask_groq=None):
    """Suggest act/section pairs for a complaint narrative.

    `ask_groq` is injected rather than imported so this module does not depend on
    `app.py` (which imports it), and so the fallback path stays testable with no
    network and no API key.

    Returns `{"suggestions": [...], "source": ..., "note": ..., "dropped": [...]}`.

    `source` is `"groq"`, `"keyword"` or `"none"`, and it is reported rather than
    hidden because the two are not equally good and an officer deciding what to
    charge is entitled to know which one they are reading.

    `dropped` lists sections the model proposed that are not in the database. It
    is returned for the log rather than for the screen: a model that starts
    inventing sections should be visible to whoever is running this, not silently
    filtered.
    """
    narrative = (narrative or "").strip()
    if not narrative:
        return {"suggestions": [], "source": "none", "note": "", "dropped": []}

    hints = _keyword_suggestions(narrative)

    if ask_groq is not None:
        raw, note = _parse(ask_groq(_prompt(narrative, hints), max_tokens=700))

        verified = []
        dropped = []
        seen = set()
        for item in raw:
            act = normalise_act(item.get("act"))
            section = str(item.get("section", "")).strip().upper()
            title = verify(act, section) if act else None

            if title is None:
                dropped.append(f'{item.get("act")} {item.get("section")}')
                continue
            if (act, section) in seen:
                continue
            seen.add((act, section))

            confidence = str(item.get("confidence", "")).strip().lower()
            verified.append({
                "act": act,
                "section": section,
                "title": title,
                "reason": str(item.get("reason", "")).strip()[:160],
                "confidence": confidence if confidence in
                              ("high", "medium", "low") else "medium",
            })

        if dropped:
            print(f"sections_ai: dropped unverifiable sections {dropped}")

        if verified:
            return {
                "suggestions": verified,
                "source": "groq",
                "note": note,
                "dropped": dropped,
            }

    # Groq is down, keyless, or every section it named failed verification.
    return {
        "suggestions": hints,
        "source": "keyword" if hints else "none",
        "note": "",
        "dropped": [],
    }
