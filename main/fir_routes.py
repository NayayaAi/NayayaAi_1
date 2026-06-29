# FIR routes: generate FIR, retrieve FIR records, PDF generation

import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from ai_engine import analyze_complaint_for_sections
from main.config import PDF_FOLDER
from main.storage_service import upload_pdf, save_fir, fir_exists, get_all_firs, get_fir

fir_bp = Blueprint('fir', __name__)


@fir_bp.route('/api/fir-records', methods=['GET'])
def get_fir_records():
    """Get all FIR records."""
    try:
        fir_records = []
        for fir in get_all_firs():
            fir_records.append(fir)
        return jsonify(fir_records)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve FIR records", "details": str(e)}), 500


@fir_bp.route('/api/fir-records/<fir_no>', methods=['GET'])
def get_fir_record(fir_no):
    """Get a specific FIR by FIR number."""
    try:
        fir = get_fir(fir_no)
        if fir:
            return jsonify(fir)
        else:
            return jsonify({"error": f"FIR record {fir_no} not found"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to retrieve FIR record", "details": str(e)}), 500


@fir_bp.route('/generate_fir', methods=['POST'])
def generate_fir():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    complaint_text = data.get("statement", "")

    
    if not data.get("act_sections"):
        ai_suggested_sections = analyze_complaint_for_sections(complaint_text)
        data["act_sections"] = ", ".join(ai_suggested_sections)

    try:
        # Check for duplicate FIR number
        if fir_exists(fir_no):
            return jsonify({"error": f"FIR number {data.get('fir_no')} already exists"}), 400

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

        # Generate PDF
        pdf_filename = f"FIR_{data.get('fir_no')}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)

        styles = getSampleStyleSheet()
        elements = []
        for line in formatted_fir.split("\n"):
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 5))

        pdf = SimpleDocTemplate(pdf_path)
        pdf.build(elements)

       
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
            "created_at": datetime.now(timezone.utc),
            "status": "Saved to Police Records"
        }

        save_fir(fir_document)

        fir_response = fir_document.copy()
        fir_response.pop("_id", None)
        fir_response["created_at"] = str(fir_response["created_at"])
        fir_response["formatted_fir"] = formatted_fir.strip()
        fir_response["message"] = "FIR has been successfully registered and saved to police records."

        return jsonify(fir_response)

    except Exception as e:
        return jsonify({"error": "Failed to save FIR to database", "details": str(e)}), 500
