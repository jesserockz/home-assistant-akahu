"""Base entity for the Akahu integration."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AkahuCoordinator
from .pyakahu import AkahuAccount


class AkahuAccountEntity(CoordinatorEntity[AkahuCoordinator]):
    """Base class for entities tied to an Akahu account.

    Entities are grouped on a "service" device per bank connection, so multiple
    accounts at the same bank share one device under the config entry.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: AkahuCoordinator, account_id: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._account_id = account_id
        account = self.account
        connection_id = account.connection_id or "unknown"
        connection_name = account.connection_name or "Akahu"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"connection_{connection_id}")},
            manufacturer=connection_name,
            name=connection_name,
        )

    @property
    def account(self) -> AkahuAccount:
        """Return the latest data for this account."""
        return self.coordinator.data[self._account_id]

    @property
    def available(self) -> bool:
        """Return whether the account is still present in the coordinator data."""
        return super().available and self._account_id in self.coordinator.data
