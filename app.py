"""
app.py — Think4U Launch Page
Flask application: public launch page + secure admin dashboard.
"""

import os
import time
import secrets
import functools
import logging
from datetime import datetime, timezone

import bcrypt
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort, make_response
)
from dotenv import load_dotenv

from config import load_config, save_config

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
log = logging.getLogger("think4u.launch")

app = Flask(__name__, static_folder="public", static_url_path="")
configured_secret = os.environ.get("SECRET_KEY", "").strip()
app.secret_key = configured_secret or secrets.token_hex(32)
if not configured_secret and os.environ.get("VERCEL"):
    log.warning("SECRET_KEY is unset in Vercel. The public page remains available, but admin sessions will not survive function restarts. Set a stable SECRET_KEY in Project Settings.")

same_site_input = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax").strip().strip("\"'").lower()
same_site_values = {"lax": "Lax", "strict": "Strict", "none": "None"}
session_same_site = same_site_values.get(same_site_input, "Lax")
if same_site_input not in same_site_values:
    log.warning("Invalid SESSION_COOKIE_SAMESITE value; using Lax.")

# Session cookie security
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=session_same_site,
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour admin sessions
)

_launch_tokens: dict[str, float] = {}
_launch_requests: dict[str, list[float]] = {}
LAUNCH_TOKEN_TTL = 900
LAUNCH_RATE_WINDOW = 60
LAUNCH_RATE_LIMIT = 5

# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["X-XSS-Protection"] = "1; mode=block"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return resp

# ---------------------------------------------------------------------------
# Rate-limiting store for login attempts (in-memory, resets on restart)
# ---------------------------------------------------------------------------
_login_attempts: dict[str, dict] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS    = 900  # 15 minutes


def _get_client_ip() -> str:
    """Use the socket peer address; forwarded headers are client-spoofable."""
    return request.remote_addr or "unknown"


def _is_locked_out(ip: str) -> tuple[bool, int]:
    """Return (is_locked, seconds_remaining)."""
    record = _login_attempts.get(ip)
    if not record:
        return False, 0
    if record["count"] < MAX_LOGIN_ATTEMPTS:
        return False, 0
    elapsed = time.time() - record["last_attempt"]
    remaining = int(LOCKOUT_SECONDS - elapsed)
    if remaining <= 0:
        del _login_attempts[ip]
        return False, 0
    return True, remaining


def _record_failed_attempt(ip: str):
    now = time.time()
    if ip not in _login_attempts:
        _login_attempts[ip] = {"count": 0, "last_attempt": now}
    _login_attempts[ip]["count"] += 1
    _login_attempts[ip]["last_attempt"] = now


def _clear_attempts(ip: str):
    _login_attempts.pop(ip, None)

# ---------------------------------------------------------------------------
# Admin authentication helpers
# ---------------------------------------------------------------------------
def _check_credentials(username: str, password: str) -> bool:
    """Verify username+password against env-stored bcrypt hash."""
    expected_user = os.environ.get("ADMIN_USERNAME", "admin")
    stored_hash   = os.environ.get("ADMIN_PASSWORD_HASH", "")
    if not stored_hash:
        log.warning("ADMIN_PASSWORD_HASH not set in environment — login disabled.")
        return False
    if username != expected_user:
        return False
    try:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except Exception:
        return False


def admin_required(f):
    """Decorator: require admin session."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def _generate_csrf() -> str:
    """Create/retrieve a CSRF token for this session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


def _validate_csrf(token: str) -> bool:
    return secrets.compare_digest(session.get("csrf_token", ""), token)


def _allow_launch_request(ip: str) -> bool:
    """Limit repeated launch handshakes from a client IP."""
    now = time.time()
    recent = [stamp for stamp in _launch_requests.get(ip, []) if now - stamp < LAUNCH_RATE_WINDOW]
    if not recent:
        _launch_requests.pop(ip, None)
    if len(recent) >= LAUNCH_RATE_LIMIT:
        _launch_requests[ip] = recent
        return False
    recent.append(now)
    _launch_requests[ip] = recent
    return True


