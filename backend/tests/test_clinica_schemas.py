import pytest
from pydantic import ValidationError


def test_clinica_create_request_rechaza_correo_invalido():
    from app.schemas.clinica import ClinicaCreateRequest

    with pytest.raises(ValidationError):
        ClinicaCreateRequest(
            nombre="Dental Test",
            admin_username="admin.test",
            correo="no-es-un-correo",
        )


def test_clinica_create_request_acepta_correo_valido():
    from app.schemas.clinica import ClinicaCreateRequest

    request = ClinicaCreateRequest(
        nombre="Dental Test",
        admin_username="admin.test",
        correo="contacto@dentaltest.com",
    )

    assert request.correo == "contacto@dentaltest.com"


def test_clinica_create_request_correo_es_opcional():
    from app.schemas.clinica import ClinicaCreateRequest

    request = ClinicaCreateRequest(nombre="Dental Test", admin_username="admin.test")

    assert request.correo is None
