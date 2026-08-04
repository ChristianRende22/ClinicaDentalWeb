import pytest

from tests.factories import crear_clinica


def _servicio(db_session):
    from app.services.personal_service import PersonalService

    return PersonalService(db_session)


def _datos(**campos):
    base = {
        "username": "dra.perez",
        "nombre": "Marta",
        "apellido": "Perez",
        "telefono": "70003344",
    }
    base.update(campos)
    return base


def test_crear_doctor_crea_usuario_y_perfil_juntos(db_session):
    from app.models import RolUsuario
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    perfil = resultado["perfil"]
    assert perfil.id_doctor is not None
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario is not None
    assert usuario.rol == RolUsuario.DOCTOR
    assert usuario.id_clinica == clinica.id_clinica
    assert perfil.id_usuario == usuario.id_usuario


def test_crear_doctor_devuelve_una_password_temporal_usable(db_session):
    from app.repositories.usuario_repository import UsuarioRepository
    from app.security.passwords import verify_password

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    temporal = resultado["password_temporal"]
    assert isinstance(temporal, str) and len(temporal) >= 12
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert verify_password(temporal, usuario.password_hash)


def test_el_usuario_nuevo_debe_cambiar_la_password(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)
    _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.debe_cambiar_password is True


def test_la_password_temporal_nunca_se_guarda_en_claro(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.password_hash != resultado["password_temporal"]


def test_username_repetido_lanza_error(db_session):
    from app.exceptions import UsernameYaExisteError

    clinica = crear_clinica(db_session)
    servicio = _servicio(db_session)
    servicio.crear_doctor(clinica.id_clinica, _datos())

    with pytest.raises(UsernameYaExisteError):
        servicio.crear_doctor(clinica.id_clinica, _datos(nombre="Otra"))


def test_una_especialidad_de_otra_clinica_es_referencia_invalida(db_session):
    from app.exceptions import ReferenciaInvalidaError
    from app.repositories.especialidad_repository import EspecialidadRepository

    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    de_b = EspecialidadRepository(db_session).crear(
        clinica_b.id_clinica, {"nombre": "Ortodoncia"}
    )

    with pytest.raises(ReferenciaInvalidaError):
        _servicio(db_session).crear_doctor(
            clinica_a.id_clinica, _datos(id_especialidad=de_b.id_especialidad)
        )


def test_si_el_perfil_falla_no_queda_el_usuario_huerfano(db_session, monkeypatch):
    """El test mas importante de esta task: la transaccion es real."""
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)
    servicio = _servicio(db_session)

    def _explotar(*args, **kwargs):
        raise RuntimeError("fallo al crear el perfil")

    monkeypatch.setattr(servicio.doctores, "crear", _explotar)

    with pytest.raises(RuntimeError):
        servicio.crear_doctor(clinica.id_clinica, _datos())

    assert UsuarioRepository(db_session).obtener_por_username("dra.perez") is None


def test_crear_asistente_funciona_igual_con_rol_asistente(db_session):
    from app.models import RolUsuario
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_asistente(
        clinica.id_clinica,
        {
            "username": "recepcion",
            "nombre": "Rosa",
            "apellido": "Diaz",
            "telefono": "70005566",
        },
    )

    assert resultado["perfil"].id_asistente is not None
    usuario = UsuarioRepository(db_session).obtener_por_username("recepcion")
    assert usuario.rol == RolUsuario.ASISTENTE


def test_dar_de_baja_desactiva_perfil_y_usuario(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)
    servicio = _servicio(db_session)
    perfil = servicio.crear_doctor(clinica.id_clinica, _datos())["perfil"]

    assert servicio.dar_de_baja_doctor(clinica.id_clinica, perfil.id_doctor) is True

    assert perfil.activo is False
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.activo is False


def test_dar_de_baja_un_doctor_de_otra_clinica_devuelve_false(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    servicio = _servicio(db_session)
    perfil = servicio.crear_doctor(clinica_a.id_clinica, _datos())["perfil"]

    assert servicio.dar_de_baja_doctor(clinica_b.id_clinica, perfil.id_doctor) is False
    assert perfil.activo is True
