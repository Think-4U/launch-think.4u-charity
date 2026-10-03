"""
config.py — Think4U Launch Page Configuration Manager
Handles loading, saving, and validating the launch_config.json file.
"""

import json
import os
from copy import deepcopy

# Absolute path to the config file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = (
    os.path.join("/tmp", "think4u-launch-config.json")
    if os.environ.get("VERCEL")
    else os.path.join(BASE_DIR, "data", "launch_config.json")
)
CONFIG_PATH = os.environ.get("DATA_PATH", DEFAULT_CONFIG_PATH)

# ---------------------------------------------------------------------------
# Default configuration — used when no config file exists yet
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "branding": {
        "org_name": "Think4U Trust",
        "tagline": "Empowering Communities, Transforming Lives",
        "primary_color": "#1f0606",
        "accent_color": "#d58d4b",
        "logo_url": "/images/logo-white.png",
        "favicon_url": "/images/favicon.ico"
    },
    "hero": {
        "headline": "A More Meaningful Future Begins Here.",
        "description": (
            "Think4U Trust is a registered charitable organisation dedicated to "
            "education, health, and community upliftment. We are preparing something "
            "extraordinary — a digital platform to connect compassion with action."
        ),
        "cta_primary_text": "LAUNCH THINK4U",
    },
    "launch": {
        "launch_button_enabled": True,
        "redirect_url": "https://think4u.org",
        "redirect_delay_seconds": 15
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
        "og_image_url": "/images/logo-white.png",
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
        redirect_url = launch.get("redirect_url", "")
        if redirect_url != "https://think4u.org":
            return False, "The launch destination must be https://think4u.org."

        try:
            delay = float(launch.get("redirect_delay_seconds", 15))
            if delay != 15:
                return False, "The success screen redirect countdown is fixed at 15 seconds."
        except (TypeError, ValueError):
            return False, "Invalid automatic redirect delay."

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True, "Configuration saved successfully."
    except Exception as e:
        return False, f"Failed to save configuration: {e}"
