from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.models import ESTADOS_ACTIVOS, Cita, Doctor, EstadoCita
from app.repositories.base import BaseRepository

#: Duracion maxima que puede tener una cita, en minutos. Es el mismo tope que
#: valida el schema CitaCreate (5 a 480, o sea hasta 8 horas).
#:
#: El prefiltro de _solapadas necesita este numero: para encontrar todas las
#: citas que puedan pisar un rango dado, alcanza con mirar las que empiezan
#: hasta DURACION_MAXIMA_MINUTOS antes del inicio de ese rango. Una cita que
#: empiece antes que eso ya termino con seguridad.
#:
#: Si alguna vez se sube el tope del schema, hay que subir este numero tambien
#: o el prefiltro empieza a dejar afuera solapamientos reales.
DURACION_MAXIMA_MINUTOS = 480


class CitaRepository(BaseRepository[Cita]):
    """CRUD de citas mas las consultas de agenda y solapamiento.

    Los metodos de solapamiento viven aca y no en los validadores porque son
    consultas, no reglas: el validador decide que hacer con la respuesta.
    """

    def listar(
        self,
        id_clinica: int,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        id_doctor: int | None = None,
        id_paciente: int | None = None,
        estado: EstadoCita | None = None,
    ) -> list[Cita]:
        stmt = select(Cita).where(Cita.id_clinica == id_clinica)
        if desde is not None:
            stmt = stmt.where(Cita.fecha_hora >= desde)
        if hasta is not None:
            stmt = stmt.where(Cita.fecha_hora <= hasta)
        if id_doctor is not None:
            stmt = stmt.where(Cita.id_doctor == id_doctor)
        if id_paciente is not None:
            stmt = stmt.where(Cita.id_paciente == id_paciente)
        if estado is not None:
            stmt = stmt.where(Cita.estado == estado)
        stmt = stmt.order_by(Cita.fecha_hora)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Cita | None:
        stmt = select(Cita).where(Cita.id_cita == id_, Cita.id_clinica == id_clinica)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Cita:
        cita = Cita(id_clinica=id_clinica, **data)
        self.db.add(cita)
        self.db.flush()
        return cita

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Cita | None:
        cita = self.obtener(id_clinica, id_)
        if cita is None:
            return None
        for campo, valor in data.items():
            setattr(cita, campo, valor)
        self.db.flush()
        return cita

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Una cita no se borra, se cancela.

        Borrarla perderia el registro de que existio, que es justamente lo que la
        clinica necesita para el historial del paciente y para las metricas del
        Modulo 7. Se implementa para cumplir el contrato de BaseRepository y se
        niega explicitamente, en vez de dejar un metodo que silenciosamente
        destruya datos.
        """
        raise NotImplementedError(
            "Las citas no se borran: usar CitaService.cancelar()"
        )

    def _solapadas(self, id_clinica: int, inicio: datetime, fin: datetime, excluir_id_cita):
        """Condicion clasica de solapamiento: inicio_a < fin_b AND inicio_b < fin_a.

        Como la duracion se guarda en minutos y no hay columna fecha_fin, el fin
        de cada cita hay que calcularlo sumando duracion_minutos. Eso se hace en
        Python y no en SQL porque la aritmetica de fechas tiene sintaxis distinta
        en SQLite y en MySQL, y no queremos que el comportamiento difiera entre
        los tests y produccion.

        Para no traer toda la tabla a Python, primero se prefiltra en SQL por
        clinica, estado y una ventana de fechas. La ventana hacia atras es
        DURACION_MAXIMA_MINUTOS y no un numero al azar: una cita que empieza
        antes que eso ya termino con seguridad, asi que no puede pisar el rango
        consultado. Si el tope de duracion sube, este prefiltro empieza a dejar
        afuera solapamientos reales — por eso son la misma constante.
        """
        margen = timedelta(minutes=DURACION_MAXIMA_MINUTOS)
        stmt = select(Cita).where(
            Cita.id_clinica == id_clinica,
            Cita.estado.in_(ESTADOS_ACTIVOS),
            Cita.fecha_hora >= inicio - margen,
            Cita.fecha_hora <= fin + margen,
        )
        if excluir_id_cita is not None:
            stmt = stmt.where(Cita.id_cita != excluir_id_cita)
        candidatas = self.db.execute(stmt).scalars().all()
        return [
            c
            for c in candidatas
            if c.fecha_hora < fin
            and inicio < c.fecha_hora + timedelta(minutes=c.duracion_minutos)
        ]

    def hay_solapamiento_de_doctor(
        self,
        id_clinica: int,
        id_doctor: int,
        inicio: datetime,
        fin: datetime,
        excluir_id_cita: int | None = None,
    ) -> bool:
        solapadas = self._solapadas(id_clinica, inicio, fin, excluir_id_cita)
        return any(c.id_doctor == id_doctor for c in solapadas)

    def hay_solapamiento_de_consultorio(
        self,
        id_clinica: int,
        id_consultorio: int,
        inicio: datetime,
        fin: datetime,
        excluir_id_cita: int | None = None,
    ) -> bool:
        solapadas = self._solapadas(id_clinica, inicio, fin, excluir_id_cita)
        return any(c.id_consultorio == id_consultorio for c in solapadas)

    def resumen_por_estado(
        self,
        id_clinica: int,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        id_doctor: int | None = None,
        incluir_por_doctor: bool = True,
    ) -> dict:
        """Cuenta citas agrupadas por estado (y opcionalmente por doctor) para
        el dashboard del Modulo 7. Mismos filtros que listar(), pero agregados
        en SQL con GROUP BY en vez de traer las filas y contarlas en Python.
        """
        filtros = [Cita.id_clinica == id_clinica]
        if desde is not None:
            filtros.append(Cita.fecha_hora >= desde)
        if hasta is not None:
            filtros.append(Cita.fecha_hora <= hasta)
        if id_doctor is not None:
            filtros.append(Cita.id_doctor == id_doctor)

        stmt_estado = (
            select(Cita.estado, func.count(Cita.id_cita)).where(*filtros).group_by(Cita.estado)
        )
        por_estado = {estado.value: 0 for estado in EstadoCita}
        total = 0
        for estado, conteo in self.db.execute(stmt_estado).all():
            por_estado[estado.value] = conteo
            total += conteo

        por_doctor: list[dict] = []
        if incluir_por_doctor:
            stmt_doctor = (
                select(Cita.id_doctor, Doctor.nombre, Doctor.apellido, Cita.estado, func.count(Cita.id_cita))
                .join(Doctor, Cita.id_doctor == Doctor.id_doctor)
                .where(*filtros)
                .group_by(Cita.id_doctor, Doctor.nombre, Doctor.apellido, Cita.estado)
            )
            acumulado: dict[int, dict] = {}
            for id_doc, nombre, apellido, estado, conteo in self.db.execute(stmt_doctor).all():
                entrada = acumulado.setdefault(
                    id_doc,
                    {
                        "id_doctor": id_doc,
                        "nombre": f"{nombre} {apellido}",
                        "total": 0,
                        "por_estado": {e.value: 0 for e in EstadoCita},
                    },
                )
                entrada["por_estado"][estado.value] = conteo
                entrada["total"] += conteo
            por_doctor = sorted(acumulado.values(), key=lambda d: d["id_doctor"])

        return {"total": total, "por_estado": por_estado, "por_doctor": por_doctor}
