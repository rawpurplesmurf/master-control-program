## [1.0.4] - 2025-10-09

### 🎯 **System Prompt Management & Data Fetcher Reliability**

#### **Configurable System Prompts**
- **Database-Backed Prompts**: New `system_prompts` MySQL table with 5 default AI personalities
  - `default_mcp`: Standard Master Control Program assistant
  - `simple_assistant`: Straightforward, minimal responses
  - `automation_focused`: Expert in home automation and device control
  - `conversational`: Friendly, engaging communication style
  - `technical_expert`: Detailed technical explanations and analysis
- **Complete CRUD API**: Full system prompt management through REST endpoints
  - `GET /api/system-prompts` - List all available prompts
  - `POST /api/system-prompts` - Create new custom prompts
  - `PUT /api/system-prompts/{id}` - Update existing prompts
  - `DELETE /api/system-prompts/{id}` - Remove prompts
  - `POST /api/system-prompts/{id}/activate` - Set active prompt
  - `GET /api/system-prompts/active` - Get currently active prompt
- **Admin Interface Integration**: System prompt management through existing admin interface
- **Prompt Template Integration**: Optional system_prompt field in prompt templates for per-template customization

#### **Enhanced Data Fetcher Reliability**
- **Improved Cache Health Check**: Updated timeout from 5 minutes to 24 hours for realistic cache validation
- **Redis Connection Recovery**: Automatic reconnection handling with graceful fallback on connection failures
- **WebSocket Resilience**: Enhanced error handling for server restarts and connection issues
- **All 11 Data Fetchers Verified**: Complete functionality validation across entire data fetcher ecosystem
  - Time/date fetchers, HA device status, rules management
  - Light/switch domain queries, entity search and retrieval
  - State summaries and pattern-based entity discovery

#### **Documentation & Testing Updates**
- **Complete API Documentation**: System prompt endpoints added to `docs/API.md`
- **cURL Examples**: Comprehensive system prompt examples in `docs/curl.md`
- **Enhanced Test Suite**: Updated `scripts/test_api.sh` with system prompt test coverage
- **Database Schema**: New migration script `mysql/schemas/08_system_prompt.sql`

## [1.0.3] - 2025-10-09

### 🧹 **Cache Management & Entity Removal System**

#### **Automatic Entity Removal Handling**
- **Real-time WebSocket Removal**: Automatic cache cleanup when Home Assistant sends `new_state=None` 
- **Periodic Cache Cleanup**: Hourly background process to remove stale entities missed by WebSocket events
- **Manual Cache Management**: API endpoints for on-demand cache cleanup and monitoring
- **Comprehensive Logging**: All entity removals logged with 7-day retention and `entity_removed` flag
- **Cache Consistency**: Domain and controllable entity caches updated during cleanup operations

#### **New Cache Management API**
- **`POST /api/ha/cache/cleanup`**: Manually trigger cache cleanup for stale entities
  - Compares cached entities with current Home Assistant state
  - Removes entities that no longer exist in HA
  - Logs cleanup actions with `cleanup_action: true` flag
  - Updates all related cache structures
- **`GET /api/ha/cache/info`**: Comprehensive cache state information
  - Total entity counts and domain breakdown
  - Controllable entity statistics
  - Cache metadata with last update timestamps
  - Sample cache keys for debugging

#### **Enhanced WebSocket Client**
- **`_handle_entity_removal()`**: Process entity removal events with proper cache cleanup
- **`_cleanup_stale_cache_entries()`**: Compare HA state with cache to find stale entries
- **`_periodic_cache_cleanup()`**: Hourly cleanup task running in background
- **Enhanced Logging**: Added `entity_removed` and `cleanup_action` flags to all log entries
- **Robust Error Handling**: Proper Redis client initialization and comprehensive exception handling

#### **Testing & Documentation**
- **Enhanced Test Suite**: Added cache management tests to `scripts/test_api.sh`
  - Cache information retrieval validation
  - Manual cleanup endpoint testing
  - Cache consistency verification after cleanup operations
- **API Documentation**: Complete cache management documentation in `/docs/API.md`
- **Integration Testing**: Comprehensive entity removal scenarios with cleanup verification

## [1.0.2] - 2025-10-06

### 🎮 **Home Assistant Device Control System**

