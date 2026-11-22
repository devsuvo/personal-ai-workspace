# Dynamic AI Provider & API Key Guide

## Supported Providers (10)

| Provider | Key | Adapter | Auth | Default Base URL |
| -------- | --- | ------- | ---- | ---------------- |
| Anthropic Claude | `anthropic` | `AnthropicProvider` | API Key (`x-api-key`) | `https://api.anthropic.com` |
| Google Gemini Developer API | `google_gemini` | `GeminiProvider` | API Key (`x-goog-api-key`) | `https://generativelanguage.googleapis.com` |
| OpenAI | `openai` | `OpenAIProvider` | Bearer API Key | `https://api.openai.com/v1` |
| DeepSeek | `deepseek` | `OpenAICompatibleProvider` | Bearer API Key | `https://api.deepseek.com/v1` |
| xAI Grok | `grok` | `OpenAICompatibleProvider` | Bearer API Key | `https://api.x.ai/v1` |
| Mistral AI | `mistral` | `OpenAICompatibleProvider` | Bearer API Key | `https://api.mistral.ai/v1` |
| Groq | `groq` | `OpenAICompatibleProvider` | Bearer API Key | `https://api.groq.com/openai/v1` |
| OpenRouter | `openrouter` | `OpenAICompatibleProvider` | Bearer API Key | `https://openrouter.ai/api/v1` |
| Ollama (Local) | `ollama` | `OllamaProvider` | None required by default | `http://127.0.0.1:11434` |
| Custom OpenAI-Compatible | `custom_openai` | `OpenAICompatibleProvider` | Optional Bearer Key | User-configured |

## Managing Providers in the UI

1. **Add a Provider**: Open **AI Providers** in the left sidebar → click **Add Provider** → choose the provider type, enter a display name, optional Base URL, and your API key → click **Save Provider**.
2. **Test Connection**: Click **Test Connection** on any provider card or inside the provider detail screen. All adapters use lightweight read-only model/auth endpoints (`GET /v1/models`, `GET /v1beta/models`, `GET /api/tags`) with zero token generation cost.
3. **Rotate or Add Multiple Keys**: Open **Manage** on a provider to add multiple labeled keys, switch the active key, rotate an existing key, or delete credentials. Saved keys are only ever shown in masked form (e.g., `sk-****abcd`).
4. **Manage Models**: Click **Fetch Available Models** to discover models from the provider, add models manually when discovery is unavailable, toggle individual models on/off, and set a **Default Model**.

## Configuring Ollama (Local Models)

1. Install and start Ollama locally (`ollama serve`), then pull a model (e.g., `ollama pull llama3.2`).
2. In **AI Providers** → **Add Provider** → choose **Ollama (Local)**.
3. Leave the API Key blank and keep Base URL as `http://127.0.0.1:11434` (or your custom local URL).
4. Click **Test Connection** and **Fetch Available Models** to import your installed local models.

## Configuring Custom OpenAI-Compatible Endpoints

1. Choose **Custom OpenAI-Compatible API** in **Add Provider**.
2. Enter your endpoint's Base URL (for example `http://127.0.0.1:1234/v1` for LM Studio or a vLLM server).
3. Add an API key if required by your server, or leave it blank for local unauthenticated servers.
4. Use **Fetch Available Models** or **Add Model Manually** to register model identifiers.
