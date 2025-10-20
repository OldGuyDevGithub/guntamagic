import asyncio
import logging
import json
import os
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_KEY, CONF_IP_ADDRESS, CONF_NAME, CONF_MAPPING, DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)


async def load_mapping(file_name):
    """Lädt das Mapping asynchron, ohne Event Loop zu blockieren."""
    try:
        mapping_file = os.path.join(os.path.dirname(__file__), file_name)
        return await asyncio.to_thread(load_mapping_sync, mapping_file)
    except Exception as e:
        _LOGGER.error("Fehler beim Laden des Mappings (%s): %s", file_name, e)
        return {}


def load_mapping_sync(mapping_file):
    """Synchrones Lesen der Mapping-Datei (für asyncio.to_thread)."""
    with open(mapping_file, "r", encoding="utf-8") as f:
        return json.load(f)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Guntamagic sensors."""
    entity_name = entry.data.get(CONF_NAME, "Guntamagic")
    mapping_file_name = entry.data.get(CONF_MAPPING)

    if not mapping_file_name:
        _LOGGER.error("Kein Mapping-File ausgewählt — Abbruch.")
        return

    mapping = await load_mapping(mapping_file_name)
    if not mapping:
        _LOGGER.error("Mapping konnte nicht geladen werden: %s", mapping_file_name)
        return

    coordinator = GuntamagicDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        GuntamagicSensor(coordinator, sensor_id, details, entity_name, entry.entry_id)
        for sensor_id, details in mapping.items()
    ]
    async_add_entities(sensors, update_before_add=True)


class GuntamagicDataUpdateCoordinator(DataUpdateCoordinator):
    """Koordinator zum Abrufen und Aktualisieren der Sensordaten."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name="guntamagic_sensors",
            update_interval=SCAN_INTERVAL,
        )
        self.hass = hass
        self.entry = entry

    async def _async_update_data(self):
        """Fetch data from the Guntamagic API."""
        session = async_get_clientsession(self.hass)
        ip_address = self.entry.data[CONF_IP_ADDRESS]
        key = self.entry.data[CONF_KEY]
        mapping_file_name = self.entry.data.get(CONF_MAPPING)

        try:
            async with session.get(f"http://{ip_address}/ext/daqdata.cgi?key={key}") as response:
                if response.status != 200:
                    raise UpdateFailed(f"Fehlerhafte Antwort: {response.status}")

                data = await response.json()
                _LOGGER.debug("Received data from API: %s", data)

                if not isinstance(data, list):
                    raise UpdateFailed("Unerwartetes Format: API sollte eine Liste zurückgeben")

                mapping = await load_mapping(mapping_file_name)

                # Nur Werte übernehmen, deren Index im Bereich liegt
                sensor_data = {
                    sensor_id: data[details["index"]]
                    for sensor_id, details in mapping.items()
                    if details["index"] < len(data)
                }

                return sensor_data

        except Exception as e:
            raise UpdateFailed(f"Fehler beim Abrufen der Daten: {e}")


class GuntamagicSensor(SensorEntity):
    """Einzelner Guntamagic Sensor."""

    def __init__(self, coordinator, sensor_id, details, entity_name, entry_id):
        self.coordinator = coordinator
        self._sensor_id = sensor_id
        self._name = details["name"]
        self._unit = details.get("unit", None)
        self._entity_name = entity_name
        self._entry_id = entry_id
        self._attr_native_unit_of_measurement = self._unit
        self._attr_unique_id = f"{entry_id}_{sensor_id}"
        self._attr_entity_id = f"sensor.{entity_name.lower()}_{self._name.replace(' ', '_').lower()}"

    async def async_added_to_hass(self):
        """Listener für automatische Updates registrieren."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def name(self):
        return f"{self._entity_name} {self._name}"

    @property
    def state(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._sensor_id, "N/A")

    @property
    def unique_id(self):
        return f"guntamagic_{self._entity_name}_{self._sensor_id}"

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        """Geräteinformationen für das Device-Objekt in HA."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": self._entity_name,
            "manufacturer": "Guntamagic",
            "model": self.coordinator.entry.data.get(CONF_MAPPING, "Unbekannt"),
            "sw_version": "1.0",
        }
