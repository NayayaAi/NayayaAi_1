# Forgot / reset password flow (email link, 15 min expiry, single use)
#
# .env (optional - without SMTP_* the reset link is printed in the Flask terminal):
#   APP_BASE_URL=http://127.0.0.1:5000
#   SMTP_HOST=smtp.gmail.com
#   SMTP_PORT=587
#   SMTP_USER=youraddress@gmail.com
#   SMTP_PASS=your_gmail_app_password
#   MAIL_FROM=NyayaAI <youraddress@gmail.com>

import hashlib
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

import bcrypt
from flask import Blueprint, jsonify, render_template, request

from main.database import mongo_db, users_collection

reset_bp = Blueprint("password_reset", __name__)

resets = mongo_db["password_resets"]

TOKEN_TTL_MINUTES = 15
MAX_REQUESTS_PER_HOUR = 3
MIN_PASSWORD_LEN = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _validate_password(pw: str):
    if len(pw) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    if not re.search(r"[A-Z]", pw):
        return "Password must contain an uppercase letter."
    if not re.search(r"[a-z]", pw):
        return "Password must contain a lowercase letter."
    if not re.search(r"[0-9]", pw):
        return "Password must contain a digit."
    if not re.search(r"[^A-Za-z0-9]", pw):
        return "Password must contain a special character."
    return None


def _same_origin_ok():
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return False
    return "/".join(origin.split("/")[:3]) == "/".join(request.host_url.split("/")[:3])


def _send_reset_email(to_email: str, name: str, link: str):
    """Sends the email via SMTP, or prints the link in the terminal (dev mode)."""
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pwd = os.environ.get("SMTP_PASS")

    if not (host and user and pwd):
        print("\n" + "=" * 60)
        print(f"[DEV MODE] Password reset link for {to_email}:")
        print(link)
        print("=" * 60 + "\n")
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your NyayaAI password"
    msg["From"] = os.environ.get("MAIL_FROM", user)
    msg["To"] = to_email
    msg.set_content(
        f"Hello {name},\n\n"
        f"We received a request to reset your NyayaAI password.\n"
        f"Open this link within {TOKEN_TTL_MINUTES} minutes:\n\n{link}\n\n"
        f"If you did not request this, ignore this email - your password stays unchanged.\n"
    )
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)), timeout=15) as s:
        s.starttls()
        s.login(user, pwd)
        s.send_message(msg)


@reset_bp.route("/forgot-password", methods=["GET"])
def forgot_page():
    return render_template("forgot_password.html")


@reset_bp.route("/forgot-password", methods=["POST"])
def forgot_submit():
    if not _same_origin_ok():
        return jsonify({"error": "Request rejected."}), 403

    email = ((request.get_json(silent=True) or {}).get("email") or "").strip().lower()
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Enter a valid email address."}), 400

    # Same reply whether or not the account exists (no account enumeration)
    generic = {"message": "If that email is registered, a reset link has been sent."}

    try:
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify(generic), 200

        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        if resets.count_documents({"user_id": user["_id"], "created_at": {"$gt": one_hour_ago}}) >= MAX_REQUESTS_PER_HOUR:
            return jsonify(generic), 200  # silently throttled

        token = secrets.token_urlsafe(32)
        resets.insert_one({
            "user_id": user["_id"],
            "token_hash": _hash(token),
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=TOKEN_TTL_MINUTES),
            "used": False,
        })

        base = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
        _send_reset_email(email, user.get("fullname", "there"), f"{base}/reset-password/{token}")
    except Exception as e:
        print(f"forgot-password error: {e}")

    return jsonify(generic), 200


def _valid_reset(token: str):
    return resets.find_one({
        "token_hash": _hash(token),
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()},
    })


@reset_bp.route("/reset-password/<token>", methods=["GET"])
def reset_page(token):
    return render_template("reset_password.html", token=token, valid=bool(_valid_reset(token)))


@reset_bp.route("/reset-password", methods=["POST"])
def reset_submit():
    if not _same_origin_ok():
        return jsonify({"error": "Request rejected."}), 403

    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    pw = data.get("password") or ""
    confirm = data.get("confirm") or ""

    if pw != confirm:
        return jsonify({"error": "Passwords do not match."}), 400
    err = _validate_password(pw)
    if err:
        return jsonify({"error": err}), 400

    rec = _valid_reset(token)
    if not rec:
        return jsonify({"error": "This reset link is invalid or has expired."}), 400

    users_collection.update_one(
        {"_id": rec["user_id"]},
        {"$set": {
            "password_hash": bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()),
            "failed_attempts": 0,
            "locked_until": None,
        }},
    )
    # Burn this token and any other outstanding ones for the user
    resets.update_many({"user_id": rec["user_id"], "used": False}, {"$set": {"used": True}})
    return jsonify({"message": "Password updated. You can sign in now."}), 200
