import logging
import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import Entity
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_KEY

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):

    _LOGGER.debug("async_setup_entry für Guntamagic wurde aufgerufen.")
    
    """Set up the Guntamagic sensors from a config entry."""
    ip_address = entry.data[CONF_IP_ADDRESS]
    key = entry.data[CONF_KEY]
    name = entry.title  # Name der Integration als Basisname nehmen
    url = f"http://{ip_address}/ext/daqdata.cgi?key={key}"

    _LOGGER.debug("Guntamagic async_setup_entry aufgerufen für IP: %s", ip_address)

    try:
        response = aiohttp.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        _LOGGER.debug("Guntamagic API Antwort: %s", data)
    except requests.RequestException as error:
        _LOGGER.error("Fehler beim Abrufen der Daten: %s", error)
        return

    if not data:
        _LOGGER.warning("Guntamagic API hat keine Daten geliefert!")

    # Sensoren aus den JSON-Daten erstellen
    sensors = [GuntamagicSensor(name, url, param, value) for param, value in data.items()]
    _LOGGER.debug("Erstelle %d Sensoren: %s", len(sensors), [sensor.name for sensor in sensors])
    async_add_entities(sensors, True)

    _LOGGER.debug("Guntamagic Sensoren hinzugefügt: %s", [sensor.name for sensor in sensors])


class GuntamagicSensor(SensorEntity):
    """Ein Sensor für jeden Wert aus dem JSON."""

    def __init__(self, name, url, param, value):
        self._attr_name = f"{name} {param}"
        self._url = url
        self._param = param
        self._state = value
        _LOGGER.debug("Sensor erstellt: %s mit Wert: %s", self._name, self._state)

    @property
    def name(self):
        """Name des Sensors."""
        return self._attr_name

    @property
    def state(self):
        """Aktueller Zustand des Sensors."""
        return self._state

    async def async_update(self):
    """Daten vom Gerät abrufen und den Zustand aktualisieren."""
    _LOGGER.debug("GuntamagicSensor async_update aufgerufen für %s", self._attr_name)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self._url, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self._state = data.get(self._param, None)
                    _LOGGER.debug("Sensor %s neuer Wert: %s", self._attr_name, self._state)
            except aiohttp.ClientError as error:
                _LOGGER.error("Fehler beim Aktualisieren des Sensors %s: %s", self._attr_name, error)
