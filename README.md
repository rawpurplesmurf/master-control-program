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

- **Advanced Command Processing Pipeline**: Complete 5-step natural language command processing:
  1. **Template Determination**: Intelligent selection of appropriate prompt templates
  2. **Data Fetching**: Automatic execution of required data fetchers for context
  3. **Prompt Construction**: Dynamic assembly of system and user prompts with real-time data
  4. **LLM Processing**: Seamless integration with Ollama for natural language understanding
  5. **Response Generation**: Structured responses with processing metadata and performance metrics
- **Natural Language Control**: Control your smart home using simple, flexible language with context-aware responses.
- **Enhanced Rules System**: Two-type intelligent rule engine:
  - **Skippy Guardrails**: Contextual safety rules that prevent inappropriate actions (e.g., no garden lights during daylight)
  - **Submind Automations**: Proactive automation rules that trigger actions based on conditions (e.g., lights on when arriving after sunset)
- **Safety and Reliability**: Multi-layer protection with intelligent guardrails and deterministic rule validation.
- **Persistent State**: Utilizes a MySQL database to store entity data, rules, and conversational history.
- **Modular Architecture**: Designed with a clear separation of concerns, where the LLM is a tool and the MCP is the intelligent orchestrator.
- **Prompt Templates Management**: Create and manage structured prompt templates with intent keywords, system prompts, user templates, and configurable pre-fetch data arrays via REST API.
- **Data Fetcher Engine**: Configurable Python-based data fetchers stored in MySQL with Redis caching, TTL management, and safe code execution for dynamic prompt data.
- **Comprehensive Prompt History System**: Complete LLM interaction tracking and management:
  - **Automatic Storage**: All AI interactions stored in Redis with rich metadata and source tracking
  - **Web Interface**: Beautiful prompt history viewer at `/html/prompt-history.html` with filtering, pagination, and re-run capabilities
  - **API Management**: Full REST API for history retrieval, statistics, re-execution, and cleanup operations
  - **Source Analytics**: Track interactions by source (API, Skippy, Submind, manual, re-run) for usage insights
  - **Performance Metrics**: Monitor processing times and identify optimization opportunities
  - **Audit Trail**: Complete history of all AI interactions for debugging and compliance
- **Web-Based Admin Interface**: Comprehensive HTML admin panel at `/html/admin.html` for managing both rule types, prompt templates, and data fetchers with real-time health monitoring.
- **Home Assistant Status Dashboard**: Beautiful HA entity viewer at `/html/ha-status.html` with real-time entity display, domain filtering, search capabilities, and comprehensive statistics dashboard.
- **Health Monitoring**: Built-in health check endpoints for monitoring database, Redis, Home Assistant, and Ollama connections.
- **Comprehensive Test Coverage**: Full test suite with 30+ tests covering all functionality including CRUD operations, health checks, HA entities, command processing pipeline, prompt history management, and external service integrations.

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

The MCP includes comprehensive web-based interfaces accessible once the server is running:

### Main Dashboard (`/html/admin.html`)
- **Rules Management**: View, create, edit, and delete both Skippy Guardrails and Submind Automations
- **Prompt Templates Management**: Full CRUD operations for prompt templates including system prompts, user templates, and pre-fetch data arrays
- **Data Fetcher Management**: Create, edit, test, and manage configurable Python data fetchers with caching and TTL controls
- **Real-Time Health Monitoring**: Live status checks for database, Redis, Home Assistant, and Ollama services
- **Bootstrap UI**: Responsive design with error handling and form validation

### Home Assistant Status Dashboard (`/html/ha-status.html`)
- **Comprehensive Entity Display**: All HA entities organized by domain (lights, switches, sensors, etc.)
- **Statistics Overview**: Real-time counts of total entities, availability status, and domain breakdown
- **Advanced Filtering**: Real-time search and domain-based filtering for quick entity location
- **Visual State Indicators**: Color-coded status badges showing entity states (on/off/unavailable)
- **Entity Details**: Full entity information including friendly names, attributes, and last changed timestamps
- **Mobile Responsive**: Works seamlessly on desktop and mobile devices

### Skippy Chat Interface (`/html/skippy-chat.html`)
- **Interactive AI Chat**: Beautiful web-based chat interface for natural conversation with Skippy AI
- **Thinking Process Visualization**: Shows step-by-step AI reasoning including template selection, data fetching, and prompt construction
- **Streaming Responses**: Real-time text streaming with typewriter effect for engaging user experience
- **Source Tracking**: All interactions automatically tagged as "skippy" source for prompt history analytics
- **Command Processing**: Full integration with MCP command pipeline including data fetchers and LLM processing
- **Responsive Design**: Mobile-optimized chat interface with Bootstrap styling and smooth animations
- **Performance Metrics**: Display processing times, template usage, interaction IDs, and metadata
- **Error Handling**: Graceful error display with connection status indicators