#### **Complete Device Control Framework**
- **Live Service Discovery**: Real-time fetching from Home Assistant's `/api/services` endpoint
- **Service Validation**: Validates all service calls against live HA service definitions
- **Action Execution Engine**: Complete device control with validation, error handling, and logging
- **Bulk Actions Support**: Execute multiple device actions in sequence for scenes and automation
- **Action History Tracking**: 7-day retention of all device actions with Redis storage

#### **New Device Control API**
- **`GET /api/ha/services`**: Live Home Assistant services with Redis caching (5-minute TTL)
  - Force refresh option (`?refresh=true`)
  - Domain filtering (`?domain=light`)
  - Field-aware parameter definitions
  - Fallback services when HA unavailable
- **`POST /api/ha/action`**: Execute single Home Assistant actions
  - Entity validation and controllability checks
  - Comprehensive error handling with suggestions
  - Service parameter validation
  - State change tracking
- **`POST /api/ha/actions/bulk`**: Execute multiple actions (max 50)
  - Sequence execution with individual result tracking
  - Partial failure handling
  - Scene and automation support
- **`GET /api/ha/entities/{entity_id}/actions`**: Action execution history
  - 7-day retention with Redis sorted sets
  - Configurable limits (1-200 results)
  - Success/failure tracking with error details

#### **New Device Control Components**
- **`mcp/ha_services.py`**: Home Assistant services manager with real-time discovery and caching
- **`mcp/ha_action_executor.py`**: Device action execution engine with validation and logging
- **Enhanced Router**: 4 new endpoints with comprehensive error handling and logging
- **Admin Interface Enhancement**: Device Control tab in admin interface (future implementation)

#### **Testing & Quality Assurance**  
- **42 New Tests**: Comprehensive test coverage for services and actions
  - `tests/test_ha_services.py` - 14 tests for service discovery and validation
  - `tests/test_ha_action_executor.py` - 13 tests for action execution and logging  
  - `tests/test_ha_services_api.py` - 15 tests for API endpoints and error handling
- **Integration Testing**: Full API test coverage including edge cases and error scenarios
- **Mock Testing**: Proper async mocking for all external service dependencies

#### **Documentation Updates**
- **Enhanced API Documentation**: Complete device control API documentation in `/docs/API.md`
- **Extended curl Examples**: New device control examples in `/docs/curl.md` 
- **Updated Test Script**: 8 new test scenarios in `scripts/test_api.sh` for device control validation
- **Action Examples**: Real-world curl examples for lights, switches, climate, and scenes

## [1.0.1] - 2025-10-04

### 🔧 **WebSocket State Logging & Redis Documentation**

#### **Entity State Change Logging**
- **Fixed Redis Client Initialization**: WebSocket client now properly initializes Redis connection for state logging
- **Real-Time Entity Logging**: Manual device state changes are now logged to Redis with 7-day retention
- **Entity Logs Admin Interface**: Complete admin interface at `/html/admin.html` with Entity Logs tab
- **Comprehensive Log API**: Full REST API for entity log queries, summaries, and filtering
- **WebSocket Message Debugging**: Enhanced WebSocket message debugging with console logging and storage

#### **Redis Documentation & Administration**
- **Complete Redis Guide**: New `/docs/redis.md` with comprehensive Redis key documentation
- **Redis Key Patterns**: Detailed documentation of all Redis keys used by MCP:
  - Entity state caching (`ha:entity:*`, `ha:domain:*`, `ha:all_states`)
  - State change logging (`ha:log:*` with chronological sorting)
  - Data fetcher caching (`data_fetcher:*` with configurable TTL)
  - WebSocket debugging (`ha:websocket:messages`)
  - Prompt history storage (`prompt_history:*`)
- **Administrative Commands**: Sample Redis CLI commands for monitoring, maintenance, and troubleshooting
- **Performance Monitoring**: Health check scripts and performance optimization guidelines
- **Maintenance Procedures**: Automated cleanup scripts and emergency recovery procedures

#### **Testing & Quality Improvements**
- **Updated WebSocket Tests**: Fixed all tests to account for Redis client initialization
- **Enhanced Test Coverage**: Added Redis connection failure testing scenarios
- **Test Suite Validation**: All 30+ tests pass with new Redis requirements

