import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database import engine, Base, SessionLocal
from .models import BackupProject, BackupSchedule, BackupHistory
from .scheduler import start_scheduler, shutdown_scheduler
from .schema_check import ensure_schema_updates
from . import api

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 0. Ensure Directories and Schema
    os.makedirs("/data/cache", exist_ok=True)
    ensure_schema_updates()

    # Startup: 1. Clean up zombie tasks
    db = SessionLocal()
    try:
        zombies = db.query(BackupHistory).filter(BackupHistory.status == "running").all()
        if zombies:
            print(f"Found {len(zombies)} zombie tasks. Resetting...")
            for task in zombies:
                task.status = "failed"
                task.log_message = "系统重启，任务意外中断"
            db.commit()
    except Exception as e:
        print(f"Error cleaning zombies: {e}")
    finally:
        db.close()

    # Startup: 2. Start the scheduler
    start_scheduler()
    yield
    # Shutdown: Stop the scheduler
    shutdown_scheduler()

app = FastAPI(title="Backup System API", version="1.0.0", lifespan=lifespan)

app.include_router(api.router)

@app.get("/")
def read_root():
    return {"status": "online", "system": "Backup Agent"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
