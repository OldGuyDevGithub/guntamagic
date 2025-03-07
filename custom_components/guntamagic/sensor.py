import logging
import json
import aiohttp
from datetime import timedelta
import os

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator, UpdateFailed)
from .const import DOMAIN, CONF_KEY

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)
MAPPING_FILE = os.path.join(os.path.dirname(__file__), "modbus_mapping.json")



def load_mapping():
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        _LOGGER.error("Fehler beim Laden des Mappings: %s", e)
        return {}


async def async_setup_entry(hass, entry, async_add_entities):
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as file:
            mapping = json.load(file)
    except Exception as e:
        _LOGGER.error("Fehler beim Laden des Mapping-Files: %s", e)
        return

    coordinator = GuntamagicDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    sensors = [GuntamagicSensor(coordinator, sensor_id, details) for sensor_id, details in mapping.items()]
    async_add_entities(sensors, update_before_add=True)


class GuntamagicDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass, _LOGGER, name="guntamagic_sensors", update_interval=SCAN_INTERVAL
        )
        self.hass = hass
        self.entry = entry

    async def _async_update_data(self):
        session = self.hass.helpers.aiohttp_client.async_get_clientsession(self.hass)  # Use HA session
        ip_address = self.entry.data[CONF_IP_ADDRESS]
        key = self.entry.data[CONF_KEY]
        try:
            async with session.get(f"http://{ip_address}/ext/daqdata.cgi?key={key}") as response:
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

