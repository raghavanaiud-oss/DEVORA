import uuid
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_access_token_lifecycle():
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id)
    assert token is not None

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


def test_jwt_refresh_token_lifecycle():
    user_id = str(uuid.uuid4())
    token = create_refresh_token(subject=user_id)
    assert token is not None

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


def test_invalid_token_decoding():
    assert decode_token("invalid.token.structure") is None
    assert decode_token("") is None
