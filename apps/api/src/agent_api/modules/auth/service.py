from __future__ import annotations

import hmac

from ...config import Settings


def authenticate(settings: Settings, username: str, password: str) -> bool:
    if settings.admin_password is None:
        return False
    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password.get_secret_value()
    )
