"""The Akahu integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
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


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: AkahuConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removing a device only when its connection is no longer reported."""
    coordinator = config_entry.runtime_data
    active_identifiers = {
        (DOMAIN, f"connection_{account.connection_id or 'unknown'}")
        for account in coordinator.data.values()
    }
    return not device_entry.identifiers.intersection(active_identifiers)
