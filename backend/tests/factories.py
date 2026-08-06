"""Helpers compartidos por los tests del Modulo 4 y del Modulo 5.

Todos hacen flush(), no commit(): quien necesite persistir de verdad (los tests
de rutas, que corren el endpoint en otro hilo) hace el commit explicito.
"""
import itertools
from datetime import datetime, timedelta

_contador_username = itertools.count(1)


def crear_clinica(db, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db.add(clinica)
    db.flush()
    return clinica


def crear_usuario(db, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash="hash-de-mentira",
        rol=rol,
    )
    db.add(usuario)
    db.flush()
    return usuario


def token_de(usuario) -> str:
    from app.security.jwt import create_access_token

    return create_access_token(
        data={
            "sub": str(usuario.id_usuario),
            "id_clinica": usuario.id_clinica,
            "rol": usuario.rol.value,
        },
        expires_delta=timedelta(minutes=10),
    )


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def headers_de(db, id_clinica, rol):
    """Crea un usuario nuevo con ese rol (username con sufijo unico, para no
    chocar con la unicidad global de username -- Modulo 1) y devuelve el
    header Authorization ya armado. Usado por los tests de rutas del
    Modulo 5 en vez de repetir este bloque en cada archivo.

    Para superadmin, ademas agrega X-Clinica-Id: un superadmin no tiene
    id_clinica propio y necesita indicar sobre cual clinica opera.
    """
    n = next(_contador_username)
    usuario = crear_usuario(
        db, rol, id_clinica if rol.value != "superadmin" else None, username=f"user.{rol.value}.{n}"
    )
    headers = auth(token_de(usuario))
    if rol.value == "superadmin":
        headers["X-Clinica-Id"] = str(id_clinica)
    return headers


def crear_paciente(db, id_clinica, **campos):
    from app.models import Paciente

    datos = {"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"}
    datos.update(campos)
    paciente = Paciente(id_clinica=id_clinica, **datos)
    db.add(paciente)
    db.flush()
    return paciente


def crear_doctor(db, id_clinica, username="dra.perez", **campos):
    from app.models import Doctor, RolUsuario

    usuario = crear_usuario(db, RolUsuario.DOCTOR, id_clinica, username)
    datos = {"nombre": "Marta", "apellido": "Perez", "telefono": "70003344"}
    datos.update(campos)
    doctor = Doctor(id_clinica=id_clinica, id_usuario=usuario.id_usuario, **datos)
    db.add(doctor)
    db.flush()
    return doctor


def crear_asistente(db, id_clinica, username="recepcion", **campos):
    from app.models import Asistente, RolUsuario

    usuario = crear_usuario(db, RolUsuario.ASISTENTE, id_clinica, username)
    datos = {"nombre": "Rosa", "apellido": "Diaz", "telefono": "70005566"}
    datos.update(campos)
    asistente = Asistente(id_clinica=id_clinica, id_usuario=usuario.id_usuario, **datos)
    db.add(asistente)
    db.flush()
    return asistente


def crear_cita(db, id_clinica, id_paciente, id_doctor, **campos):
    from app.models import Cita

    datos = {"fecha_hora": datetime(2026, 9, 1, 9, 0), "duracion_minutos": 30}
    datos.update(campos)
    cita = Cita(
        id_clinica=id_clinica,
        id_paciente=id_paciente,
        id_doctor=id_doctor,
        **datos,
    )
    db.add(cita)
    db.flush()
    return cita


def crear_tratamiento(db, id_clinica, **campos):
    from app.models import Tratamiento

    datos = {"nombre": "Limpieza dental", "precio": "25.00"}
    datos.update(campos)
    tratamiento = Tratamiento(id_clinica=id_clinica, **datos)
    db.add(tratamiento)
    db.flush()
    return tratamiento


def crear_metodo_pago(db, id_clinica, **campos):
    from app.models import MetodoPago

    datos = {"nombre": "Efectivo"}
    datos.update(campos)
    metodo = MetodoPago(id_clinica=id_clinica, **datos)
    db.add(metodo)
    db.flush()
    return metodo


def crear_plan_aceptado_con_presupuesto(db, id_clinica, id_paciente, id_doctor, id_tratamiento, cantidad=1):
    """Arma un PlanTratamiento con un detalle y su Presupuesto ya en estado
    ACEPTADO -- el punto de partida que FacturaService.generar_desde_presupuesto
    necesita.
    """
    from decimal import Decimal

    from app.models import (
        EstadoPresupuesto,
        PlanTratamiento,
        PlanTratamientoDetalle,
        Presupuesto,
        Tratamiento,
    )

    plan = PlanTratamiento(id_clinica=id_clinica, id_paciente=id_paciente, id_doctor=id_doctor)
    db.add(plan)
    db.flush()

    tratamiento = db.get(Tratamiento, id_tratamiento)
    detalle = PlanTratamientoDetalle(
        id_plan=plan.id_plan,
        id_tratamiento=id_tratamiento,
        cantidad=cantidad,
        precio_unitario=tratamiento.precio,
    )
    db.add(detalle)

    presupuesto = Presupuesto(
        id_clinica=id_clinica,
        id_plan=plan.id_plan,
        monto_total=str(Decimal(str(tratamiento.precio)) * cantidad),
        estado=EstadoPresupuesto.ACEPTADO,
    )
    db.add(presupuesto)
    db.flush()
    return plan, detalle, presupuesto
