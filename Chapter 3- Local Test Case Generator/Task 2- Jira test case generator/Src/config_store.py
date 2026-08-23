import json
import os
from pathlib import Path

from dotenv import load_dotenv

from jira_client import normalize_jira_base_url

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
CONFIG_PATH = BASE_DIR / "settings.json"

load_dotenv(dotenv_path=ENV_PATH, override=False)

DEFAULT_SETTINGS = {
    "jira_url": os.getenv("JIRA_URL", ""),
    "jira_email": os.getenv("JIRA_EMAIL", ""),
    "jira_api_token": os.getenv("JIRA_API_TOKEN", ""),
    "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
    "ollama_model": os.getenv("OLLAMA_MODEL", "gemma3:1b"),
    "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
    "groq_api_key": os.getenv("GROQ_API_KEY", ""),
    "groq_model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
}


def load_settings():
    """Load persisted settings and merge in any .env default values."""
    settings = dict(DEFAULT_SETTINGS)

    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as handle:
                stored_settings = json.load(handle)
            if isinstance(stored_settings, dict):
                settings.update(stored_settings)
        except Exception:
            settings = dict(DEFAULT_SETTINGS)

    # Ensure provider falls back safely to ollama if blank.
    if not settings.get("llm_provider"):
        settings["llm_provider"] = "ollama"

    if settings.get("jira_url"):
        settings["jira_url"] = normalize_jira_base_url(settings["jira_url"])

    return settings


def save_settings(settings):
    """Write JSON settings file containing Jira credentials and LLM provider selection."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)

    return settings


def get_setting(key, default=None):
    settings = load_settings()
    return settings.get(key, default)
