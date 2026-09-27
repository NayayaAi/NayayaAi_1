from flask import Blueprint, request, jsonify, render_template, session
from main.storage_service import (
    add_docket_entry, get_docket_for_judge, get_docket_entry,
    check_docket_conflict, update_docket_entry, delete_docket_entry
)

judge_bp = Blueprint("judge", __name__, url_prefix="/judge")


def _require_judge():
    if session.get("role") != "judge":
        return jsonify({"error": "unauthorized"}), 403
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
    return jsonify(entries)


@judge_bp.route("/docket", methods=["POST"])
def create_docket_entry():
    auth_fail = _require_judge()
    if auth_fail:
        return auth_fail

    data = request.get_json()
    judge_id = session.get("user_id")
    hearing_date = data["hearing_date"]

    conflict = check_docket_conflict(judge_id, hearing_date)
    if conflict:
        return jsonify({
            "error": "conflict",
            "message": f"Overlaps with case {conflict['case_id']} at {conflict['hearing_date']}"
        }), 409

    entry = add_docket_entry(
        judge_id=judge_id,
        case_id=data["case_id"],
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
    data = request.get_json()

    entry = get_docket_entry(entry_id)
    if not entry or entry["judge_id"] != judge_id:
        return jsonify({"error": "not_found"}), 404

    if "hearing_date" in data and data["hearing_date"] != entry["hearing_date"]:
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