"""Common fixtures for the Akahu integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.akahu.const import CONF_APP_TOKEN, CONF_USER_TOKEN, DOMAIN
from custom_components.akahu.pyakahu import AkahuAccount, AkahuBalance, AkahuUser


USER_ID = "user_id_123"
USER_NAME = "Test User"
APP_TOKEN = "app_token_test"
USER_TOKEN = "user_token_test"


def make_account(
    *,
    account_id: str = "acc_1",
    name: str = "Everyday",
    connection_id: str | None = "conn_anz",
    connection_name: str | None = "ANZ",
    current: float | None = 1234.56,
    currency: str = "NZD",
) -> AkahuAccount:
    """Build an AkahuAccount fixture."""
    return AkahuAccount(
        id=account_id,
        name=name,
        status="ACTIVE",
        type="CHECKING",
        formatted_account="01-2345-6789012-00",
        connection_id=connection_id,
        connection_name=connection_name,
        balance=AkahuBalance(
            current=current,
            available=current,
            limit=None,
            currency=currency,
            overdrawn=False,
        ),
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Ensure the custom integration is loaded for every test."""
    yield


@pytest.fixture
def mock_user() -> AkahuUser:
    """Return a default authenticated Akahu user."""
    return AkahuUser(id=USER_ID, name=USER_NAME)


@pytest.fixture
def mock_accounts() -> list[AkahuAccount]:
    """Return two default Akahu accounts at distinct connections."""
    return [
        make_account(
            account_id="acc_1",
            name="Everyday",
            connection_id="conn_anz",
            connection_name="ANZ",
            current=1234.56,
        ),
        make_account(
            account_id="acc_2",
            name="Savings",
            connection_id="conn_asb",
            connection_name="ASB",
            current=9876.54,
        ),
    ]


@pytest.fixture
def mock_client(
    mock_user: AkahuUser, mock_accounts: list[AkahuAccount]
) -> Generator[AsyncMock]:
    """Patch the AkahuClient used by both the coordinator and config flow."""
    with (
        patch(
            "custom_components.akahu.coordinator.AkahuClient", autospec=True
        ) as coord_cls,
        patch(
            "custom_components.akahu.config_flow.AkahuClient", autospec=True
        ) as flow_cls,
    ):
        instance = AsyncMock()
        instance.async_get_user.return_value = mock_user
        instance.async_get_accounts.return_value = mock_accounts
        coord_cls.return_value = instance
        flow_cls.return_value = instance
        yield instance


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mocked Akahu config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=USER_NAME,
        data={CONF_APP_TOKEN: APP_TOKEN, CONF_USER_TOKEN: USER_TOKEN},
        unique_id=USER_ID,
    )
