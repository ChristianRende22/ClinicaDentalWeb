"""Helpers de validacion compartidos entre schemas de distintos dominios.

Nacieron en app/schemas/personas.py (Modulo 4) y se movieron aca cuando el
Modulo 5 los necesito de nuevo en tratamiento.py, consulta.py, etc. -- mismo
criterio que llevo CatalogoRepository a su propio archivo en el Modulo 3: no
copiar una regla de validacion dos veces.
"""


def texto_limpio(valor: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise ValueError("No puede estar vacio")
    return limpio


def no_nulo(valor, campo: str):
    """Rechaza un null explicito en un campo que la columna no admite.

    Los schemas Update declaran todo como `X | None` para permitir la
    actualizacion parcial, pero eso hace que un null EXPLICITO en el body
    tambien pase la validacion y llegue al setattr del repositorio. Contra una
    columna nullable=False eso es un IntegrityError, o sea un 500 donde
    corresponde un 422. "Ausente" y "null" no son lo mismo y hay que
    distinguirlos en el borde.
    """
    if valor is None:
        raise ValueError(f"'{campo}' no puede ser null")
    return valor
