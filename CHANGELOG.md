## [0.5.0] - 2025-10-03

### Added
- **Enhanced Rules System**: Complete redesign supporting two intelligent rule types
  - **Skippy Guardrails**: Contextual safety rules that prevent inappropriate actions
    - Entity pattern matching (e.g., `light.garden_*`)
    - Action blocking with JSON condition evaluation
    - Override keywords for emergency situations
    - Time-based and sensor-based guard conditions
  - **Submind Automations**: Proactive automation rules with trigger-based execution
    - Complex trigger condition evaluation using JSON
    - Multi-action execution with Home Assistant service calls
    - Manual execution endpoint and cron-style scheduling support
    - Execution tracking with timestamps and counters
- **Advanced Database Schema**: Enhanced rules table supporting both rule types
  - JSON field storage for complex conditions and actions
  - Priority system for rule ordering and execution
  - Execution metadata tracking (last executed, count)
  - Proper indexing for rule type filtering and performance
- **Updated API Endpoints**: Complete CRUD operations for enhanced rules
  - Rule type filtering (`?rule_type=skippy_guardrail` or `submind_automation`)
  - Specific rule retrieval with parsed JSON fields
  - Manual execution endpoint for submind automations (`POST /api/rules/{id}/execute`)
  - JSON field validation and serialization in all responses
- **Enhanced Admin Interface**: Separate forms for both rule types
  - Dedicated creation forms for Skippy Guardrails and Submind Automations
  - Rule type filtering and visual status indicators
  - JSON field validation with error handling
  - Execute button for manual submind automation testing
- **Comprehensive Documentation**: Complete guides for the new rules system
  - Enhanced Rules System guide (`docs/enhanced-rules-system.md`) with examples and field formats
  - Updated API documentation with detailed JSON schemas and rule type endpoints
  - Extended curl examples for both rule types with proper JSON payloads
  - Integration documentation for Home Assistant services and action execution
  - Updated README.md with enhanced features section and documentation links

### Technical Implementation Details
- **Database Schema Migration**: Successfully migrated from old rules structure
  - Dropped and recreated rules table with enhanced schema
  - Fixed MySQL DEFAULT value issues and NOT NULL constraints
  - Updated sample data fetchers to reference new rule structure
- **JSON Field Storage**: Implemented proper JSON serialization/deserialization
  - Guard conditions and trigger conditions stored as TEXT with JSON content
  - Target actions and blocked actions arrays properly serialized
  - Client-side parsing for admin interface display and editing
- **Admin Interface Enhancements**: Complete UI overhaul for rule management
  - Separate creation forms with rule-type-specific fields
  - Visual badges for rule types and status indicators
  - JSON validation with user-friendly error messages
  - Dynamic form switching based on rule type selection
- **API Response Optimization**: JSON fields parsed for all rule endpoints
  - Automatic JSON parsing in list and get operations
  - Proper serialization in create and update responses
  - Error handling for malformed JSON in input validation

### Fixed
- **Pydantic Schema Bug**: Fixed critical issue with mutable default values in schemas
  - Removed `{}` and `[]` default values that caused "Python type dict cannot be converted" errors
  - Changed all JSON field defaults to `None` to prevent shared mutable state
  - Updated router JSON serialization to handle `None` values properly with fallbacks
- **API Server Stability**: Improved error handling and data validation
  - Enhanced JSON field processing in rule creation endpoint
  - Better handling of optional fields with null values
  - More robust type conversion for database compatibility

### Summary
This release represents a complete transformation of the MCP rules system from a simple trigger-target model to a sophisticated two-type intelligent automation framework. The new system provides both preventive safety measures (Skippy Guardrails) and proactive automation capabilities (Submind Automations) with comprehensive JSON-based configuration, execution tracking, and a fully updated admin interface. All documentation, tests, and API examples have been updated to reflect the new architecture. Critical schema bugs have been resolved to ensure stable API operation.

### Enhanced
- **Pydantic Schemas**: Updated to support new rule structure with proper validation
  - Converted from `orm_mode` to `from_attributes` for Pydantic v2 compatibility
  - Added `from_orm` class method for datetime field serialization
  - Comprehensive schema validation for both rule types with optional fields
- **Database Models**: SQLAlchemy models updated with JSON field handling
  - Enhanced Rule model with all new fields and proper defaults
  - DateTime handling with `datetime.datetime.utcnow()` for timestamps
  - Removed unused imports (ForeignKey, Index) for cleaner dependencies
