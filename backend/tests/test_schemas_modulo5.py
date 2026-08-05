import pytest
from pydantic import ValidationError


def test_tratamiento_create_rechaza_precio_no_positivo():
    from app.schemas.tratamiento import TratamientoCreate

    with pytest.raises(ValidationError):
        TratamientoCreate(nombre="Limpieza", precio="0")
    with pytest.raises(ValidationError):
        TratamientoCreate(nombre="Limpieza", precio="-5")


def test_tratamiento_create_rechaza_nombre_vacio():
    from app.schemas.tratamiento import TratamientoCreate

    with pytest.raises(ValidationError):
        TratamientoCreate(nombre="   ", precio="10")


def test_tratamiento_update_rechaza_null_explicito_en_activo():
    from app.schemas.tratamiento import TratamientoUpdate

    with pytest.raises(ValidationError):
        TratamientoUpdate(activo=None)
    # Pero omitir el campo (no mandarlo) es valido.
    TratamientoUpdate()


def test_detalle_create_exige_cantidad_al_menos_uno():
    from app.schemas.plan_tratamiento import DetalleCreate

    with pytest.raises(ValidationError):
        DetalleCreate(id_tratamiento=1, cantidad=0)


def test_receta_create_exige_al_menos_un_medicamento():
    from app.schemas.receta import RecetaCreate

    with pytest.raises(ValidationError):
        RecetaCreate(id_paciente=1, id_doctor=1, medicamentos=[])


def test_pieza_dental_item_request_numero_pieza_acotado():
    from app.schemas.odontograma import PiezaDentalItemRequest

    with pytest.raises(ValidationError):
        PiezaDentalItemRequest(numero_pieza=33, estado="sano")
    with pytest.raises(ValidationError):
        PiezaDentalItemRequest(numero_pieza=0, estado="sano")
    PiezaDentalItemRequest(numero_pieza=32, estado="sano")
