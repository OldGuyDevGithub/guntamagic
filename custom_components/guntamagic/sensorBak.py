import logging
import aiohttp
import json
import os

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME

from .const import DOMAIN, CONF_KEY

_LOGGER = logging.getLogger(__name__)
MAPPING_FILE = os.path.join(os.path.dirname(__file__), "modbus_mapping.json")


def load_mapping():
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        _LOGGER.error("Fehler beim Laden des Mappings: %s", e)
        return {}


async def async_setup_entry(hass, entry, async_add_entities):

    ip_address = entry.data[CONF_IP_ADDRESS]
    key = entry.data[CONF_KEY]
    name = entry.data.get(CONF_NAME, DOMAIN)
    url = f"http://{ip_address}/ext/daqdata.cgi?key={key}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                data = await response.json()
    except aiohttp.ClientError as error:
        _LOGGER.error("Error fetching data: %s", error)
        return

    if not isinstance(data, list):
        _LOGGER.error("Erwartete Liste, aber API gab: %s", type(data))
        return

    mapping = load_mapping()
    sensors = [
        GuntamagicSensor(name, url, mapping.get(str(i), f"Unbekannt_{i}"),
                         value)
        for i, value in enumerate(data)
    ]

    _LOGGER.debug("Erstellte Sensoren: %s", [s.name for s in sensors])
    async_add_entities(sensors, True)

    _LOGGER.debug("Guntamagic Sensoren hinzugefügt: %s",
                  [sensor.name for sensor in sensors])


class GuntamagicSensor(SensorEntity):
    "Ein Sensor für jeden Wert aus dem JSON."

    def __init__(self, name, url, param, value):
        self._name = f"{name} {param}"
        self._url = url
        self._param = param
        self._state = value
        _LOGGER.debug("Sensor erstellt: %s mit Wert: %s",
                      self._name, self._state)

    @property
    def name(self):
        "Name des Sensors."
        return self._name

    @property
    def state(self):
        "Aktueller Zustand des Sensors."
        return self._state

    async def async_update(self):
        "Daten vom Gerät abrufen und den Zustand aktualisieren."
        _LOGGER.debug("GuntamagicSensor async_update aufgerufen für %s",
                      self._name)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self._url, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self._state = data.get(self._param, None)
                    _LOGGER.debug("Sensor %s neuer Wert: %s", self._attr_name,
                                  self._state)
            except aiohttp.ClientError as error:
                _LOGGER.error("Fehler beim Aktualisieren des Sensors %s: %s",
                              self._name, error)
