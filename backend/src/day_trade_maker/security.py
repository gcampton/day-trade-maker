from __future__ import annotations

import os
from dataclasses import dataclass
from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class EnvSecuritySettings:
    broker_side_effect_auth_required: bool = False
    broker_side_effect_admin_token: str | None = None
    broker_side_effect_csrf_token: str | None = None

    @classmethod
    def from_environment(cls) -> EnvSecuritySettings:
        return cls(
            broker_side_effect_auth_required=_env_flag_enabled(
                "DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_AUTH_REQUIRED"
            ),
            broker_side_effect_admin_token=_optional_env(
                "DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_ADMIN_TOKEN"
            ),
            broker_side_effect_csrf_token=_optional_env(
                "DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_CSRF_TOKEN"
            ),
        )


def require_broker_side_effect_authorization(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    settings = EnvSecuritySettings.from_environment()
    if not settings.broker_side_effect_auth_required:
        return

    if (
        settings.broker_side_effect_admin_token is None
        or settings.broker_side_effect_csrf_token is None
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Broker side-effect authorization is required but not configured",
        )

    expected_authorization = f"Bearer {settings.broker_side_effect_admin_token}"
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Broker side-effect authorization is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not compare_digest(authorization, expected_authorization):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid broker side-effect authorization is required",
        )

    if csrf_token is None or not compare_digest(
        csrf_token,
        settings.broker_side_effect_csrf_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid broker side-effect CSRF token is required",
        )


def _env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
