<<<<<<< HEAD
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from thefuzz import process, fuzz
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId
from datetime import datetime
from flask_wtf.csrf import CSRFProtect, CSRFError
from reportlab.lib.styles import getSampleStyleSheet
from ai_engine import analyze_complaint_for_sections
from rag_engine import search_law
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from flask import requests, jsonify
import jwt
import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask import send_from_directory
import subprocess
import json

from case import search_case_outcome, format_outcome_html

app = Flask(__name__)
app.secret_key = "nyaya_ai_ultra_secure_key"

# Initialize CSRF protection
# csrf = CSRFProtect(app)  # Disabled CSRF protection
OLLAMA_URL = "http://localhost:11434/api/generate"

def ask_ollama(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "phi3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 150
                    }
                }
            )

        # Check if request was successful
        if response.status_code != 200:
            print(f"Ollama API Error: {response.status_code} - {response.text}")
            return "AI service error. Please try again."

        data = response.json()

        # Safe extraction of response
        result = data.get("response")
        if not result:
            return "No response from AI"

        return result.strip()

    except requests.exceptions.Timeout:
        print("Ollama Timeout Error")
        return "AI is taking too long. Try again."

    except requests.exceptions.ConnectionError:
        print("Ollama Connection Error")
        return "Cannot connect to AI server. Is Ollama running?"

    except Exception as e:
        print("Unexpected Ollama Error:", e)
        return "AI response unavailable"

# 2. DATABASE CONNECTIONS
DB_PATH = os.path.join(app.root_path, "IndiaLaw.db")
try:
    # Use 127.0.0.1 for local Python connection
    client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
    db = client["NyayaAI_DB"]
    users_collection = db["users"]
    client.server_info() 
except Exception as e:
    print(f"ERROR: MongoDB connection failed: {e}")

# 3. USER MODEL AND LOADER




# --- ROUTES ---



# --- FIR LOGIC (SQLite) ---

# Optional CORS support
try:
    from flask_cors import CORS
    CORS(app)
except ModuleNotFoundError:
    print("Warning: flask_cors not installed. API will still work from same origin.")

# Indian Districts and Police Stations
INDIAN_DISTRICTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Puducherry", "Chandigarh"
]

SAMPLE_POLICE_STATIONS = {
    "Delhi": ["North Delhi PS", "South Delhi PS", "East Delhi PS", "West Delhi PS", "Central Delhi PS"],
    "Maharashtra": ["Mumbai North PS", "Mumbai South PS", "Pune PS", "Nagpur PS"],
    "Karnataka": ["Bangalore PS", "Mysore PS", "Hubli PS"],
    "Tamil Nadu": ["Chennai PS", "Coimbatore PS", "Madurai PS"],
    "Uttar Pradesh": ["Lucknow PS", "Kanpur PS", "Varanasi PS"]
}

LEGAL_ACTS = ["IPC", "CRPC", "NIA", "IEA", "HMA", "CPC", "IDA", "MVA"]

def init_fir_table():
    """Initialize FIR records table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fir_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fir_no TEXT UNIQUE NOT NULL,
                dist TEXT NOT NULL,
                ps TEXT NOT NULL,
                year TEXT NOT NULL,
                fir_date TEXT NOT NULL,
                act_sections TEXT,
                occurrence_day TEXT,
                occurrence_date TEXT,
                occurrence_time TEXT,
                info_received_date TEXT,
                info_received_time TEXT,
                gdr_entry_no TEXT,
                type_of_information TEXT,
                place_of_occurrence TEXT,
                complainant_name TEXT,
                father_husband_name TEXT,
                dob TEXT,
                nationality TEXT,
                passport_no TEXT,
                date_of_issue TEXT,
                place_of_issue TEXT,
                occupation TEXT,
                address TEXT,
                details_of_accused TEXT,
                reasons_for_delay TEXT,
                property_particulars TEXT,
                statement TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Active'
            )
        ''')
        conn.commit()
        conn.close()
        print("FIR records table initialized successfully.")
    except Exception as e:
        print(f"Error initializing FIR table: {e}")

def init_user_table():
    """Initialize users table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'police',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("Users table initialized successfully.")
    except Exception as e:
        print(f"Error initializing users table: {e}")
        