def _launch_response(config: dict):
    now = time.time()
    for old_token, expires_at in list(_launch_tokens.items()):
        if expires_at <= now:
            _launch_tokens.pop(old_token, None)
    token = secrets.token_urlsafe(32)
    _launch_tokens[token] = now + LAUNCH_TOKEN_TTL
    context = _build_page_context(config)
    context["launch_token"] = token
    response = make_response(render_template("launch.html", **context))
    response.set_cookie("launch_token", token, httponly=True, secure=app.config["SESSION_COOKIE_SECURE"], samesite="Lax", max_age=LAUNCH_TOKEN_TTL)
    return response

# ---------------------------------------------------------------------------
# Context processor — make csrf token available in all templates
# ---------------------------------------------------------------------------
@app.context_processor
def inject_globals():
    return {
        "csrf_token": _generate_csrf(),
        "current_year": datetime.now(timezone.utc).year,
    }

# ---------------------------------------------------------------------------
# PUBLIC ROUTES
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the launch page; visitors leave only after pressing its button."""
    config = load_config()
    resp = _launch_response(config)
    # No-cache so status changes reflect immediately
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.post("/launch/authorize")
def authorize_launch():
    """Consume a one-use launch token before showing launch animation."""
    token = request.headers.get("X-Launch-Token", "")
    cookie_token = request.cookies.get("launch_token", "")
    if not token or not cookie_token or not secrets.compare_digest(token, cookie_token):
        return jsonify({"success": False, "message": "Invalid launch session."}), 403
    expires = _launch_tokens.pop(token, None)
    if not expires or expires < time.time():
        return jsonify({"success": False, "message": "This launch action has expired or was already used."}), 409
    if not _allow_launch_request(_get_client_ip()):
        return jsonify({"success": False, "message": "Please wait before trying again."}), 429
    if not load_config().get("launch", {}).get("launch_button_enabled", True):
        return jsonify({"success": False, "message": "The launch action is currently unavailable."}), 403
    response = jsonify({"success": True, "redirect_url": "https://think4u.org"})
    response.delete_cookie("launch_token")
    return response


def _build_page_context(config: dict) -> dict:
    """Flatten config into a clean template context dict."""
    b = config.get("branding", {})
    h = config.get("hero", {})
    lc = config.get("launch", {})
    co = config.get("content", {})
    se = config.get("seo", {})

    return {
        # Branding
        "org_name":      b.get("org_name", "Think4U Trust"),
        "tagline":       b.get("tagline", ""),
        "primary_color": b.get("primary_color", "#1f0606"),
        "accent_color":  b.get("accent_color", "#d58d4b"),
        "logo_url":      b.get("logo_url", "/images/logo-white.png"),
        "favicon_url":   b.get("favicon_url", "/images/favicon.ico"),
        # Hero
        "headline":          h.get("headline", "A More Meaningful Future Begins Here."),
        "description":       h.get("description", ""),
        "cta_primary_text":  h.get("cta_primary_text", "LAUNCH THINK4U"),
        "redirect_url":         lc.get("redirect_url", "https://think4u.org"),
        "redirect_delay":       15,
        "launch_button_enabled":lc.get("launch_button_enabled", True),
        # Content
        "mission_text":    co.get("mission_text", ""),
        "contact_email":   co.get("contact_email", ""),
        "contact_phone":   co.get("contact_phone", ""),
        "contact_address": co.get("contact_address", ""),
        "social_links":    co.get("social_links", {}),
        # SEO
        "page_title":       se.get("page_title", "Think4U Trust — Official Launch"),
        "meta_description": se.get("meta_description", ""),
        "og_image_url":     se.get("og_image_url", ""),
        "og_title":         se.get("og_title", ""),
        "og_description":   se.get("og_description", ""),
    }

# ---------------------------------------------------------------------------
# ADMIN ROUTES
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Secure admin login with rate-limiting and CSRF."""
    ip = _get_client_ip()
    locked, remaining = _is_locked_out(ip)

    if locked:
        flash(f"Too many failed attempts. Try again in {remaining // 60}m {remaining % 60}s.", "error")
        return render_template("admin/login.html", locked=True, remaining=remaining), 429

    if request.method == "POST":
        # CSRF check
        if not _validate_csrf(request.form.get("csrf_token", "")):
            abort(403)

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if _check_credentials(username, password):
            _clear_attempts(ip)
            session.clear()
            session["admin_logged_in"] = True
            session["admin_user"] = username
            session.permanent = True
            log.info("Admin login success from %s", ip)
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/admin"):
                return redirect(next_url)
            return redirect(url_for("admin_dashboard"))
        else:
            _record_failed_attempt(ip)
            locked, remaining = _is_locked_out(ip)
            log.warning("Admin login failure from %s (attempt %d)", ip,
                        _login_attempts.get(ip, {}).get("count", 0))
            if locked:
                flash(f"Account locked for {remaining // 60}m {remaining % 60}s.", "error")
                return render_template("admin/login.html", locked=True, remaining=remaining), 429
            flash("Invalid credentials. Please try again.", "error")

    return render_template("admin/login.html", locked=False, remaining=0)


