from sqlalchemy.orm import Session

from app.models import Receta
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.receta_repository import RecetaDetalleRepository, RecetaRepository
from app.services.consulta_service import validar_doctor_activo, validar_paciente_activo


class RecetaService:
    """Alta transaccional de Receta + sus RecetaDetalle, copiando el patron
    de PersonalService.crear_doctor: una receta sin medicamentos no es un
    estado intermedio valido, asi que se crean juntos o no se crea ninguno.
    """

    def __init__(self, db: Session):
        self.db = db
        self.recetas = RecetaRepository(db)
        self.detalles = RecetaDetalleRepository(db)
        self.pacientes = PacienteRepository(db)
        self.doctores = DoctorRepository(db)

    def crear(self, id_clinica: int, datos: dict) -> Receta:
        medicamentos = datos.get("medicamentos") or []
        if not medicamentos:
            raise ValueError("Una receta necesita al menos un medicamento")

        validar_paciente_activo(self.pacientes, id_clinica, datos["id_paciente"])
        validar_doctor_activo(self.doctores, id_clinica, datos["id_doctor"])

        campos_receta = {
            k: v for k, v in datos.items() if k != "medicamentos"
        }
        try:
            receta = self.recetas.crear(id_clinica, campos_receta)
            for medicamento in medicamentos:
                self.detalles.crear(receta.id_receta, medicamento)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return receta
