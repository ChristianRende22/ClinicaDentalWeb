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
