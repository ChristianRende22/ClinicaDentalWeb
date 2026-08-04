class InvalidCredentialsError(Exception):
    """El usuario no existe, esta inactivo, o la contrasena no coincide."""


class ClinicaInactivaError(Exception):
    """La clinica del usuario no esta en estado 'activa'."""


class UsernameYaExisteError(Exception):
    """Ya existe un Usuario con ese username."""


class NombreDuplicadoEnClinicaError(Exception):
    """Ya existe un registro con ese nombre en esa clinica."""


class HorarioInvalidoError(Exception):
    """El horario de un dia es incoherente (cierre <= apertura, o falta una hora)."""


class ReferenciaInvalidaError(Exception):
    """Una FK apunta a algo que no existe, esta inactivo, o es de otra clinica."""


class CitaEnElPasadoError(Exception):
    """La fecha y hora de la cita ya paso."""


class AnticipacionInsuficienteError(Exception):
    """No se respeta la anticipacion minima configurada por la clinica."""


class FueraDeHorarioClinicaError(Exception):
    """La cita no cae dentro del horario de atencion de la clinica."""


class DoctorNoDisponibleError(Exception):
    """El doctor no tiene un bloque disponible que cubra ese horario."""


class ChoqueDeCitaError(Exception):
    """Ya hay una cita solapada para ese doctor o ese consultorio."""


class TransicionInvalidaError(Exception):
    """El estado actual de la cita no admite esa transicion."""
