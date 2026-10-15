from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session, send_file
from main.storage_service import (
    add_docket_entry, get_docket_for_judge, get_docket_entry,
    check_docket_conflict, update_docket_entry, delete_docket_entry,
    get_fir, get_fir_statuses, close_case
)
import os
import sqlite3
from main import orders_service as orders
from main.database import DB_PATH

judge_bp = Blueprint("judge", __name__, url_prefix="/judge")


def _require_judge():
    if session.get("role") != "judge":
        return jsonify({"error": "unauthorized"}), 403
    return None


def _parse_hearing_date(value):
    """Returns datetime or None if invalid. Accepts 'YYYY-MM-DD HH:MM' or ISO 'T' format."""
    try:
        return datetime.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        return None


@judge_bp.route("/dashboard")
def dashboard():
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    return render_template("judge_dashboard.html")


@judge_bp.route("/docket", methods=["GET"])
def get_docket():
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    judge_id = session.get("user_id")
    status = request.args.get("status") or None
    urgency = request.args.get("urgency") or None
    entries = get_docket_for_judge(judge_id, status, urgency)
    statuses = get_fir_statuses({e["case_id"] for e in entries})
    for e in entries:
        e["case_status"] = statuses.get(e["case_id"], "")
    return jsonify(entries)


@judge_bp.route("/docket", methods=["POST"])
def create_docket_entry():
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail

    data = request.get_json() or {}
    judge_id = session.get("user_id")

    case_id = (data.get("case_id") or "").strip()
    if not case_id:
        return jsonify({"error": "invalid", "message": "Case ID is required."}), 400

    fir = get_fir(case_id)
    if fir and (fir.get("status") or "").lower() == "closed":
        return jsonify({"error": "closed", "message": f"Case {case_id} is closed."}), 409

    hearing_date = data.get("hearing_date")
    hd = _parse_hearing_date(hearing_date)
    if hd is None:
        return jsonify({"error": "invalid", "message": "Invalid hearing date."}), 400

    # No past dates
    if hd < datetime.now():
        return jsonify({"error": "past_date", "message": "Hearing date cannot be in the past."}), 400

    # No duplicate case in this judge's docket
    existing = get_docket_for_judge(judge_id)
    if any((e.get("case_id") or "").strip().lower() == case_id.lower() for e in existing):
        return jsonify({
            "error": "duplicate",
            "message": f"Case {case_id} is already in your docket."
        }), 409

    conflict = check_docket_conflict(judge_id, hearing_date)
    if conflict:
        return jsonify({
            "error": "conflict",
            "message": f"Overlaps with case {conflict['case_id']} at {conflict['hearing_date']}"
        }), 409

    entry = add_docket_entry(
        judge_id=judge_id,
        case_id=case_id,
        hearing_date=hearing_date,
        case_type=data.get("case_type", ""),
        urgency=data.get("urgency", "normal"),
        remarks=data.get("remarks", "")
    )
    return jsonify(entry), 201


@judge_bp.route("/docket/<int:entry_id>", methods=["PUT"])
def edit_docket_entry(entry_id):
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail

    judge_id = session.get("user_id")
    data = request.get_json() or {}

    entry = get_docket_entry(entry_id)
    if not entry or entry["judge_id"] != judge_id:
        return jsonify({"error": "not_found"}), 404

    if "hearing_date" in data and data["hearing_date"] != entry["hearing_date"]:
        hd = _parse_hearing_date(data["hearing_date"])
        if hd is None:
            return jsonify({"error": "invalid", "message": "Invalid hearing date."}), 400
        # Past-date check only when the date is actually being changed
        if hd < datetime.now():
            return jsonify({"error": "past_date", "message": "Hearing date cannot be in the past."}), 400

        conflict = check_docket_conflict(judge_id, data["hearing_date"], exclude_id=entry_id)
        if conflict:
            return jsonify({
                "error": "conflict",
                "message": f"Overlaps with case {conflict['case_id']} at {conflict['hearing_date']}"
            }), 409

    updates = {k: v for k, v in data.items() if k in
               ("hearing_date", "case_type", "urgency", "status", "remarks")}
    update_docket_entry(entry_id, judge_id, updates)
    return jsonify(get_docket_entry(entry_id))


@judge_bp.route("/docket/<int:entry_id>", methods=["DELETE"])
def remove_docket_entry(entry_id):
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail

    judge_id = session.get("user_id")
    entry = get_docket_entry(entry_id)
    if not entry or entry["judge_id"] != judge_id:
        return jsonify({"error": "not_found"}), 404

    delete_docket_entry(entry_id, judge_id)
    return jsonify({"deleted": entry_id})


