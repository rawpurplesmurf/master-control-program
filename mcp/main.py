from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from mcp.router import router as api_router
from mcp.database import engine, Base
from mcp.home_assistant import poll_home_assistant
from mcp.health_checks import check_mysql_connection, check_redis_connection, check_home_assistant_connection, check_ollama_connection

app = FastAPI(
    title="Main Control Program",
    description="An AI-powered controller for Home Assistant.",
    version="0.1.0"
)

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    print("--- Main Control Program Initializing ---")

    print("\n[1/4] Performing System Health Checks...")
    check_mysql_connection()
    await check_redis_connection()
    await check_home_assistant_connection()
    await check_ollama_connection()

    print("\n[2/4] Initializing Database...")
    # Create database tables if they don't exist
    # This is suitable for development, but for production, consider using migrations (e.g., Alembic)
    Base.metadata.create_all(bind=engine)
    print("  - Database tables verified/created.")

    print("\n[3/4] Starting Background Services...")
    # Start background polling task
    scheduler.add_job(poll_home_assistant, 'interval', minutes=30)
    scheduler.start()
    print("  - APScheduler started for background tasks.")
    # Run once on startup
    await poll_home_assistant()

    print("\n[4/4] API Ready.")
    print("\n--- MCP Startup Complete. Waiting for commands. ---")

@app.on_event("shutdown")
def shutdown_event():
    print("\n--- Shutting down MCP ---")
    scheduler.shutdown()
    print("  - Background services stopped.")
    print("--- Shutdown complete. ---")

# Mount the html/ directory to serve static admin interface
app.mount("/html", StaticFiles(directory="html"), name="html")

# Include the API router
app.include_router(api_router)