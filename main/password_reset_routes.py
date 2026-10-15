
import hashlib
import html
import os
import re
import secrets
import smtplib
import threading
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import parseaddr

import bcrypt
import requests
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


def _smtp_settings():
    host = (os.environ.get("SMTP_HOST") or "").strip()
    user = (os.environ.get("SMTP_USER") or "").strip()
    pwd = (os.environ.get("SMTP_PASS") or "").replace(" ", "")  # Google shows app passwords with spaces
    port = int(os.environ.get("SMTP_PORT", 587))
    sender = (os.environ.get("MAIL_FROM") or user).strip()
    return host, port, user, pwd, sender


def _build_message(to_email: str, name: str, link: str, sender: str) -> EmailMessage:
    safe_name = html.escape(name)
    msg = EmailMessage()
    msg["Subject"] = "Reset your NyayaAI password"
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(
        f"Hello {name},\n\n"
        f"We received a request to reset your NyayaAI password.\n"
        f"Open this link within {TOKEN_TTL_MINUTES} minutes:\n\n{link}\n\n"
        f"If you did not request this, ignore this email - your password stays unchanged.\n\n"
        f"- NyayaAI\n"
    )
    msg.add_alternative(
        f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:480px;margin:auto;padding:24px;color:#1f2937">
  <h2 style="margin:0 0 12px;color:#111827">Reset your password</h2>
  <p>Hello {safe_name},</p>
  <p>We received a request to reset your NyayaAI password. This link works for
     <b>{TOKEN_TTL_MINUTES} minutes</b> and can be used only once.</p>
  <p style="margin:24px 0">
    <a href="{link}" style="background:#1d4ed8;color:#ffffff;padding:12px 22px;border-radius:6px;
       text-decoration:none;font-weight:bold;display:inline-block">Reset Password</a>
  </p>
  <p style="font-size:13px;color:#6b7280">Button not working? Copy this link into your browser:<br>
     <a href="{link}" style="color:#1d4ed8;word-break:break-all">{link}</a></p>
  <p style="font-size:13px;color:#6b7280">If you did not request this, ignore this email.
     Your password stays unchanged.</p>
</div>""",
        subtype="html",
    )
    return msg


def _deliver(to_email: str, name: str, link: str):
    """Runs in a background thread so the page replies instantly (and response time never
    reveals whether an account exists)."""
    host, port, user, pwd, sender = _smtp_settings()
    try:
        msg = _build_message(to_email, name, link, sender)
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as s:
                s.login(user, pwd)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls()
                s.login(user, pwd)
                s.send_message(msg)
        print(f"[MAIL] Password reset email sent to {to_email}")
    except Exception as e:
        print(f"[MAIL ERROR] Could not send reset email to {to_email}: {e}")


def _deliver_brevo(to_email: str, name: str, link: str):
    """Sends through Brevo's HTTPS API (port 443). Runs in a background thread."""
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    sender_raw = os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER", "")
    sender_name, sender_email = parseaddr(sender_raw)
    try:
        msg = _build_message(to_email, name, link, sender_raw)
        text_part = msg.get_body(preferencelist=("plain",)).get_content()
        html_part = msg.get_body(preferencelist=("html",)).get_content()
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"},
            json={
                "sender": {"name": sender_name or "NyayaAI", "email": sender_email},
                "to": [{"email": to_email, "name": name}],
                "subject": "Reset your NyayaAI password",
                "htmlContent": html_part,
                "textContent": text_part,
            },
            timeout=20,
        )
        if r.status_code in (200, 201):
            print(f"[MAIL] Password reset email sent to {to_email} (Brevo)")
        else:
            print(f"[MAIL ERROR] Brevo rejected the email to {to_email}: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[MAIL ERROR] Could not send reset email to {to_email} (Brevo): {e}")


def _send_reset_email(to_email: str, name: str, link: str):
    """Sends the reset link to the user's inbox via SMTP.
    Terminal printing is only a fallback for local development (APP_ENV != production)."""
    if os.environ.get("BREVO_API_KEY", "").strip():
        threading.Thread(target=_deliver_brevo, args=(to_email, name, link), daemon=True).start()
        return

    host, port, user, pwd, sender = _smtp_settings()

    if host and user and pwd:
        threading.Thread(target=_deliver, args=(to_email, name, link), daemon=True).start()
        return

    if os.environ.get("APP_ENV", "development").lower() == "production":
        print("[MAIL ERROR] No email provider configured (BREVO_API_KEY or SMTP_*) - reset email NOT sent.")
        return

    print("\n" + "=" * 60)
    print(f"[DEV MODE - SMTP not configured] Password reset link for {to_email}:")
    print(link)
    print("=" * 60 + "\n")


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
            print(f"[RESET] No account with email {email} - no email sent.")
            return jsonify(generic), 200

        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        if resets.count_documents({"user_id": user["_id"], "created_at": {"$gt": one_hour_ago}}) >= MAX_REQUESTS_PER_HOUR:
            print(f"[RESET] Rate limit hit for {email} - no email sent.")
            return jsonify(generic), 200  # throttled

        token = secrets.token_urlsafe(32)
        resets.insert_one({
            "user_id": user["_id"],
            "token_hash": _hash(token),
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=TOKEN_TTL_MINUTES),
            "used": False,
        })

        base = (os.environ.get("APP_BASE_URL") or request.host_url).rstrip("/")
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