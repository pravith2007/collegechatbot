import logging
from fastapi import HTTPException, Security, status, Header
from fastapi.security import APIKeyHeader
from config import ADMIN_API_KEY

logger = logging.getLogger("kec_auth")

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

def verify_admin_key(
    x_admin_key: str = Security(api_key_header),
    authorization: str = Header(None)
) -> bool:
    """
    Validates admin credentials via either:
    1. 'X-Admin-Key' header
    2. 'Authorization: Bearer <key>' header
    """
    provided_key = None
    if x_admin_key:
        provided_key = x_admin_key.strip()
    elif authorization and authorization.startswith("Bearer "):
        provided_key = authorization[7:].strip()

    if not provided_key or provided_key != ADMIN_API_KEY:
        logger.warning("Unauthorized access attempt to administrator endpoint.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Administrator API Key. Access denied.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True
