"""
utils.py — Utility functions for LankAmerica Compass
"""
import os
import json
from pathlib import Path


def format_currency(amount: float) -> str:
    """Format a float as a currency string, e.g. $1,234.56 or -$1,234.56"""
    if amount is None:
        amount = 0.0
    negative = amount < 0
    abs_val = abs(amount)
    formatted = f"${abs_val:,.2f}"
    if negative:
        formatted = f"-{formatted}"
    return formatted


def parse_currency(text: str) -> float:
    """Parse a currency string into a float. Handles $, commas, negatives."""
    if not text:
        return 0.0
    text = text.strip().replace('$', '').replace(',', '').replace(' ', '')
    try:
        return float(text)
    except ValueError:
        return 0.0


def get_sync_provider(path: str) -> str:
    """Infer cloud sync provider from the file path."""
    if not path:
        return "Local"
    path_lower = path.lower().replace('\\', '/')
    if 'onedrive' in path_lower:
        return "OneDrive"
    if 'google drive' in path_lower or 'googledrive' in path_lower or 'gdrive' in path_lower:
        return "Google Drive"
    if 'dropbox' in path_lower:
        return "Dropbox"
    if 'nextcloud' in path_lower:
        return "Nextcloud"
    return "Local"


def get_db_default_path() -> str:
    """Return the default compass.db path under ~/Documents/LankAmericaCompass/"""
    docs = Path.home() / "Documents" / "LankAmericaCompass"
    docs.mkdir(parents=True, exist_ok=True)
    return str(docs / "compass.db")


CONFIG_PATH = Path.home() / ".lankamerica_config.json"


def load_config() -> dict:
    """Load config from ~/.lankamerica_config.json"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: dict) -> None:
    """Save config to ~/.lankamerica_config.json"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def get_assets_dir() -> Path:
    """Return the assets/ directory relative to the application root."""
    here = Path(__file__).resolve().parent.parent
    return here / "assets"
