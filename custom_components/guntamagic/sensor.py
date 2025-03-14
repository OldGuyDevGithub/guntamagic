import logging
import json
from datetime import timedelta
import os

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator, UpdateFailed)
from .const import CONF_KEY, CONF_IP_ADDRESS, CONF_NAME

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

    entity_name = entry.data.get(CONF_NAME, "Guntamagic") 

    coordinator = GuntamagicDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    sensors = [GuntamagicSensor(coordinator, sensor_id, details, entity_name) for sensor_id, details in mapping.items()]
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
                data = await response.json()
                _LOGGER.debug("Received data from API: %s", data)  # Log response

                if not isinstance(data, list):
                    raise UpdateFailed("Unerwartetes Format: API sollte eine Liste zurückgeben")

                # Load mapping file (sensor_id → index in list)
                mapping = load_mapping()

                # Convert list to dictionary using mapping
                sensor_data = {sensor_id: data[details["index"]] for sensor_id, details in mapping.items() if details["index"] < len(data)}

                return sensor_data
        except Exception as e:
            raise UpdateFailed(f"Fehler beim Abrufen der Daten: {e}")


class GuntamagicSensor(SensorEntity):
    def __init__(self, coordinator, sensor_id, details, entity_name):
        self.coordinator = coordinator
        self._sensor_id = sensor_id
        self._name = details["name"]
        self._unit = details.get("unit", None)
        self._entity_name = entity_name
        self._attr_native_unit_of_measurement = self._unit
        self._attr_unique_id = f"{entity_name.lower()}_{sensor_id}"  # EINDEUTIGE ENTITY-ID
        self._attr_entity_id = f"sensor.{entity_name.lower()}_{self._name.replace(' ', '_').lower()}"  # ENTITY-ID FÜR HOME ASSISTANT

    async def async_added_to_hass(self):
        """Registriere den Listener für automatische Updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def name(self):
        return f"{self._entity_name} {self._name}" 
    @property
    def state(self):
        """Returns the sensor value from coordinator data."""
        if not self.coordinator.data:
            return None  # Prevents crashes if data isn't available yet
        return self.coordinator.data.get(self._sensor_id, "N/A")  # Use .get() to avoid errors

    @property
    def unique_id(self):
        return f"guntamagic_{self._entity_name}_{self._sensor_id}"

    @property
    def should_poll(self):
        return False
