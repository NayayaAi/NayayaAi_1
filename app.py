from flask import Flask, request, jsonify, render_template, render_template_string, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from thefuzz import process, fuzz
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId
from datetime import datetime, timezone
from flask_wtf.csrf import CSRFProtect, CSRFError
from reportlab.lib.styles import getSampleStyleSheet
from ai_engine import analyze_complaint_for_sections
from rag_engine import search_law
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from flask import  jsonify
import jwt
from authlib.integrations.flask_client import OAuth
from urllib.parse import urlencode

from functools import wraps
from werkzeug.utils import secure_filename
from flask import send_from_directory
import subprocess
import json
from main.storage_service import upload_pdf, save_fir, get_all_firs, get_fir, fir_exists
from dotenv import load_dotenv
load_dotenv()

# Import missing person routes
from missing_person import missing_person_bp, init_missing_person_tables
from case import search_case_outcome, format_outcome_html


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = os.environ.get("OPENROUTER_URL", "")

def ask_openrouter(prompt, system_prompt=None, max_tokens=1000, temperature=0.3):
    
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set in .env")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://nyayaai.local",
            "X-Title": "NyayaAI"
        }
        
        default_system = "You are an expert Indian legal advisor. Be clear, simple, and helpful."
        
        payload = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt or default_system
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"OpenRouter error: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        if 'choices' not in data or len(data['choices']) == 0:
            print(f"Unexpected OpenRouter response: {data}")
            return None
            
        return data['choices'][0]['message']['content'].strip()
    
    except requests.exceptions.Timeout:
        print("OpenRouter timeout - request took too long")
        return None
    except requests.exceptions.ConnectionError:
        print("OpenRouter connection error - check your internet")
        return None
    except Exception as e:
        print(f"OpenRouter API Error: {e}")
        return None



# ---------------- OLLAMA SETUP ----------------
import requests

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

app = Flask(__name__)
app.secret_key = "nyaya_ai_ultra_secure_key"

oauth = OAuth(app)
 
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
 
