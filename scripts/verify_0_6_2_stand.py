"""Stand verification for 0.6.2 token auto-refresh.

Read-only: authenticates, refreshes, and lists at most one task per check.
Creates nothing, modifies nothing, deletes nothing — ruvents.megaplan.ru is
the customer's production account, not a sandbox.

Unit tests (respx mocks) only prove the SDK builds requests the way its
author intended. This script is the only evidence that the *server* agrees:
each check asserts a semantic fact about the server's behavior — that the
superseded refresh token is genuinely rejected, that the refreshed access
token is genuinely accepted, which wire form the server actually uses to
signal 401 — rather than merely "the call didn't raise".

Credentials come from the environment (``MEGAPLAN_URL``, ``MEGAPLAN_USERNAME``,
``MEGAPLAN_PASSWORD``); a value already exported wins, otherwise it is read
from ``.env.local`` next to the repository root. Never print credential
values, access tokens, or refresh tokens.

Usage:
    python scripts/verify_0_6_2_stand.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

from megaplan_sdk import MegaplanClient
from megaplan_sdk.exceptions import AuthenticationError, MegaplanError
from megaplan_sdk.models.auth import AuthTokenResponse

RESULTS: list[tuple[str, bool, str]] = []

# The server accepts a superseded refresh token for a short reuse leeway
# after rotation (observed live: an immediate reuse and a reuse after 3s
# both silently return the already-issued successor token instead of
# rotating again or failing; a reuse after 90s raises AuthenticationError).
# That is standard OAuth2 refresh-token-reuse leeway, not evidence that old
# tokens stay valid — but it means check 2 must wait past the window to
# observe the real single-use contract; testing immediately after rotation
# tests the leeway, not rejection. See CLAUDE.md's API quirks entry.
_REUSE_LEEWAY_S = 90


def record(name: str, passed: bool, detail: str = "") -> None:
    """Record and print one check result."""
    RESULTS.append((name, passed, detail))
    print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


def _load_env_file(path: Path) -> None:
    """Load ``KEY=VALUE`` lines from `path` into ``os.environ``.

    Never overrides a variable already set in the environment. A minimal,
    dependency-free dotenv reader — python-dotenv is not a project
    dependency, and ``.env.local`` here is a flat, unquoted ``KEY=VALUE`` list.
    Copied verbatim from ``scripts/verify_0_6_1_stand.py`` (lines 108-122):
    the password contains ``&``, so ``source .env.local`` in zsh breaks on
    it and the file must be read line by line instead.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


class _LogCapture(logging.Handler):
    """Collects formatted ``megaplan_sdk`` log messages for later inspection.

    Used only by check 5 to determine, after the fact, which branch of the
    401-detection logic in ``HTTPClient._request`` actually fired — without
    parsing stdout by hand.
    """

    def __init__(self) -> None:
        """Initialize with an empty message buffer."""
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Append the record's rendered message to the buffer."""
        self.messages.append(record.getMessage())


async def check_rotation(url: str, user: str, password: str) -> str:
    """1-2. The server rotates refresh tokens and kills the previous one past the reuse leeway.

    Check 2 waits ``_REUSE_LEEWAY_S`` after rotation before reusing the
    superseded token. An immediate reuse is not a valid test of rejection:
    the server has a short grace window in which a superseded token still
    returns its already-issued successor instead of failing (see
    ``_REUSE_LEEWAY_S``'s comment and CLAUDE.md) — waiting past it is the
    only way to observe the real single-use contract.

    Returns:
        A live refresh token for the checks that follow.
    """
    async with MegaplanClient(url) as client:
        first = await client.authenticate(user, password)
        second = await client.auth.refresh_token(first.refresh_token)

        rotated = bool(second.refresh_token) and second.refresh_token != first.refresh_token
        record("1. refresh_token rotates on every refresh", rotated)

        print(
            f"     waiting {_REUSE_LEEWAY_S}s past rotation before testing reuse "
            "rejection (an immediate retry would only observe the server's reuse leeway)"
        )
        await asyncio.sleep(_REUSE_LEEWAY_S)
        try:
            await client.auth.refresh_token(first.refresh_token)
        except AuthenticationError as e:
            record(
                "2. the superseded refresh_token is rejected past the reuse leeway",
                True,
                str(e)[:80],
            )
        else:
            record(
                "2. the superseded refresh_token is rejected past the reuse leeway",
                False,
                "old token still works",
            )

        return second.refresh_token or ""


async def check_new_token_works(url: str, refresh_token: str) -> None:
    """3. The access token obtained by refreshing is accepted by the API.

    Correction (task-8 brief): the brief's original body hardcoded a PASS
    and would let a raised ``MegaplanError`` crash the whole script instead
    of recording a FAIL. A check that cannot fail is worse than no check.
    """
    try:
        async with MegaplanClient(url, refresh_token=refresh_token) as client:
            tasks = await client.tasks.list(limit=1)
    except MegaplanError as e:
        record("3. refreshed access token is accepted", False, f"{type(e).__name__}: {e}")
        return
    record("3. refreshed access token is accepted", True, f"{len(tasks)} task(s) read")


