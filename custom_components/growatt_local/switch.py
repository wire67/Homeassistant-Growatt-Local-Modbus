import logging
from datetime import timedelta
from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MODEL,
    CONF_NAME,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .const import (
    CONF_FIRMWARE,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)
from .sensor_types.inverter import INVERTER_SWITCH_TYPES
from .sensor_types.offgrid import OFFGRID_SWITCH_TYPES
from .sensor_types.storage import STORAGE_SWITCH_TYPES
from .sensor_types.switch_entity_description import GrowattSwitchEntityDescription

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.data[CONF_SERIAL_NUMBER]]
    entities = []
    sensor_descriptions: list[GrowattSwitchEntityDescription] = []
    supported_key_names = coordinator.growatt_api.get_register_names()

    for sensor in list(set(STORAGE_SWITCH_TYPES + INVERTER_SWITCH_TYPES + OFFGRID_SWITCH_TYPES)):
        if sensor.key not in supported_key_names:
            continue
        sensor_descriptions.append(sensor)

    coordinator.get_keys_by_name({sensor.key for sensor in sensor_descriptions}, True)

    entities.extend(
        [
            GrowattDeviceEntity(
                coordinator, description=description, entry=config_entry
            )
            for description in sensor_descriptions
        ]
    )

    async_add_entities(entities, True)


class GrowattDeviceEntity(CoordinatorEntity, RestoreEntity, SwitchEntity):
    """An entity using CoordinatorEntity."""

    def __init__(self, coordinator, description, entry):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, description.key)
        self.entity_description: GrowattSwitchEntityDescription = description
        self._config_entry = entry

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_SERIAL_NUMBER])},
            manufacturer="Growatt",
            model=entry.data[CONF_MODEL],
            sw_version=entry.data[CONF_FIRMWARE],
            name=entry.data[CONF_NAME],
        )

    @property
    def name(self):
        return f"{self._config_entry.data[CONF_NAME]} {self.entity_description.name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{DOMAIN}_{self._config_entry.data[CONF_SERIAL_NUMBER]}_{self.entity_description.key}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        register = self.coordinator.get_holding_register_by_name(self.entity_description.key)
        _LOGGER.debug("Device type %s key %s and register %d", self._attr_unique_id, register.name, register.register)
        await self.coordinator.write_register(register.register, 0)
        #   state_on: 0 # SbU
        #   state_off: 3 # SUb

    async def async_turn_off(self, **kwargs: Any) -> None:
        register = self.coordinator.get_holding_register_by_name(self.entity_description.key)
        _LOGGER.debug("Device type %s key %s and register %d", self._attr_unique_id, register.name, register.register)
        await self.coordinator.write_register(register.register, 3)
        await self.coordinator.force_refresh()
        #   state_on: 0 # SbU
        #   state_off: 3 # SUb

    async def async_added_to_hass(self) -> None:
        """Call when entity is about to be added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_state():
            self._attr_is_on = state.state == STATE_ON

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(self.entity_description.key)) is None:
            _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)
            return

        _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)

        value = int(state)

        #   state_on: 0 # SbU
        #   state_off: 3 # SUb
        self._attr_is_on = value == 0

        self.async_write_ha_state()

    @callback
    def _handle_midnight_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(self.entity_description.key)) is None:
            _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)
            return

        _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)
        value = int(state)

        self._attr_is_on = value == 1
        self.async_write_ha_state()