github = oauth.register(
    name='github',
    client_id=os.environ.get('GITHUB_CLIENT_ID'),
    client_secret=os.environ.get('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

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

# ==================== MISSING PERSON FEATURE ====================
# Register missing person blueprint
app.register_blueprint(missing_person_bp)

# Initialize missing person tables
init_missing_person_tables(DB_PATH)

# Set upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/missing_persons')
def missing_persons_page():
    return render_template('missing_persons.html')


@app.route('/missing_persons_template')
def missing_persons_template():
    return render_template('missing_persons_fragment.html')

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
        role = session.get('role')
        if role == 'judge':
            return redirect(url_for('judge_dashboard'))
        if role == 'citizen':
            return redirect(url_for('citizen_dashboard'))
        if role == 'lawyer':
            return redirect(url_for('lawyer_dashboard'))
        return render_template('index.html')
    return redirect(url_for('signup')) # Direct new visitors to signup first

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

# ==================== CITIZEN COMPLAINTS ====================
import uuid

def init_complaints_table():
    """Create complaints table for citizen-filed complaints."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citizen_complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            incident_description TEXT NOT NULL,
            incident_date TEXT,
            location TEXT,
            status TEXT DEFAULT 'Pending',
            fir_no TEXT,
            officer_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/citizen-dashboard')
def citizen_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'citizen':
        return redirect(url_for('home'))
    return render_template('citizen_dashboard.html')

@app.route('/judge-dashboard')
def judge_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') not in ['judge', 'admin']:
        return redirect('/')
    return render_template('judge_dashboard.html')

@app.route('/api/complaint', methods=['POST'])
def file_complaint():
    """Citizen files a new complaint."""
    data = request.get_json()
    name = data.get('full_name', '').strip()
    description = data.get('incident_description', '').strip()
    if not name or not description:
        return jsonify({"error": "Name and incident description are required"}), 400

    tracking_id = "CMP-" + str(uuid.uuid4())[:8].upper()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO citizen_complaints
              (tracking_id, full_name, phone, incident_description, incident_date, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            tracking_id,
            name,
            data.get('phone', ''),
            description,
            data.get('incident_date', ''),
            data.get('location', '')
        ))
        conn.commit()
        conn.close()
        return jsonify({"tracking_id": tracking_id, "status": "Pending"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/api/complaints/all', methods=['GET'])
def get_all_complaints():
    """Police: get all citizen complaints."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tracking_id, full_name, phone, incident_description,
                   incident_date, location, status, fir_no, officer_notes,
                   created_at, updated_at
            FROM citizen_complaints
            ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{
            "tracking_id":          r[0],
            "full_name":            r[1],
            "phone":                r[2],
            "incident_description": r[3],
            "incident_date":        r[4],
            "location":             r[5],
            "status":               r[6],
            "fir_no":               r[7],
            "officer_notes":        r[8],
            "created_at":           r[9],
            "updated_at":           r[10]
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/complaints/<tracking_id>', methods=['PATCH'])
def update_complaint(tracking_id):
    """Police: update complaint status, FIR number, notes."""
    data       = request.get_json()
    new_status = data.get('status')
    fir_no     = data.get('fir_no')
    notes      = data.get('officer_notes')
 
    valid_statuses = ['Pending', 'Under Review', 'FIR Filed', 'Closed']
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400
 
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE citizen_complaints
            SET status = ?, fir_no = ?, officer_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE tracking_id = ?
        ''', (new_status, fir_no, notes, tracking_id.upper()))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Complaint not found"}), 404
        conn.commit()
        conn.close()
        return jsonify({"message": "Updated successfully", "tracking_id": tracking_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/complaint/<tracking_id>', methods=['GET'])
def track_complaint(tracking_id):
    """Track a complaint by its tracking ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tracking_id, full_name, incident_description, incident_date,
                   location, status, fir_no, officer_notes, created_at, updated_at
            FROM citizen_complaints WHERE tracking_id = ?
        ''', (tracking_id.upper(),))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Complaint not found. Check your tracking ID."}), 404
        return jsonify({
            "tracking_id": row[0],
            "full_name": row[1],
            "incident_description": row[2],
            "incident_date": row[3],
            "location": row[4],
            "status": row[5],
            "fir_no": row[6],
            "officer_notes": row[7],
            "created_at": row[8],
            "updated_at": row[9]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rights-chat', methods=['POST'])
def rights_chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"answer": "Invalid request."}), 400
        question = data.get('question', '').strip()
        print(f"DEBUG: OPENROUTER_KEY set={bool(OPENROUTER_API_KEY)}, question={question[:30]}")
        if not question:
            return jsonify({"answer": "Please ask a question about your rights."}), 400

        try:
            results = search_law(question)
        except Exception as rag_err:
            print(f"RAG failed: {rag_err}")
            results = None

        if not results:
            # RAG failed or no results — try OpenRouter
            or_answer = ask_openrouter(
                prompt=f"A citizen asks about their rights under Indian law: {question}\n\nAnswer in simple, plain language. Be concise.",
                system_prompt="You are a helpful Indian legal assistant. Explain legal rights simply. End with: ⚠️ For official help call 15100.",
                max_tokens=400
            )
            if or_answer:
                return jsonify({"answer": or_answer})
            # Final fallback — keyword
            return jsonify({"answer": build_keyword_fallback(question)})

        answer = format_rights_answer(results, question)
        return jsonify({"answer": answer})

    except Exception as e:
        print(f"rights_chat error: {e}")
        return jsonify({"answer": build_keyword_fallback(
            request.get_json(silent=True, force=True).get('question', '')
        )}), 200


def format_rights_answer(results, question):
    """Format RAG results into plain, citizen-friendly language."""
    top = results[:2]  # Use top 2 matches only
    lines = []

    for item in top:
        section = item.get('section', '')
        title   = item.get('title', '')
        desc    = item.get('description', '') or ''

        # Trim description to first 2 sentences for speed + readability
        sentences = desc.replace('.\n', '. ').split('. ')
        short_desc = '. '.join(sentences[:3]).strip()
        if short_desc and not short_desc.endswith('.'):
            short_desc += '.'

        if section and title:
            lines.append(f"📘 Section {section} — {title}\n{short_desc}")
        elif title:
            lines.append(f"📘 {title}\n{short_desc}")

    answer = "\n\n".join(lines)
    answer += "\n\n⚠️ This is for awareness only. Visit your nearest Legal Aid centre or call 15100 for official help."
    return answer


def build_keyword_fallback(question):
    """Instant keyword-based fallback — no AI needed."""
    q = question.lower()

    if any(w in q for w in ['arrest', 'arrested', 'police custody', 'detained']):
        return (
            "🛡️ Your Rights When Arrested:\n\n"
            "• You must be told the reason for your arrest.\n"
            "• You have the right to call a lawyer immediately.\n"
            "• You cannot be detained beyond 24 hours without a magistrate's order.\n"
            "• You have the right to free legal aid if you cannot afford a lawyer.\n\n"
            "📞 Call Legal Aid: 15100"
        )
    elif any(w in q for w in ['bail', 'bailable', 'release']):
        return (
            "🔑 Your Right to Bail:\n\n"
            "• For bailable offences, bail is your legal right — police must grant it.\n"
            "• For non-bailable offences, only a court can grant bail.\n"
            "• You can apply for Anticipatory Bail (Section 438 CrPC) before arrest.\n"
            "• A magistrate must be informed within 24 hours of arrest.\n\n"
            "📞 Call Legal Aid: 15100"
        )
    elif any(w in q for w in ['fir', 'complaint', 'register', 'refuse', 'refused']):
        return (
            "📝 If Police Refuse to File Your FIR:\n\n"
            "• Police are legally bound to register FIRs for cognizable offences.\n"
            "• If refused, send a written complaint to the Superintendent of Police.\n"
            "• You can also file directly with a Magistrate under Section 156(3) CrPC.\n"
            "• E-FIR can be filed online in most states.\n\n"
            "📞 Call Legal Aid: 15100"
        )
    elif any(w in q for w in ['lawyer', 'advocate', 'legal aid', 'free legal']):
        return (
            "⚖️ Your Right to a Lawyer:\n\n"
            "• Every arrested person has the right to consult a lawyer (Article 22).\n"
            "• If you cannot afford one, the state must provide a free lawyer.\n"
            "• Contact the District Legal Services Authority (DLSA) in your district.\n"
            "• National Legal Aid helpline: 15100 (free, 24×7).\n\n"
            "📞 Call Legal Aid: 15100"
        )
    elif any(w in q for w in ['women', 'woman', 'harassment', 'domestic', 'violence', 'assault']):
        return (
            "👩 Women's Legal Rights:\n\n"
            "• A woman can only be arrested between 6 AM and 6 PM (with exceptions).\n"
            "• A female officer must be present during arrest of a woman.\n"
            "• Domestic violence is an offence under the Protection of Women from Domestic Violence Act.\n"
            "• File complaints at your nearest One Stop Centre or call 181 (Women Helpline).\n\n"
            "📞 Women Helpline: 1091 | One Stop Centre: 181"
        )
    elif any(w in q for w in ['cyber', 'online', 'fraud', 'scam', 'hack', 'hacked']):
        return (
            "💻 Cyber Crime Rights:\n\n"
            "• Report cyber crimes at cybercrime.gov.in or call 1930.\n"
            "• Cyber fraud is covered under the IT Act 2000 and IPC Section 420.\n"
            "• File a complaint within the first few hours for best results.\n"
            "• Keep screenshots and transaction IDs as evidence.\n\n"
            "📞 Cyber Crime Helpline: 1930"
        )
    elif any(w in q for w in ['child', 'minor', 'pocso', 'juvenile']):
        return (
            "🧒 Child Protection Rights:\n\n"
            "• POCSO Act protects children from sexual offences.\n"
            "• Any person can report child abuse — it is mandatory for some professions.\n"
            "• Complaints can be filed at any police station regardless of location.\n"
            "• Child Helpline: 1098 (free, 24×7).\n\n"
            "📞 Child Helpline: 1098"
        )
    else:
        return (
            "⚖️ General Legal Rights in India:\n\n"
            "• You have the right to remain silent when questioned by police.\n"
            "• You cannot be forced to be a witness against yourself (Article 20).\n"
            "• Every person has the right to approach a court for justice.\n"
            "• Free legal aid is available to all citizens who cannot afford a lawyer.\n\n"
            "📞 National Legal Aid Helpline: 15100\n"
            "Try asking about: arrest rights, bail, FIR filing, lawyer rights, women's rights, or cyber crime."
        )

@app.route('/api/sections/<act>', methods=['GET'])
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

@app.route('/lawyer-dashboard')
def lawyer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'lawyer':
        return redirect(url_for('home'))
    return render_template('lawyer_dashboard.html')

# ── ADD THIS IMPORT at the top of app.py ──
from groq import Groq

# ── ADD THIS after load_dotenv() ──
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def ask_groq(prompt, max_tokens=2000):
    """Fast legal AI using Groq — 300-800 tokens/sec, free tier."""
    try:
        client_groq = Groq(api_key=GROQ_API_KEY)
        chat_completion = client_groq.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Indian criminal lawyer with 20 years of experience. "
                        "You draft precise, court-ready legal documents following Indian law. "
                        "Always reference BNSS (replacing CrPC), BNS (replacing IPC), and BSA (replacing Evidence Act) "
                        "where applicable alongside old provisions. Be formal and thorough."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",  # fastest + best quality on Groq free tier
            max_tokens=max_tokens,
            temperature=0.3,  # low temp = consistent legal language
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None  # will fall back to RAG template


# ════════════════════════════════════════════
# LAWYER PORTAL — AI ENDPOINTS (Groq powered)
# ════════════════════════════════════════════

@app.route('/api/lawyer/draft-document', methods=['POST'])
def lawyer_draft_document():
    if 'user_id' not in session or session.get('role') != 'lawyer':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    # Search RAG for relevant legal sections
    rag_results = search_law(prompt[:300])

    # Build RAG context to inject into Groq prompt
    rag_context = ""
    if rag_results:
        rag_context = "\n\nRELEVANT LEGAL SECTIONS FROM DATABASE:\n"
        for r in rag_results[:3]:
            rag_context += (
                f"• Section {r.get('section', '')}: {r.get('title', '')} — "
                f"{r.get('description', '')[:200]}\n"
            )

    enhanced_prompt = prompt + rag_context

    # Try Groq first
    text = ask_groq(enhanced_prompt, max_tokens=2000)

    # Fallback to RAG template if Groq fails
    if not text:
        text = generate_rag_document_lawyer(prompt, rag_results)

    return jsonify({"text": text})


@app.route('/api/lawyer/bail-draft', methods=['POST'])
def lawyer_bail_draft():
    if 'user_id' not in session or session.get('role') != 'lawyer':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    # RAG search for bail-related sections
    rag_results = search_law(prompt[:300])

    # Build RAG context
    rag_context = ""
    if rag_results:
        rag_context = "\n\nRELEVANT BAIL PROVISIONS FROM NYAYAAI DATABASE:\n"
        for r in rag_results[:4]:
            rag_context += (
                f"• Section {r.get('section', '')}: {r.get('title', '')} — "
                f"{r.get('description', '')[:200]}\n"
            )

    enhanced_prompt = prompt + rag_context

    # Try Groq
    text = ask_groq(enhanced_prompt, max_tokens=2000)

    # Fallback
    if not text:
        text = generate_rag_document_lawyer(prompt, rag_results)

    return jsonify({"text": text})


# ── Precedent Finder also uses Groq ──
@app.route('/api/lawyer/find-precedents', methods=['POST'])
def lawyer_find_precedents():
    if 'user_id' not in session or session.get('role') != 'lawyer':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    query = data.get('query', '').strip()
    search_type = data.get('type', 'laws')

    if not query:
        return jsonify({"answer": "Please enter a search query."}), 400

    # RAG search first
    rag_results = search_law(query)

    rag_context = ""
    if rag_results:
        rag_context = "\n\nFROM NYAYAAI LEGAL DATABASE:\n"
        for r in rag_results[:4]:
            rag_context += (
                f"• Section {r.get('section', '')}: {r.get('title', '')} — "
                f"{r.get('description', '')[:200]}\n"
            )

    if search_type == 'outcome':
        groq_prompt = (
            f"As an Indian legal expert, analyze this situation and predict likely case outcome "
            f"with relevant Supreme Court and High Court precedents:\n\n{query}{rag_context}\n\n"
            f"Give: 1) Likely outcome 2) Key precedents 3) Relevant sections 4) Advice"
        )
    else:
        groq_prompt = (
            f"As an Indian legal expert, find all relevant law sections for:\n\n{query}"
            f"{rag_context}\n\n"
            f"Give: 1) Applicable IPC/BNS sections 2) CrPC/BNSS provisions "
            f"3) Key Supreme Court judgments 4) Legal strategy"
        )

    answer = ask_groq(groq_prompt, max_tokens=1500)

    if not answer:
        # Pure RAG fallback
        if rag_results:
            answer = "⚖️ RELEVANT LEGAL SECTIONS (NyayaAI Database):\n\n"
            for r in rag_results[:5]:
                answer += f"📘 Section {r.get('section','')}: {r.get('title','')}\n"
                answer += f"   {r.get('description','')[:300]}\n\n"
        else:
            answer = "No matching legal sections found. Please refine your query."

    return jsonify({"answer": answer})


# ════════════════════════════════════
# RAG FALLBACK DOCUMENT GENERATOR
# ════════════════════════════════════

def generate_rag_document_lawyer(prompt, rag_results):
    """Builds a structured legal document from RAG results when Groq is unavailable."""
    from datetime import datetime
    today = datetime.now().strftime("%d %B %Y")

    # Extract fields from prompt
    accused = court = case_no = sections = facts = custody = bail_type = ps = ""
    for line in prompt.split('\n'):
        line = line.strip()
        if 'Accused:' in line:        accused    = line.split('Accused:')[-1].strip()
        if 'Court:' in line:          court      = line.split('Court:')[-1].strip()
        if 'FIR' in line and ':' in line: case_no = line.split(':')[-1].strip()
        if 'Section' in line and 'Charged' in line: sections = line.split(':')[-1].strip()
        if 'Grounds' in line:         facts      = line.split(':')[-1].strip()
        if 'Custody' in line:         custody    = line.split(':')[-1].strip()
        if 'Bail Type' in line:       bail_type  = line.split(':')[-1].strip()
        if 'Police Station' in line:  ps         = line.split(':')[-1].strip()

    accused    = accused or "The Applicant"
    court      = court or "SESSIONS COURT"
    case_no    = case_no or "___"
    sections   = sections or "___"
    custody    = custody or "some days"

    # Build citations from RAG
    rag_citations = ""
    if rag_results:
        rag_citations = "\nLEGAL PROVISIONS (NyayaAI Database):\n"
        for r in rag_results[:4]:
            rag_citations += (
                f"• Section {r.get('section','')}: {r.get('title','')}\n"
                f"  {r.get('description','')[:200]}\n\n"
            )

    return f"""IN THE COURT OF {court.upper()}

APPLICATION FOR BAIL
Under Section 480 BNSS / Section 437 CrPC

                                        Case No.: {case_no}
                            State vs. {accused.upper()}

MOST RESPECTFULLY SHOWETH:

1.  The present application is filed seeking bail for the applicant
    {accused}, who has been in custody for {custody}.

2.  The applicant is charged under: {sections}

GROUNDS FOR BAIL:

I.   The applicant is a first-time offender with no prior criminal
     antecedents, deserving the benefit of bail.

II.  The investigation in the present case is complete and the
     applicant's continued detention is unnecessary.

III. The applicant is a permanent resident with deep roots in the
     community — no risk of absconding or fleeing justice.

IV.  The applicant is the sole breadwinner of the family; continued
     detention causes irreparable hardship to dependants.

V.   There is no risk of tampering with witnesses or evidence as
     the chargesheet has already been filed.

VI.  The Hon'ble Supreme Court in Arnesh Kumar v. State of Bihar
     (2014) 8 SCC 273 cautioned against casual arrests.

VII. The Hon'ble Supreme Court in Sanjay Chandra v. CBI (2012)
     held that bail is the rule, jail is the exception.
{rag_citations}
UNDERTAKING:
The applicant undertakes to:
(a) Appear before this Court on every date of hearing
(b) Not tamper with evidence or influence witnesses
(c) Not leave the jurisdiction without prior permission
(d) Surrender passport if directed

PRAYER:
It is, therefore, most humbly prayed that this Hon'ble Court may
be pleased to:

(a) Release the applicant {accused} on bail on such terms and
    conditions as this Hon'ble Court deems fit and proper;

(b) Pass such other and further orders as this Hon'ble Court
    deems just and proper in the facts and circumstances.

AND FOR THIS ACT OF KINDNESS, THE APPLICANT SHALL AS IN
DUTY BOUND EVER PRAY.

Place: {court}
Date:  {today}

                                    Respectfully submitted,


                            ________________________________
                                   ADVOCATE FOR APPLICANT
                                   Bar Enrolment No.: ______
                                   Bar Council of ________"""

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
evidence_collection = db["evidence_files"]

# Folder to store generated PDFs
PDF_FOLDER = "generated_firs"
os.makedirs(PDF_FOLDER, exist_ok=True)



@app.route('/api/fir-records', methods=['GET'])
def get_fir_records():
    """Get all FIR records"""
    try:
        fir_records = []
        for fir in get_all_firs() :
            fir_records.append(fir)

        return jsonify(fir_records)

    except Exception as e:
        return jsonify({"error": "Failed to retrieve FIR records", "details": str(e)}), 500


@app.route('/api/fir-records/<fir_no>', methods=['GET'])
def get_fir_record(fir_no):
    """Get specific FIR"""
    try:
        fir = get_fir(fir_no)

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
        if fir_exists(data.get("fir_no")):
            return jsonify({"error": "FIR already exists"}), 400

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
        pdf_url = upload_pdf(pdf_path, fir_id)
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
            
            "pdf_url": pdf_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "Saved to Police Records"
        }

        fir_document["pdf_url"] = pdf_url
        save_fir(fir_document)
    
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
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'evidence')
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
        session['fullname'] = user.get('fullname', 'Advocate')
        
        return jsonify({
            "message": "Login successful",
            "role": user['role'],
            "unique_id": user['unique_id'],
            "redirect": (
                "/citizen-dashboard" if user['role'] == 'citizen'
                else "/judge-dashboard" if user['role'] == 'judge'
                else "/lawyer-dashboard" if user['role'] == 'lawyer'
                else "/")  # ← UPDATED
            }), 200
    
    return render_template('login.html')


