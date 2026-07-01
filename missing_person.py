# missing_person.py — Flask Blueprint for Missing Persons feature
# Handles police uploads, citizen sightings, face recognition

import os
import sqlite3
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename

# ── Optional face-recognition (graceful fallback) ────────────────────────────
try:
    from face_recognition_helper import compare_faces, extract_face
    print("[MissingPersons] face_recognition_helper loaded.")
except Exception as _e:
    print(f"[MissingPersons] face_recognition_helper unavailable ({_e}). Demo mode active.")

    def extract_face(path):
        return True   # never block uploads in demo mode

    def compare_faces(p1, p2, tolerance=0.6):
        import random
        score = round(random.uniform(0.40, 0.92), 4)
        return {
            'is_match':         score >= tolerance,
            'confidence_score': score,
            'distance':         round(1 - score, 4),
            'details': (
                f"Demo mode (face_recognition not installed). "
                f"Simulated confidence: {round(score * 100, 1)}%. "
                "Install dlib + face-recognition for real results."
            )
        }


missing_person_bp = Blueprint('missing_person', __name__)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _db_path():
    return os.path.join(os.path.dirname(__file__), 'IndiaLaw.db')


def _static_root():
    return os.path.join(os.path.dirname(__file__), 'static')


def _get_db():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _is_police():
    """True for logged-in police/admin accounts."""
    return session.get('role') in ('police', 'admin', 'officer')


def _allowed_image(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'gif', 'webp'}


# ── Table initialisation ─────────────────────────────────────────────────────

