"""Authentication models for Megaplan SDK."""

from pydantic import BaseModel, ConfigDict


class AuthTokenResponse(BaseModel):
    """OAuth2 token endpoint response (FR-A/FR-B).

    Returned by ``auth.authenticate()`` and ``auth.refresh_token()`` so that
    callers persisting tokens externally receive the rotated
    ``refresh_token`` and ``expires_in`` alongside the access token. The
    server rotates the refresh token on every successful refresh — the
    returned one is the only guaranteed-valid token going forward.

    Attributes:
        access_token: OAuth2 access token.
        refresh_token: Rotated refresh token (None if the server omitted it).
        expires_in: Access token lifetime in seconds.
        token_type: Token type, normally "bearer".
        scope: Granted scope, if any.
    """

    access_token: str
    refresh_token: str | None = None
    expires_in: int = 172800
    token_type: str = "bearer"
    scope: str | None = None

    model_config = ConfigDict(extra="allow")
