"""
config.py — Think4U Launch Page Configuration Manager
Handles loading, saving, and validating the launch_config.json file.
"""

import json
import os
import pytz
from datetime import datetime
from copy import deepcopy

# Absolute path to the config file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "data", "launch_config.json")

# ---------------------------------------------------------------------------
# Default configuration — used when no config file exists yet
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "branding": {
        "org_name": "Think4U Trust",
        "tagline": "Empowering Communities, Transforming Lives",
        "primary_color": "#1f0606",
        "accent_color": "#d58d4b",
        "logo_url": "/static/images/logo-white.png",
        "favicon_url": "/static/images/favicon.ico"
    },
    "hero": {
        "headline": "A More Meaningful Future Begins Here.",
        "description": (
            "Think4U Trust is a registered charitable organisation dedicated to "
            "education, health, and community upliftment. We are preparing something "
            "extraordinary — a digital platform to connect compassion with action."
        ),
        "cta_primary_text": "LAUNCH THINK4U",
        "cta_primary_url": "#contact",
        "cta_secondary_text": "Learn About Think4U",
        "cta_secondary_url": "https://think4u.org",
        "hero_image_url": ""
    },
    "launch": {
        "launch_date": "2027-01-26",
        "launch_time": "09:00",
        "timezone": "Asia/Kolkata",
        "launch_status": "coming_soon",   # 'coming_soon' | 'launched'
        "countdown_visible": True,
        "launch_button_enabled": True,
        "auto_redirect": False,
        "redirect_url": "https://think4u.org",
        "redirect_delay_seconds": 1.7,
        "animation_style": "orbit"
    },
    "content": {
        "mission_text": (
            "At Think4U Trust, we believe every act of kindness has the power to "
            "change lives. Our mission is to build bridges between those who want to "
            "give and those who need support — through education, healthcare, food "
            "security, and community development programmes."
        ),
        "contact_email": "info@think4u.org",
        "contact_phone": "+91 XXXXX XXXXX",
        "contact_address": "Hyderabad, Telangana, India",
        "social_links": {
            "facebook": "https://facebook.com/think4utrust",
            "instagram": "https://instagram.com/think4utrust",
            "twitter": "https://twitter.com/think4utrust",
            "linkedin": "https://linkedin.com/company/think4utrust",
            "youtube": ""
        }
    },
    "seo": {
        "page_title": "Think4U Trust — Official Launch",
        "meta_description": (
            "Think4U Trust is launching a new platform to connect communities, "
            "support education, health, and social impact across India. "
            "Discover the mission and launch of Think4U Trust."
        ),
        "og_image_url": "/static/images/og-image.png",
        "og_title": "Think4U Trust — Official Launch",
        "og_description": (
            "A new chapter in community-driven social impact. "
            "Meet Think4U Trust. Our journey starts here."
        )
    }
}


def load_config() -> dict:
    """Load config from JSON, merging with defaults for any missing keys."""
    config = deepcopy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Deep-merge saved values over defaults
            for section, values in saved.items():
                if section in config and isinstance(values, dict):
                    config[section].update(values)
                else:
                    config[section] = values
        except (json.JSONDecodeError, IOError):
            pass  # Fall back to defaults on corrupt/missing file
    return config


