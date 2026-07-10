"""Tests for the bundled pyakahu async client."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientError
import pytest

from custom_components.akahu.pyakahu import (
    AkahuAuthError,
    AkahuClient,
    AkahuConnectionError,
)
from custom_components.akahu.pyakahu import client as client_mod


def _fake_session(status: int = 200, payload: Any = None) -> MagicMock:
    """Return an AsyncMock session whose .get() yields the given response."""
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=payload or {})
    session = MagicMock()
    session.get = AsyncMock(return_value=response)
    return session


def _failing_session(exc: Exception) -> MagicMock:
    """Return a session whose .get() raises *exc*."""
    session = MagicMock()
    session.get = AsyncMock(side_effect=exc)
    return session


def _make_client(session: MagicMock) -> AkahuClient:
    return AkahuClient(session=session, app_token="app", user_token="user")


async def test_get_user_uses_preferred_name() -> None:
    """The user's preferred_name wins over first_name."""
    session = _fake_session(
        payload={
            "item": {
                "_id": "u1",
                "preferred_name": "Jess",
                "first_name": "Jessica",
            }
        }
    )
    client = _make_client(session)
    user = await client.async_get_user()
    assert user.id == "u1"
    assert user.name == "Jess"

    session.get.assert_awaited_once()
    args, kwargs = session.get.call_args
    assert args[0] == f"{client_mod.API_BASE_URL}/me"
    assert kwargs["headers"]["Authorization"] == "Bearer user"
    assert kwargs["headers"]["X-Akahu-Id"] == "app"


async def test_get_user_falls_back_to_first_name() -> None:
    """Without preferred_name the client uses first_name."""
    session = _fake_session(
        payload={"item": {"_id": "u2", "first_name": "Jo"}}
    )
    user = await _make_client(session).async_get_user()
    assert user.name == "Jo"


async def test_get_accounts_parses_full_payload() -> None:
    """Accounts with all fields populate every dataclass attribute."""
    payload = {
        "items": [
            {
                "_id": "a1",
                "name": "Everyday",
                "status": "ACTIVE",
                "type": "CHECKING",
                "formatted_account": "01-2345-6789012-00",
                "connection": {"_id": "c1", "name": "ANZ"},
                "balance": {
                    "current": 100.0,
                    "available": 95.0,
                    "limit": None,
                    "currency": "NZD",
                    "overdrawn": False,
                },
            }
        ]
    }
    accounts = await _make_client(_fake_session(payload=payload)).async_get_accounts()
    assert len(accounts) == 1
    account = accounts[0]
    assert account.id == "a1"
    assert account.connection_id == "c1"
    assert account.connection_name == "ANZ"
    assert account.balance.current == 100.0
    assert account.balance.currency == "NZD"


async def test_get_accounts_handles_missing_fields() -> None:
    """Bare-minimum payloads use defaults."""
    payload = {"items": [{"_id": "a1", "name": "Bare"}]}
    accounts = await _make_client(_fake_session(payload=payload)).async_get_accounts()
    account = accounts[0]
    assert account.status == "UNKNOWN"
    assert account.connection_id is None
    assert account.balance.currency == "NZD"
    assert account.balance.current is None


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_errors(status: int) -> None:
    """401 and 403 responses raise AkahuAuthError."""
    client = _make_client(_fake_session(status=status))
    with pytest.raises(AkahuAuthError):
        await client.async_get_user()


async def test_other_http_errors_become_connection_errors() -> None:
    """5xx responses raise AkahuConnectionError."""
    client = _make_client(_fake_session(status=503))
    with pytest.raises(AkahuConnectionError):
        await client.async_get_user()


async def test_network_failure_raises_connection_error() -> None:
    """A transport-level ClientError is wrapped as AkahuConnectionError."""
    client = _make_client(_failing_session(ClientError("boom")))
    with pytest.raises(AkahuConnectionError):
        await client.async_get_user()
