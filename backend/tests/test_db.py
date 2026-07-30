import pytest


def test_get_db_yields_session_and_closes_it(monkeypatch):
    import app.db as db_module

    closed = {"value": False}

    class FakeSession:
        def close(self):
            closed["value"] = True

    monkeypatch.setattr(db_module, "SessionLocal", lambda: FakeSession())

    gen = db_module.get_db()
    session = next(gen)

    assert isinstance(session, FakeSession)
    assert closed["value"] is False

    with pytest.raises(StopIteration):
        next(gen)

    assert closed["value"] is True
