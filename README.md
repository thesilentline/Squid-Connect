# Squid Connect

Squid Connect is a multi-provider LLM chatbot platform paired with an asynchronous inference logging and telemetry ingestion system (ILIS).

---

## Tech Stack

- **Python App (Chatbot & Web UI)**: Python 3.12, FastAPI, SQLAlchemy (Async/asyncpg), Pydantic v2, Vanilla JS / HTML5 UI, Chart.js.
- **Java App (ILIS Ingestion Service)**: Java 21, Spring Boot 3, Spring Data JPA, Hibernate, OpenAPI / Swagger.
- **Database**: PostgreSQL 16 (`chatbot` and `ilis` databases).
- **Containerization & Orchestration**: Docker, Docker Compose.

---

## Quickstart (First-Time Setup)

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose installed.

### 2. Run the Entire Stack
From the project root directory, run:

```bash
docker-compose up --build
```

This starts all three services:
1. **PostgreSQL**: `localhost:5432`
2. **Java ILIS Ingestion Service**: `http://localhost:8081`
3. **Python Chatbot & Web UI**: `http://localhost:8080`

---

## Application Access & URLs

| Service | URL | Description |
| :--- | :--- | :--- |
| **Squid Connect Web UI** | [http://localhost:8080](http://localhost:8080) | Interactive chat interface & dashboard |
| **Python API Docs (Swagger)** | [http://localhost:8080/docs](http://localhost:8080/docs) | Interactive FastAPI documentation |
| **Java ILIS API Docs (Swagger)** | [http://localhost:8081/ilis/swagger-ui.html](http://localhost:8081/ilis/swagger-ui.html) | Telemetry & ingestion API documentation |

---

## Configuring LLM Providers & Models

1. Open [http://localhost:8080](http://localhost:8080) in your browser.
2. Click the **Settings (Gear Icon)** in the bottom left drawer.
3. Select your provider (**OpenAI**, **Anthropic**, **Google Gemini**, **Groq**, **Ollama**, or **Custom Proxy**).
4. Enter your API key, custom base URL (optional), default model, and configured custom models (separated by commas).
5. Click **Save Provider & Models**.

---

## Database Connection

- **Host**: `localhost`
- **Port**: `5432`
- **User**: `admin_user`
- **Password**: `user123`
- **Databases**:
  - `chatbot`: Chat conversations, messages, and provider configurations (`jdbc:postgresql://localhost:5432/chatbot`)
  - `ilis`: Ingestion telemetry events, metrics, and payloads (`jdbc:postgresql://localhost:5432/ilis`)

---

## Stopping the Services

```bash
docker-compose down
```
To stop and reset database volumes:
```bash
docker-compose down -v
```