- **API Router**: Complete endpoint overhaul with enhanced functionality
  - JSON field parsing and serialization in all rule responses
  - Rule type filtering implementation with proper query parameter handling
  - Manual execution endpoint with validation and error handling
  - Improved datetime handling in update operations
- **Test Coverage**: New comprehensive test suite for enhanced rules functionality
  - Created `test_new_rules.py` with 11 comprehensive test cases
  - Mock objects updated to match new rule structure with all fields
  - Tests for both rule types, filtering, creation, updates, and execution
  - JSON field validation and parsing verification
- **Error Handling**: Improved validation and error messages for complex rule structures
- **API Test Script**: Complete overhaul of `test_api.sh` script
  - Updated to test both Skippy Guardrails and Submind Automations
  - Added data fetcher testing with creation, execution, and cleanup
  - Enhanced prompt template testing with proper pre_fetch_data arrays
  - Comprehensive cleanup section for all created test resources
  - Updated test numbering from 18 to 29 total test cases

## [0.4.0] - 2025-10-01

### Added
- **Data Fetcher Engine**: Complete configurable data fetching system for prompt templates
  - MySQL-stored Python code blocks with safe execution environment
  - Redis caching with configurable TTL per fetcher (default 5 minutes, 1-minute freshness check)
  - Built-in data fetchers: `current_time`, `ha_device_status`, `rules_list`, `light_entities`
  - Safe execution environment with controlled imports (datetime, json, Redis, database access)
  - Automatic `failed_fetch` handling with error logging instead of null values
- **Data Fetcher Management API**: Full CRUD operations at `/api/data-fetchers`
  - Create, read, update, delete data fetchers via REST API
  - Test endpoint (`/test`) for immediate code execution without caching
  - Refresh endpoint (`/refresh`) to force cache updates
  - List all available fetchers with descriptions and TTL settings
- **Enhanced Admin Interface**: Complete web management for data fetchers
  - Create and edit Python code blocks through web interface
  - Test data fetchers directly from the admin panel with result preview
  - Refresh cache and view execution results
  - Syntax highlighting and code validation in textarea forms
- **Database Schema**: New `data_fetchers` table with proper indexing
  - Auto-incrementing ID, unique fetcher keys, TTL configuration
  - Created/updated timestamps, active/inactive status
  - Sample data fetchers included in migration scripts

### Enhanced
- **Prompt Template Processing**: Integration with data fetcher engine
  - Automatic data fetching based on `pre_fetch_data` array in templates
  - Context building with all required data before prompt formatting
  - Error handling for missing placeholders and failed data fetches
- **Logging**: Comprehensive console logging for all data fetch operations
  - Cache hit/miss logging with age information
  - Execution time tracking and error details
  - Failed fetch warnings with specific error messages
- **Documentation**: Complete API documentation and curl examples for data fetchers

### Technical Details
- **Safe Code Execution**: Restricted `exec()` environment with only approved imports
- **Cache Strategy**: Redis keys `mcp:prefetch:{fetcher_key}` with metadata
- **Error Resilience**: Failed fetches return `{failed_fetch: true, error: "details"}` instead of breaking
- **Database Integration**: Full SQLAlchemy model with proper relationships and constraints

---

## [0.3.1] - 2025-10-01

### Changed
- **Prompt Templates Schema**: Updated `pre_fetch_data` field from `Dict[str, Any]` to `List[str]` for better semantic clarity
  - Pre-fetch data now expects a simple array of strings indicating what data to fetch: `["ha_device_status", "rules_list", "current_time"]`
  - Backward compatibility maintained: existing templates with dictionary format are automatically converted to arrays
  - Updated HTML admin form to use textarea with array examples and improved JSON validation

### Fixed
- **API Validation**: Resolved 422 Unprocessable Entity errors when creating prompt templates through the web interface
- **JSON Handling**: Enhanced error messages and validation for pre_fetch_data field in admin form

---

## [0.3.0] - 2025-10-01

### Added
- **Prompt Templates Management**: Full CRUD API for managing prompt templates via `/api/prompts` endpoints
  - Create, read, update, delete prompt templates with structured data including template names, intent keywords, system prompts, user templates, and pre-fetch data configurations
  - JSON serialization/deserialization for complex pre-fetch data stored as text in MySQL
- **Static HTML Admin Interface**: Complete web-based admin interface at `/html/admin.html`
  - Manage all database entries (rules and prompt templates) through a user-friendly web interface
  - Real-time health monitoring for all system components (database, Redis, Home Assistant, Ollama)
  - Bootstrap-powered responsive design with error handling and form validation
