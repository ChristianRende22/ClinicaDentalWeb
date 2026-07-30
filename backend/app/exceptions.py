class InvalidCredentialsError(Exception):
    """El usuario no existe, esta inactivo, o la contrasena no coincide."""


class ClinicaInactivaError(Exception):
    """La clinica del usuario no esta en estado 'activa'."""


class UsernameYaExisteError(Exception):
    """Ya existe un Usuario con ese username."""
