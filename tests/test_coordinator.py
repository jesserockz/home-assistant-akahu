"""Tests for the Akahu coordinator's update + stale-device handling."""

from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.akahu.const import DOMAIN, UPDATE_INTERVAL
from custom_components.akahu.pyakahu import AkahuConnectionError, AkahuError

from .conftest import make_account


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_update_failed_on_connection_error(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A connection error after first refresh raises UpdateFailed."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data

    mock_client.async_get_accounts.side_effect = AkahuConnectionError("offline")
    try:
        await coordinator._async_update_data()
    except UpdateFailed as err:
        assert err.translation_key == "cannot_connect"
    else:
        raise AssertionError("UpdateFailed was not raised")


async def test_update_failed_on_generic_akahu_error(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A non-auth, non-connection AkahuError raises UpdateFailed (unknown)."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data

    mock_client.async_get_accounts.side_effect = AkahuError("boom")
    try:
        await coordinator._async_update_data()
    except UpdateFailed as err:
        assert err.translation_key == "unknown_error"
    else:
        raise AssertionError("UpdateFailed was not raised")


async def test_stale_device_removed_when_connection_disappears(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A connection that vanishes between refreshes is removed from the registry."""
    await _setup(hass, mock_config_entry)
    device_registry = dr.async_get(hass)
    assert (
        device_registry.async_get_device(identifiers={(DOMAIN, "connection_conn_asb")})
        is not None
    )

    mock_client.async_get_accounts.return_value = [
        make_account(
            account_id="acc_1",
            name="Everyday",
            connection_id="conn_anz",
            connection_name="ANZ",
            current=1234.56,
        )
    ]
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (
        device_registry.async_get_device(identifiers={(DOMAIN, "connection_conn_asb")})
        is None
    )


async def test_account_without_connection_uses_unknown_device(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Accounts that omit connection metadata land on the 'unknown' device."""
    mock_client.async_get_accounts.return_value = [
        make_account(
            account_id="acc_unknown",
            name="Mystery",
            connection_id=None,
            connection_name=None,
        )
    ]
    await _setup(hass, mock_config_entry)
    device_registry = dr.async_get(hass)
    assert (
        device_registry.async_get_device(identifiers={(DOMAIN, "connection_unknown")})
        is not None
    )
