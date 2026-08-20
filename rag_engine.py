from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import pandas as pd
import os
import re

DB_PATH = "law_vector_db"

# -----------------------------
# SECTION NUMBER DETECTION
# -----------------------------
# Matches "section 420", "sec 420", "u/s 420", "420 IPC", "420A", etc.
_SECTION_PATTERNS = [
    re.compile(r'\b(?:section|sec\.?|u/s)\s*[:\-]?\s*(\d+[a-zA-Z]?)\b', re.IGNORECASE),
    re.compile(r'\b(\d+[a-zA-Z]?)\s*(?:ipc|crpc|bns|bnss|iea)\b', re.IGNORECASE),
    # act name BEFORE the number, e.g. "ipc 420", "crpc 154", "IPC-420"
    re.compile(r'\b(?:ipc|crpc|bns|bnss|iea)\s*[:\-]?\s*(\d+[a-zA-Z]?)\b', re.IGNORECASE),
]

def extract_section_number(query: str):
    """Return the section number if the query explicitly names one, else None."""
    for pattern in _SECTION_PATTERNS:
        m = pattern.search(query)
        if m:
            return m.group(1).upper()
    return None


# -----------------------------
# EMBEDDING MODEL
# -----------------------------
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# -----------------------------
# EXACT SECTION LOOKUP (built once at import)
# -----------------------------
def _build_section_lookup():
    """Maps section number (str, uppercased) -> {section, title, description}.

    Built directly from law_data.csv so exact lookups don't require touching
    FAISS internals (e.g. db.docstore._dict, which is a private attribute).
    """
    lookup = {}
    try:
        df = pd.read_csv("law_data.csv")
        for _, row in df.iterrows():
            key = str(row['Section']).strip().upper()
            lookup[key] = {
                "section": str(row['Section']),
                "title": row['Title'],
                "description": row['Description']
            }
    except FileNotFoundError:
        print("Warning: law_data.csv not found, exact-section lookup disabled.")
    return lookup

SECTION_LOOKUP = _build_section_lookup()


# -----------------------------
# CREATE VECTOR DATABASE
# -----------------------------
def create_vector_db():

    df = pd.read_csv("law_data.csv")

    documents = []

    for _, row in df.iterrows():

        content = f"""
Section: {row['Section']}
Title: {row['Title']}
Description: {row['Description']}
"""

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "section": str(row['Section']),
                    "title": row['Title']
                }
            )
        )

    db = FAISS.from_documents(
        documents,
        embedding_model
    )

    db.save_local(DB_PATH)

    print("Vector database created successfully")


# -----------------------------
# SEARCH LAW
# -----------------------------
def search_law(query, min_similarity=0.35):
    """
    Search over the legal sections DB.

    First checks whether the query explicitly names a section number
    ("420", "section 420", "u/s 420", "420 IPC") -- if so, returns that
    single section directly via exact lookup instead of running semantic
    search. This avoids handing back 2-3 unrelated "nearest neighbor"
    sections when the user only asked about one specific section.

    If no section number is named (or it's not found in the CSV), falls
    back to semantic search over FAISS.

    min_similarity: cutoff on the 0-1 similarity_score (derived from FAISS's
    L2 distance) below which a result is considered irrelevant and dropped.
    This prevents forcing the top-3 nearest neighbors onto queries that have
    nothing to do with the database (e.g. "how to write vakalatnama" was
    returning unrelated sections like murder/rape provisions just because
    they were the least-far vectors in the index).

    Tune this value by printing similarity_score for a few known-relevant
    and known-irrelevant queries against your actual embedding model/data --
    0.35 is a reasonable starting point, not a guarantee.

    Returns None if nothing clears the threshold, so callers can fall back
    to the LLM's own general knowledge instead of injecting noise.
    """

    # --- Exact section short-circuit ---
    section_no = extract_section_number(query)
    if section_no and section_no in SECTION_LOOKUP:
        match = SECTION_LOOKUP[section_no]
        return [{
            "score": 1.0,
            "section": match["section"],
            "title": match["title"],
            "description": match["description"]
        }]
    # If a section number was named but not found in the CSV, fall through
    # to semantic search rather than returning nothing -- could be a typo
    # or an act your CSV doesn't cover.

    db = FAISS.load_local(
        DB_PATH,
        embedding_model,
        allow_dangerous_deserialization=True
    )

    # Use similarity_search_with_score so we get FAISS's own distance
    # instead of re-scoring with substring/fuzzy matching, which was
    # discarding good semantic matches for multi-word queries.
    docs_with_scores = db.similarity_search_with_score(query, k=10)

    best_results = []

    for doc, distance in docs_with_scores:

        content = doc.page_content
        lines = content.strip().split("\n")

        section = ""
        title = ""
        description = ""

        for line in lines:
            line = line.strip()
            if line.startswith("Section:"):
                section = line.replace("Section:", "").strip()
            elif line.startswith("Title:"):
                title = line.replace("Title:", "").strip()
            elif line.startswith("Description:"):
                description = line.replace("Description:", "").strip()

        # Lower L2 distance = more similar. Convert to a 0-1 score.
        similarity_score = 1 / (1 + distance)

        # Skip weak matches entirely -- don't force irrelevant results
        # just because they're the "least bad" in the index.
        if similarity_score < min_similarity:
            continue

        best_results.append({
            "score": similarity_score,
            "section": section,
            "title": title,
            "description": description
        })

    # Already ordered by FAISS distance (best first), but re-sort
    # explicitly since we transformed the raw distance into a score.
    best_results = sorted(best_results, key=lambda x: x["score"], reverse=True)

    final_results = []
    seen = set()
    for item in best_results:
        if item["section"] not in seen:
            seen.add(item["section"])
            final_results.append(item)

    if not final_results:
        return None   # <-- Nothing relevant enough; let the caller fall back

    return final_results[:3]   # <-- Return list of dicts, not a formatted string


if __name__ == "__main__":
    create_vector_db()