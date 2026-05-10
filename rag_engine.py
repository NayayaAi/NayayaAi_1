from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

DB_PATH = "law_vector_db"

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def create_vector_db():
    loader = CSVLoader(file_path="law_data.csv")
    documents = loader.load()

    db = FAISS.from_documents(documents, embedding_model)

    db.save_local(DB_PATH)

    print("✅ Vector database created successfully")

def search_law(query):
    db = FAISS.load_local(
        DB_PATH,
        embedding_model,
        allow_dangerous_deserialization=True
    )

    docs = db.similarity_search(query, k=3)

    results = []

    for doc in docs:
        results.append(doc.page_content)

    return "\n".join(results)

if __name__ == "__main__":
    create_vector_db()