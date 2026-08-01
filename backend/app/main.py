from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.clinicas import router as clinicas_router
from app.api.routes.configuracion import router as configuracion_router
from app.api.routes.consultorios import router as consultorios_router
from app.api.routes.especialidades import router as especialidades_router
from app.api.routes.horarios import router as horarios_router
from app.api.routes.metodos_pago import router as metodos_pago_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
app.include_router(clinicas_router)
app.include_router(especialidades_router)
app.include_router(consultorios_router)
app.include_router(metodos_pago_router)
app.include_router(horarios_router)
app.include_router(configuracion_router)
