# General routes: home page and health check

from flask import Blueprint, render_template, redirect, url_for, session

general_bp = Blueprint('general', __name__)


@general_bp.route('/', methods=['GET'])
def home():
    if 'user_id' in session:
        return render_template('index.html')
    return redirect(url_for('auth.signup'))


@general_bp.route('/health', methods=['GET'])
def health():
    from flask import jsonify
    return jsonify({"status": "ok", "message": "Nyaya AI engine reachable"}), 200