async def check_proactive(url: str, user: str, password: str) -> None:
    """4. A locally expired token is refreshed before the request goes out.

    Reads the token off ``client._auth_manager`` (private, on purpose — see
    below), not ``client.auth.get_access_token()``: ``client.auth`` wraps its
    *own*, independent ``AuthManager`` instance (``AuthResource.__init__``
    constructs a fresh one rather than reusing the client's), which is never
    the object ``HTTPClient`` consults for proactive/reactive refresh
    (``client._auth_manager``, wired via ``set_token_provider``). Since this
    script never calls ``client.auth.authenticate()``/``refresh_token()``,
    ``client.auth.get_access_token()`` stays ``None`` throughout and would
    make this check fail regardless of whether the SDK actually refreshed —
    a script bug caught while implementing this check, not an SDK finding
    about the server. See the report's "contradicts an assumption" section
    for why this split is still worth flagging as an SDK-side loose end.
    """
    async with MegaplanClient(url) as client:
        await client.authenticate(user, password)
        before = client._auth_manager.get_access_token()

        # Private attribute on purpose: forcing expiry is the only way to
        # exercise the proactive branch without waiting out the real TTL.
        client._auth_manager._expires_at = time.time() - 10

        await client.tasks.list(limit=1)
        after = client._auth_manager.get_access_token()
        record("4. proactive refresh on expired token", before != after and bool(after))


async def check_reactive(url: str, user: str, password: str) -> str:
    """5. A rejected token is refreshed and the request replayed.

    Also determines HOW the server signals 401 — a real HTTP status code, or
    HTTP 200 with ``meta.status == 401`` inside the envelope — by capturing
    ``megaplan_sdk`` log records at DEBUG/INFO level for the duration of the
    call and inspecting them afterwards:

    * ``"HTTP error 401 on ..."`` (WARNING, from the ``httpx.HTTPStatusError``
      branch) only appears when the server used a real HTTP status code.
    * ``"Request rejected with 401; attempting token refresh"`` (INFO) fires
      in both branches, so its presence alone does not distinguish them —
      only the *absence* of the WARNING line does.

    Returns:
        A short human-readable description of which form the server used.

    Note:
        ``log_level="DEBUG"`` is passed to the ``MegaplanClient`` constructor
        itself, not set on the logger beforehand: ``MegaplanClient.__init__``
        calls ``setup_logging(log_level)``, which calls
        ``logger.setLevel(...)`` unconditionally on this same
        ``"megaplan_sdk"`` logger — a level set before construction is
        silently overwritten back to the ``"WARNING"`` default the moment
        the client is built, which would leave ``saw_retry_signal`` always
        ``False`` and made the envelope branch unobservable regardless of
        what the server actually did.
    """
    sdk_logger = logging.getLogger("megaplan_sdk")
    capture = _LogCapture()
    previous_level = sdk_logger.level
    sdk_logger.addHandler(capture)

    tasks_read: int | None = None
    error: MegaplanError | None = None
    try:
        async with MegaplanClient(url, log_level="DEBUG") as client:
            await client.authenticate(user, password)
            client.set_access_token("invalid-token-0000")
            try:
                tasks = await client.tasks.list(limit=1)
                tasks_read = len(tasks)
            except MegaplanError as e:
                error = e
    finally:
        sdk_logger.removeHandler(capture)
        sdk_logger.setLevel(previous_level)

    saw_http_401 = any("HTTP error 401" in m for m in capture.messages)
    saw_retry_signal = any("Request rejected with 401" in m for m in capture.messages)

    if saw_http_401:
        form = "HTTP status code 401"
    elif saw_retry_signal:
        form = "HTTP 200 with meta.status == 401 inside the envelope"
    else:
        form = "UNKNOWN — no 401 signal observed in the captured logs"

    if error is not None:
        record("5. reactive refresh after 401", False, f"{type(error).__name__}: {error}")
    else:
        record("5. reactive refresh after 401", True, f"{tasks_read} task(s) after replay")
    print(f"     server signals 401 via: {form}")
    return form


async def check_single_flight(url: str, user: str, password: str) -> None:
    """6. Ten concurrent requests on an expired token cause one refresh."""
    refreshes: list[AuthTokenResponse] = []

    async with MegaplanClient(url, on_token_refresh=refreshes.append) as client:
        await client.authenticate(user, password)
        refreshes.clear()
        client._auth_manager._expires_at = time.time() - 10

        await asyncio.gather(*(client.tasks.list(limit=1) for _ in range(10)))

    record(
        "6. ten parallel requests refresh once",
        len(refreshes) == 1,
        f"{len(refreshes)} refresh(es)",
    )


async def main() -> None:
    """Run every check and exit non-zero if any of them failed."""
    _load_env_file(Path(__file__).resolve().parent.parent / ".env.local")
    missing = [
        name
        for name in ("MEGAPLAN_URL", "MEGAPLAN_USERNAME", "MEGAPLAN_PASSWORD")
        if name not in os.environ
    ]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)

    url = os.environ["MEGAPLAN_URL"]
    user = os.environ["MEGAPLAN_USERNAME"]
    password = os.environ["MEGAPLAN_PASSWORD"]

    refresh_token = await check_rotation(url, user, password)
    await check_new_token_works(url, refresh_token)
    await check_proactive(url, user, password)
    form = await check_reactive(url, user, password)
    await check_single_flight(url, user, password)

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)} PASS, {len(failed)} FAIL")
    print(f"server's 401 signalling form: {form}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
