from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from thefuzz import fuzz
import pandas as pd
import os

DB_PATH = "law_vector_db"

# -----------------------------
# EMBEDDING MODEL
# -----------------------------
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

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

    print("✅ Vector database created successfully")


# -----------------------------
# SEARCH LAW
# -----------------------------
def search_law(query):

    db = FAISS.load_local(
        DB_PATH,
        embedding_model,
        allow_dangerous_deserialization=True
    )

    docs = db.similarity_search(query, k=10)

    query_lower = query.lower()

    best_results = []

    for doc in docs:

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

        score = 0
        if section.lower() in query_lower:
            score += 100
        if query_lower in title.lower():
            score += 50
        if query_lower in description.lower():
            score += 30

        fuzzy_score = fuzz.token_sort_ratio(
            query_lower,
            f"{section} {title} {description}".lower()
        )
        score += fuzzy_score

        if score > 60:
            best_results.append({
                "score": score,
                "section": section,
                "title": title,
                "description": description
            })

    best_results = sorted(best_results, key=lambda x: x["score"], reverse=True)

    final_results = []
    seen = set()
    for item in best_results:
        if item["section"] not in seen:
            seen.add(item["section"])
            final_results.append(item)

    if not final_results:
        return None   # <-- Return None instead of a string

    return final_results[:3]   # <-- Return list of dicts, not a formatted string


if __name__ == "__main__":
    create_vector_db()