@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@app.route("/admin/")
@admin_required
def admin_redirect():
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    config = load_config()
    ctx = {
        "config":           config,
        "admin_user":       session.get("admin_user", "admin"),
    }
    return render_template("admin/dashboard.html", **ctx)


@app.route("/admin/save", methods=["POST"])
@admin_required
def admin_save():
    """Save configuration submitted from the admin dashboard."""
    if not _validate_csrf(request.form.get("csrf_token", "")):
        return jsonify({"success": False, "message": "Invalid CSRF token."}), 403

    form = request.form

    # ---------- Build config dict from form ----------
    new_config = {
        "branding": {
            "org_name":      form.get("org_name", "").strip(),
            "tagline":       form.get("tagline", "").strip(),
            "primary_color": form.get("primary_color", "#1f0606").strip(),
            "accent_color":  form.get("accent_color", "#d58d4b").strip(),
            "logo_url":      form.get("logo_url", "").strip(),
            "favicon_url":   form.get("favicon_url", "").strip(),
        },
        "hero": {
            "headline":           form.get("headline", "").strip(),
            "description":        form.get("description", "").strip(),
            "cta_primary_text":   form.get("cta_primary_text", "").strip(),
        },
        "launch": {
            "launch_button_enabled": form.get("launch_button_enabled") == "true",
            "redirect_url":          "https://think4u.org",
            "redirect_delay_seconds":15,
        },
        "content": {
            "mission_text":    form.get("mission_text", "").strip(),
            "contact_email":   form.get("contact_email", "").strip(),
            "contact_phone":   form.get("contact_phone", "").strip(),
            "contact_address": form.get("contact_address", "").strip(),
            "social_links": {
                "facebook":  form.get("social_facebook", "").strip(),
                "instagram": form.get("social_instagram", "").strip(),
                "twitter":   form.get("social_twitter", "").strip(),
                "linkedin":  form.get("social_linkedin", "").strip(),
                "youtube":   form.get("social_youtube", "").strip(),
            }
        },
        "seo": {
            "page_title":       form.get("page_title", "").strip(),
            "meta_description": form.get("meta_description", "").strip(),
            "og_image_url":     form.get("og_image_url", "").strip(),
            "og_title":         form.get("og_title", "").strip(),
            "og_description":   form.get("og_description", "").strip(),
        }
    }

    success, message = save_config(new_config)
    if success:
        log.info("Admin saved launch page configuration")
    else:
        log.error("Admin config save failed: %s", message)

    return jsonify({"success": success, "message": message})


@app.route("/admin/preview")
@admin_required
def admin_preview():
    """Render the public launch page for in-admin preview."""
    config = load_config()
    return _launch_response(config)

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template("admin/login.html", error="Access denied.", locked=False, remaining=0), 403


@app.errorhandler(404)
def not_found(e):
    return "<h2 style='font-family:sans-serif;text-align:center;margin-top:4rem'>Page not found.</h2>", 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    host  = os.environ.get("FLASK_HOST", "127.0.0.1")
    port  = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    log.info("Starting Think4U Launch Page on %s:%s (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
