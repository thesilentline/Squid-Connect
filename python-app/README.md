# Squid Connect - Universal Multi-Provider LLM Chatbot Backend & UI

A clean, modular FastAPI backend with an embedded lightweight HTML/JS frontend. Built with **zero user mapping or user IDs**. Supports creating new chat sessions, browsing previous conversation histories, and generating AI completions across multiple LLM providers (OpenAI, Anthropic, Gemini, Groq, Ollama).

---

## Features

1. **Feature 1: Start New Chats**
   - Start a fresh chat via `POST /api/v1/conversations` or directly via the web UI.
   - Or send a prompt to `POST /api/v1/chat` without a `conversation_id` (auto-creates a new conversation and titles it from the first prompt).
2. **Feature 2: Browse and Resume Older Chats with Request & Response History**
   - `GET /api/v1/conversations`: List all previous chats with message counts, timestamps, and preview snippets.
   - `GET /api/v1/conversations/{conversation_id}`: Open any older chat to view its entire chronological history of prompts and answers.
   - `POST /api/v1/conversations/{conversation_id}/messages`: Continue conversation in an existing session with context preservation.
   - `PATCH /api/v1/conversations/{conversation_id}`: Rename chat title.
   - `DELETE /api/v1/conversations/{conversation_id}`: Delete a chat and its history.
3. **Universal LLM Provider Credentials & Dynamic Factory**
   - Store API keys globally per provider (OpenAI, Anthropic, Gemini, Groq, Ollama) via `POST /api/v1/llm/configs`.
   - No authentication, tokens, user IDs, or login IDs required.
4. **Built-in Lightweight Web UI**
   - Served directly from FastAPI at `http://localhost:8000/`.
   - All network requests are executed as transparent, direct browser `fetch()` calls.

---

## API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **`GET`** | `/` | **Built-in Web UI** (Squid Connect) |
| **`POST`** | `/api/v1/conversations` | **1. Start a new chat** session |
| **`GET`** | `/api/v1/conversations` | **2. List all past chats** (summaries & previews) |
| **`GET`** | `/api/v1/conversations/{conversation_id}` | **2. Go to an older chat** with full request/response history |
| **`POST`** | `/api/v1/conversations/{conversation_id}/messages` | **Send prompt in existing chat** & get answer |
| **`PATCH`** | `/api/v1/conversations/{conversation_id}` | **Rename** chat title |
| **`DELETE`** | `/api/v1/conversations/{conversation_id}` | **Delete** a chat session |
| **`POST`** | `/api/v1/chat` | **Universal chat prompt endpoint** (creates or continues chat) |
| **`POST`** | `/api/v1/llm/configs` | Store/update LLM provider API credentials |
| **`GET`** | `/api/v1/llm/configs` | List stored provider configurations |
| **`GET`** | `/api/v1/llm/providers` | List supported LLM providers and models |

---

## How to Run

1. **Activate Virtual Environment & Install Dependencies**:
   ```bash
   cd backend
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the FastAPI Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Open in Browser**:
   - **Squid Connect Web UI**: [http://localhost:8000/](http://localhost:8000/)
   - **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
