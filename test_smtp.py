import os, smtplib, socket
from dotenv import load_dotenv

load_dotenv()
user = os.environ.get("SMTP_USER", "").strip()
pwd = os.environ.get("SMTP_PASS", "").replace(" ", "")
print("SMTP_USER =", repr(user))
print("SMTP_PASS length =", len(pwd), "(should be 16)")

for port in (465, 587):
    print(f"\n--- Testing smtp.gmail.com:{port} ---")
    try:
        socket.create_connection(("smtp.gmail.com", port), timeout=10).close()
        print("TCP connection: OK")
    except Exception as e:
        print("TCP connection FAILED:", e)
        continue
    try:
        if port == 465:
            s = smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=15)
        else:
            s = smtplib.SMTP("smtp.gmail.com", port, timeout=15)
            s.starttls()
        s.login(user, pwd)
        print("LOGIN: OK  <-- use this port in .env")
        s.quit()
    except Exception as e:
        print("FAILED:", type(e).__name__, e)