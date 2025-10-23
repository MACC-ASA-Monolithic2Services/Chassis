# -*- coding: utf-8 -*-
"""Application dependency injector."""
import logging
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWTError

from .config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

# JWT Token Verify #################################################################################
async def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        # Cargar la clave pública desde el archivo configurado
        with open(settings.PUBLIC_KEY_PATH, "r", encoding="utf-8") as key_file:
            public_key = key_file.read()
        
        # Decodificar y validar firma + expiración
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        
        # Si todo va bien, devolvemos el payload con info del usuario
        logger.debug("JWT token validated successfully for user: %s", payload.get("sub"))
        return payload
        
    except PyJWTError as e:
        logger.warning("Invalid JWT: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Token verification error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )