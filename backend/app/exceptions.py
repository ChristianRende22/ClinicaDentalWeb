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
    """El estado actual de la cita (o del plan de tratamiento) no admite esa transicion."""


class ReferenciaEnUsoError(Exception):
    """No se puede dar de baja: algo activo depende de este registro.

    Distinta de ReferenciaInvalidaError (que es sobre una FK que APUNTA a un
    registro invalido). Esta es al reves: alguien quiere dar de baja un
    registro al que otros le APUNTAN activamente. Nace de la decision de
    politica que quedo pendiente al cerrar el Modulo 4 (ver seccion 11 del
    spec de ese modulo): bloquear la baja si hay referencias activas, en vez
    de dejarla en el aire o cancelar en cascada.
    """


class PresupuestoNoAceptadoError(Exception):
    """No se puede generar una factura: el presupuesto de este plan todavia
    no fue aceptado por el paciente."""


class FacturaConPagosError(Exception):
    """No se puede anular: la factura ya tiene pagos registrados."""


class FacturaAnuladaError(Exception):
    """No se pueden registrar pagos sobre una factura anulada."""


class PagoExcedeSaldoError(Exception):
    """El monto del pago es mayor al saldo pendiente de la factura."""