@app.route('/auth/google')
def auth_google():
    """Redirect user to Google OAuth"""
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)
 
 
@app.route('/auth/google/callback')
def auth_google_callback():
    """Handle Google OAuth callback"""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            return redirect(url_for('login'))
        
        email = user_info.get('email')
        fullname = user_info.get('name', 'Google User')
        profile_pic = user_info.get('picture', '')
        
        # Find or create user
        user = users_collection.find_one({'email': email})
        
        if not user:
            # Create new user (default role: citizen for OAuth signups)
            unique_id = generate_unique_id('citizen')
            password_hash = bcrypt.hashpw(
                os.urandom(16),  # Random password since OAuth
                bcrypt.gensalt()
            )
            
            user = {
                'fullname': fullname,
                'email': email,
                'password_hash': password_hash,
                'role': 'citizen',  # Default role
                'unique_id': unique_id,
                'profile_pic': profile_pic,
                'oauth_provider': 'google',
                'created_at': datetime.utcnow()
            }
            users_collection.insert_one(user)
        else:
            # Update profile pic if not already set
            if not user.get('profile_pic'):
                users_collection.update_one(
                    {'_id': user['_id']},
                    {'$set': {'profile_pic': profile_pic, 'oauth_provider': 'google'}}
                )
            user = users_collection.find_one({'_id': user['_id']})
        
        # Log user in
        session['user_id'] = str(user['_id'])
        session['role'] = user['role']
        session['unique_id'] = user['unique_id']
        session['fullname'] = user.get('fullname', 'User')
        
        # Redirect based on role
        if user['role'] == 'citizen':
            return redirect(url_for('citizen_dashboard'))
        elif user['role'] == 'judge':
            return redirect(url_for('judge_dashboard'))
        elif user['role'] == 'lawyer':
            return redirect(url_for('lawyer_dashboard'))
        else:
            return redirect(url_for('home'))
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for('login'))
 
 
# ──── GITHUB OAUTH ────────────────────────────────────
 
