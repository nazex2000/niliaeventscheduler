from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
import asyncio
from app.utils.firebase_utils import check_new_documents, check_new_documents_aemc, check_new_messages_aemc

def start_scheduler():
    scheduler = BackgroundScheduler()

    # Agendar a tarefa para rodar a cada 5 minutos
    scheduler.add_job(
        lambda: asyncio.run(check_new_documents()),
        "interval",
        minutes=5,
        id="firebase_check_job"
    )

    scheduler.add_job(
        lambda: asyncio.run(check_new_documents_aemc()),
        "interval",
        minutes=1,
        id="firebase_check_job_aemc"
    )
    
    scheduler.add_job(
        lambda: asyncio.run(check_new_messages_aemc()),
        "interval",
        minutes=1,
        id="firebase_check_job_aemc_messages"
    )
    
    scheduler.start()
    return scheduler
