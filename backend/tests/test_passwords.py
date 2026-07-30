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
