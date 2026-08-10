import os
import re
from pathlib import Path

import streamlit as st

from config_store import load_settings, save_settings
from jira_client import fetch_jira_issue, extract_jira_key
from llm_client import generate_test_cases


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "testcase_creator.md"


st.set_page_config(page_title="Jira Test Case Generator", page_icon="🧪", layout="wide")

st.title("Jira Test Case Generator")
st.caption("Generate draft QA test cases from a Jira ticket using Ollama or Groq")

settings = load_settings()

# Keep a tiny in-memory chat store, which is enough for the requested UI shape.
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.markdown("### Workspace")
    st.markdown("Provider: " + (settings.get("llm_provider") or "ollama"))
    st.markdown("Ollama: " + (settings.get("ollama_url") or "http://localhost:11434"))
    st.markdown("Model: " + (settings.get("ollama_model") or "gemma3:1b"))

chat_placeholder = st.container()

with chat_placeholder:
    for role, content in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(content)

user_prompt = st.chat_input("Describe the Jira ticket you want test cases for...")

if user_prompt:
    jira_key = extract_jira_key(user_prompt)
    if not jira_key:
        response_text = "I could not find a Jira issue key in your request. Example: 'create test cases for QA-102'."
        st.session_state.chat_history.append(("user", user_prompt))
        st.session_state.chat_history.append(("assistant", response_text))
        with st.chat_message("assistant"):
            st.markdown(response_text)
    else:
        st.session_state.chat_history.append(("user", user_prompt))

        with st.chat_message("assistant"):
            st.markdown("I’ll fetch the Jira ticket, merge the requirements into a template, and generate a test case draft.")

        try:
            issue = fetch_jira_issue(jira_key, settings)
            ticket_context = issue.get("summary", "")
            description = issue.get("description", "")
            acceptance_criteria = issue.get("acceptance_criteria", "")

            if TEMPLATE_PATH.exists():
                template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
            else:
                template_text = "ROLE - You are a Senior QA Engineer.\n\nTASK - Generate 25 test cases for the provided requirements.\n\nFORMAT:\n| Test ID | Description | Pre-conditions | Steps | Expected Result | Priority |\n\nREQUIREMENTS:\n[PASTE REQUIREMENTS HERE]\n"

            generated = generate_test_cases(
                jira_key=jira_key,
                summary=ticket_context,
                description=description,
                acceptance_criteria=acceptance_criteria,
                template_text=template_text,
                settings=settings,
            )

            st.session_state.chat_history.append(("assistant", generated))
            with st.chat_message("assistant"):
                st.markdown(generated)

        except Exception as exc:
            response_text = f"I hit a problem while generating the test cases: {exc}"
            st.session_state.chat_history.append(("assistant", response_text))
            with st.chat_message("assistant"):
                st.markdown(response_text)
