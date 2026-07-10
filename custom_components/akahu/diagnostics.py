"""Diagnostics support for the Akahu integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_APP_TOKEN, CONF_USER_TOKEN
from .coordinator import AkahuConfigEntry

TO_REDACT = {
    CONF_APP_TOKEN,
    CONF_USER_TOKEN,
    "id",
    "_id",
    "name",
    "formatted_account",
    "connection_id",
    "connection_name",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AkahuConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "accounts": [
            async_redact_data(asdict(account), TO_REDACT)
            for account in coordinator.data.values()
        ],
    }
