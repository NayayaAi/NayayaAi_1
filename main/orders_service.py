# Orders & Drafts for the Judge Portal: Supabase storage, Groq drafting, PDF export.
import os
from io import BytesIO
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from main.storage_service import supabase

TABLE = "judge_orders"

ORDER_TYPES = [
    "Bail Order", "Adjournment Order", "Summons", "Notice", "Interim Order",
    "Remand Order", "Warrant", "Charge Order", "Final Judgment", "Custom",
]


# ───────────── storage ─────────────
def _now():
    return datetime.now(timezone.utc).isoformat()


def create_order(judge_id, case_id, order_type, title, content, ai_generated=False):
    res = supabase.table(TABLE).insert({
        "judge_id": str(judge_id),
        "case_id": case_id,
        "order_type": order_type,
        "title": title,
        "content": content,
        "status": "draft",
        "ai_generated": ai_generated,
    }).execute()
    return res.data[0] if res.data else None


def list_orders(judge_id, status=None, case_id=None):
    q = supabase.table(TABLE).select("*").eq("judge_id", str(judge_id))
    if status:
        q = q.eq("status", status)
    if case_id:
        q = q.eq("case_id", case_id)
    return q.order("updated_at", desc=True).execute().data


def get_order(order_id):
    res = supabase.table(TABLE).select("*").eq("id", order_id).execute()
    return res.data[0] if res.data else None


def update_order(order_id, judge_id, updates):
    updates = dict(updates)
    updates["updated_at"] = _now()
    if updates.get("status") == "finalised":
        updates["finalised_at"] = _now()
    res = supabase.table(TABLE).update(updates) \
        .eq("id", order_id).eq("judge_id", str(judge_id)).execute()
    return res.data[0] if res.data else None


def delete_order(order_id, judge_id):
    res = supabase.table(TABLE).delete() \
        .eq("id", order_id).eq("judge_id", str(judge_id)).execute()
    return len(res.data) > 0


# ───────────── AI drafting (Groq) ─────────────
def generate_order_text(order_type, fir, hearings, instructions="", judge_name="Judge"):
    """Returns draft text, or None if Groq is unavailable."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        from groq import Groq
        fir = fir or {}
        facts = (
            f"Case / FIR No: {fir.get('fir_no', '')}\n"
            f"Complainant: {fir.get('complainant_name', '')}\n"
            f"District: {fir.get('dist', '')}   Police Station: {fir.get('ps', '')}\n"
            f"Act/Sections: {fir.get('act_sections', '')}\n"
            f"Status: {fir.get('status', '')}\n"
            f"Incident: {fir.get('incident_description') or fir.get('description') or ''}\n"
        )
        hist = "\n".join(
            f"- {h.get('hearing_date')} [{h.get('status')}] {h.get('remarks') or ''}"
            for h in (hearings or [])
        ) or "- none recorded"
        prompt = (
            f"Draft a court {order_type} in the format used by Indian courts.\n\n"
            f"CASE FACTS\n{facts}\nHEARING HISTORY\n{hist}\n\n"
            f"JUDGE'S INSTRUCTIONS\n{instructions or 'None — use a standard form.'}\n\n"
            "Rules: plain text only (no markdown symbols). Use headings in CAPITALS: "
            "COURT, CASE DETAILS, ORDER, then date/place/signature block for "
            f"'{judge_name}'. Cite BNS/BNSS/BSA alongside IPC/CrPC/Evidence Act only where "
            "genuinely applicable. Do NOT invent facts, names, dates or case citations — "
            "use [BRACKETED PLACEHOLDERS] for anything not given above."
        )
        client = Groq(api_key=api_key)
        out = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": (
                    "You assist an Indian judge by preparing draft judicial orders. "
                    "Output is a draft for the judge's review, never a final order.")},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2500,
            temperature=0.2,
            reasoning_effort="low",
        )
        return out.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq order draft error: {e}")
        return None


# ───────────── PDF export (reportlab) ─────────────
def order_to_pdf(order):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=25 * mm, rightMargin=25 * mm,
                            topMargin=22 * mm, bottomMargin=22 * mm,
                            title=order.get("title") or order.get("order_type", "Order"))
    ss = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=ss["Title"], fontName="Times-Bold", fontSize=15, spaceAfter=4)
    sub = ParagraphStyle("s", parent=ss["Normal"], fontName="Times-Roman", fontSize=10,
                         alignment=1, textColor="#555555", spaceAfter=14)
    body = ParagraphStyle("b", parent=ss["Normal"], fontName="Times-Roman", fontSize=12, leading=18)
    note = ParagraphStyle("n", parent=body, fontSize=9, textColor="#B45309")

    story = [
        Paragraph(escape(order.get("order_type") or "Order").upper(), h),
        Paragraph(f"Case No: {escape(order.get('case_id', ''))}", sub),
    ]
    for para in (order.get("content") or "").split("\n"):
        story.append(Paragraph(escape(para) or "&nbsp;", body))
    if order.get("status") != "finalised":
        story += [Spacer(1, 14), Paragraph("DRAFT — not a final order. For the presiding judge's review.", note)]
    doc.build(story)
    buf.seek(0)
    return buf
