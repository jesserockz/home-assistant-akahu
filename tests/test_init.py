"""Tests for the Akahu integration setup, unload, and device removal."""

from unittest.mock import AsyncMock

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.akahu import async_remove_config_entry_device
from custom_components.akahu.const import DOMAIN
from custom_components.akahu.pyakahu import AkahuAuthError, AkahuConnectionError

from .conftest import make_account


async def _setup(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Add the entry to hass and finish setup."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_unload(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Entry sets up cleanly and unloads cleanly."""
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_on_connection_error(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """First refresh failures put the entry into the retry state."""
    mock_client.async_get_accounts.side_effect = AkahuConnectionError("offline")
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_triggers_reauth(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An auth error during setup starts the reauth flow."""
    mock_client.async_get_accounts.side_effect = AkahuAuthError("bad")
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"].get("source") == "reauth" for flow in flows)


async def test_remove_device_blocks_active_device(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Removing an active device is rejected."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    account = next(iter(coordinator.data.values()))

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, f"connection_{account.connection_id}")}
    )
    assert device is not None
    assert not await async_remove_config_entry_device(
        hass, mock_config_entry, device
    )


async def test_remove_device_allows_stale_device(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Removing a device whose connection is gone is allowed."""
    await _setup(hass, mock_config_entry)
    device_registry = dr.async_get(hass)
    stale = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "connection_gone")},
    )
    assert await async_remove_config_entry_device(
        hass, mock_config_entry, stale
    )