@app.route('/auth/github')
def auth_github():
    """Redirect user to GitHub OAuth"""
    redirect_uri = url_for('auth_github_callback', _external=True)
    return github.authorize_redirect(redirect_uri)
 
 
@app.route('/auth/github/callback')
def auth_github_callback():
    """Handle GitHub OAuth callback"""
    try:
        token = github.authorize_access_token()
        
        # Get user info from GitHub API
        resp = github.get('user', token=token)
        user_info = resp.json()
        
        github_id = user_info.get('id')
        email = user_info.get('email') or f"github_{github_id}@noreply.github.com"
        fullname = user_info.get('name') or user_info.get('login')
        profile_pic = user_info.get('avatar_url', '')
        
        # Find or create user
        user = users_collection.find_one({'email': email})
        
        if not user:
            # Create new user (default role: citizen for OAuth signups)
            unique_id = generate_unique_id('citizen')
            password_hash = bcrypt.hashpw(
                os.urandom(16),  # Random password since OAuth
                bcrypt.gensalt()
            )
            
            user = {
                'fullname': fullname,
                'email': email,
                'password_hash': password_hash,
                'role': 'citizen',  # Default role
                'unique_id': unique_id,
                'profile_pic': profile_pic,
                'github_id': github_id,
                'oauth_provider': 'github',
                'created_at': datetime.utcnow()
            }
            users_collection.insert_one(user)
        else:
            # Update profile pic and github_id if not already set
            updates = {}
            if not user.get('profile_pic'):
                updates['profile_pic'] = profile_pic
            if not user.get('github_id'):
                updates['github_id'] = github_id
            if updates:
                updates['oauth_provider'] = 'github'
                users_collection.update_one(
                    {'_id': user['_id']},
                    {'$set': updates}
                )
            user = users_collection.find_one({'_id': user['_id']})
        
        # Log user in
        session['user_id'] = str(user['_id'])
        session['role'] = user['role']
        session['unique_id'] = user['unique_id']
        session['fullname'] = user.get('fullname', 'User')
        
        # Redirect based on role
        if user['role'] == 'citizen':
            return redirect(url_for('citizen_dashboard'))
        elif user['role'] == 'judge':
            return redirect(url_for('judge_dashboard'))
        elif user['role'] == 'lawyer':
            return redirect(url_for('lawyer_dashboard'))
        else:
            return redirect(url_for('home'))
        
    except Exception as e:
        print(f"GitHub OAuth error: {e}")
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for('login'))
    
    
    

