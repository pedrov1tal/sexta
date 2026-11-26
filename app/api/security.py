import hmac
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_admin_api_key(
    provided_key: Annotated[str | None, Security(api_key_header)],
) -> None:
    expected_key = settings.admin_api_key.get_secret_value()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A chave de API administrativa não está configurada.",
        )
    if provided_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API obrigatória.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave de API inválida.",
        )
