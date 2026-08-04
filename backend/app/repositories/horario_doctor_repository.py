from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.exceptions import HorarioInvalidoError
from app.models import DiaSemana, Doctor, HorarioDoctor

#: Orden natural de la semana, para ordenar en SQL sin depender de como el
#: motor ordene el tipo ENUM (SQLite lo guarda como texto y ordenaria alfabetico).
_ORDEN_DIA = {dia: indice for indice, dia in enumerate(DiaSemana)}


class HorarioDoctorRepository:
    """Bloques de disponibilidad de un doctor.

    NO hereda de BaseRepository: es un recurso anidado bajo doctor, su identidad
    es (id_clinica, id_doctor) mas el bloque, no un int simple como asume la
    firma de la clase base. Misma excepcion documentada que
    HorarioClinicaRepository y ConfiguracionClinicaRepository.

    Igual exige id_clinica como primer parametro, y lo aplica verificando que el
    doctor pertenezca a esa clinica antes de tocar nada.
    """

    def __init__(self, db: Session):
        self.db = db

    def _doctor_de_la_clinica(self, id_clinica: int, id_doctor: int) -> Doctor | None:
        stmt = select(Doctor).where(
            Doctor.id_doctor == id_doctor, Doctor.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def listar_de_doctor(self, id_clinica: int, id_doctor: int) -> list[HorarioDoctor]:
        """Lista vacia si el doctor no existe o es de otra clinica."""
        if self._doctor_de_la_clinica(id_clinica, id_doctor) is None:
            return []
        stmt = select(HorarioDoctor).where(HorarioDoctor.id_doctor == id_doctor)
        bloques = list(self.db.execute(stmt).scalars().all())
        # Ordenar en Python y no en SQL: el ENUM se guarda como texto y el motor
        # ordenaria alfabeticamente (domingo antes que lunes).
        bloques.sort(key=lambda b: (_ORDEN_DIA[b.dia_semana], b.hora_inicio))
        return bloques

    @staticmethod
    def _validar(bloques: list[dict]) -> None:
        """Valida TODOS los bloques antes de que se escriba ninguno, para que el
        horario no pueda quedar en un estado intermedio inconsistente.
        """
        for bloque in bloques:
            if bloque["hora_fin"] <= bloque["hora_inicio"]:
                raise HorarioInvalidoError(
                    f"{bloque['dia_semana'].value}: la hora de fin debe ser posterior "
                    f"a la de inicio"
                )

        por_dia: dict[DiaSemana, list[dict]] = {}
        for bloque in bloques:
            por_dia.setdefault(bloque["dia_semana"], []).append(bloque)

        for dia, del_dia in por_dia.items():
            ordenados = sorted(del_dia, key=lambda b: b["hora_inicio"])
            for anterior, siguiente in zip(ordenados, ordenados[1:]):
                if siguiente["hora_inicio"] < anterior["hora_fin"]:
                    raise HorarioInvalidoError(
                        f"{dia.value}: hay dos bloques solapados"
                    )

    def reemplazar_de_doctor(
        self, id_clinica: int, id_doctor: int, bloques: list[dict]
    ) -> list[HorarioDoctor]:
        """Reemplaza el conjunto completo de bloques del doctor.

        Devuelve lista vacia sin tocar nada si el doctor es de otra clinica.
        """
        if self._doctor_de_la_clinica(id_clinica, id_doctor) is None:
            return []

        self._validar(bloques)

        self.db.execute(delete(HorarioDoctor).where(HorarioDoctor.id_doctor == id_doctor))
        for bloque in bloques:
            self.db.add(HorarioDoctor(id_doctor=id_doctor, **bloque))
        self.db.flush()
        return self.listar_de_doctor(id_clinica, id_doctor)
