from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import HorarioInvalidoError
from app.models import DiaSemana, HorarioClinica

_ORDEN_DIAS = {dia: indice for indice, dia in enumerate(DiaSemana)}


class HorarioClinicaRepository:
    """Horario de atencion de la clinica, una fila por dia.

    NO hereda de BaseRepository porque la llave es compuesta
    (id_clinica + dia_semana), no un int simple como asume esa firma. Misma
    excepcion documentada que ClinicaModuloRepository. Aun asi, todos sus
    metodos exigen id_clinica como primer parametro.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _validar_dia(dia: dict) -> None:
        if dia.get("cerrado", False):
            return

        apertura = dia.get("hora_apertura")
        cierre = dia.get("hora_cierre")
        nombre_dia = dia["dia_semana"].value

        if apertura is None or cierre is None:
            raise HorarioInvalidoError(
                f"{nombre_dia}: un dia abierto necesita hora de apertura y de cierre"
            )
        if cierre <= apertura:
            raise HorarioInvalidoError(
                f"{nombre_dia}: la hora de cierre debe ser posterior a la de apertura"
            )

    def listar_semana(self, id_clinica: int) -> list[HorarioClinica]:
        stmt = select(HorarioClinica).where(HorarioClinica.id_clinica == id_clinica)
        filas = list(self.db.execute(stmt).scalars().all())
        return sorted(filas, key=lambda fila: _ORDEN_DIAS[fila.dia_semana])

    def reemplazar_semana(self, id_clinica: int, dias: list[dict]) -> list[HorarioClinica]:
        """Upsert de los dias recibidos. Valida TODOS antes de escribir ninguno,
        para que un dia invalido no deje la semana a medias.
        """
        for dia in dias:
            self._validar_dia(dia)

        existentes = {fila.dia_semana: fila for fila in self.listar_semana(id_clinica)}

        for dia in dias:
            cerrado = dia.get("cerrado", False)
            apertura = None if cerrado else dia.get("hora_apertura")
            cierre = None if cerrado else dia.get("hora_cierre")

            fila = existentes.get(dia["dia_semana"])
            if fila is None:
                fila = HorarioClinica(
                    id_clinica=id_clinica,
                    dia_semana=dia["dia_semana"],
                    hora_apertura=apertura,
                    hora_cierre=cierre,
                    cerrado=cerrado,
                )
                self.db.add(fila)
            else:
                fila.hora_apertura = apertura
                fila.hora_cierre = cierre
                fila.cerrado = cerrado

        self.db.flush()
        return self.listar_semana(id_clinica)