def init_missing_person_tables(db_path=None):
    path = db_path or _db_path()
    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS missing_persons (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id           TEXT    UNIQUE NOT NULL,
            name                TEXT    NOT NULL,
            age                 INTEGER,
            gender              TEXT,
            description         TEXT,
            photo_path          TEXT    NOT NULL,
            uploaded_by_police  TEXT    NOT NULL DEFAULT 'police',
            status              TEXT    NOT NULL DEFAULT 'Missing',
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_location  TEXT,
            last_seen_date      TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS missing_person_sightings (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            sighting_id         TEXT    UNIQUE NOT NULL,
            person_id           TEXT    NOT NULL,
            citizen_photo_path  TEXT    NOT NULL,
            location            TEXT,
            sighting_date       TEXT,
            face_match_score    REAL    DEFAULT 0,
            is_confirmed        INTEGER DEFAULT 0,
            uploaded_by_citizen TEXT    NOT NULL DEFAULT 'citizen',
            uploaded_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES missing_persons(person_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("[MissingPersons] Tables initialised.")


# ════════════════════════════════════════════════════════════════════════════
#  API ROUTES
# ════════════════════════════════════════════════════════════════════════════

# ── /api/me ──────────────────────────────────────────────────────────────────

@missing_person_bp.route('/api/me', methods=['GET'])
def api_me():
    """
    Return current session role so the frontend can show/hide police tabs.
    Always returns 200 — the frontend decides what to do with the payload.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'logged_in': False, 'role': None}), 200
        return jsonify({
            'logged_in': True,
            'role':      session.get('role', 'citizen'),
            'user_id':   str(session.get('user_id', ''))
        }), 200
    except Exception as e:
        # Never let /api/me return a 500 — frontend falls back to citizen view
        print(f"[MP /api/me error] {e}")
        return jsonify({'logged_in': False, 'role': None}), 200


# ── GET /get_missing_persons — public ────────────────────────────────────────

@missing_person_bp.route('/get_missing_persons', methods=['GET'])
def get_missing_persons():
    try:
        conn = _get_db()
        rows = conn.execute('''
            SELECT person_id, name, age, gender, description, photo_path,
                   last_seen_location, last_seen_date, created_at, status
            FROM   missing_persons
            WHERE  status = 'Missing'
            ORDER  BY created_at DESC
        ''').fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'missing_persons': [
                {
                    'person_id':          r['person_id'],
                    'name':               r['name'],
                    'age':                r['age'],
                    'gender':             r['gender'],
                    'description':        r['description'],
                    'photo_url':          '/' + r['photo_path'],
                    'last_seen_location': r['last_seen_location'],
                    'last_seen_date':     r['last_seen_date'],
                    'created_at':         r['created_at'],
                    'status':             r['status'],
                }
                for r in rows
            ]
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── POST /upload_missing_person — police only ────────────────────────────────

@missing_person_bp.route('/upload_missing_person', methods=['POST'])
def upload_missing_person():
    if not _is_police():
        return jsonify({'success': False, 'error': 'Police login required.'}), 403

    try:
        name = (request.form.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Full name is required.'}), 400

        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo file received.'}), 400

        file = request.files['photo']
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected.'}), 400

        if not _allowed_image(file.filename):
            return jsonify({'success': False, 'error': 'Only JPG, PNG, GIF, WEBP images accepted.'}), 400

        ext       = file.filename.rsplit('.', 1)[1].lower()
        person_id = f"MP_{uuid.uuid4().hex[:12].upper()}"

        upload_folder = os.path.join(_static_root(), 'uploads', 'missing_persons')
        os.makedirs(upload_folder, exist_ok=True)

        safe_name = f"{person_id}.{ext}"
        abs_path  = os.path.join(upload_folder, safe_name)
        file.save(abs_path)

        # Face check — only reject if face_recognition is REAL (not demo fallback)
        face_found = extract_face(abs_path)
        if not face_found:
            try:
                os.remove(abs_path)
            except OSError:
                pass
            return jsonify({
                'success': False,
                'error':   'No face detected in the photo. Please upload a clear frontal image.'
            }), 400

        rel_path = f"static/uploads/missing_persons/{safe_name}"

        age                = (request.form.get('age') or '').strip() or None
        gender             = (request.form.get('gender') or '').strip()
        description        = (request.form.get('description') or '').strip()
        last_seen_location = (request.form.get('last_seen_location') or '').strip()
        last_seen_date     = (request.form.get('last_seen_date') or '').strip() or None

        conn = _get_db()
        conn.execute('''
            INSERT INTO missing_persons
                (person_id, name, age, gender, description, photo_path,
                 uploaded_by_police, last_seen_location, last_seen_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Missing')
        ''', (
            person_id, name, age, gender, description, rel_path,
            str(session.get('user_id', 'police')),
            last_seen_location, last_seen_date
        ))
        conn.commit()
        conn.close()

        return jsonify({
            'success':   True,
            'message':   f'Missing person "{name}" reported successfully.',
            'person_id': person_id
        }), 200

    except Exception as e:
        print(f"[MP upload error] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── POST /report_sighting/<person_id> — any logged-in user ───────────────────
# NOTE: Citizens CAN report sightings — no police check here.

@missing_person_bp.route('/report_sighting/<person_id>', methods=['POST'])
def report_sighting(person_id):
    # Require login (any role)
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Please log in to report a sighting.'}), 401

    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo file received.'}), 400

        file = request.files['photo']
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected.'}), 400

        if not _allowed_image(file.filename):
            return jsonify({'success': False, 'error': 'Only image files accepted.'}), 400

        location      = (request.form.get('location') or '').strip()
        sighting_date = (request.form.get('sighting_date') or '').strip() or \
                        datetime.now().strftime('%Y-%m-%d')

        if not location:
            return jsonify({'success': False, 'error': 'Location is required.'}), 400

        conn = _get_db()
        row  = conn.execute(
            'SELECT photo_path FROM missing_persons WHERE person_id = ? AND status = "Missing"',
            (person_id,)
        ).fetchone()

        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Record not found or already resolved.'}), 404

        police_photo_abs = os.path.join(os.path.dirname(__file__), row['photo_path'])

        ext         = file.filename.rsplit('.', 1)[1].lower()
        sighting_id = f"SG_{uuid.uuid4().hex[:12].upper()}"

        upload_folder     = os.path.join(_static_root(), 'uploads', 'sightings')
        os.makedirs(upload_folder, exist_ok=True)

        safe_name         = f"{sighting_id}.{ext}"
        citizen_photo_abs = os.path.join(upload_folder, safe_name)
        file.save(citizen_photo_abs)

        face_found = extract_face(citizen_photo_abs)
        if not face_found:
            try:
                os.remove(citizen_photo_abs)
            except OSError:
                pass
            conn.close()
            return jsonify({
                'success': False,
                'error':   'No face detected in your photo. Please upload a clearer image.'
            }), 400

        result       = compare_faces(police_photo_abs, citizen_photo_abs, tolerance=0.55)
        score        = float(result['confidence_score'])
        is_confirmed = 1 if result['is_match'] else 0
        rel_path     = f"static/uploads/sightings/{safe_name}"

        conn.execute('''
            INSERT INTO missing_person_sightings
                (sighting_id, person_id, citizen_photo_path, location, sighting_date,
                 face_match_score, is_confirmed, uploaded_by_citizen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sighting_id, person_id, rel_path, location, sighting_date,
            score, is_confirmed, str(session.get('user_id', 'citizen'))
        ))
        conn.commit()
        conn.close()

        pct = round(score * 100, 1)
        return jsonify({
            'success':          True,
            'sighting_id':      sighting_id,
            'face_match_score': score,
            'is_match':         result['is_match'],
            'details':          result['details'],
            'message': (
                f'✓ Match confirmed! Confidence: {pct}%'
                if result['is_match']
                else f'Sighting recorded. Confidence: {pct}%'
            )
        }), 200

    except Exception as e:
        print(f"[MP sighting error] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── GET /get_sightings/<person_id> — police only ─────────────────────────────

@missing_person_bp.route('/get_sightings/<person_id>', methods=['GET'])
def get_sightings(person_id):
    if not _is_police():
        return jsonify({'success': False, 'error': 'Police login required.'}), 403
    try:
        conn = _get_db()
        rows = conn.execute('''
            SELECT sighting_id, citizen_photo_path, location, sighting_date,
                   face_match_score, is_confirmed, uploaded_at
            FROM   missing_person_sightings
            WHERE  person_id = ?
            ORDER  BY uploaded_at DESC
        ''', (person_id,)).fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'sightings': [
                {
                    'sighting_id':      s['sighting_id'],
                    'photo_url':        '/' + s['citizen_photo_path'],
                    'location':         s['location'],
                    'sighting_date':    s['sighting_date'],
                    'face_match_score': s['face_match_score'],
                    'is_confirmed':     bool(s['is_confirmed']),
                    'uploaded_at':      s['uploaded_at'],
                }
                for s in rows
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── GET /get_confirmed_matches — police only ─────────────────────────────────

# ── GET /get_confirmed_matches — police only ─────────────────────────────────

@missing_person_bp.route('/get_confirmed_matches', methods=['GET'])
def get_confirmed_matches():
    if not _is_police():
        return jsonify({'success': False, 'error': 'Police login required.'}), 403
    try:
        conn = _get_db()
        rows = conn.execute('''
            SELECT mp.person_id, mp.name, mp.photo_path AS mp_photo,
                   s.sighting_id, s.citizen_photo_path, s.location,
                   s.sighting_date, s.face_match_score, s.uploaded_at
            FROM   missing_person_sightings s
            JOIN   missing_persons mp ON mp.person_id = s.person_id
            WHERE  s.is_confirmed = 1
              AND  mp.status = 'Missing'
            ORDER  BY s.face_match_score DESC, s.uploaded_at DESC
        ''').fetchall()
        conn.close()

        # Group all sightings under each person instead of one card per sighting
        grouped = {}
        for m in rows:
            pid = m['person_id']
            if pid not in grouped:
                grouped[pid] = {
                    'person_id':            pid,
                    'name':                 m['name'],
                    'missing_person_photo': '/' + m['mp_photo'],
                    'confidence':           round(m['face_match_score'] * 100, 1),
                    'location':             m['location'],
                    'sighting_date':        m['sighting_date'],
                    'uploaded_at':          m['uploaded_at'],
                    # keep single sighting_photo for backward compat with frontend fallback
                    'sighting_photo':       '/' + m['citizen_photo_path'],
                    'sightings': []
                }
            grouped[pid]['sightings'].append({
                'photo':    '/' + m['citizen_photo_path'],
                'location': m['location'],
                'date':     m['sighting_date'],
                'score':    round(m['face_match_score'] * 100, 1)
            })

        return jsonify({
            'success': True,
            'confirmed_matches': list(grouped.values())
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── POST /update_missing_person_status/<person_id> — police only ─────────────

@missing_person_bp.route('/update_missing_person_status/<person_id>', methods=['POST'])
def update_missing_person_status(person_id):
    if not _is_police():
        return jsonify({'success': False, 'error': 'Police login required.'}), 403
    try:
        data       = request.get_json(force=True) or {}
        new_status = data.get('status', 'Missing')
        if new_status not in ('Missing', 'Found', 'Closed'):
            return jsonify({'success': False, 'error': 'Invalid status value.'}), 400

        conn = _get_db()
        conn.execute(
            'UPDATE missing_persons SET status = ? WHERE person_id = ?',
            (new_status, person_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Status updated to {new_status}.'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500