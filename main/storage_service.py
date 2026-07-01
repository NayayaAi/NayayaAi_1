
import os
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_pdf(pdf_path, fir_id):
    """Upload PDF to Supabase Storage, return public URL."""
    with open(pdf_path, "rb") as f:
        supabase.storage.from_("firs").upload(
            f"{fir_id}.pdf", f,
            {"content-type": "application/pdf"}
        )
    url = supabase.storage.from_("firs").get_public_url(f"{fir_id}.pdf")
    
    return url

def save_fir(fir_document):
    """Save FIR metadata to Supabase database."""
    supabase.table("firs").insert(fir_document).execute()

def get_all_firs():
    """Fetch all FIRs from Supabase."""
    result = supabase.table("firs").select("*").execute()
    return result.data

def get_fir(fir_no):
    """Fetch a single FIR by FIR number."""
    result = supabase.table("firs").select("*").eq("fir_no", fir_no).execute()
    return result.data[0] if result.data else None

def fir_exists(fir_no):
    """Check if a FIR number already exists."""
    result = supabase.table("firs").select("fir_no").eq("fir_no", fir_no).execute()
    return len(result.data) > 0