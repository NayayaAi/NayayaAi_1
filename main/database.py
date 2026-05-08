# Database connections and table initialization for SQLite and MongoDB

import sqlite3
import os
from pymongo import MongoClient

# Resolve path to IndiaLaw.db from project root (parent of main/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "IndiaLaw.db")

# MongoDB connection
try:
    client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
    mongo_db = client["NyayaAI_DB"]
    users_collection = mongo_db["users"]
    fir_collection = mongo_db["fir_records"]
    client.server_info()
except Exception as e:
    print(f"ERROR: MongoDB connection failed: {e}")


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