#### **Technical Fixes**
- **WebSocket Client**: Proper Redis client initialization in `connect()` method
- **State Change Handler**: Fixed nested JSON parsing for Home Assistant WebSocket events
- **Entity Log Storage**: Implemented Redis sorted sets for chronological state change logging
- **Debug Logging**: Enhanced WebSocket message processing with detailed console output

## [1.0.0] - 2025-10-03

### 🚀 **Real-Time Home Assistant WebSocket Integration**

#### **Major Architecture Migration: Polling → WebSocket**
- **Real-Time State Updates**: Replaced 30-minute polling with live WebSocket connection to Home Assistant
- **Redis State Cache**: Entity states now cached in Redis with automatic real-time updates
- **Performance Improvements**: Data fetchers execute in milliseconds instead of seconds
- **Auto-Reconnection**: Intelligent WebSocket reconnection with exponential backoff
- **Comprehensive State Management**: New `mcp/ha_state.py` module providing clean async API

#### **New WebSocket Components**
- **`mcp/ha_websocket.py`**: Complete WebSocket client with authentication and state caching
- **`mcp/ha_state.py`**: Redis-based state manager with search, filtering, and convenience functions
- **WebSocket Health Check**: New `/api/health/websocket` endpoint for connection monitoring
- **Enhanced Data Fetchers**: 7 new WebSocket-aware data fetchers for real-time state access

#### **Enhanced Data Fetcher Capabilities**
- **Real-Time Access Functions**:
  - `get_ha_lights_on()` - All lights currently on
  - `get_ha_switches_on()` - All switches currently on
  - `search_ha_entities(pattern)` - Pattern-based entity search
  - `get_ha_domain_entities(domain)` - All entities for specific domain
- **Async Support**: Data fetchers now support `asyncio` for WebSocket state access
- **Cache Health Monitoring**: Automatic validation of cache freshness (alerts if >5 minutes old)

#### **Migration Benefits**
- ⚡ **Real-time updates** instead of 30-minute delays
- 🚀 **10x faster data fetchers** with Redis cache
- 🔄 **Automatic reconnection** with connection health monitoring
- 📊 **Rich state queries** - search by domain, pattern, state value
- 🛡️ **Graceful degradation** with comprehensive error handling
- ✅ **Full backward compatibility** - existing code continues to work

#### **Removed Dependencies**
- **APScheduler**: No longer needed for polling background tasks
- **MySQL Entity Storage**: Entities now stored in Redis cache for faster access
- **Polling Delays**: Eliminated 30-minute polling intervals

#### **Technical Details**
- **WebSocket Authentication**: Automatic token-based authentication with Home Assistant
- **Event Subscription**: Real-time subscription to `state_changed` events
- **Cache Structure**: Organized by domain (`ha:domain:light`), entity (`ha:entity:light.living_room`), and summary (`ha:metadata`)
- **Connection Recovery**: Handles network issues, HA restarts, and authentication failures
- **Test Coverage**: 16 new tests covering WebSocket client and state manager functionality

## [0.9.0] - 2025-10-03

### 🧠 **Intelligent Template Selection System**

#### **Major Enhancement: Keyword-Based Template Matching**
- **Smart Template Selection**: Automatically selects the best prompt template based on command content
- **Intent Keywords**: Each template defines comma-separated keywords that trigger its use
- **First 5 Words Analysis**: System analyzes the first 5 words of each command for keyword matching
- **Scoring Algorithm**: Templates receive points for each matched keyword
- **Intelligent Tie-Breaking**: When templates have equal scores, prefers templates with more total keywords (more specific)
- **Fallback Strategy**: Uses 'default' template when no keywords match

#### **Template Selection Examples**
- **Home Automation**: Commands starting with "turn, switch, set, adjust, control" → `home_automation` template
- **Information Queries**: Commands starting with "what, when, where, how, why" → `information` template  
- **Time/Weather**: Commands starting with "time, weather, temperature, forecast" → `time_weather` template
- **No Match**: Commands with no keyword matches → `default` template

#### **Enhanced Admin Interface**
- **Template Management**: Improved prompt templates tab with keyword visualization
- **Keyword Badges**: Intent keywords displayed as colored badges for easy identification
- **Selection Documentation**: Built-in explanation of how intelligent selection works
- **Better Layout**: Enhanced table design with truncated content and tooltips

