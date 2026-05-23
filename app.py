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
