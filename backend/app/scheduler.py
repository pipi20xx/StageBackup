from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from .database import SQLALCHEMY_DATABASE_URL

# Configure job store to use our existing SQLite database
jobstores = {
    'default': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URL)
}

executors = {
    'default': ThreadPoolExecutor(20)
}

job_defaults = {
    'coalesce': False,
    'max_instances': 1
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("APScheduler started.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("APScheduler shut down.")