## [0.8.0] - 2025-10-03

### Added - Comprehensive Prompt History System
- **Complete LLM Interaction Tracking**: Store and manage all prompt/response interactions
  - **Automatic Storage**: Every command processed through `/api/command` is automatically stored in Redis
  - **Rich Metadata**: Capture processing time, template used, context keys, source, and timestamps
  - **Source Tracking**: Tag interactions by source (api, skippy, submind, rerun, manual)
  - **30-Day Retention**: Automatic cleanup with configurable TTL in Redis
- **Prompt History API Endpoints**: Complete REST API for history management
  - `GET /api/prompt-history` - Retrieve history with pagination and filtering
  - `GET /api/prompt-history/stats` - Get statistics and source distribution
  - `GET /api/prompt-history/{id}` - Get specific interaction details
  - `POST /api/prompt-history/{id}/rerun` - Re-execute previous prompts
  - `DELETE /api/prompt-history/{id}` - Remove specific interactions
- **Beautiful Web Interface**: New prompt history management page
  - **Interactive Timeline**: View all prompt interactions in chronological order
  - **Source Filtering**: Filter by API, Skippy, Submind, rerun, or manual sources
  - **Detailed Views**: Expandable cards showing full prompts and responses
  - **Re-run Capability**: One-click re-execution of any previous prompt
  - **Performance Metrics**: Processing times and metadata visualization
  - **Responsive Design**: Mobile-friendly Bootstrap 5 interface
- **Enhanced Command Processing**: Updated pipeline with history integration
  - **Source Parameter**: Commands now accept source tracking parameter
  - **Interaction IDs**: All commands return unique interaction IDs
  - **Error Logging**: Failed commands also stored in history for debugging
  - **Metadata Enrichment**: Enhanced metadata capture including template and context information
- **Skippy Chat Interface**: Beautiful web-based AI chat interface
  - **Interactive Chat UI**: Real-time conversation interface with streaming responses
  - **Thinking Process Visualization**: Shows AI reasoning steps including template selection and data fetching
  - **Source Integration**: All chat interactions automatically tagged as "skippy" source
  - **Performance Metrics Display**: Shows processing times, templates used, and interaction metadata
  - **Responsive Design**: Mobile-optimized Bootstrap interface with smooth animations
  - **Error Handling**: Graceful connection error display and status indicators

### Enhanced
- **Admin Interface Redesign**: Improved tabbed layout for better organization
  - **Tabbed Navigation**: Separated Health Checks, Prompt Templates, Data Fetchers, and Rules into distinct tabs
  - **Improved Styling**: Enhanced tab design with better visual hierarchy and Bootstrap integration
  - **Lazy Loading**: Tab content loads only when accessed for better performance
  - **Better UX**: Cleaner layout with improved button placement and visual consistency
- **Navigation Updates**: Added Skippy Chat and prompt history links to all admin interfaces
- **Test Coverage**: Comprehensive test suite for prompt history functionality
  - 15 new test functions covering all history operations
  - Error handling, pagination, filtering, and re-run functionality testing
  - Proper mocking of Redis operations and LLM calls
- **API Documentation**: Complete documentation for all prompt history endpoints
- **cURL Examples**: Extensive examples for all history operations and use cases
- **Test Scripts**: Enhanced `test_api.sh` with prompt history validation

### Technical Architecture
- **Redis Storage Strategy**: Efficient storage using sorted sets for chronological access
- **Async Architecture**: Full async/await support for all history operations  
- **Error Resilience**: Graceful handling of Redis failures without breaking command processing
- **Memory Management**: Automatic cleanup and TTL management for storage efficiency
- **Performance Optimization**: Pagination support for large history datasets

### Use Cases Enabled
- **Debugging**: See exactly what prompts were sent to LLM and responses received
- **Performance Analysis**: Track processing times and identify bottlenecks
- **Response Comparison**: Re-run old prompts to see how LLM responses evolve
- **Audit Trail**: Complete history of all AI interactions for compliance
- **Template Testing**: Compare effectiveness of different prompt templates
- **Source Analytics**: Understand usage patterns across different system components

## [0.7.0] - 2025-10-03

