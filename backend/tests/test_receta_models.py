from tests.factories import crear_clinica, crear_doctor, crear_paciente


def test_receta_id_consulta_opcional(db_session):
    from app.models import Receta

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    receta = Receta(
        id_clinica=clinica.id_clinica,
        id_paciente=paciente.id_paciente,
        id_doctor=doctor.id_doctor,
    )
    db_session.add(receta)
    db_session.flush()
    assert receta.id_consulta is None
    assert receta.indicaciones_generales is None


def test_receta_detalle_campos_requeridos(db_session):
    from app.models import Receta, RecetaDetalle

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    receta = Receta(
        id_clinica=clinica.id_clinica,
        id_paciente=paciente.id_paciente,
        id_doctor=doctor.id_doctor,
    )
    db_session.add(receta)
    db_session.flush()

    detalle = RecetaDetalle(
        id_receta=receta.id_receta,
        medicamento="Amoxicilina",
        dosis="500mg",
        frecuencia="cada 8 horas",
    )
    db_session.add(detalle)
    db_session.flush()
    assert detalle.duracion is None
    assert detalle.indicaciones is None
