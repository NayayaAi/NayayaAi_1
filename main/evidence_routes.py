# Evidence routes: file upload for FIR evidence and locker access verification

import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

evidence_bp = Blueprint('evidence', __name__)


@evidence_bp.route('/upload_evidence/<fir_no>', methods=['POST'])
def upload_evidence(fir_no):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(f"{fir_no}_{file.filename}")
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    return jsonify({"message": f"Evidence uploaded successfully for FIR {fir_no}", "file_path": file_path})


@evidence_bp.route('/verify-locker-access', methods=['POST'])
def verify_locker_access():
    try:
        data = request.get_json()
        pin = data.get("pin")

        # Static password for locker access
        if pin == "secure@123":
            return jsonify({"success": True, "message": "Access Granted"})
        else:
            return jsonify({"success": False, "message": "Wrong Password ❌"}), 401

    except Exception as e:
        return jsonify({"success": False, "message": "Server Error", "error": str(e)}), 500