### Added - Advanced Command Processing Pipeline
- **Complete 5-Step Processing Architecture**: Revolutionary command processing system
  - **Step 1 - Template Determination**: Intelligent prompt template selection (currently defaults to 'default')
  - **Step 2 - Data Fetching**: Automatic execution of template-specified data fetchers
  - **Step 3 - Prompt Construction**: Dynamic assembly of system and user prompts with real-time context
  - **Step 4 - LLM Processing**: Seamless Ollama integration with error handling and timeout management
  - **Step 5 - Response Generation**: Structured responses with processing metadata and performance metrics
- **Enhanced Command Processor Module** (`mcp/command_processor.py`)
  - Modular pipeline with clear separation of concerns
  - Comprehensive error handling for each pipeline stage
  - Performance monitoring with millisecond-precision timing
  - Structured logging for debugging and analytics
  - Context management for prompt template variables
- **Updated API Endpoint**: Complete redesign of `/api/command` endpoint
  - Pipeline-based processing replacing legacy implementation
  - Rich response format with success indicators and metadata
  - Processing time metrics for performance monitoring
  - Template and data fetcher execution tracking
  - Source tracking for command origin identification
- **Comprehensive Test Suite**: Complete test coverage for command processing
  - 8 new test functions in `tests/test_command_processing.py`
  - Success scenario testing with proper mocking
  - Error handling validation for all failure modes
  - Template determination and data fetcher execution testing
  - LLM integration and response formatting validation
  
### Enhanced
- **Documentation Updates**: Complete documentation refresh
  - **API Documentation**: Enhanced `/api/command` endpoint documentation with pipeline details
  - **cURL Examples**: Multiple command processing examples with expected responses
  - **Test Scripts**: Enhanced `test_api.sh` with command pipeline testing including default template creation
  - **README**: Added command processing pipeline section with architecture diagram and usage examples
- **Error Handling**: Graceful error management throughout pipeline
  - Template not found scenarios with clear error messages
  - Data fetcher execution failures with fallback handling
  - LLM communication errors with structured error responses
  - Processing timeout management with performance tracking

### Technical Architecture
- **Pipeline Integration**: Seamless integration with existing MCP architecture
  - Template system integration for dynamic prompt construction
  - Data fetcher engine integration for real-time context gathering
  - Ollama service integration with robust error handling
  - Database logging for command history and analytics
- **Performance Optimization**: Efficient processing with caching and optimization
  - Redis caching integration for data fetcher results
  - TTL management for cached data freshness
  - Parallel data fetcher execution where applicable
  - Structured response caching for repeated commands

## [0.6.0] - 2025-10-03

### Added
- **Home Assistant Status Interface**: Beautiful web-based HA entity viewer
  - **Comprehensive Entity Display**: All HA entities with state, attributes, and metadata
  - **Smart Organization**: Grouped by domain (lights, switches, sensors, etc.)  
  - **Advanced Filtering**: Real-time search and domain-based filtering
  - **Statistics Dashboard**: Entity counts, availability status, domain breakdown
  - **Responsive Design**: Mobile-friendly interface with Bootstrap 5
  - **Visual State Indicators**: Color-coded status badges for entity states
- **HA Entities API Endpoint**: New `/api/ha/entities` endpoint
  - Redis cache integration for fast entity retrieval
  - Fallback to direct HA API when cache unavailable
  - Comprehensive error handling for connection issues
  - Full entity data including state, attributes, timestamps
- **Enhanced Navigation**: Unified navigation across admin interfaces
  - Bootstrap navbar with responsive design
  - Clear navigation between Dashboard and HA Status pages
  - Visual icons and active state indicators

### Fixed
- **Critical DateTime Serialization**: Resolved 500 errors in rules API
  - Fixed datetime field conversion to ISO string format
  - Updated all CRUD endpoints (list, get, create, update)
  - Proper handling of `created_at`, `updated_at`, `last_executed` fields
  - Consistent JSON serialization across all rule endpoints

### Updated
- **Test Coverage**: Added comprehensive HA entities endpoint tests
- **Documentation**: Updated API.md with new HA entities endpoint
- **cURL Examples**: Added HA entities testing commands in curl.md
- **Test Scripts**: Enhanced test_api.sh with HA entities validation

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