- **Comprehensive Test Coverage**: Added 14 new tests achieving 100% coverage for new functionality
  - Full test suite for prompt templates CRUD operations (5 tests)
  - Complete test coverage for all health check endpoints with success/error scenarios (9 tests)
  - Fixed and improved all existing tests (12 tests) with proper mocking and import resolution

### Improved
- **API Documentation**: Updated `docs/API.md` with complete prompt template endpoint documentation
- **cURL Examples**: Enhanced `docs/curl.md` with comprehensive prompt template API examples
- **Test Infrastructure**: Improved test reliability with better mocking, proper async handling, and SQLAlchemy compatibility
- **Database Schema**: Added `04_prompt_templates.sql` schema with proper MySQL JSON handling via Text fields

### Changed
- **Route Consistency**: All API endpoints now consistently use `/api/` prefixes for uniform URL structure
- **JSON Handling**: Implemented proper JSON serialization for `pre_fetch_data` field in prompt templates
- **Pydantic Schemas**: Updated schemas to use `Dict[str, Any]` for JSON fields instead of `List[str]`
- **Static File Serving**: FastAPI now serves the `html/` directory at `/html/` for admin interface access

### Fixed
- **SQLAlchemy Compatibility**: Resolved import issues with `NoResultFound`, `OperationalError`, and JSON column types
- **Test Import Paths**: Fixed all test import paths to use correct module references (`mcp.action_executor`, `mcp.ollama`, etc.)
- **Response Validation**: Added proper datetime formatting and JSON conversion for API responses
- **Router Initialization**: Eliminated duplicate router definitions that were causing endpoint registration issues

### Technical Details
- **Test Suite**: 26 total tests (12 existing + 14 new), all passing
- **New Endpoints**: 5 prompt template endpoints + 1 alias endpoint for health checks
- **Database**: New `prompt_templates` table with auto-incrementing ID and timestamp fields
- **Admin Interface**: Single-page application with AJAX calls, JSON pretty-printing, and error handling

---

## [0.2.1] - 2025-10-01

### Added
- The Home Assistant poller now prints clear log messages for each step: polling, entity count, Redis write, and sleep.

### Fixed
- The poller now correctly uses REDIS_HOST and REDIS_PORT from .env if REDIS_URL is not set, matching MCP configuration style.

---
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-10-01

### Added
- Implemented Redis caching for Ollama API calls to improve performance.
- Created `mcp/cache.py` to manage the Redis client.
- Created `docs/API.md` to document the MCP API.
- Added comprehensive tests for the `/api/rules` endpoint (CRUD) with full mocking.
- Added `homeassistant/poller.py` for polling Home Assistant and caching controllable entities in Redis.
- Added `homeassistant/ha_client.py` for sending control commands to Home Assistant.
- Added tests for Home Assistant polling and control modules (`test_ha_poller.py`, `test_ha_client.py`).
- Added FastAPI healthcheck endpoints for Home Assistant, Redis, Ollama, and MySQL database (`/api/health/ha`, `/api/health/redis`, `/api/health/ollama`, `/api/health/db`).
- Added example curl commands for all healthcheck endpoints to `docs/curl.md`.

### Improved
- Updated `docs/API.md` to fully document all endpoints and response schemas, including `/api/rules` CRUD and `/api/command`.
- Ensured `docs/curl.md` and `README.md` are up to date and correctly linked to all documentation, including API examples and healthchecks.
- README now clearly instructs users not to include a trailing slash in `HA_URL` to avoid 404 errors with the Home Assistant API.
- All scripts that use environment variables now load them from `.env` using `python-dotenv` for reliable configuration.

### Changed
- Updated `mcp/health_checks.py` to use an asynchronous Redis client and improved error reporting.
- Updated `mcp/main.py` to call the asynchronous Redis health check and to run all health checks at startup.
- Updated `README.md` to include a consolidated "Project Documentation" section with links to the changelog, API documentation, and todo list.

### Fixed
- Fixed Home Assistant URL handling: clarified that `HA_URL` in `.env` should not have a trailing slash to avoid 404 errors when calling the API.
- Fixed a bug where healthcheck endpoints were defined before the router, causing a `NameError` on startup.
- Fixed test mocks for `/api/rules` to ensure compatibility with FastAPI response validation and SQLAlchemy patterns.
- Fixed all test imports and mocks so that tests can run in isolation without requiring a working production environment.

### Security
- No security-specific changes in this release.

---

## [Unreleased]
