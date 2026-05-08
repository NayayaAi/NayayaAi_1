# Legal API routes: districts, police stations, acts, sections, and section search

import sqlite3
from flask import Blueprint, request, jsonify
from main.config import INDIAN_DISTRICTS, SAMPLE_POLICE_STATIONS, LEGAL_ACTS
from main.database import DB_PATH

legal_bp = Blueprint('legal', __name__)


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


@legal_bp.route('/api/districts', methods=['GET'])
def get_districts():
    """Return list of Indian districts."""
    return jsonify(sorted(INDIAN_DISTRICTS))


@legal_bp.route('/api/police-stations/<district>', methods=['GET'])
def get_police_stations(district):
    """Return police stations for a district."""
    stations = SAMPLE_POLICE_STATIONS.get(district, [f"{district} PS"])
    return jsonify(stations)


@legal_bp.route('/api/acts', methods=['GET'])
def get_acts():
    """Return available legal acts."""
    return jsonify(LEGAL_ACTS)


@legal_bp.route('/api/sections/<act>', methods=['GET'])
def get_sections(act):
    """Return sections for a specific act."""
    sections = get_sections_for_act(act)
    return jsonify(sections)


@legal_bp.route('/api/search-sections', methods=['GET'])
def search_sections():
    """Search sections across all acts by keyword."""
    query = request.args.get('q', '').lower()
    if not query or len(query) < 2:
        return jsonify([])

    results = []
    for act in LEGAL_ACTS:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT Section, section_title FROM {act} WHERE lower(section_title) LIKE ? OR lower(section_desc) LIKE ? LIMIT 10",
                (f"%{query}%", f"%{query}%")
            )
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    "act": act,
                    "section": row[0],
                    "title": row[1]
                })
            conn.close()
        except Exception as e:
            print(f"Error searching sections: {e}")

    return jsonify(results[:20])