### Prompt History Dashboard (`/html/prompt-history.html`)
- **Complete Interaction Timeline**: Chronological view of all LLM prompt/response interactions
- **Source-Based Filtering**: Filter by API, Skippy, Submind, re-run, or manual sources
- **Detailed Interaction Cards**: Expandable views showing full prompts, responses, and metadata
- **Re-run Capability**: One-click re-execution of any previous prompt with source tracking
- **Performance Analytics**: Processing times, template usage, and interaction statistics
- **Search and Pagination**: Find specific interactions quickly with advanced search and pagination
- **Mobile-Optimized**: Fully responsive design for viewing history on any device

### API Endpoints

The MCP provides REST API endpoints for all functionality:

- **Command Processing**: `/api/command` (POST) - Enhanced pipeline for natural language command processing with automatic history storage
- **Rules**: `/api/rules` (GET, POST, PUT, DELETE) with rule type filtering
- **Prompt Templates**: `/api/prompts` (GET, POST, PUT, DELETE) 
- **Data Fetchers**: `/api/data-fetchers` (GET, POST, PUT, DELETE) with test/refresh endpoints
- **Prompt History**: Complete history management API:
  - `/api/prompt-history` (GET) - Retrieve history with pagination and source filtering
  - `/api/prompt-history/stats` (GET) - Statistics and source distribution analytics  
  - `/api/prompt-history/{id}` (GET) - Detailed interaction view
  - `/api/prompt-history/{id}/rerun` (POST) - Re-execute previous prompts
  - `/api/prompt-history/{id}` (DELETE) - Remove specific interactions
- **Home Assistant Entities**: `/api/ha/entities` (GET) for real-time HA entity data
- **Health Checks**: `/api/health` and `/api/health/{service}` for system monitoring

For complete API documentation, see [docs/API.md](./docs/API.md) and [docs/curl.md](./docs/curl.md) for example usage.

### Command Processing Pipeline

The MCP implements a sophisticated 5-step command processing pipeline:

```
1. Template Determination
   ├── Analyze incoming command
   ├── Select appropriate prompt template (currently defaults to 'default')
   └── Load template configuration including pre-fetch requirements

2. Data Fetching
   ├── Execute all data fetchers specified in template's pre_fetch_data
   ├── Retrieve current Home Assistant device states
   ├── Gather active rules and system context
   └── Apply caching and TTL management for performance

3. Prompt Construction
   ├── Build system prompt with retrieved context
   ├── Construct user prompt using template variables
   ├── Inject real-time data (time, device status, rules)
   └── Format final prompt for LLM consumption

4. LLM Processing
   ├── Send constructed prompt to Ollama
   ├── Handle streaming or standard responses
   ├── Apply timeout and error handling
   └── Process LLM response for structured output

5. Response Generation & History Storage
   ├── Format LLM response with metadata
   ├── Store complete interaction in prompt history (Redis)
   ├── Include processing performance metrics and source tracking
   ├── Log command execution for analytics
   └── Return structured JSON with success indicators and interaction ID
```

**Example Usage:**
```bash
# Send a command (automatically stored in prompt history)
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "Turn on the living room light", "source": "api"}'

# View prompt history
curl -X GET http://localhost:8000/api/prompt-history?limit=5

# Re-run a previous prompt
curl -X POST http://localhost:8000/api/prompt-history/{interaction_id}/rerun
```

**Prerequisites:**
- A prompt template named 'default' must exist in the database
- Required data fetchers must be configured for the template
- Ollama service must be running and accessible

## Home Assistant Poller

- The poller script (`homeassistant/poller.py`) now prints clear log messages for each step: polling, entity count, Redis write, and sleep. This makes it easy to monitor and debug its operation in real time.

4.  **Run the application:**
    ```bash
    uvicorn mcp.main:app --reload
    ```

## Running Tests

This project uses `pytest` for testing with comprehensive coverage of all functionality. The test suite includes 35+ tests covering:

- **CRUD Operations**: Rules, prompt templates, and data fetchers management
- **Prompt History**: Complete testing of history storage, retrieval, filtering, re-run, and cleanup operations
- **Health Checks**: All service connectivity testing
- **External Integrations**: Home Assistant entities, Redis, Ollama services
- **Command Processing Pipeline**: Complete 5-step pipeline testing including template determination, data fetching, prompt construction, LLM integration, and response formatting
- **Action Execution**: Command processing and execution
- **Enhanced Rules**: Both Skippy Guardrails and Submind Automations testing
- **HA Entity Management**: Home Assistant entity retrieval and caching
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