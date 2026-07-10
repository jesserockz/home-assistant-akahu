"""Data update coordinator for the Akahu integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_APP_TOKEN, CONF_USER_TOKEN, DOMAIN, LOGGER, UPDATE_INTERVAL
from .pyakahu import (
    AkahuAccount,
    AkahuAuthError,
    AkahuClient,
    AkahuConnectionError,
    AkahuError,
)

type AkahuConfigEntry = ConfigEntry[AkahuCoordinator]


class AkahuCoordinator(DataUpdateCoordinator[dict[str, AkahuAccount]]):
    """Coordinator that fetches account balances from Akahu."""

    config_entry: AkahuConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: AkahuConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = AkahuClient(
            session=async_get_clientsession(hass),
            app_token=config_entry.data[CONF_APP_TOKEN],
            user_token=config_entry.data[CONF_USER_TOKEN],
        )
        self._known_connection_ids: set[str] = set()

    async def _async_update_data(self) -> dict[str, AkahuAccount]:
        """Fetch the latest account data from Akahu."""
        try:
            accounts = await self.client.async_get_accounts()
        except AkahuAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_auth",
            ) from err
        except AkahuConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err
        except AkahuError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err

        data = {account.id: account for account in accounts}
        self._async_remove_stale_devices(data)
        return data

    def _async_remove_stale_devices(
        self, accounts: dict[str, AkahuAccount]
    ) -> None:
        """Drop devices for connections Akahu no longer reports."""
        current_connection_ids = {
            account.connection_id or "unknown" for account in accounts.values()
        }
        stale = self._known_connection_ids - current_connection_ids
        if stale:
            device_registry = dr.async_get(self.hass)
            for connection_id in stale:
                device = device_registry.async_get_device(
                    identifiers={(DOMAIN, f"connection_{connection_id}")}
                )
                if device is not None:
                    device_registry.async_update_device(
                        device.id,
                        remove_config_entry_id=self.config_entry.entry_id,
                    )
        self._known_connection_ids = current_connection_ids
