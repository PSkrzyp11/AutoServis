from datetime import datetime
from typing import Final

from fastapi import Response

from app.core.config import Settings
from app.core.time import utc_now

REFRESH_TOKEN_COOKIE = "refresh_token"
REFRESH_TOKEN_COOKIE_PATH = "/api/v1/auth"
SESSION_HINT_COOKIE = "session_present"
SESSION_HINT_COOKIE_PATH = "/"
SESSION_HINT_VALUE = "1"
SAME_SITE_POLICY: Final = "lax"


def set_session_cookies(
    response: Response,
    *,
    refresh_token: str,
    expires_at: datetime,
    settings: Settings,
) -> None:
    max_age = max(int((expires_at - utc_now()).total_seconds()), 0)
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=max_age,
        path=REFRESH_TOKEN_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=SAME_SITE_POLICY,
    )
    response.set_cookie(
        SESSION_HINT_COOKIE,
        SESSION_HINT_VALUE,
        max_age=max_age,
        path=SESSION_HINT_COOKIE_PATH,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=SAME_SITE_POLICY,
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_TOKEN_COOKIE,
        path=REFRESH_TOKEN_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=SAME_SITE_POLICY,
    )
    response.delete_cookie(
        SESSION_HINT_COOKIE,
        path=SESSION_HINT_COOKIE_PATH,
        secure=settings.cookie_secure,
        samesite=SAME_SITE_POLICY,
    )
