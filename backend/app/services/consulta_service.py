from sqlalchemy.orm import Session

from app.exceptions import ReferenciaInvalidaError
from app.models import Consulta
from app.repositories.consulta_repository import ConsultaRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.paciente_repository import PacienteRepository


def validar_paciente_activo(pacientes: PacienteRepository, id_clinica: int, id_paciente: int) -> None:
    """Compartido por ConsultaService y RecetaService: mismo chequeo, no
    conviene tenerlo escrito dos veces.
    """
    paciente = pacientes.obtener(id_clinica, id_paciente)
    if paciente is None:
        raise ReferenciaInvalidaError("El paciente no existe en esta clinica")
    if not paciente.activo:
        raise ReferenciaInvalidaError("El paciente esta dado de baja")


def validar_doctor_activo(doctores: DoctorRepository, id_clinica: int, id_doctor: int) -> None:
    doctor = doctores.obtener(id_clinica, id_doctor)
    if doctor is None:
        raise ReferenciaInvalidaError("El doctor no existe en esta clinica")
    if not doctor.activo:
        raise ReferenciaInvalidaError("El doctor esta dado de baja")


class ConsultaService:
    """Valida paciente y doctor antes de registrar la consulta. Dos reglas,
    no siete: no amerita el patron de validadores independientes del
    Modulo 4 (ver seccion 4 del spec del Modulo 5).
    """

    def __init__(self, db: Session):
        self.db = db
        self.consultas = ConsultaRepository(db)
        self.pacientes = PacienteRepository(db)
        self.doctores = DoctorRepository(db)

    def crear(self, id_clinica: int, datos: dict) -> Consulta:
        validar_paciente_activo(self.pacientes, id_clinica, datos["id_paciente"])
        validar_doctor_activo(self.doctores, id_clinica, datos["id_doctor"])
        return self.consultas.crear(id_clinica, datos)
