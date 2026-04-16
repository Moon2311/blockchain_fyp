"""
Flask application — REST API for the React SPA + optional static SPA hosting.

Run API (development, with Vite on :5173):
    cd backend && python app.py

Production (after `npm run build` in web/):
    The same server can serve web/dist at / while /api/* stays JSON.
"""

import os

from flask import Flask, send_from_directory
from flask_cors import CORS

from api_routes import api_bp
from blockchain_utils import blockchain_status
from database import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
WEB_DIST = os.path.join(ROOT_DIR, "web", "dist")

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "fyp-blockchain-custody-secret-2024"
)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

init_db()

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5000",
                "http://127.0.0.1:5000",
            ],
            "supports_credentials": True,
        }
    },
)

app.register_blueprint(api_bp)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    """Serve the React production build when `web/dist` exists."""
    if not os.path.isdir(WEB_DIST):
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>ChainCustody API</title></head>"
            "<body style='font-family:system-ui;max-width:40rem;margin:3rem auto;padding:0 1rem;'>"
            "<h1>Backend API is running</h1>"
            "<p>Start the React UI with <code>cd web && npm install && npm run dev</code> "
            "(Vite proxies <code>/api</code> to this server).</p>"
            "<p>Or build the SPA: <code>cd web && npm run build</code>, then reload — "
            "this server will serve <code>web/dist</code>.</p>"
            "</body></html>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    target = os.path.join(WEB_DIST, path) if path else None
    if path and os.path.isfile(target):
        return send_from_directory(WEB_DIST, path)
    return send_from_directory(WEB_DIST, "index.html")


if __name__ == "__main__":
    print("=" * 60)
    print("  Blockchain Chain of Custody – Flask API")
    print("  FYP by M. Talha  |  fa-2022/BS/DFCS/075")
    print("=" * 60)
    bs = blockchain_status()
    print(f"  Ganache connected : {bs['connected']}")
    print(f"  Contract deployed : {bs['deployed']}")
    if not bs["connected"]:
        print("  ⚠  Start Ganache on port 7545 first!")
    if not bs["deployed"]:
        print("  ⚠  Run  python deploy.py  to deploy the contract.")
    print("  API: http://127.0.0.1:5000/api/…")
    print("  UI:  cd ../web && npm run dev  →  http://127.0.0.1:5173")
    print("=" * 60)
    app.run(debug=True, port=5000)
