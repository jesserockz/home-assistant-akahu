"""Data update coordinator for the Akahu integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
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
        return {account.id: account for account in accounts}
