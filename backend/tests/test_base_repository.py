import pytest


def test_base_repository_no_se_puede_instanciar_directamente(db_session):
    from app.repositories.base import BaseRepository

    with pytest.raises(TypeError):
        BaseRepository(db_session)


def test_subclase_concreta_debe_implementar_todos_los_metodos(db_session):
    from app.repositories.base import BaseRepository

    class RepositorioIncompleto(BaseRepository):
        def listar(self, id_clinica):
            return []

    with pytest.raises(TypeError):
        RepositorioIncompleto(db_session)
