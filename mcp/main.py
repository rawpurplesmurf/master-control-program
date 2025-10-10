import logging
import sys
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from mcp.router import router as api_router
from mcp.database import engine, Base
from mcp.ha_websocket import start_ha_websocket_client, stop_ha_websocket_client
from mcp.health_checks import check_mysql_connection, check_redis_connection, check_home_assistant_connection, check_ollama_connection

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Configure debug logger to write to debug.log file
debug_logger = logging.getLogger('debug')
debug_handler = logging.FileHandler('debug.log')
debug_handler.setLevel(logging.ERROR)
debug_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
debug_handler.setFormatter(debug_formatter)
debug_logger.addHandler(debug_handler)
debug_logger.setLevel(logging.ERROR)

# Configure Home Assistant WebSocket logger to write to homeassistant.log
ha_logger = logging.getLogger('mcp.ha_websocket')
ha_handler = logging.FileHandler('homeassistant.log')
ha_handler.setLevel(logging.DEBUG)
ha_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ha_handler.setFormatter(ha_formatter)
ha_logger.addHandler(ha_handler)
ha_logger.setLevel(logging.DEBUG)  # Allow all levels to be logged to file

# Add console handler for HA websocket that only shows WARNING and above
ha_console_handler = logging.StreamHandler(sys.stdout)
ha_console_handler.setLevel(logging.WARNING)
ha_console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ha_console_handler.setFormatter(ha_console_formatter)
ha_logger.addHandler(ha_console_handler)

ha_logger.propagate = False  # Don't propagate to root logger

# Configure WebSocket-specific logger for verbose message details
websocket_logger = logging.getLogger('mcp.websocket')
websocket_handler = logging.FileHandler('websocket.log')
websocket_handler.setLevel(logging.DEBUG)
websocket_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
websocket_handler.setFormatter(websocket_formatter)
websocket_logger.addHandler(websocket_handler)
websocket_logger.setLevel(logging.DEBUG)
websocket_logger.propagate = False  # Don't propagate to root or console

# Set specific log levels for different components
logging.getLogger('mcp.router').setLevel(logging.INFO)
logging.getLogger('mcp.command_processor').setLevel(logging.INFO)
logging.getLogger('mcp.data_fetcher_engine').setLevel(logging.INFO)
logging.getLogger('mcp.ollama').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Reduce SQL query spam
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)   # Reduce connection pool spam
logging.getLogger('httpx').setLevel(logging.WARNING)  # Reduce HTTP request spam

# For even more detailed logging, you can enable DEBUG/INFO level when needed:
# logging.getLogger('mcp').setLevel(logging.DEBUG)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)  # Shows SQL queries
# logging.getLogger('httpx').setLevel(logging.INFO)  # Shows HTTP request details

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Main Control Program",
    description="An AI-powered controller for Home Assistant.",
    version="0.1.0"
)

# Global exception handler to catch all unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    debug_logger = logging.getLogger('debug')
    debug_logger.error(f"Unhandled exception on {request.method} {request.url}: {traceback.format_exc()}")
    
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"→ {request.method} {request.url.path} - Client: {request.client.host}")
    if request.query_params:
        logger.info(f"  Query params: {dict(request.query_params)}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"← {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

@app.on_event("startup")
async def startup_event():
    logger.info("=== Main Control Program Initializing ===")

    logger.info("[1/4] Performing System Health Checks...")
    check_mysql_connection()
    await check_redis_connection()
    await check_home_assistant_connection()
    await check_ollama_connection()

    logger.info("[2/4] Initializing Database...")
    # Create database tables if they don't exist
    # This is suitable for development, but for production, consider using migrations (e.g., Alembic)
    Base.metadata.create_all(bind=engine)
    logger.info("  - Database tables verified/created")

    logger.info("[3/4] Starting Background Services...")
    # Start Home Assistant WebSocket client
    await start_ha_websocket_client()
    logger.info("  - Home Assistant WebSocket client started")

    logger.info("[4/4] API Ready")
    logger.info("=== MCP Startup Complete. Waiting for commands ===")
    logger.info("Available endpoints:")
    logger.info("  - Admin Interface: /html/admin.html")
    logger.info("  - HA Status Dashboard: /html/ha-status.html")
    logger.info("  - API Documentation: /docs")
    logger.info("  - Command Processing: POST /api/command")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=== Shutting down MCP ===")
    await stop_ha_websocket_client()
    logger.info("Home Assistant WebSocket client stopped")
    logger.info("MCP shutdown complete")
    print("  - Background services stopped.")
    print("--- Shutdown complete. ---")

# Mount the html/ directory to serve static admin interface
app.mount("/html", StaticFiles(directory="html"), name="html")

# Include the API router
app.include_router(api_router)