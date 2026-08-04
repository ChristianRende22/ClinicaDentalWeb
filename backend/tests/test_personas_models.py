from datetime import time

import pytest
from sqlalchemy.exc import IntegrityError


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _usuario(db_session, id_clinica, username="dra.perez"):
    from app.models import RolUsuario, Usuario

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash="x",
        rol=RolUsuario.DOCTOR,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def test_paciente_nace_activo_y_sin_fecha_de_nacimiento(db_session):
    from app.models import Paciente

    clinica = _clinica(db_session)
    paciente = Paciente(
        id_clinica=clinica.id_clinica,
        nombre="Ana",
        apellido="Lopez",
        telefono="70001122",
    )
    db_session.add(paciente)
    db_session.flush()

    assert paciente.id_paciente is not None
    assert paciente.activo is True
    assert paciente.fecha_nacimiento is None
    assert paciente.correo is None


def test_paciente_no_tiene_columna_edad(db_session):
    """La edad es un dato derivado de fecha_nacimiento, no se almacena."""
    from app.models import Paciente

    assert "edad" not in Paciente.__table__.columns


def test_paciente_no_tiene_columna_id_usuario(db_session):
    """El paciente no se loguea: la clinica opera el sistema en su nombre."""
    from app.models import Paciente

    assert "id_usuario" not in Paciente.__table__.columns


def test_doctor_exige_usuario_y_admite_especialidad_nula(db_session):
    from app.models import Doctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    assert doctor.id_doctor is not None
    assert doctor.id_especialidad is None
    assert doctor.activo is True


def test_un_usuario_no_puede_tener_dos_doctores(db_session):
    from app.models import Doctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    db_session.add_all(
        [
            Doctor(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Marta",
                apellido="Perez",
                telefono="70001122",
            ),
            Doctor(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Otra",
                apellido="Persona",
                telefono="70003344",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_asistente_tambien_exige_usuario_unico(db_session):
    from app.models import Asistente

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica, "recepcion")
    db_session.add_all(
        [
            Asistente(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Rosa",
                apellido="Diaz",
                telefono="70005566",
            ),
            Asistente(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Otra",
                apellido="Persona",
                telefono="70007788",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_un_doctor_puede_tener_varios_bloques_el_mismo_dia(db_session):
    """A diferencia de HorarioClinica: el doctor atiende manana y tarde."""
    from app.models import DiaSemana, Doctor, HorarioDoctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    db_session.add_all(
        [
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(8, 0),
                hora_fin=time(12, 0),
            ),
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(14, 0),
                hora_fin=time(18, 0),
            ),
        ]
    )

    db_session.flush()  # no debe explotar


def test_dos_bloques_con_el_mismo_inicio_el_mismo_dia_violan_la_unicidad(db_session):
    from app.models import DiaSemana, Doctor, HorarioDoctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    db_session.add_all(
        [
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(8, 0),
                hora_fin=time(12, 0),
            ),
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(8, 0),
                hora_fin=time(9, 0),
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_horario_doctor_nace_disponible(db_session):
    from app.models import DiaSemana, Doctor, HorarioDoctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    bloque = HorarioDoctor(
        id_doctor=doctor.id_doctor,
        dia_semana=DiaSemana.MARTES,
        hora_inicio=time(8, 0),
        hora_fin=time(12, 0),
    )
    db_session.add(bloque)
    db_session.flush()

    assert bloque.disponible is True


def test_configuracion_gana_anticipacion_minima_con_default_24(db_session):
    from app.models import ConfiguracionClinica

    clinica = _clinica(db_session)
    config = ConfiguracionClinica(id_clinica=clinica.id_clinica)
    db_session.add(config)
    db_session.flush()

    assert config.anticipacion_minima_reserva_horas == 24
