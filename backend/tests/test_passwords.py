def test_hash_password_no_devuelve_texto_plano():
    from app.security.passwords import hash_password

    resultado = hash_password("clave123")

    assert resultado != "clave123"
    assert resultado.startswith("$2b$")


def test_verify_password_acepta_la_clave_correcta():
    from app.security.passwords import hash_password, verify_password

    hashed = hash_password("clave123")

    assert verify_password("clave123", hashed) is True


def test_verify_password_rechaza_clave_incorrecta():
    from app.security.passwords import hash_password, verify_password

    hashed = hash_password("clave123")

    assert verify_password("otra-clave", hashed) is False


def test_generar_password_temporal_tiene_longitud_razonable():
    from app.security.passwords import generar_password_temporal

    password = generar_password_temporal()

    assert isinstance(password, str)
    assert len(password) >= 12


def test_generar_password_temporal_no_repite_valores():
    from app.security.passwords import generar_password_temporal

    generadas = {generar_password_temporal() for _ in range(20)}

    assert len(generadas) == 20
