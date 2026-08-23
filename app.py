"""
MindCare Navigator - Flask Application Entry Point
Clean initialization with blueprint registration.
"""

# Python 3.10+ compatibility patch
import collections
import collections.abc
for _name in ("MutableMapping", "Mapping", "Sequence", "Iterable", "Callable"):
    if not hasattr(collections, _name):
        setattr(collections, _name, getattr(collections.abc, _name))

import logging
import os
from flask import Flask, jsonify, request, render_template, send_from_directory

import backend.database.db as db
from backend.config import FLASK_DEBUG, SERVER_PORT
from backend.routes import auth_bp, chat_bp, psychologist_bp, community_bp

log = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder="static", static_url_path="")

# Explicit static file route (needed for Vercel serverless)
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(os.path.join(app.root_path, "static"), filename)

# Register API blueprints (no URL prefix)
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(psychologist_bp)
app.register_blueprint(community_bp)


# ---------------------------------------------------------------------------
# Page routes (kept here to preserve url_for endpoint names in templates)
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/features")
def features():
    return render_template("features.html")


@app.route("/locator")
def locator():
    return render_template("locator.html")


@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/login")
@app.route("/login.html")
def login_page():
    return render_template("login.html")


@app.route("/register")
@app.route("/register.html")
def register_page():
    return render_template("register.html")


@app.route("/psychologist-list")
@app.route("/psychologist-list.html")
def psychologist_list():
    return render_template("psychologist-list.html")


@app.route("/psychologist-chat")
@app.route("/psychologist-chat.html")
def psychologist_chat():
    return render_template("psychologist-chat.html")


@app.route("/psychologist-dashboard")
@app.route("/psychologist-dashboard.html")
def psychologist_dashboard():
    return render_template("psychologist-dashboard.html")


@app.route("/community")
def community_page():
    return render_template("community.html")


@app.route("/api/contact", methods=["POST"])
def contact_api():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    if not name or not email or not message:
        return jsonify({"error": "Missing fields"}), 400

    log.info("Contact form: %s (%s)", name, email)
    return jsonify({"success": "Message sent successfully"})


# ---------------------------------------------------------------------------
# CORS support
# ---------------------------------------------------------------------------

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------

try:
    if db.check_connection():
        db.ensure_schema()
        log.info("Database schema verified.")
except Exception as e:
    log.warning("Schema initialization failed: %s", e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, port=SERVER_PORT)