@judge_bp.route("/case/<fir_no>/close", methods=["POST"])
def close_case_route(fir_no):
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail

    judge_id = session.get("user_id")
    fir_no = fir_no.strip()
    note = ((request.get_json(silent=True) or {}).get("note") or "").strip()

    # The judge may only close a case that is in their own docket
    docket = get_docket_for_judge(judge_id)
    if not any((e.get("case_id") or "").strip() == fir_no for e in docket):
        return jsonify({"error": "forbidden", "message": "This case is not in your docket."}), 403

    fir = get_fir(fir_no)
    if not fir:
        return jsonify({"error": "not_found", "message": "FIR not found."}), 404
    if (fir.get("status") or "").lower() == "closed":
        return jsonify({"error": "already_closed", "message": "Case is already closed."}), 409

    if not close_case(fir_no, judge_id, note):
        return jsonify({"error": "not_found", "message": "FIR not found."}), 404

    # Keep the citizen/police complaint (SQLite) in sync
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE citizen_complaints SET status = 'Closed', updated_at = CURRENT_TIMESTAMP WHERE fir_no = ?",
            (fir_no,),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"complaint sync error on close: {e}")

    return jsonify({"message": "Case closed", "fir_no": fir_no, "status": "Closed"})


# ═══════════════ ORDERS & DRAFTS ═══════════════
def _judge_case_ids(judge_id):
    return {(e.get("case_id") or "").strip() for e in get_docket_for_judge(judge_id)}


def _own_order(order_id, judge_id):
    o = orders.get_order(order_id)
    return o if o and str(o["judge_id"]) == str(judge_id) else None


@judge_bp.route("/orders", methods=["GET"])
def list_orders_route():
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    return jsonify(orders.list_orders(
        session.get("user_id"),
        request.args.get("status") or None,
        request.args.get("case_id") or None,
    ))


@judge_bp.route("/orders", methods=["POST"])
def create_order_route():
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    judge_id = session.get("user_id")
    d = request.get_json(silent=True) or {}
    case_id = (d.get("case_id") or "").strip()
    if case_id not in _judge_case_ids(judge_id):
        return jsonify({"error": "forbidden", "message": "Case is not in your docket."}), 403
    order_type = d.get("order_type") if d.get("order_type") in orders.ORDER_TYPES else "Custom"
    title = (d.get("title") or "").strip() or f"{order_type} — {case_id}"
    o = orders.create_order(judge_id, case_id, order_type, title,
                            d.get("content") or "", bool(d.get("ai_generated")))
    return jsonify(o), 201


@judge_bp.route("/orders/<int:order_id>", methods=["PUT"])
def update_order_route(order_id):
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    judge_id = session.get("user_id")
    o = _own_order(order_id, judge_id)
    if not o:
        return jsonify({"error": "not_found"}), 404
    if o["status"] == "finalised":
        return jsonify({"error": "locked", "message": "Finalised orders cannot be edited."}), 409
    d = request.get_json(silent=True) or {}
    updates = {k: d[k] for k in ("title", "content", "order_type", "status") if k in d}
    if updates.get("status") not in (None, "draft", "finalised"):
        return jsonify({"error": "invalid", "message": "Bad status."}), 400
    if updates.get("status") == "finalised" and not (updates.get("content", o["content"]) or "").strip():
        return jsonify({"error": "invalid", "message": "Cannot finalise an empty order."}), 400
    return jsonify(orders.update_order(order_id, judge_id, updates))


@judge_bp.route("/orders/<int:order_id>", methods=["DELETE"])
def delete_order_route(order_id):
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    judge_id = session.get("user_id")
    o = _own_order(order_id, judge_id)
    if not o:
        return jsonify({"error": "not_found"}), 404
    if o["status"] == "finalised":
        return jsonify({"error": "locked", "message": "Finalised orders cannot be deleted."}), 409
    orders.delete_order(order_id, judge_id)
    return jsonify({"deleted": order_id})


@judge_bp.route("/orders/generate", methods=["POST"])
def generate_order_route():
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    judge_id = session.get("user_id")
    d = request.get_json(silent=True) or {}
    case_id = (d.get("case_id") or "").strip()
    if case_id not in _judge_case_ids(judge_id):
        return jsonify({"error": "forbidden", "message": "Case is not in your docket."}), 403
    order_type = d.get("order_type") if d.get("order_type") in orders.ORDER_TYPES else "Custom"
    hearings = [e for e in get_docket_for_judge(judge_id) if e.get("case_id") == case_id]
    text = orders.generate_order_text(
        order_type, get_fir(case_id), hearings,
        (d.get("instructions") or "").strip(), session.get("name", "Judge"),
    )
    if not text:
        return jsonify({"error": "ai_unavailable",
                        "message": "AI drafting is unavailable right now. Write the order manually."}), 503
    return jsonify({"content": text})


@judge_bp.route("/orders/<int:order_id>/pdf", methods=["GET"])
def order_pdf_route(order_id):
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail
    o = _own_order(order_id, session.get("user_id"))
    if not o:
        return jsonify({"error": "not_found"}), 404
    return send_file(orders.order_to_pdf(o), mimetype="application/pdf",
                     as_attachment=True, download_name=f"Order_{o['case_id']}_{o['id']}.pdf")
