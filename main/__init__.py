# Registers all blueprints into the Flask app

from main.general_routes import general_bp
from main.auth_routes import auth_bp
from main.fir_routes import fir_bp
from main.evidence_routes import evidence_bp
from main.legal_routes import legal_bp


def register_blueprints(app):
    app.register_blueprint(general_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(fir_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(legal_bp)
