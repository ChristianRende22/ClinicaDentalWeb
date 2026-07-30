def test_settings_reads_from_env(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "3307")
    monkeypatch.setenv("DB_USER", "dental_user")
    monkeypatch.setenv("DB_PASSWORD", "s3cret")
    monkeypatch.setenv("DB_NAME", "clinica_test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")

    from app.config import Settings

    settings = Settings()

    assert settings.db_host == "db.example.com"
    assert settings.db_port == 3307
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expire_minutes == 60


def test_settings_database_url_format(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_USER", "root")
    monkeypatch.setenv("DB_PASSWORD", "")
    monkeypatch.setenv("DB_NAME", "clinica_test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")

    from app.config import Settings

    settings = Settings()

    assert settings.database_url == "mysql+mysqlconnector://root:@localhost:3306/clinica_test"
