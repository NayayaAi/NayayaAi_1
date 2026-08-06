import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Reuses the same Mongo instance/DB as app.py's users_collection.
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017/")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["NyayaAI_DB"]

# Same collection name app.py already references as `fir_collection`
# (db["fir_records"]) — keeps evidence-upload's FIR-existence check working.
firs_collection = db["fir_records"]

# app.py already creates this folder and saves the PDF there before calling
# upload_pdf(), so we just serve it back from the same place instead of
# pushing it to cloud storage.
PDF_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_firs")
os.makedirs(PDF_FOLDER, exist_ok=True)

# Update this if the app is ever hosted somewhere other than localhost:5000.
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def upload_pdf(pdf_path, fir_id):
    """PDF is already saved locally by app.py (generated_firs/<fir_no>.pdf).
    Just hand back a URL that /fir-pdf/<filename> can serve."""
    filename = os.path.basename(pdf_path)
    return f"{BASE_URL}/fir-pdf/{filename}"


def save_fir(fir_document):
    """Save FIR metadata to MongoDB."""
    firs_collection.insert_one(fir_document)


def get_all_firs():
    """Fetch all FIRs from MongoDB (excluding Mongo's internal _id)."""
    return list(firs_collection.find({}, {"_id": 0}))


def get_fir(fir_no):
    """Fetch a single FIR by FIR number."""
    return firs_collection.find_one({"fir_no": fir_no}, {"_id": 0})


def fir_exists(fir_no):
    """Check if a FIR number already exists."""
    if not fir_no:
        return False
    return firs_collection.count_documents({"fir_no": fir_no}) > 0