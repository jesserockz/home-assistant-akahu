"""Async HTTP client for the Akahu Personal API."""

from typing import Any

from aiohttp import ClientError, ClientSession

from .exceptions import AkahuAuthError, AkahuConnectionError
from .models import AkahuAccount, AkahuUser

API_BASE_URL = "https://api.akahu.io/v1"


class AkahuClient:
    """Async client for the Akahu Personal API."""

    def __init__(
        self,
        session: ClientSession,
        app_token: str,
        user_token: str,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._app_token = app_token
        self._user_token = user_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._user_token}",
            "X-Akahu-Id": self._app_token,
        }

    async def _request(self, path: str) -> dict[str, Any]:
        """Perform a GET request against the API."""
        try:
            response = await self._session.get(
                f"{API_BASE_URL}{path}", headers=self._headers
            )
        except ClientError as err:
            raise AkahuConnectionError(str(err)) from err

        if response.status in (401, 403):
            raise AkahuAuthError(f"Unauthorized response: {response.status}")
        if response.status >= 400:
            raise AkahuConnectionError(f"HTTP {response.status}")
        payload: dict[str, Any] = await response.json()
        return payload

    async def async_get_user(self) -> AkahuUser:
        """Fetch the authenticated user's profile."""
        data = await self._request("/me")
        return AkahuUser.from_api(data.get("item", {}))

    async def async_get_accounts(self) -> list[AkahuAccount]:
        """Fetch the list of accounts the user has connected."""
        data = await self._request("/accounts")
        return [AkahuAccount.from_api(item) for item in data.get("items", [])]
