import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps

from bson.objectid import ObjectId
from flask import (
    Blueprint, current_app, jsonify, redirect, render_template,
    request, session, url_for,
)
from pymongo import MongoClient

from main.storage_service import get_all_firs

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

_client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
_db = _client["NyayaAI_DB"]
users = _db["users"]
alerts = _db["admin_alerts"]
audit = _db["evidence_access_log"]


def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return wrapper


def _clean(doc):
    doc["_id"] = str(doc["_id"])
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()  # stored in UTC
    return doc


def _oid(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


@admin_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return redirect(url_for("home"))
    return render_template("admin_dashboard.html", admin_name=session.get("fullname", "Admin"))


# ── Overview stats ──
@admin_bp.route("/api/stats")
@admin_only
def stats():
    roles = ["citizen", "police", "lawyer", "judge", "admin"]
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        firs = len(get_all_firs())
    except Exception:
        firs = None
    try:
        conn = sqlite3.connect(os.path.join(current_app.root_path, "IndiaLaw.db"))
        complaints = conn.execute("SELECT COUNT(*) FROM citizen_complaints").fetchone()[0]
        conn.close()
    except Exception:
        complaints = None

    return jsonify({
        "users_by_role": {r: users.count_documents({"role": r}) for r in roles},
        "pending_approvals": users.count_documents({"status": "pending"}),
        "open_alerts": alerts.count_documents({"status": "open"}),
        "evidence_views_today": audit.count_documents(
            {"action": "viewed_file", "timestamp": {"$gte": today}}
        ),
        "firs": firs,
        "complaints": complaints,
    })


# ── Charts ──
@admin_bp.route("/api/charts")
@admin_only
def charts():
    try:
        firs = get_all_firs()
    except Exception as e:
        return jsonify({"error": f"Could not load FIRs: {e}"}), 500

    districts = Counter((f.get("dist") or "Unknown") for f in firs)
    statuses = Counter((f.get("status") or "Active") for f in firs)
    top = districts.most_common(10)

    return jsonify({
        "districts": {"labels": [d for d, _ in top], "values": [c for _, c in top]},
        "statuses": {"labels": list(statuses.keys()), "values": list(statuses.values())},
    })


# ── Users ──
@admin_bp.route("/api/users")
@admin_only
def list_users():
    q = {}
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    s = request.args.get("q", "").strip()
    if role:
        q["role"] = role
    if status in ("pending", "rejected"):
        q["status"] = status
    if s:
        rx = {"$regex": re.escape(s), "$options": "i"}
        q["$or"] = [{"fullname": rx}, {"email": rx}, {"unique_id": rx}]
    docs = users.find(q, {"password_hash": 0}).sort("created_at", -1).limit(200)
    return jsonify([_clean(d) for d in docs])


@admin_bp.route("/api/users/<user_id>/<action>", methods=["POST"])
@admin_only
def user_action(user_id, action):
    updates = {
        "approve": {"status": "approved"},
        "reject": {"status": "rejected"},
        "lock": {"locked_until": datetime.utcnow() + timedelta(days=3650)},
        "unlock": {"locked_until": None, "failed_attempts": 0},
    }
    if action not in updates:
        return jsonify({"error": "Invalid action"}), 400
    if user_id == session.get("user_id"):
        return jsonify({"error": "You can't do that to your own account."}), 400
    oid = _oid(user_id)
    if not oid:
        return jsonify({"error": "Invalid id"}), 400
    res = users.update_one({"_id": oid}, {"$set": updates[action]})
    if not res.matched_count:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"message": "Updated"})


# ── Alerts ──
@admin_bp.route("/api/alerts")
@admin_only
def list_alerts():
    status = request.args.get("status", "open")
    docs = alerts.find({"status": status}).sort("created_at", -1).limit(100)
    return jsonify([_clean(d) for d in docs])


@admin_bp.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
@admin_only
def resolve_alert(alert_id):
    oid = _oid(alert_id)
    if not oid:
        return jsonify({"error": "Invalid id"}), 400
    alerts.update_one({"_id": oid}, {"$set": {
        "status": "resolved",
        "resolved_by": session.get("user_id"),
        "resolved_at": datetime.utcnow(),
    }})
    return jsonify({"message": "Resolved"})


# ── Audit log ──
@admin_bp.route("/api/audit")
@admin_only
def audit_log():
    q = {}
    fir_no = request.args.get("fir_no", "").strip()
    user = request.args.get("user", "").strip()
    if fir_no:
        q["fir_no"] = fir_no
    if user:
        q["username"] = {"$regex": re.escape(user), "$options": "i"}
    docs = audit.find(q).sort("timestamp", -1).limit(200)
    return jsonify([_clean(d) for d in docs])