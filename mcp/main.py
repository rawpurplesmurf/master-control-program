import logging
import sys
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from mcp.router import router as api_router
from mcp.database import engine, Base
from mcp.home_assistant import poll_home_assistant
from mcp.health_checks import check_mysql_connection, check_redis_connection, check_home_assistant_connection, check_ollama_connection

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

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

scheduler = AsyncIOScheduler()

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
    # Start background polling task
    scheduler.add_job(poll_home_assistant, 'interval', minutes=30)
    scheduler.start()
    logger.info("  - APScheduler started for background tasks")
    # Run once on startup
    await poll_home_assistant()

    logger.info("[4/4] API Ready")
    logger.info("=== MCP Startup Complete. Waiting for commands ===")
    logger.info("Available endpoints:")
    logger.info("  - Admin Interface: /html/admin.html")
    logger.info("  - HA Status Dashboard: /html/ha-status.html")
    logger.info("  - API Documentation: /docs")
    logger.info("  - Command Processing: POST /api/command")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("=== Shutting down MCP ===")
    scheduler.shutdown()
    logger.info("Scheduler stopped")
    logger.info("MCP shutdown complete")
    print("  - Background services stopped.")
    print("--- Shutdown complete. ---")

# Mount the html/ directory to serve static admin interface
app.mount("/html", StaticFiles(directory="html"), name="html")

# Include the API router
app.include_router(api_router)