def save_config(data: dict) -> tuple[bool, str]:
    """
    Validate and save configuration to JSON file.
    Returns (success: bool, message: str).
    """
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

        # Basic validation
        launch = data.get("launch", {})
        tz_name = launch.get("timezone", "Asia/Kolkata")
        try:
            pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            return False, f"Unknown timezone: {tz_name}"

        # Validate date/time format
        launch_date = launch.get("launch_date", "")
        launch_time = launch.get("launch_time", "")
        try:
            datetime.strptime(f"{launch_date} {launch_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return False, "Invalid launch date or time format."

        # Only the user-initiated launch button may navigate visitors away.
        if launch.get("launch_status") not in ("coming_soon", "launched"):
            return False, "Invalid launch_status value."

        redirect_url = launch.get("redirect_url", "")
        if redirect_url != "https://think4u.org":
            return False, "The launch destination must be https://think4u.org."

        try:
            delay = float(launch.get("redirect_delay_seconds", 1.7))
            if not 1.2 <= delay <= 2.5:
                return False, "Launch animation duration must be between 1.2 and 2.5 seconds."
        except (TypeError, ValueError):
            return False, "Invalid launch animation duration."

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True, "Configuration saved successfully."
    except Exception as e:
        return False, f"Failed to save configuration: {e}"


def get_launch_status(config: dict) -> str:
    """Return 'coming_soon' or 'launched'."""
    return config.get("launch", {}).get("launch_status", "coming_soon")


def get_countdown_target_utc(config: dict) -> str:
    """
    Return the launch datetime as a UTC ISO 8601 string for the JS countdown.
    E.g. '2027-01-26T03:30:00Z'
    """
    launch = config.get("launch", {})
    date_str = launch.get("launch_date", "2027-01-26")
    time_str = launch.get("launch_time", "09:00")
    tz_name  = launch.get("timezone", "Asia/Kolkata")

    try:
        tz = pytz.timezone(tz_name)
        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        local_dt = tz.localize(naive_dt)
        utc_dt   = local_dt.astimezone(pytz.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        # Safe fallback
        return "2027-01-26T03:30:00Z"


def get_display_launch_datetime(config: dict) -> str:
    """
    Return a human-readable launch datetime string for display on the page.
    E.g. '26 January 2027 at 9:00 AM IST'
    """
    launch = config.get("launch", {})
    date_str = launch.get("launch_date", "2027-01-26")
    time_str = launch.get("launch_time", "09:00")
    tz_name  = launch.get("timezone", "Asia/Kolkata")

    try:
        tz = pytz.timezone(tz_name)
        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        local_dt = tz.localize(naive_dt)
        tz_abbr  = local_dt.strftime("%Z")
        # Use %d/%I and strip leading zero (cross-platform, works on Windows too)
        day  = str(local_dt.day)
        hour = str(local_dt.hour % 12 or 12)
        ampm = local_dt.strftime("%p")
        mins = local_dt.strftime("%M")
        month_year = local_dt.strftime("%B %Y")
        return f"{day} {month_year} at {hour}:{mins} {ampm} {tz_abbr}"
    except Exception:
        return f"{date_str} at {time_str} ({tz_name})"


# Common timezones list for the admin dropdown
COMMON_TIMEZONES = [
    ("Asia/Kolkata",       "Asia/Kolkata (IST, UTC+5:30)"),
    ("UTC",                "UTC"),
    ("Asia/Dubai",         "Asia/Dubai (GST, UTC+4)"),
    ("Asia/Singapore",     "Asia/Singapore (SGT, UTC+8)"),
    ("Asia/Tokyo",         "Asia/Tokyo (JST, UTC+9)"),
    ("Asia/Shanghai",      "Asia/Shanghai (CST, UTC+8)"),
    ("Europe/London",      "Europe/London (GMT/BST)"),
    ("Europe/Paris",       "Europe/Paris (CET/CEST)"),
    ("Europe/Berlin",      "Europe/Berlin (CET/CEST)"),
    ("America/New_York",   "America/New_York (ET)"),
    ("America/Chicago",    "America/Chicago (CT)"),
    ("America/Denver",     "America/Denver (MT)"),
    ("America/Los_Angeles","America/Los_Angeles (PT)"),
    ("America/Sao_Paulo",  "America/Sao_Paulo (BRT)"),
    ("Australia/Sydney",   "Australia/Sydney (AEST/AEDT)"),
    ("Pacific/Auckland",   "Pacific/Auckland (NZST/NZDT)"),
]
