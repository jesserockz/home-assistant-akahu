"""The Akahu integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import AkahuConfigEntry, AkahuCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: AkahuConfigEntry) -> bool:
    """Set up Akahu from a config entry."""
    coordinator = AkahuCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AkahuConfigEntry) -> bool:
    """Unload an Akahu config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
