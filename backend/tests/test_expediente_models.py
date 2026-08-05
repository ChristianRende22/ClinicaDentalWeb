from datetime import datetime

from tests.factories import crear_clinica, crear_doctor, crear_paciente


def crear_tratamiento(db, id_clinica, **campos):
    from app.models import Tratamiento

    datos = {"nombre": "Limpieza dental", "precio": "25.00"}
    datos.update(campos)
    tratamiento = Tratamiento(id_clinica=id_clinica, **datos)
    db.add(tratamiento)
    db.flush()
    return tratamiento


def crear_consulta(db, id_clinica, id_paciente, id_doctor, **campos):
    from app.models import Consulta

    datos = {"fecha_hora": datetime(2026, 9, 1, 10, 0)}
    datos.update(campos)
    consulta = Consulta(
        id_clinica=id_clinica, id_paciente=id_paciente, id_doctor=id_doctor, **datos
    )
    db.add(consulta)
    db.flush()
    return consulta


def test_tratamiento_defaults(db_session):
    clinica = crear_clinica(db_session)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    assert tratamiento.activo is True
    assert tratamiento.descripcion is None
    assert tratamiento.duracion_minutos_estimada is None


def test_tratamiento_nombre_unico_por_clinica(db_session):
    from sqlalchemy.exc import IntegrityError

    clinica = crear_clinica(db_session)
    crear_tratamiento(db_session, clinica.id_clinica, nombre="Limpieza")
    try:
        crear_tratamiento(db_session, clinica.id_clinica, nombre="Limpieza")
        assert False, "debia lanzar IntegrityError"
    except IntegrityError:
        db_session.rollback()


def test_consulta_defaults_y_relaciones(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    consulta = crear_consulta(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    assert consulta.id_cita is None
    assert consulta.motivo is None
    assert consulta.notas is None


def test_diagnostico_pieza_numero_opcional(db_session):
    from app.models import Diagnostico

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    consulta = crear_consulta(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    diagnostico = Diagnostico(
        id_clinica=clinica.id_clinica,
        id_consulta=consulta.id_consulta,
        descripcion="Caries en molar",
    )
    db_session.add(diagnostico)
    db_session.flush()
    assert diagnostico.pieza_numero is None


def test_odontograma_uno_por_paciente(db_session):
    from sqlalchemy.exc import IntegrityError

    from app.models import Odontograma

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)

    db_session.add(Odontograma(id_clinica=clinica.id_clinica, id_paciente=paciente.id_paciente))
    db_session.flush()
    try:
        db_session.add(
            Odontograma(id_clinica=clinica.id_clinica, id_paciente=paciente.id_paciente)
        )
        db_session.flush()
        assert False, "debia lanzar IntegrityError"
    except IntegrityError:
        db_session.rollback()


def test_pieza_dental_estado_default_sano_y_values_callable(db_session):
    from app.models import EstadoPiezaDental, Odontograma, PiezaDental

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    odontograma = Odontograma(id_clinica=clinica.id_clinica, id_paciente=paciente.id_paciente)
    db_session.add(odontograma)
    db_session.flush()

    pieza = PiezaDental(id_odontograma=odontograma.id_odontograma, numero_pieza=8)
    db_session.add(pieza)
    db_session.flush()
    db_session.refresh(pieza)

    assert pieza.estado == EstadoPiezaDental.SANO
    # values_callable: lo que se guarda es el .value en minusculas, no el .name
    assert pieza.estado.value == "sano"


def test_pieza_dental_unica_por_odontograma_y_numero(db_session):
    from sqlalchemy.exc import IntegrityError

    from app.models import Odontograma, PiezaDental

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    odontograma = Odontograma(id_clinica=clinica.id_clinica, id_paciente=paciente.id_paciente)
    db_session.add(odontograma)
    db_session.flush()

    db_session.add(PiezaDental(id_odontograma=odontograma.id_odontograma, numero_pieza=8))
    db_session.flush()
    try:
        db_session.add(
            PiezaDental(id_odontograma=odontograma.id_odontograma, numero_pieza=8)
        )
        db_session.flush()
        assert False, "debia lanzar IntegrityError"
    except IntegrityError:
        db_session.rollback()
