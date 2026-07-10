"""Tests for the Akahu diagnostics."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.akahu.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redacts_secrets(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Tokens, account IDs and bank-identifying fields are redacted."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diag["entry"]["title"] == mock_config_entry.title
    assert diag["entry"]["data"]["app_token"] == "**REDACTED**"
    assert diag["entry"]["data"]["user_token"] == "**REDACTED**"

    assert len(diag["accounts"]) == 2
    for account in diag["accounts"]:
        assert account["id"] == "**REDACTED**"
        assert account["name"] == "**REDACTED**"
        assert account["connection_id"] == "**REDACTED**"
        assert account["connection_name"] == "**REDACTED**"
        assert account["formatted_account"] == "**REDACTED**"
        assert "balance" in account
        assert account["balance"]["currency"] == "NZD"
