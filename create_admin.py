import re
from datetime import datetime

import bcrypt
from pymongo import MongoClient

users = MongoClient("mongodb://127.0.0.1:27017/")["NyayaAI_DB"]["users"]


def password_error(pw):
    if len(pw) < 10:
        return "Password must be at least 10 characters."
    if not re.search(r"[A-Z]", pw):
        return "Password must contain an uppercase letter."
    if not re.search(r"[a-z]", pw):
        return "Password must contain a lowercase letter."
    if not re.search(r"[0-9]", pw):
        return "Password must contain a digit."
    if not re.search(r"[^A-Za-z0-9]", pw):
        return "Password must contain a special character."
    return None


email = input("Admin email: ").strip().lower()
name = input("Full name: ").strip() or "Admin"

existing = users.find_one({"email": email})
if existing:
    ans = input("This email already exists. Make it an admin? (y/n): ").strip().lower()
    if ans != "y":
        raise SystemExit("Cancelled.")
    users.update_one(
        {"_id": existing["_id"]},
        {"$set": {"role": "admin", "status": "approved", "locked_until": None, "failed_attempts": 0}},
    )
    raise SystemExit("Existing user promoted to admin. Log in with their current password.")

# Visible input on purpose (local one-time script)
pw = input("Password (10+ chars, upper, lower, digit, special): ")
err = password_error(pw)
if err:
    raise SystemExit(err)

users.insert_one({
    "fullname": name,
    "email": email,
    "password_hash": bcrypt.hashpw(pw.encode(), bcrypt.gensalt()),
    "role": "admin",
    "unique_id": "ADM001",
    "status": "approved",
    "created_at": datetime.utcnow(),
    "failed_attempts": 0,
    "locked_until": None,
})
print("Admin created.")