import json
import os
from pathlib import Path

import requests


OLLAMA_DEFAULT_URL = "http://localhost:11434"


def build_prompt(jira_key, summary, description, acceptance_criteria, template_text):
    prompt = f"""
You are a Senior QA Engineer.

Generate test cases for Jira issue {jira_key}.

Ticket summary:
{summary}

Ticket description:
{description}

Acceptance criteria:
{acceptance_criteria}

Use this template structure:
{template_text}

Only return the final test cases in a structured QA table format. Keep it clear, implementation-ready and avoid hallucinations.
"""
    return prompt


def call_ollama(prompt, settings):
    ollama_url = (settings.get("ollama_url") or OLLAMA_DEFAULT_URL).rstrip("/")
    ollama_model = settings.get("ollama_model") or "gemma3:1b"

    payload = {
        "model": ollama_model,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(
        f"{ollama_url}/api/generate",
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Ollama call failed: HTTP {response.status_code} - {response.text}")

    result = response.json()
    return result.get("response") or "No response received from Ollama."


def call_groq(prompt, settings):
    groq_api_key = (settings.get("groq_api_key") or "").strip()
    if not groq_api_key:
        raise RuntimeError("GROQ API key is not configured in settings.")

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.2,
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Groq call failed: HTTP {response.status_code} - {response.text}")

    result = response.json()
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("Groq returned an empty chat completion.")

    return choices[0].get("message", {}).get("content") or "No Groq response returned."


def generate_test_cases(jira_key, summary, description, acceptance_criteria, template_text, settings):
    """Generate structured QA test cases using the configured provider and fallback logic."""
    provider = (settings.get("llm_provider") or "ollama").lower()

    prompt = build_prompt(jira_key, summary, description, acceptance_criteria, template_text)

    try:
        if provider == "groq":
            return call_groq(prompt, settings)
        return call_ollama(prompt, settings)
    except Exception as ollama_or_groq_error:
        # Critical fallback rule: do not call Groq unless Ollama is unavailable or the user has selected it.
        # If provider is Groq, the given exception should surface; if provider is Ollama, retry with Groq.
        if provider != "groq":
            try:
                return call_groq(prompt, settings)
            except Exception as groq_error:
                raise RuntimeError(f"Ollama fallback failed and Groq fallback failed: {ollama_or_groq_error}; {groq_error}")
        raise RuntimeError(f"Groq generation failed: {ollama_or_groq_error}")
