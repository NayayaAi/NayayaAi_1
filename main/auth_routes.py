# Authentication routes: signup, login, logout, dashboard

import bcrypt
from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from main.database import users_collection

auth_bp = Blueprint('auth', __name__)


def generate_unique_id(role):
    """Generate unique ID based on role."""
    role_prefixes = {
        'police': 'POL',
        'citizen': 'CIT',
        'lawyer': 'LAW',
        'judge': 'JUD'
    }
    prefix = role_prefixes.get(role, 'USR')

    try:
        existing_users = users_collection.find({'role': role}).sort('unique_id', -1).limit(1)
        last_user = list(existing_users)
        if last_user:
            last_id = last_user[0]['unique_id']
            try:
                num = int(last_id[3:]) + 1
            except:
                num = 1
        else:
            num = 1
    except:
        num = 1

    return f"{prefix}{num:03d}"


@auth_bp.route('/signup', methods=['GET', 'POST'])
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

        if users_collection.find_one({'email': email}):
            return jsonify({"error": "Email already registered"}), 400

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        if role in ['police', 'lawyer', 'judge']:
            unique_id = data.get('unique_id', '').strip().upper()
            if not unique_id:
                return jsonify({"error": "Unique ID is required for police, lawyer, or judge"}), 400

            role_prefixes = {'police': 'POL', 'lawyer': 'LAW', 'judge': 'JUD'}
            expected_prefix = role_prefixes[role]
            if not unique_id.startswith(expected_prefix):
                return jsonify({"error": f"Unique ID for {role} must start with {expected_prefix}"}), 400

            if users_collection.find_one({'unique_id': unique_id}):
                return jsonify({"error": "Unique ID already registered"}), 400
        else:
            unique_id = generate_unique_id(role)

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


@auth_bp.route('/login', methods=['GET', 'POST'])
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

        session['user_id'] = str(user['_id'])
        session['role'] = user['role']
        session['unique_id'] = user['unique_id']

        return jsonify({
            "message": "Login successful",
            "role": user['role'],
            "unique_id": user['unique_id']
        }), 200

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('general.home'))


@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    return render_template('dashboard.html', user=user)
