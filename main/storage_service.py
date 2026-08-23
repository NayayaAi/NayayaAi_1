
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
    os.remove(pdf_path)  # delete local temp
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

def assign_lawyer_to_fir(fir_no, lawyer_id):
    """Assign a lawyer to a FIR by fir_no. Returns True if a row was updated."""
    result = supabase.table("firs").update(
        {"assigned_lawyer_id": lawyer_id}
    ).eq("fir_no", fir_no).execute()
    return len(result.data) > 0

def get_firs_by_lawyer(lawyer_id):
    """Fetch all FIRs assigned to a given lawyer."""
    result = supabase.table("firs").select("*").eq("assigned_lawyer_id", lawyer_id).execute()
    return result.data

def add_case_hearing(fir_no, hearing_date, note):
    """Add a hearing date for a case."""
    result = supabase.table("case_hearings").insert({
        "fir_no": fir_no,
        "hearing_date": hearing_date,
        "note": note
    }).execute()
    return result.data[0] if result.data else None

def get_case_hearings(fir_no):
    """Fetch all hearings for a case, oldest first."""
    result = supabase.table("case_hearings").select("*").eq("fir_no", fir_no).order("hearing_date").execute()
    return result.data

def save_case_draft(fir_no, kind, content):
    """Save a generated draft for a case."""
    result = supabase.table("case_drafts").insert({
        "fir_no": fir_no,
        "kind": kind,
        "content": content
    }).execute()
    return result.data[0] if result.data else None

def get_case_drafts(fir_no):
    """Fetch all saved drafts for a case, newest first."""
    result = supabase.table("case_drafts").select("*").eq("fir_no", fir_no).order("created_at", desc=True).execute()
    return result.data

def delete_case_draft(fir_no, draft_id):
    """Delete a specific draft. Returns True if a row was deleted."""
    result = supabase.table("case_drafts").delete().eq("id", draft_id).eq("fir_no", fir_no).execute()
    return len(result.data) > 0

def get_case_drafts_for_firs(fir_nos):
    """Fetch all drafts across a list of FIR numbers, newest first."""
    if not fir_nos:
        return []
    result = supabase.table("case_drafts").select("*").in_("fir_no", fir_nos).order("created_at", desc=True).execute()
    return result.data

def update_fir_status(fir_no, status):
    """Update the status field on a FIR. Returns True if a row was updated."""
    result = supabase.table("firs").update({"status": status}).eq("fir_no", fir_no).execute()
    return len(result.data) > 0

def update_next_hearing_date(fir_no, hearing_date):
    """Update the next_hearing_date field on a FIR record."""
    result = supabase.table("firs").update({"next_hearing_date": hearing_date}).eq("fir_no", fir_no).execute()
    return len(result.data) > 0

def add_case_deadline(fir_no, deadline_type, due_date, note=""):
    """Insert a new deadline for a case."""
    result = supabase.table("case_deadlines").insert({
        "fir_no": fir_no,
        "deadline_type": deadline_type,
        "due_date": due_date,
        "note": note,
        "completed": False
    }).execute()
    return result.data[0] if result.data else None

def get_case_deadlines(fir_no):
    """All deadlines for one case, soonest first."""
    result = supabase.table("case_deadlines").select("*").eq("fir_no", fir_no).order("due_date").execute()
    return result.data

def mark_deadline_complete(fir_no, deadline_id, completed):
    """Toggle a deadline's completed flag."""
    result = supabase.table("case_deadlines").update({"completed": completed}).eq("id", deadline_id).eq("fir_no", fir_no).execute()
    return len(result.data) > 0

def delete_case_deadline(fir_no, deadline_id):
    supabase.table("case_deadlines").delete().eq("id", deadline_id).eq("fir_no", fir_no).execute()

def get_upcoming_deadlines_for_firs(fir_nos, days_ahead=14):
    """Across all of a lawyer's cases: incomplete deadlines due within N days (includes overdue)."""
    if not fir_nos:
        return []
    from datetime import datetime, timedelta
    cutoff = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
    result = supabase.table("case_deadlines") \
        .select("*") \
        .in_("fir_no", fir_nos) \
        .eq("completed", False) \
        .lte("due_date", cutoff) \
        .order("due_date") \
        .execute()
    return result.data

def set_client_visibility(fir_no, visible, note):
    """Toggle whether a case's status is visible to the client, with an optional note."""
    result = supabase.table("firs").update({
        "visible_to_client": visible,
        "client_note": note
    }).eq("fir_no", fir_no).execute()
    return len(result.data) > 0