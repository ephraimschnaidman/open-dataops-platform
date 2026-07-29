from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from api.config import Settings, get_settings
from api.repositories.users import UserRepository
from api.schemas.auth import AuthenticationErrorResponse, TokenResponse
from api.services.authentication import (
    AuthenticationService,
    InvalidCredentialsError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def get_authentication_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticationService:
    return AuthenticationService(
        UserRepository(request.app.state.database_pool),
        settings,
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": "Incorrect username or password.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": AuthenticationErrorResponse,
            "description": "PostgreSQL is unavailable.",
        },
    },
)
async def create_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[
        AuthenticationService,
        Depends(get_authentication_service),
    ],
) -> TokenResponse:
    try:
        return await service.authenticate(
            username=form_data.username,
            password=form_data.password,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except Exception as error:
        logger.warning(
            "Authentication database operation failed",
            extra={"event": "authentication_database_operation_failed"},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
