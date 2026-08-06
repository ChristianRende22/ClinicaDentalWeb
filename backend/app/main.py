from fastapi import FastAPI

from app.api.routes.asistentes import router as asistentes_router
from app.api.routes.auth import router as auth_router
from app.api.routes.citas import router as citas_router
from app.api.routes.clinicas import router as clinicas_router
from app.api.routes.configuracion import router as configuracion_router
from app.api.routes.consultas import router as consultas_router
from app.api.routes.consultorios import router as consultorios_router
from app.api.routes.doctores import router as doctores_router
from app.api.routes.especialidades import router as especialidades_router
from app.api.routes.facturas import router as facturas_router
from app.api.routes.horarios import router as horarios_router
from app.api.routes.metodos_pago import router as metodos_pago_router
from app.api.routes.odontogramas import router as odontogramas_router
from app.api.routes.pacientes import router as pacientes_router
from app.api.routes.planes_tratamiento import router as planes_tratamiento_router
from app.api.routes.presupuestos import router as presupuestos_router
from app.api.routes.recetas import router as recetas_router
from app.api.routes.tratamientos import router as tratamientos_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
app.include_router(clinicas_router)
app.include_router(especialidades_router)
app.include_router(consultorios_router)
app.include_router(metodos_pago_router)
app.include_router(horarios_router)
app.include_router(configuracion_router)
app.include_router(pacientes_router)
app.include_router(doctores_router)
app.include_router(asistentes_router)
app.include_router(citas_router)
app.include_router(tratamientos_router)
app.include_router(consultas_router)
app.include_router(odontogramas_router)
app.include_router(planes_tratamiento_router)
app.include_router(presupuestos_router)
app.include_router(recetas_router)
app.include_router(facturas_router)
