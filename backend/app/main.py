from fastapi import FastAPI

from app.api.routes.auth import router as auth_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
