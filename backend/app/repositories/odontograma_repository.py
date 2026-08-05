from sqlalchemy import select

from app.models import EstadoPiezaDental, Odontograma, PiezaDental

NUMERO_PIEZA_MINIMO = 1
NUMERO_PIEZA_MAXIMO = 32


class OdontogramaRepository:
    """No hereda BaseRepository: la unidad real de trabajo es la pieza, y el
    odontograma es solo su contenedor 1:1 con el paciente. Todos los metodos
    igual exigen id_clinica.
    """

    def __init__(self, db):
        self.db = db

    def obtener_o_crear(self, id_clinica: int, id_paciente: int) -> Odontograma:
        """Mismo patron que ConfiguracionClinicaRepository.obtener_o_crear
        (Modulo 3): se crea al vuelo la primera vez que se consulta.
        """
        stmt = select(Odontograma).where(
            Odontograma.id_clinica == id_clinica, Odontograma.id_paciente == id_paciente
        )
        odontograma = self.db.execute(stmt).scalars().first()
        if odontograma is None:
            odontograma = Odontograma(id_clinica=id_clinica, id_paciente=id_paciente)
            self.db.add(odontograma)
            self.db.flush()
        return odontograma

    def listar_piezas(self, id_clinica: int, id_paciente: int) -> list[PiezaDental]:
        """Rellena con 'sano' las piezas que no tienen fila todavia, mismo
        patron que HorarioClinicaRepository.listar_semana con
        HORARIO_POR_DEFECTO. NO persiste el relleno: solo lo devuelve.
        """
        odontograma = self.obtener_o_crear(id_clinica, id_paciente)
        stmt = select(PiezaDental).where(PiezaDental.id_odontograma == odontograma.id_odontograma)
        existentes = {p.numero_pieza: p for p in self.db.execute(stmt).scalars().all()}

        piezas = []
        for numero in range(NUMERO_PIEZA_MINIMO, NUMERO_PIEZA_MAXIMO + 1):
            if numero in existentes:
                piezas.append(existentes[numero])
            else:
                piezas.append(
                    PiezaDental(
                        id_odontograma=odontograma.id_odontograma,
                        numero_pieza=numero,
                        estado=EstadoPiezaDental.SANO,
                    )
                )
        return piezas

    def actualizar_pieza(
        self, id_clinica: int, id_paciente: int, numero_pieza: int, data: dict
    ) -> PiezaDental:
        """Upsert de una sola pieza (decision 4 del spec: el PUT del
        odontograma es parcial, no todo-o-nada como HorarioClinica).
        """
        if not (NUMERO_PIEZA_MINIMO <= numero_pieza <= NUMERO_PIEZA_MAXIMO):
            raise ValueError(
                f"numero_pieza debe estar entre {NUMERO_PIEZA_MINIMO} y {NUMERO_PIEZA_MAXIMO}"
            )

        odontograma = self.obtener_o_crear(id_clinica, id_paciente)
        stmt = select(PiezaDental).where(
            PiezaDental.id_odontograma == odontograma.id_odontograma,
            PiezaDental.numero_pieza == numero_pieza,
        )
        pieza = self.db.execute(stmt).scalars().first()
        if pieza is None:
            pieza = PiezaDental(
                id_odontograma=odontograma.id_odontograma, numero_pieza=numero_pieza
            )
            self.db.add(pieza)

        for campo, valor in data.items():
            setattr(pieza, campo, valor)
        self.db.flush()
        return pieza
