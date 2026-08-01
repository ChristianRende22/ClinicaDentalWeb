from sqlalchemy.orm import Session

from app.models import ConfiguracionClinica


class ConfiguracionClinicaRepository:
    """Configuracion 1:1 de una clinica.

    NO hereda de BaseRepository: la relacion es 1:1 y la PK ES id_clinica, asi
    que obtener(id_clinica, id_) no tendria sentido. Los valores por defecto
    viven unicamente en el modelo; aca no se repiten.
    """

    def __init__(self, db: Session):
        self.db = db

    def obtener_o_crear(self, id_clinica: int) -> ConfiguracionClinica:
        """Devuelve la configuracion de la clinica, creandola con los defaults del
        modelo si todavia no existe. Idempotente.
        """
        config = self.db.get(ConfiguracionClinica, id_clinica)
        if config is None:
            config = ConfiguracionClinica(id_clinica=id_clinica)
            self.db.add(config)
            self.db.flush()
        return config

    def actualizar(self, id_clinica: int, data: dict) -> ConfiguracionClinica:
        config = self.obtener_o_crear(id_clinica)
        for campo, valor in data.items():
            setattr(config, campo, valor)
        self.db.flush()
        return config
