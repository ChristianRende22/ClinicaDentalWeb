import pytest

from tests.factories import crear_clinica, crear_doctor, crear_paciente


def _service(db):
    from app.services.receta_service import RecetaService

    return RecetaService(db)


def _medicamento(**campos):
    datos = {"medicamento": "Amoxicilina", "dosis": "500mg", "frecuencia": "cada 8 horas"}
    datos.update(campos)
    return datos


def test_crear_con_un_medicamento(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    receta = _service(db_session).crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "medicamentos": [_medicamento()],
        },
    )
    assert receta.id_receta is not None

    from app.repositories.receta_repository import RecetaDetalleRepository

    detalles = RecetaDetalleRepository(db_session).listar_de_receta(
        clinica.id_clinica, receta.id_receta
    )
    assert len(detalles) == 1


def test_crear_sin_medicamentos_lanza_value_error_y_no_persiste_nada(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    with pytest.raises(ValueError):
        _service(db_session).crear(
            clinica.id_clinica,
            {
                "id_paciente": paciente.id_paciente,
                "id_doctor": doctor.id_doctor,
                "medicamentos": [],
            },
        )

    from app.repositories.receta_repository import RecetaRepository

    assert RecetaRepository(db_session).listar(clinica.id_clinica) == []


def test_crear_valida_paciente_activo(db_session):
    from app.exceptions import ReferenciaInvalidaError
    from app.repositories.paciente_repository import PacienteRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    PacienteRepository(db_session).eliminar(clinica.id_clinica, paciente.id_paciente)

    with pytest.raises(ReferenciaInvalidaError):
        _service(db_session).crear(
            clinica.id_clinica,
            {
                "id_paciente": paciente.id_paciente,
                "id_doctor": doctor.id_doctor,
                "medicamentos": [_medicamento()],
            },
        )
