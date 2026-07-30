from datetime import timedelta

import pytest


def test_create_and_decode_access_token():
    from app.security.jwt import create_access_token, decode_access_token

    token = create_access_token(
        data={"sub": "42", "id_clinica": 7, "rol": "admin"},
        expires_delta=timedelta(minutes=10),
    )
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["id_clinica"] == 7
    assert payload["rol"] == "admin"
    assert "exp" in payload


def test_decode_access_token_expirado_lanza_token_error():
    from app.security.jwt import TokenError, create_access_token, decode_access_token

    token = create_access_token(
        data={"sub": "42", "id_clinica": None, "rol": "superadmin"},
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_decode_access_token_invalido_lanza_token_error():
    from app.security.jwt import TokenError, decode_access_token

    with pytest.raises(TokenError):
        decode_access_token("token-que-no-es-un-jwt-valido")
