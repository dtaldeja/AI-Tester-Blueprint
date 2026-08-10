import json
import re

import requests



def extract_jira_key(message):
    """Find a Jira key like QA-102 inside a natural-language prompt."""
    pattern = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
    matches = pattern.findall(message or "")
    return matches[0] if matches else None


def fetch_jira_issue(issue_key, settings):
    """Fetch a Jira issue via REST API using stored credentials."""
    jira_url = (settings.get("jira_url") or "").strip().rstrip("/")
    jira_email = (settings.get("jira_email") or "").strip()
    jira_token = (settings.get("jira_api_token") or "").strip()

    if not jira_url or not jira_email or not jira_token:
        raise ValueError("Jira URL, Jira email, and Jira API token must be configured in Settings.")

    if "/rest/api" not in jira_url and "/browse" in jira_url:
        # Convert old Browse URL style to a Jira API base URL.
        base = jira_url.split("/browse", 1)[0]
        jira_url = base

    url = f"{jira_url}/rest/api/3/issue/{issue_key}?fields=summary,description,acceptancecriteria"

    response = requests.get(
        url,
        auth=(jira_email, jira_token),
        headers={"Accept": "application/json"},
        timeout=20,
    )

    if response.status_code != 200:
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