@app.route('/citizen_dashboard')
def citizen_dashboard_redirect():
    return redirect(url_for('citizen_dashboard'))

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

    if not fir_collection.find_one({"fir_no": fir_no}):
        return jsonify({"error": "FIR number does not exist. Please enter a valid FIR."}), 400

    filename = secure_filename(file.filename)

    # create FIR-wise folder
    fir_folder = os.path.join(UPLOAD_FOLDER, fir_no)
    os.makedirs(fir_folder, exist_ok=True)

    file_path = os.path.join(fir_folder, filename)
    file.save(file_path)

    # store metadata in MongoDB (skip if same FIR + filename already exists)
    if not evidence_collection.find_one({"fir_no": fir_no, "filename": filename}):
        evidence_collection.insert_one({
            "fir_no": fir_no,
            "filename": filename,
            "filepath": file_path,
            "file_type": file.mimetype or "application/octet-stream",
            "file_size": os.path.getsize(file_path),
            "uploaded_at": datetime.utcnow()
        })

    return jsonify({
        "message": "File uploaded successfully",
        "file": filename,
        "fir_no": fir_no
    })
#endpoint to list all evidence files for a FIR
@app.route('/get-evidence/<fir_no>', methods=['GET'])
def get_evidence(fir_no):
    docs = evidence_collection.find({"fir_no": fir_no}, {"_id": 0, "filename": 1})
    return jsonify([doc["filename"] for doc in docs])
