"""
FeirasWallet — Flask application entry point.

Implements W3C Verifiable Credentials + DID:KEY for farmer market access.
The association issues short-lived VendorAccessCredentials (24-48h) to
registered farmers. Verification works 100% offline via DID:KEY resolution.

Usage:
    python app.py
"""

import base64
import os

from flask import Flask, jsonify, redirect
from flask_cors import CORS

from config import config


def setup_association_keys() -> None:
    """
    Bootstrap the association's DID:KEY from environment.
    If ASSOCIATION_PRIVATE_KEY_B64 is not set, generate a new key
    and print instructions. Stores key bytes and DID in config at runtime.
    """
    from utils.did_key import generate_did_key, did_from_private_bytes

    priv_b64 = config.ASSOCIATION_PRIVATE_KEY_B64

    if priv_b64:
        priv_bytes = base64.b64decode(priv_b64)
        did = did_from_private_bytes(priv_bytes)
        config.ASSOCIATION_PRIVATE_KEY_BYTES = priv_bytes
        config.ASSOCIATION_DID = did
        print(f"Association DID:KEY loaded: {did}")
    else:
        print()
        print("WARNING: ASSOCIATION_PRIVATE_KEY_B64 not set in .env")
        print("Generating a temporary key for this session (not persisted).")
        print("Run 'python generate_keys.py' and add the key to .env for production.")
        print()
        did, priv_bytes = generate_did_key()
        config.ASSOCIATION_PRIVATE_KEY_BYTES = priv_bytes
        config.ASSOCIATION_DID = did
        print(f"Temporary DID:KEY: {did}")


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['ENV'] = config.ENV
    app.config['DEBUG'] = config.DEBUG

    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/verify/*": {"origins": "*"}
    })

    from routes.admin_routes import admin_bp
    from routes.farmer_routes import farmer_bp
    from routes.feira_routes import feira_bp
    from routes.wallet_routes import wallet_bp
    from routes.verifier_routes import verifier_bp
    from routes.api_routes import api_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(farmer_bp)
    app.register_blueprint(feira_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(verifier_bp)
    app.register_blueprint(api_bp)

    @app.route('/')
    def index():
        return redirect('/admin/')

    @app.route('/admin')
    def admin_redirect():
        return redirect('/admin/')

    @app.route('/health')
    def health():
        return jsonify({
            "status": "ok",
            "association_did": config.ASSOCIATION_DID
        })

    @app.errorhandler(404)
    def not_found(error):
        return redirect('/admin/')

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app


setup_association_keys()
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
