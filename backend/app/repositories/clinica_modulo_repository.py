from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClinicaModulo

MODULOS_DISPONIBLES = [
    "pacientes",
    "citas",
    "odontogramas",
    "presupuestos",
    "recetas",
    "facturacion",
    "dashboards",
    "notificaciones",
]


class ClinicaModuloRepository:
    """No hereda de BaseRepository: la llave de ClinicaModulo es compuesta
    (id_clinica + modulo, un string), no un int como asume BaseRepository.
    Igual exige id_clinica como primer parametro en todos sus metodos.
    """

    def __init__(self, db: Session):
        self.db = db

    def sembrar_modulos_default(self, id_clinica: int) -> None:
        for modulo in MODULOS_DISPONIBLES:
            self.db.add(
                ClinicaModulo(id_clinica=id_clinica, modulo=modulo, habilitado=True)
            )
        self.db.flush()

    def listar(self, id_clinica: int) -> list[ClinicaModulo]:
        stmt = select(ClinicaModulo).where(ClinicaModulo.id_clinica == id_clinica)
        return list(self.db.execute(stmt).scalars().all())

    def actualizar_estado(
        self, id_clinica: int, modulo: str, habilitado: bool
    ) -> ClinicaModulo | None:
        registro = self.db.get(ClinicaModulo, (id_clinica, modulo))
        if registro is None:
            return None
        registro.habilitado = habilitado
        self.db.flush()
        return registro
