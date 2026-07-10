"""Tests for the Akahu config flow."""

from unittest.mock import AsyncMock

import pytest

from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.akahu.const import CONF_APP_TOKEN, CONF_USER_TOKEN, DOMAIN
from custom_components.akahu.pyakahu import (
    AkahuAuthError,
    AkahuConnectionError,
    AkahuUser,
)

from .conftest import APP_TOKEN, USER_ID, USER_NAME, USER_TOKEN


VALID_INPUT = {CONF_APP_TOKEN: APP_TOKEN, CONF_USER_TOKEN: USER_TOKEN}


async def test_user_flow_happy_path(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """Successful user flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] in (None, {})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USER_NAME
    assert result["data"] == VALID_INPUT
    assert result["result"].unique_id == USER_ID


async def test_user_flow_falls_back_to_default_title(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """When the API returns no name we still create an entry titled 'Akahu'."""
    mock_client.async_get_user.return_value = AkahuUser(id=USER_ID, name=None)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Akahu"


@pytest.mark.parametrize(
    ("exception", "expected_error"),
    [
        (AkahuAuthError("nope"), "invalid_auth"),
        (AkahuConnectionError("nope"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors_then_recovers(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    exception: Exception,
    expected_error: str,
) -> None:
    """Each validation error is surfaced and the flow can recover."""
    mock_client.async_get_user.side_effect = exception

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    mock_client.async_get_user.side_effect = None
    mock_client.async_get_user.return_value = AkahuUser(id=USER_ID, name=USER_NAME)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_duplicate_aborts(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Adding the same user twice aborts."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_happy_path(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reauth with the same user updates the entry and aborts successfully."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    new_input = {
        CONF_APP_TOKEN: "app_token_new",
        CONF_USER_TOKEN: "user_token_new",
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], new_input
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == new_input


async def test_reauth_wrong_account(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reauth that resolves to a different user is rejected."""
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_user.return_value = AkahuUser(id="other_user", name="Other")

    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


async def test_reauth_invalid_then_recovers(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reauth surfaces validation errors and recovers."""
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_user.side_effect = AkahuAuthError("bad")

    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_client.async_get_user.side_effect = None
    mock_client.async_get_user.return_value = AkahuUser(id=USER_ID, name=USER_NAME)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reconfigure_happy_path(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfigure updates the entry tokens."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_input = {
        CONF_APP_TOKEN: "app_token_v2",
        CONF_USER_TOKEN: "user_token_v2",
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], new_input
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == new_input


async def test_reconfigure_wrong_account(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfigure with a different user is rejected."""
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_user.return_value = AkahuUser(id="other", name=None)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


async def test_reconfigure_validation_error(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfigure surfaces validation errors and lets the user retry."""
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_user.side_effect = AkahuConnectionError("nope")

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