def init_evidence_table():
    """Create a table to store paths to uploaded evidence files."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
CREATE TABLE IF NOT EXISTS evidence_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_no TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fir_no) REFERENCES fir_records (fir_no)
    )
    ''')
    conn.commit()
    conn.close()

# Call this in your if __name__ == '__main__': block
        
 # Default to simple hurt if nothing matches

def get_sections_for_act(act_code):
    """Get all sections for a specific act from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT Section, section_title FROM {act_code} ORDER BY Section LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        return [{"section": row[0], "title": row[1]} for row in rows]
    except Exception as e:
        print(f"Error getting sections for act {act_code}: {e}")
        return []

@app.route('/', methods=['GET'])
def home():
    if 'user_id' in session:
        return render_template('index.html')
    return redirect(url_for('signup'))  # Direct new visitors to signup first

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Nyaya AI engine reachable"}), 200

@app.route('/api/districts', methods=['GET'])
def get_districts():
    """Return list of Indian districts."""
    return jsonify(sorted(INDIAN_DISTRICTS))

@app.route('/api/police-stations/<district>', methods=['GET'])
def get_police_stations(district):
    """Return police stations for a district."""
    stations = SAMPLE_POLICE_STATIONS.get(district, [f"{district} PS"])
    return jsonify(stations)

@app.route('/api/acts', methods=['GET'])
def get_acts():
    """Return available legal acts."""
    return jsonify(LEGAL_ACTS)

