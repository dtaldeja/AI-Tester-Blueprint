import re
from urllib.parse import quote, urlsplit, urlunsplit

import requests

def extract_jira_key(message):
    """Find a Jira key like QA-102 inside a natural-language prompt."""
    pattern = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
    matches = pattern.findall(message or "")
    return matches[0] if matches else None


def configured_issue_key(settings):
    """Return the issue key from a configured Jira browse URL, when present."""
    return extract_jira_key(settings.get("jira_url", ""))


def normalize_jira_base_url(value):
    """Convert a Jira site URL or browse URL into an API base URL."""
    raw_url = (value or "").strip()
    if not raw_url:
        return ""

    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Jira URL must include http:// or https:// and a hostname.")

    path = parsed.path.rstrip("/")
    rest_api_index = path.lower().find("/rest/api")
    browse_index = path.lower().find("/browse/")
    if rest_api_index >= 0:
        path = path[:rest_api_index]
    elif browse_index >= 0:
        path = path[:browse_index]

    return urlunsplit((parsed.scheme, parsed.netloc, path, "", "")).rstrip("/")


def fetch_jira_issue(issue_key, settings):
    """Fetch a Jira issue via REST API using stored credentials."""
    jira_url = normalize_jira_base_url(settings.get("jira_url"))
    jira_email = (settings.get("jira_email") or "").strip()
    jira_token = (settings.get("jira_api_token") or "").strip()

    if not jira_url or not jira_email or not jira_token:
        raise ValueError("Jira URL, Jira email, and Jira API token must be configured in Settings.")

    safe_issue_key = quote((issue_key or "").strip(), safe="-")
    url = f"{jira_url}/rest/api/3/issue/{safe_issue_key}?fields=summary,description,acceptancecriteria"

    response = requests.get(
        url,
        auth=(jira_email, jira_token),
        headers={"Accept": "application/json"},
        timeout=20,
    )

    if response.status_code != 200:
        if response.status_code == 404:
            raise RuntimeError(
                f"Jira could not access issue {issue_key}. Check that the issue key exists in "
                "this Jira site and that the configured account has Browse permission. "
                "Jira reports both missing issues and insufficient permissions as HTTP 404."
            )
        raise RuntimeError(f"Jira API request failed: HTTP {response.status_code} - {response.text}")

    payload = response.json()
    fields = payload.get("fields", {})

    description = fields.get("description")
    parsed_description = ""
    if isinstance(description, dict):
        parsed_description = description.get("content") or ""
    elif isinstance(description, str):
        parsed_description = description
    else:
        parsed_description = ""

    acceptance_criteria = fields.get("acceptancecriteria") or fields.get("acceptance_criteria") or ""

    summary = fields.get("summary") or "No summary was provided by Jira."

    return {
        "key": issue_key,
        "summary": summary,
        "description": parsed_description,
        "acceptance_criteria": acceptance_criteria,
        "raw": payload,
    }