#endpoint to serve evidence files
@app.route('/evidence-file/<fir_no>/<filename>')
def get_file(fir_no, filename):
    return send_from_directory(
        os.path.join(UPLOAD_FOLDER, fir_no),
        filename
    )

@app.route('/api/evidence', methods=['GET'])
def api_get_evidence():
    """Get evidence files for a specific FIR number."""
    fir_no = request.args.get('fir_no', '').strip()
    if not fir_no:
        return jsonify([])
    
    docs = evidence_collection.find({"fir_no": fir_no}, {"_id": 0})
    result = []
    for doc in docs:
        filename = doc.get("filename", "")
        file_type = doc.get("file_type", "application/octet-stream")
        
        # Determine category
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
            category = 'image'
        elif ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']:
            category = 'video'
        elif ext in ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a']:
            category = 'audio'
        elif ext == 'pdf':
            category = 'pdf'
        else:
            category = 'other'
        
        result.append({
            "fir_no": doc.get("fir_no", ""),
            "filename": filename,
            "file_type": category,
            "file_url": f"/evidence-file/{fir_no}/{filename}",
            "uploaded_at": str(doc.get("uploaded_at", ""))
        })
    
    return jsonify(result)


@app.route('/api/evidence/log-access', methods=['POST'])
def log_evidence_access():
    """Log evidence locker access (stub — returns 200 silently)."""
    # Optionally store to DB later; for now just acknowledge
    return jsonify({"logged": True}), 200