app.route('/api/sections/<act>', methods=['GET'])
def get_sections(act):
    """Return sections with optional search and pagination."""
    if act not in LEGAL_ACTS:
        return jsonify({"error": "Invalid act"}), 400

    search = request.args.get('search', '').strip().lower()
    page   = max(1, int(request.args.get('page', 1)))
    limit  = int(request.args.get('limit', 20))
    offset = (page - 1) * limit

    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Build WHERE clause
        if search:
            where = "WHERE lower(Section) LIKE ? OR lower(section_title) LIKE ? OR lower(section_desc) LIKE ?"
            params = (f"%{search}%", f"%{search}%", f"%{search}%")
        else:
            where  = ""
            params = ()

        # Total count
        cursor.execute(f"SELECT COUNT(*) FROM {act} {where}", params)
        total = cursor.fetchone()[0]

        # Paginated rows — fetch description too
        cursor.execute(
            f"SELECT Section, section_title, section_desc FROM {act} {where} ORDER BY rowid LIMIT ? OFFSET ?",
            params + (limit, offset)
        )
        rows = cursor.fetchall()
        conn.close()

        return jsonify({
            "act":     act,
            "total":   total,
            "page":    page,
            "limit":   limit,
            "pages":   max(1, (total + limit - 1) // limit),
            "results": [
                {"section": r[0], "title": r[1], "description": r[2] or ""}
                for r in rows
            ]
        })

    except Exception as e:
        print(f"Sections error for {act}: {e}")
        return jsonify({"error": str(e)}), 500
    
    # ── Section Detail (for comparison tool) ──────────────────────
@app.route('/api/section-detail/<act>/<section_no>', methods=['GET'])
def get_section_detail(act, section_no):
    if act not in LEGAL_ACTS:
        return jsonify({"error": "Invalid act"}), 400
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT Section, section_title, section_desc FROM {act} WHERE Section = ? LIMIT 1",
            (section_no,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Section not found"}), 404
        return jsonify({"section": row[0], "title": row[1], "description": row[2] or ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Case Outcome Predictor ─────────────────────────────────────
@app.route('/api/predict-outcome', methods=['POST'])
def predict_outcome():
    data = request.get_json()
    situation = data.get('situation', '').strip()
    if not situation:
        return jsonify({"prediction": "❌ Please describe the situation."}), 400
    results = search_case_outcome(situation, top_n=5)
    html    = format_outcome_html(results)
    return jsonify({"prediction": html})

BARE_ACTS_URLS = {
    "IPC": "https://indiacode.nic.in/bitstream/123456789/2263/1/A1860-45.pdf",
    "CRPC": "https://indiacode.nic.in/bitstream/123456789/1611/1/A1973-2.pdf",
    "BNS": "https://indiacode.nic.in/bitstream/123456789/20062/1/a2023-45.pdf",
    "BNSS": "https://indiacode.nic.in/bitstream/123456789/20064/1/a2023-46.pdf",
    "IEA": "https://indiacode.nic.in/bitstream/123456789/2187/1/A1872-1.pdf",
}

@app.route('/open-bare-act/<act_code>')
def open_bare_act(act_code):
    url = BARE_ACTS_URLS.get(act_code.upper())
    if not url:
        return jsonify({"error": "Act not found"}), 404
    return redirect(url)


@app.route('/api/search-sections', methods=['GET'])
def search_sections():
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return jsonify([])

    # ---------------------------
    # 1. NORMAL DATABASE SEARCH
    # ---------------------------
    db_results = []

    for act in LEGAL_ACTS:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT Section, section_title 
                FROM {act}
                WHERE lower(section_title) LIKE ? 
                OR lower(section_desc) LIKE ?
                LIMIT 5
                """,
                (f"%{query.lower()}%", f"%{query.lower()}%")
            )
            rows = cursor.fetchall()

            for row in rows:
                db_results.append({
                    "act": act,
                    "section": row[0],
                    "title": row[1]
                })

            conn.close()

        except Exception as e:
            print("DB search error:", e)

    # ---------------------------
    # 2. AI SEARCH (OLLAMA)
    # ---------------------------
    prompt = f"""
    You are an Indian legal assistant.

    Find relevant law sections for this query:
    "{query}"

    Return ONLY JSON in this format:
    [
      {{"act": "IPC", "section": "420", "title": "Cheating"}},
      {{"act": "IPC", "section": "406", "title": "Criminal breach of trust"}}
    ]
    """

    ai_output = ask_ollama(prompt)

    try:
        start = ai_output.find("[")
        end = ai_output.rfind("]") + 1
        cleaned = ai_output[start:end]
        ai_results = json.loads(cleaned)
    except:
        ai_results = [{
        "act": "AI",
        "section": "-",
        "title": ai_output[:200]
    }]

    # ---------------------------
    # MERGE RESULTS
    # ---------------------------
    final_results = db_results + ai_results

    return jsonify(final_results[:20])
@app.route('/api/ask-law', methods=['POST'])
def ask_law():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "❌ Please ask a legal question."}), 400

    # Search relevant laws from RAG — now returns list of dicts or None
    results = search_law(question)

    if not results:
        return jsonify({"answer": "❌ No matching legal section found."})

    # Build beautiful output from structured data
    answer = "⚖️ NYAYA AI LEGAL ANALYSIS\n"
    answer += "═══════════════════════════════\n\n"

    for item in results:
        section     = item.get("section", "N/A")
        title       = item.get("title", "N/A")
        description = item.get("description", "N/A")

        answer += f"📘 IPC Section {section}\n"
        answer += f"📌 Title: {title}\n\n"
        answer += f"📝 Explanation:\n{description}\n\n"
        answer += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    answer += (
        "✅ These sections are highly relevant to your legal query.\n"
        "⚠️ Please consult a legal authority for official action."
    )

    return jsonify({"answer": answer})






# MongoDB connection

fir_collection = db["fir_records"]

# Folder to store generated PDFs
PDF_FOLDER = "generated_firs"
os.makedirs(PDF_FOLDER, exist_ok=True)


@app.route('/api/fir-records', methods=['GET'])
def get_fir_records():
    """Get all FIR records"""
    try:
        fir_records = []
        for fir in fir_collection.find({}, {"_id": 0}):
            fir_records.append(fir)

        return jsonify(fir_records)

    except Exception as e:
        return jsonify({"error": "Failed to retrieve FIR records", "details": str(e)}), 500


@app.route('/api/fir-records/<fir_no>', methods=['GET'])
def get_fir_record(fir_no):
    """Get specific FIR"""
    try:
        fir = fir_collection.find_one({"fir_no": fir_no}, {"_id": 0})

        if fir:
            return jsonify(fir)
        else:
            return jsonify({"error": f"FIR record {fir_no} not found"}), 404

    except Exception as e:
        return jsonify({"error": "Failed to retrieve FIR record", "details": str(e)}), 500


@app.route('/generate_fir', methods=['POST'])
def generate_fir():

    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    complaint_text = data.get("statement", "")

    # AI suggestion (logic unchanged)
    if not data.get("act_sections"):
        ai_suggested_sections = analyze_complaint_for_sections(complaint_text)
        data["act_sections"] = ", ".join(ai_suggested_sections)

    try:

        # Check duplicate FIR number
        if fir_collection.find_one({"fir_no": data.get("fir_no")}):
            return jsonify({"error": f"FIR number {data.get('fir_no')} already exists"}), 400

        # Generate FIR ID
        fir_id = str(datetime.utcnow().timestamp()).replace(".", "")

        formatted_fir = f"""
FIR ID: {fir_id}
FIR NO: {data.get("fir_no", "")}
DISTRICT: {data.get("dist", "")}
POLICE STATION: {data.get("ps", "")}
YEAR: {data.get("year", "")}
FIR DATE: {data.get("fir_date", "")}
ACT SECTIONS: {data.get("act_sections", "")}
OCCURRENCE DAY: {data.get("occurrence_day", "")}
OCCURRENCE DATE: {data.get("occurrence_date", "")}
OCCURRENCE TIME: {data.get("occurrence_time", "")}
INFO RECEIVED DATE: {data.get("info_received_date", "")}
INFO RECEIVED TIME: {data.get("info_received_time", "")}
GDR ENTRY NO: {data.get("gdr_entry_no", "")}
TYPE OF INFORMATION: {data.get("type_of_information", "")}
PLACE OF OCCURRENCE: {data.get("place_of_occurrence", "")}
COMPLAINANT NAME: {data.get("complainant_name", "")}
FATHER/HUSBAND NAME: {data.get("father_husband_name", "")}
DOB: {data.get("dob", "")}
NATIONALITY: {data.get("nationality", "")}
PASSPORT NO: {data.get("passport_no", "")}
DATE OF ISSUE: {data.get("date_of_issue", "")}
PLACE OF ISSUE: {data.get("place_of_issue", "")}
OCCUPATION: {data.get("occupation", "")}
ADDRESS: {data.get("address", "")}
DETAILS OF ACCUSED: {data.get("details_of_accused", "")}
REASONS FOR DELAY: {data.get("reasons_for_delay", "")}
PROPERTY PARTICULARS: {data.get("property_particulars", "")}
STATEMENT: {data.get("statement", "")}

STATUS: Saved to Police Records
MESSAGE: FIR has been successfully registered and saved to police records.
"""

        # -------------------------
        # Generate PDF
        # -------------------------

        pdf_filename = f"FIR_{data.get('fir_no')}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)

        styles = getSampleStyleSheet()
        elements = []

        for line in formatted_fir.split("\n"):
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 5))

        pdf = SimpleDocTemplate(pdf_path)
        pdf.build(elements)

        # -------------------------
        # Store in MongoDB
        # -------------------------

        fir_document = {
            "fir_id": fir_id,
            "fir_no": data.get("fir_no", ""),
            "dist": data.get("dist", ""),
            "ps": data.get("ps", ""),
            "year": data.get("year", ""),
            "fir_date": data.get("fir_date", ""),
            "act_sections": data.get("act_sections", ""),
            "occurrence_day": data.get("occurrence_day", ""),
            "occurrence_date": data.get("occurrence_date", ""),
            "occurrence_time": data.get("occurrence_time", ""),
            "info_received_date": data.get("info_received_date", ""),
            "info_received_time": data.get("info_received_time", ""),
            "gdr_entry_no": data.get("gdr_entry_no", ""),
            "type_of_information": data.get("type_of_information", ""),
            "place_of_occurrence": data.get("place_of_occurrence", ""),
            "complainant_name": data.get("complainant_name", ""),
            "father_husband_name": data.get("father_husband_name", ""),
            "dob": data.get("dob", ""),
            "nationality": data.get("nationality", ""),
            "passport_no": data.get("passport_no", ""),
            "date_of_issue": data.get("date_of_issue", ""),
            "place_of_issue": data.get("place_of_issue", ""),
            "occupation": data.get("occupation", ""),
            "address": data.get("address", ""),
            "details_of_accused": data.get("details_of_accused", ""),
            "reasons_for_delay": data.get("reasons_for_delay", ""),
            "property_particulars": data.get("property_particulars", ""),
            "statement": data.get("statement", ""),
            "pdf_file": pdf_filename,
            "created_at": datetime.utcnow(),
            "status": "Saved to Police Records"
        }

        fir_collection.insert_one(fir_document)
    
        fir_response = fir_document.copy()
        fir_response.pop("_id", None)
        fir_response["created_at"] = str(fir_response["created_at"])
        fir_response["formatted_fir"] = formatted_fir.strip()
        fir_response["message"] = "FIR has been successfully registered and saved to police records."

        return jsonify(fir_response)

    except Exception as e:
        return jsonify({"error": "Failed to save FIR to database", "details": str(e)}), 500
import os
from werkzeug.utils import secure_filename

# Configuration
UPLOAD_FOLDER = 'static/uploads/evidence'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Creates folder automatically

@app.route('/upload_evidence/<fir_no>', methods=['POST'])
def upload_evidence(fir_no):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    # Secure the filename and save it
    filename = secure_filename(f"{fir_no}_{file.filename}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    # Return success response
    return jsonify({"message": f"Evidence uploaded successfully for FIR {fir_no}", "file_path": file_path})

def generate_unique_id(role):
    """Generate unique ID based on role."""
    role_prefixes = {
        'police': 'POL',
        'citizen': 'CIT',
        'lawyer': 'LAW',
        'judge': 'JUD'
    }
    prefix = role_prefixes.get(role, 'USR')
    
    # Find the highest existing ID for this role
    try:
        existing_users = users_collection.find({'role': role}).sort('unique_id', -1).limit(1)
        last_user = list(existing_users)
        if last_user:
            last_id = last_user[0]['unique_id']
            # Extract number and increment
            try:
                num = int(last_id[3:]) + 1
            except:
                num = 1
        else:
            num = 1
    except:
        num = 1
    
    return f"{prefix}{num:03d}"

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        fullname = data.get('fullname')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        
        if not all([fullname, email, password, role]):
            return jsonify({"error": "All fields are required"}), 400
        
        if role not in ['police', 'citizen', 'lawyer', 'judge']:
            return jsonify({"error": "Invalid role"}), 400
        
        # Check if user already exists
        if users_collection.find_one({'email': email}):
            return jsonify({"error": "Email already registered"}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Unique ID handling by role
        if role in ['police', 'lawyer', 'judge']:
            unique_id = data.get('unique_id', '').strip().upper()
            if not unique_id:
                return jsonify({"error": "Unique ID is required for police, lawyer, or judge"}), 400

            # Prefix must match role rule
            role_prefixes = {'police': 'POL', 'lawyer': 'LAW', 'judge': 'JUD'}
            expected_prefix = role_prefixes[role]
            if not unique_id.startswith(expected_prefix):
                return jsonify({"error": f"Unique ID for {role} must start with {expected_prefix}"}), 400

            # Unique ID should not already exist
            if users_collection.find_one({'unique_id': unique_id}):
                return jsonify({"error": "Unique ID already registered"}), 400
        else:
            unique_id = generate_unique_id(role)

        # Create user document
        user = {
            'fullname': fullname,
            'email': email,
            'password_hash': password_hash,
            'role': role,
            'unique_id': unique_id,
            'created_at': datetime.utcnow()
        }
        
        try:
            users_collection.insert_one(user)
            return jsonify({
                "message": "User registered successfully",
                "unique_id": unique_id,
                "role": role
            }), 201
        except Exception as e:
            return jsonify({"error": f"Registration failed: {str(e)}"}), 500
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({"error": "Email and password are required"}), 400
        
        user = users_collection.find_one({'email': email})
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Store user in session
        session['user_id'] = str(user['_id'])
        session['role'] = user['role']
        session['unique_id'] = user['unique_id']
        
        return jsonify({
            "message": "Login successful",
            "role": user['role'],
            "unique_id": user['unique_id']
        }), 200
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', user=user)
#password for locker access (can be used for admin features or sensitive data access)
@app.route('/verify-locker-access', methods=['POST'])
def verify_locker_access():
    data = request.json
    pin = data.get("pin")

    # match with your frontend PIN
    if pin == "secure@123":   # or "1234" if you want simple
        return jsonify({"success": True})
    else:
        return jsonify({
            "success": False,
            "message": "Wrong Password ❌"
        }), 401

#upload evidence files related to a FIR (images, videos, documents)

@app.route('/upload-evidence', methods=['POST'])
def upload_evidence_file():
    fir_no = request.form.get("fir_no")
    file = request.files.get("file")

    if not fir_no or not file:
        return jsonify({"error": "Missing FIR or file"}), 400

    filename = secure_filename(file.filename)

    # create FIR-wise folder
    fir_folder = os.path.join(UPLOAD_FOLDER, fir_no)
    os.makedirs(fir_folder, exist_ok=True)

    file_path = os.path.join(fir_folder, filename)
    file.save(file_path)

    return jsonify({
        "message": "File uploaded successfully",
        "file": filename,
        "fir_no": fir_no
    })
#endpoint to list all evidence files for a FIRS
@app.route('/get-evidence/<fir_no>', methods=['GET'])
def get_evidence(fir_no):
    fir_folder = os.path.join(UPLOAD_FOLDER, fir_no)

    if not os.path.exists(fir_folder):
        return jsonify([])

    files = os.listdir(fir_folder)

    return jsonify(files)
#endpoint to serve evidence files
@app.route('/evidence-file/<fir_no>/<filename>')
def get_file(fir_no, filename):
    return send_from_directory(
        os.path.join(UPLOAD_FOLDER, fir_no),
        filename
    )
if __name__ == '__main__':
    init_fir_table()
    init_user_table()
    init_evidence_table()
    app.run(debug=True, port=5000)
=======
import os
from flask import Flask
from main import register_blueprints
from main.config import PDF_FOLDER, UPLOAD_FOLDER
from main.database import init_fir_table, init_user_table, init_evidence_table

app = Flask(__name__)
app.secret_key = "nyaya_ai_ultra_secure_key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Optional CORS support
try:
    from flask_cors import CORS
    CORS(app)
except ModuleNotFoundError:
    print("Warning: flask_cors not installed. API will still work from same origin.")

register_blueprints(app)

if __name__ == '__main__':
    init_fir_table()
    init_user_table()
    init_evidence_table()
    app.run(debug=True, port=5000)
>>>>>>> Person-A
