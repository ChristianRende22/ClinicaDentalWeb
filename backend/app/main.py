from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.clinicas import router as clinicas_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
app.include_router(clinicas_router)