@app.route('/get-all-evidence', methods=['GET'])
def get_all_evidence():
    """Return all evidence grouped by FIR number from MongoDB."""
    result = {}
    for doc in evidence_collection.find({}, {"_id": 0, "fir_no": 1, "filename": 1}):
        fir_no = doc["fir_no"]
        result.setdefault(fir_no, []).append(doc["filename"])
    return jsonify(result)

@app.route('/fir/view/<fir_no>', methods=['GET'])
def view_fir(fir_no):
    """Render a FIR as a readable HTML page (opens in new tab)."""
    fir = get_fir(fir_no)
    if not fir:
        return f"<h2>FIR {fir_no} not found.</h2>", 404
    created_at = str(fir.get("created_at", ""))
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>FIR {{ fir.fir_no }} — NyayaAI</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1e293b; }
    h1 { color: #1e3a8a; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }
    .fir-badge { display: inline-block; background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 999px; font-weight: bold; font-size: 1.1em; margin-bottom: 16px; }
    .section { margin: 12px 0; }
    .label { font-weight: bold; color: #475569; }
    .value { margin-left: 8px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .narrative { background: #f8fafc; border-left: 4px solid #2563eb; padding: 12px 16px; font-style: italic; white-space: pre-wrap; margin-top: 6px; }
    .disclaimer { color: #ef4444; font-size: 0.75em; margin-top: 32px; }
    @media print { button { display: none; } }
  </style>
</head>
<body>
  <h1>FORM IF-1 — First Information Report</h1>
  <div class="fir-badge">{{ fir.fir_no }}</div>
  <button onclick="window.print()" style="float:right;padding:6px 16px;background:#2563eb;color:white;border:none;border-radius:6px;cursor:pointer;">Print</button>
  <div class="grid">
    <div class="section"><span class="label">District:</span><span class="value">{{ fir.dist }}</span></div>
    <div class="section"><span class="label">Police Station:</span><span class="value">{{ fir.ps }}</span></div>
    <div class="section"><span class="label">Year:</span><span class="value">{{ fir.year }}</span></div>
    <div class="section"><span class="label">FIR Date:</span><span class="value">{{ fir.fir_date }}</span></div>
    <div class="section"><span class="label">Act/Sections:</span><span class="value">{{ fir.act_sections }}</span></div>
    <div class="section"><span class="label">Occurrence:</span><span class="value">{{ fir.occurrence_day }}, {{ fir.occurrence_date }}, {{ fir.occurrence_time }}</span></div>
    <div class="section"><span class="label">Info Received:</span><span class="value">{{ fir.info_received_date }} {{ fir.info_received_time }}</span></div>
    <div class="section"><span class="label">GDR Entry:</span><span class="value">{{ fir.gdr_entry_no }}</span></div>
    <div class="section"><span class="label">Type of Info:</span><span class="value">{{ fir.type_of_information }}</span></div>
    <div class="section"><span class="label">Place of Occurrence:</span><span class="value">{{ fir.place_of_occurrence }}</span></div>
  </div>
  <div class="section"><span class="label">Complainant:</span><span class="value">{{ fir.complainant_name }}</span></div>
  <div class="section"><span class="label">Father/Husband:</span><span class="value">{{ fir.father_husband_name }}</span></div>
  <div class="grid">
    <div class="section"><span class="label">DOB:</span><span class="value">{{ fir.dob }}</span></div>
    <div class="section"><span class="label">Nationality:</span><span class="value">{{ fir.nationality }}</span></div>
    <div class="section"><span class="label">Occupation:</span><span class="value">{{ fir.occupation }}</span></div>
    <div class="section"><span class="label">Address:</span><span class="value">{{ fir.address }}</span></div>
  </div>
  <div class="section"><span class="label">Accused Details:</span><span class="value">{{ fir.details_of_accused }}</span></div>
  <div class="section"><span class="label">Reasons for Delay:</span><span class="value">{{ fir.reasons_for_delay }}</span></div>
  <div class="section"><span class="label">Property Particulars:</span><span class="value">{{ fir.property_particulars }}</span></div>
  <div class="section"><span class="label">Narrative:</span>
    <div class="narrative">{{ fir.statement }}</div>
  </div>
  <div class="section"><span class="label">Status:</span><span class="value">{{ fir.status }}</span></div>
  <div class="section"><span class="label">Created At:</span><span class="value">{{ created_at }}</span></div>
  <p class="disclaimer">Disclaimer: This is a system-generated draft. Must be verified by authorized personnel.</p>
</body>
</html>""", fir=fir, created_at=created_at)


@app.route('/fir/download/<fir_no>', methods=['GET'])
def download_fir(fir_no):
    """Download the generated PDF for a FIR."""
    safe_name = secure_filename(fir_no)
    pdf_filename = f"FIR_{safe_name}.pdf"
    pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
    if not os.path.exists(pdf_path):
        return jsonify({"error": f"PDF for FIR {fir_no} not found"}), 404
    return send_from_directory(
        PDF_FOLDER,
        pdf_filename,
        as_attachment=True,
        download_name=f"{fir_no}.pdf"
    )


def seed_evidence_from_filesystem():
    """Migrate existing on-disk evidence files into MongoDB (skips already-present records)."""
    if not os.path.exists(UPLOAD_FOLDER):
        return
    seeded = 0
    for fir_no in os.listdir(UPLOAD_FOLDER):
        fir_folder = os.path.join(UPLOAD_FOLDER, fir_no)
        if not os.path.isdir(fir_folder):
            continue
        for filename in os.listdir(fir_folder):
            full_path = os.path.join(fir_folder, filename)
            if not os.path.isfile(full_path):
                continue
            if evidence_collection.find_one({"fir_no": fir_no, "filename": filename}):
                continue
            evidence_collection.insert_one({
                "fir_no": fir_no,
                "filename": filename,
                "filepath": full_path,
                "file_type": "application/octet-stream",
                "file_size": os.path.getsize(full_path),
                "uploaded_at": datetime.utcnow()
            })
            seeded += 1
    if seeded:
        print(f"Evidence migration: seeded {seeded} file(s) into MongoDB.")

if __name__ == '__main__':
    init_fir_table()
    init_user_table()
    init_evidence_table()
    init_complaints_table()
    seed_evidence_from_filesystem()
    app.run(debug=True, port=5000)
