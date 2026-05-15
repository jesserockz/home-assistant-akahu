"""Sensor platform for the Akahu integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AkahuConfigEntry, AkahuCoordinator
from .entity import AkahuAccountEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AkahuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Akahu balance sensors."""
    coordinator = entry.runtime_data
    known_accounts: set[str] = set()

    @callback
    def _add_new_accounts() -> None:
        new_accounts = set(coordinator.data) - known_accounts
        if not new_accounts:
            return
        known_accounts.update(new_accounts)
        async_add_entities(
            AkahuBalanceSensor(coordinator, account_id) for account_id in new_accounts
        )

    _add_new_accounts()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_accounts))


class AkahuBalanceSensor(AkahuAccountEntity, SensorEntity):
    """Sensor that reports an account's current balance."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: AkahuCoordinator, account_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, account_id)
        self._attr_unique_id = f"{account_id}_balance"
        self._attr_name = self.account.name
        self._attr_native_unit_of_measurement = self.account.balance.currency

    @property
    def native_value(self) -> float | None:
        """Return the current balance."""
        return self.account.balance.current
