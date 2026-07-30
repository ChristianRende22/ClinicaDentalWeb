from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Repositorio base para recursos aislados por clinica.

    Todo metodo recibe id_clinica como primer parametro obligatorio, sin
    default. Ningun repositorio de un recurso tenant-scoped (Paciente,
    Doctor, Cita, etc. en modulos futuros) puede heredar de esta clase y
    omitir el filtro de clinica en sus queries.
    """

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    def listar(self, id_clinica: int) -> list[T]:
        ...

    @abstractmethod
    def obtener(self, id_clinica: int, id_: int) -> T | None:
        ...

    @abstractmethod
    def crear(self, id_clinica: int, data: dict) -> T:
        ...

    @abstractmethod
    def actualizar(self, id_clinica: int, id_: int, data: dict) -> T | None:
        ...

    @abstractmethod
    def eliminar(self, id_clinica: int, id_: int) -> bool:
        ...
