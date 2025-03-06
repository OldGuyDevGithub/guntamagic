import logging
import json
import aiohttp
from datetime import timedelta
import asyncio

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator, UpdateFailed)
from .const import DOMAIN, CONF_KEY

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)
MAPPING_FILE = "custom_components/guntamagic/modbus_mapping.json"
API_URL = f"http://{ip_address}/ext/daqdata.cgi?key={key}"

async def async_setup_entry(hass, entry, async_add_entities):
    try:
        with open(hass.config.path(MAPPING_FILE), "r", encoding="utf-8") as file:
            mapping = json.load(file)
    except Exception as e:
        _LOGGER.error("Fehler beim Laden des Mapping-Files: %s", e)
        return

    coordinator = GuntamagicDataUpdateCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()
    
    sensors = [GuntamagicSensor(coordinator, sensor_id, details) for sensor_id, details in mapping.items()]
    async_add_entities(sensors, update_before_add=True)

class GuntamagicDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass):
        super().__init__(
            hass, _LOGGER, name="guntamagic_sensors", update_interval=SCAN_INTERVAL
        )
        self.hass = hass

    async def _async_update_data(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Fehlerhafte Antwort: {response.status}")
                    return await response.json()
        except Exception as e:
            raise UpdateFailed(f"Fehler beim Abrufen der Daten: {e}")

class GuntamagicSensor(SensorEntity):
    def __init__(self, coordinator, sensor_id, details):
        self.coordinator = coordinator
        self._sensor_id = sensor_id
        self._name = details["name"]
        self._unit = details.get("unit", None)
        self._attr_native_unit_of_measurement = self._unit
        self._attr_native_value = "Testwert"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self.coordinator.data.get(self._sensor_id)

    @property
    def unique_id(self):
        return f"guntamagic_{self._sensor_id}"

    @property
    def should_poll(self):
        return False

    async def async_update(self):
        #await self.coordinator.async_request_refresh()
        self._attr_native_value = self.coordinator.data.get(self._sensor_key, "Kein Wert")
        self.async_write_ha_state()