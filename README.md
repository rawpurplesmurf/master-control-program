# Main Control Program (MCP)

## Project Documentation

- **Changelog**: See the [CHANGELOG.md](./CHANGELOG.md) for a detailed list of changes and release notes.
- **API Documentation**: For details on how to interact with the MCP, see the [API.md](./docs/API.md) documentation.
- **Enhanced Rules System**: Complete guide to Skippy Guardrails and Submind Automations in [enhanced-rules-system.md](./docs/enhanced-rules-system.md).
- **Data Fetcher Guide**: Learn how to create and use configurable data fetchers in [data-fetcher.md](./docs/data-fetcher.md).
- **API Examples**: See [curl.md](./docs/curl.md) for example curl commands to test the API.
- **TODO**: The [todo.md](./docs/todo.md) file contains a list of tasks to be completed.

The Main Control Program (MCP) is a Python-based application that integrates a local Ollama Large Language Model (LLM) with a Home Assistant smart home automation system. The MCP's core function is to translate natural language commands into actionable Home Assistant API calls, enabling intelligent and context-aware control of smart home devices.

## Features

- **Natural Language Control**: Control your smart home using simple, flexible language.
- **Enhanced Rules System**: Two-type intelligent rule engine:
  - **Skippy Guardrails**: Contextual safety rules that prevent inappropriate actions (e.g., no garden lights during daylight)
  - **Submind Automations**: Proactive automation rules that trigger actions based on conditions (e.g., lights on when arriving after sunset)
- **Safety and Reliability**: Multi-layer protection with intelligent guardrails and deterministic rule validation.
- **Persistent State**: Utilizes a MySQL database to store entity data, rules, and conversational history.
- **Modular Architecture**: Designed with a clear separation of concerns, where the LLM is a tool and the MCP is the intelligent orchestrator.
- **Prompt Templates Management**: Create and manage structured prompt templates with intent keywords, system prompts, user templates, and configurable pre-fetch data arrays via REST API.
- **Data Fetcher Engine**: Configurable Python-based data fetchers stored in MySQL with Redis caching, TTL management, and safe code execution for dynamic prompt data.
- **Web-Based Admin Interface**: Comprehensive HTML admin panel at `/html/admin.html` for managing both rule types, prompt templates, and data fetchers with real-time health monitoring.
- **Health Monitoring**: Built-in health check endpoints for monitoring database, Redis, Home Assistant, and Ollama connections.
- **Comprehensive Test Coverage**: Full test suite with 28+ tests covering all functionality including CRUD operations, health checks, and external service integrations.

## Technology Stack

- **Programming Language**: Python 3.9+
- **Web Framework**: FastAPI
- **Database**: MySQL
- **ORM**: SQLAlchemy
- **Cache**: Redis (for command caching and prompt history)
- **Background Tasks**: APScheduler
- **Configuration**: python-dotenv

## Project Structure

```
├── docs/               # Design documents, API docs, and specifications
├── homeassistant/      # Home Assistant integration (poller and client)
├── html/               # Static web admin interface
├── mcp/                # Core MCP application source code
├── mysql/              # Database setup scripts and schema definitions
├── scripts/            # Utility scripts for testing
├── skippy/             # Frontend application code  
├── submind/            # Submind module code
├── tests/              # Comprehensive test suite (26 tests)
├── .gitignore
├── CHANGELOG.md
├── README.md
├── requirements.txt
└── pytest.ini         # Test configuration
```

## Setup and Installation

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    - In the project root, copy the `.env.example` file to `.env`.
    - Fill in the required credentials for Home Assistant, Ollama, MySQL, and Redis.
    - **Important:**
        - The `HA_URL` in your `.env` file should NOT have a trailing slash (e.g., use `http://venus.localdomain:8123` not `http://venus.localdomain:8123/`). This avoids 404 errors when calling the Home Assistant API.
        - The poller will use `REDIS_URL` if set, otherwise it will construct the connection string from `REDIS_HOST` and `REDIS_PORT` (e.g., `REDIS_HOST=synology4`, `REDIS_PORT=6379`).

## Admin Interface & Health Monitoring

The MCP includes a comprehensive web-based admin interface accessible at `/html/admin.html` once the server is running. This interface provides:

- **Rules Management**: View, create, edit, and delete automation rules
- **Prompt Templates Management**: Full CRUD operations for prompt templates including system prompts, user templates, and pre-fetch data arrays
- **Data Fetcher Management**: Create, edit, test, and manage configurable Python data fetchers with caching and TTL controls
- **Real-Time Health Monitoring**: Live status checks for:
  - Database connectivity
  - Redis cache availability
  - Home Assistant API connection
  - Ollama LLM service status
- **Bootstrap UI**: Responsive design with error handling and form validation

### API Endpoints

The MCP provides REST API endpoints for all functionality:

- **Rules**: `/api/rules` (GET, POST, PUT, DELETE)
- **Prompt Templates**: `/api/prompts` (GET, POST, PUT, DELETE) 
- **Data Fetchers**: `/api/data-fetchers` (GET, POST, PUT, DELETE) with test/refresh endpoints
- **Health Checks**: `/api/health` and `/api/health/{service}`

For complete API documentation, see [docs/API.md](./docs/API.md) and [docs/curl.md](./docs/curl.md) for example usage.

## Home Assistant Poller

- The poller script (`homeassistant/poller.py`) now prints clear log messages for each step: polling, entity count, Redis write, and sleep. This makes it easy to monitor and debug its operation in real time.

4.  **Run the application:**
    ```bash
    uvicorn mcp.main:app --reload
    ```

## Running Tests

This project uses `pytest` for testing with comprehensive coverage of all functionality. The test suite includes 26 tests covering:

- **CRUD Operations**: Rules and prompt templates management
- **Health Checks**: All service connectivity testing
- **External Integrations**: Home Assistant, Redis, Ollama services
- **Action Execution**: Command processing and execution
- **Configuration Management**: Environment and database setup

To run the test suite:

```bash
# Ensure your virtual environment is activated
pytest

# Run with verbose output to see individual test results
pytest -v

# Run with coverage reporting
pytest --cov=mcp
```

All tests use proper mocking to ensure isolation and can run without external service dependencies.