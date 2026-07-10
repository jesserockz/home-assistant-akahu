"""Tests for the Akahu sensor platform."""

from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.akahu.const import UPDATE_INTERVAL

from .conftest import make_account


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_balance_sensors_created(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Each account becomes a balance sensor with the expected value."""
    await _setup(hass, mock_config_entry)
    registry = er.async_get(hass)

    entry = registry.async_get_entity_id("sensor", "akahu", "acc_1_balance")
    assert entry is not None
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "1234.56"
    assert state.attributes["unit_of_measurement"] == "NZD"
    assert state.attributes["device_class"] == "monetary"
    assert state.attributes["state_class"] == "total"


async def test_new_account_dynamic_discovery(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Accounts added between refreshes are picked up automatically."""
    await _setup(hass, mock_config_entry)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", "akahu", "acc_3_balance") is None

    mock_client.async_get_accounts.return_value = [
        *mock_client.async_get_accounts.return_value,
        make_account(
            account_id="acc_3",
            name="Credit Card",
            connection_id="conn_bnz",
            connection_name="BNZ",
            current=-250.00,
        ),
    ]
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert registry.async_get_entity_id("sensor", "akahu", "acc_3_balance") is not None


async def test_removed_account_at_same_connection_goes_unavailable(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """When an account vanishes but its connection remains, its sensor goes unavailable."""
    mock_client.async_get_accounts.return_value = [
        make_account(
            account_id="acc_1",
            name="Everyday",
            connection_id="conn_anz",
            connection_name="ANZ",
            current=1234.56,
        ),
        make_account(
            account_id="acc_2",
            name="Bonus Saver",
            connection_id="conn_anz",
            connection_name="ANZ",
            current=500.00,
        ),
    ]
    await _setup(hass, mock_config_entry)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", "akahu", "acc_2_balance")
    assert entity_id is not None
    assert hass.states.get(entity_id).state == "500.0"

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

    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
