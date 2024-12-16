from fastapi import FastAPI
from app.scheduler import start_scheduler

app = FastAPI()

# Iniciar o scheduler
scheduler = start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    # Parar o scheduler ao encerrar o app
    scheduler.shutdown()

@app.get("/")
async def root():
    return {"message": "FastAPI Firebase Scheduler is running"}
