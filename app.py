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

from config import (
    load_config, save_config, get_launch_status,
    get_countdown_target_utc, get_display_launch_datetime,
    COMMON_TIMEZONES, DEFAULT_CONFIG
)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
log = logging.getLogger("think4u.launch")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Session cookie security
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour admin sessions
)

# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["X-XSS-Protection"] = "1; mode=block"
    return resp

# ---------------------------------------------------------------------------
# Rate-limiting store for login attempts (in-memory, resets on restart)
# ---------------------------------------------------------------------------
_login_attempts: dict[str, dict] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS    = 900  # 15 minutes


def _get_client_ip() -> str:
    """Get real IP, honouring common proxy headers."""
    return (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP", "")
        or request.remote_addr
        or "unknown"
    )


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
    ctx = _build_page_context(config)
    resp = make_response(render_template("launch.html", **ctx))
    # No-cache so status changes reflect immediately
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


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
        "logo_url":      b.get("logo_url", "/static/images/logo-white.png"),
        "favicon_url":   b.get("favicon_url", "/static/images/favicon.ico"),
        # Hero
        "headline":          h.get("headline", "A More Meaningful Future Begins Here."),
        "description":       h.get("description", ""),
        "cta_primary_text":  h.get("cta_primary_text", "LAUNCH THINK4U"),
        "cta_primary_url":   h.get("cta_primary_url", "#contact"),
        "cta_secondary_text":h.get("cta_secondary_text", "Learn About Think4U"),
        "cta_secondary_url": h.get("cta_secondary_url", "https://think4u.org"),
        "hero_image_url":    h.get("hero_image_url", ""),
        # Countdown
        "countdown_visible":    lc.get("countdown_visible", True),
        "countdown_target_utc": get_countdown_target_utc(config),
        "launch_display_dt":    get_display_launch_datetime(config),
        "auto_redirect":        lc.get("auto_redirect", False),
        "redirect_url":         lc.get("redirect_url", "https://think4u.org"),
        "redirect_delay":       lc.get("redirect_delay_seconds", 1.7),
        "launch_button_enabled":lc.get("launch_button_enabled", True),
        "timezone":             lc.get("timezone", "Asia/Kolkata"),
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
        "timezones":        COMMON_TIMEZONES,
        "launch_status":    get_launch_status(config),
        "countdown_target": get_countdown_target_utc(config),
        "launch_display_dt":get_display_launch_datetime(config),
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
            "cta_primary_url":    form.get("cta_primary_url", "").strip(),
            "cta_secondary_text": form.get("cta_secondary_text", "").strip(),
            "cta_secondary_url":  form.get("cta_secondary_url", "").strip(),
            "hero_image_url":     form.get("hero_image_url", "").strip(),
        },
        "launch": {
            "launch_date":           form.get("launch_date", "").strip(),
            "launch_time":           form.get("launch_time", "").strip(),
            "timezone":              form.get("timezone", "Asia/Kolkata").strip(),
            "launch_status":         form.get("launch_status", "coming_soon").strip(),
            "countdown_visible":     form.get("countdown_visible") == "true",
            "auto_redirect":         False,
            "launch_button_enabled": form.get("launch_button_enabled") == "true",
            "redirect_url":          "https://think4u.org",
            "redirect_delay_seconds":float(form.get("redirect_delay_seconds", 1.7) or 1.7),
            "animation_style":       form.get("animation_style", "orbit").strip(),
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
        log.info("Admin saved config. Launch status: %s", new_config["launch"]["launch_status"])
    else:
        log.error("Admin config save failed: %s", message)

    return jsonify({"success": success, "message": message})


@app.route("/admin/preview")
@admin_required
def admin_preview():
    """Render the public launch page for in-admin preview."""
    config = load_config()
    ctx = _build_page_context(config)
    ctx["is_preview"] = True
    return render_template("launch.html", **ctx)


@app.route("/admin/status")
@admin_required
def admin_status():
    """JSON endpoint returning current launch status (for live UI updates)."""
    config = load_config()
    return jsonify({
        "launch_status":    get_launch_status(config),
        "countdown_target": get_countdown_target_utc(config),
        "launch_display_dt":get_display_launch_datetime(config),
    })

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
