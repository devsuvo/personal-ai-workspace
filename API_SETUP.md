# AI Provider & API Key Setup Guide

Personal AI Workspace ships with **zero hardcoded API keys**. You configure your own keys dynamically through the **AI Providers** page on each computer independently.

## Supported Providers

1. **Anthropic Claude** (`https://api.anthropic.com`) — API Key
2. **Google Gemini Developer API** (`https://generativelanguage.googleapis.com`) — API Key (sent via `x-goog-api-key` header)
3. **OpenAI** (`https://api.openai.com/v1`) — API Key
4. **DeepSeek** (`https://api.deepseek.com/v1`) — API Key
5. **xAI Grok** (`https://api.x.ai/v1`) — API Key
6. **Mistral AI** (`https://api.mistral.ai/v1`) — API Key
7. **Groq** (`https://api.groq.com/openai/v1`) — API Key
8. **OpenRouter** (`https://openrouter.ai/api/v1`) — API Key
9. **Ollama (Local)** (`http://127.0.0.1:11434`) — No API key required by default
10. **Custom OpenAI-Compatible API** — Custom Base URL (e.g. LM Studio, vLLM) + optional API key

## Step-by-Step Setup

1. Open **AI Providers** in the left sidebar.
2. Click **Add Provider** and choose your provider.
3. Enter a display name and paste your API key (or leave blank for local Ollama).
4. Click **Save Provider** — your key is encrypted immediately with Fernet (`AES-128-CBC + HMAC-SHA256`) before saving to SQLite.
5. Click **Test Connection** to verify authentication using a lightweight read-only endpoint (zero token generation cost).
6. Click **Manage** → **Fetch Available Models** (or add a model ID manually) and click **Set Default**.

## Switching Providers & Models

- Use the **Provider** and **Model** dropdowns directly in the Chat composer or AI Tools page to switch models at any time without restarting.
- If a provider has multiple saved API keys, a **Credential** selector appears automatically.

## Security Guarantees

- API keys are never stored in plaintext in SQLite, never stored in browser `localStorage`, never returned to the frontend (only masked fingerprints like `sk-****abcd`), and redacted from backend logs.
- Never copy `personal_ai_workspace.db` or `master.key` between Windows and macOS; configure API keys separately on each computer.
