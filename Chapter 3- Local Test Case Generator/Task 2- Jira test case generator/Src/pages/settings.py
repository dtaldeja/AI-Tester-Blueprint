import streamlit as st

from config_store import load_settings, save_settings
from jira_client import fetch_jira_issue, normalize_jira_base_url

st.set_page_config(page_title="Settings", page_icon="⚙️")

st.title("Settings")
st.caption("Persist Jira and LLM provider configuration locally")

settings = load_settings()

with st.form("settings_form"):
    st.subheader("Jira")
    jira_url = st.text_input("Jira Base URL", value=settings.get("jira_url", ""))
    jira_email = st.text_input("Jira Email ID", value=settings.get("jira_email", ""))
    jira_api_token = st.text_input("Jira API Token", value=settings.get("jira_api_token", ""), type="password")

    st.subheader("LLM")
    llm_provider = st.selectbox(
        "LLM Provider",
        options=["ollama", "groq"],
        index=0 if (settings.get("llm_provider") or "ollama") == "ollama" else 1,
    )
    ollama_url = st.text_input("Ollama URL", value=settings.get("ollama_url") or "http://localhost:11434")
    ollama_model = st.text_input("Ollama Model", value=settings.get("ollama_model") or "gemma3:1b")
    groq_api_key = st.text_input("Groq API Key", value=settings.get("groq_api_key", ""), type="password")
    groq_model = st.text_input("Groq Model", value=settings.get("groq_model") or "openai/gpt-oss-20b")

    submitted = st.form_submit_button("Save Settings")

if submitted:
    try:
        normalized_jira_url = normalize_jira_base_url(jira_url)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    new_settings = {
        "jira_url": normalized_jira_url,
        "jira_email": jira_email,
        "jira_api_token": jira_api_token,
        "llm_provider": llm_provider,
        "ollama_url": ollama_url,
        "ollama_model": ollama_model,
        "groq_api_key": groq_api_key,
        "groq_model": groq_model,
    }
    save_settings(new_settings)
    settings = new_settings
    st.success("Settings saved locally to settings.json")

st.subheader("Test Jira connection")
test_issue_key = st.text_input("Issue key to test", value="KAN-1")
if st.button("Check Jira access"):
    try:
        issue = fetch_jira_issue(test_issue_key, settings)
        st.success(f"Jira access works for {test_issue_key}: {issue.get('summary', 'No summary')}")
    except Exception as exc:
        st.error(str(exc))

st.info("Ollama is the default provider. Groq is used only for fallback or explicit provider selection.")
