import logging
import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

CONF_KEY = "key"
DEFAULT_NAME = "Guntamagic Sensor"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Required(CONF_KEY): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    ip_address = entry.data[CONF_IP_ADDRESS]
    key = entry.data[CONF_KEY]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    url = f"http://{ip_address}/ext/daqdata.cgi?key={key}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        _LOGGER.error("Error fetching data: %s", error)
        return
    
    sensors = [GuntamagicSensor(name, url, param, value) for param, value in data.items()]
    async_add_entities(sensors, True)

class GuntamagicSensor(Entity):
    def __init__(self, name, url, param, value):
        self._name = f"{name} {param}"
        self._url = url
        self._param = param
        self._state = value

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    async def async_update(self):
        try:
            response = requests.get(self._url, timeout=10)
            response.raise_for_status()
            data = response.json()
            self._state = data.get(self._param, None)
        except requests.RequestException as error:
            _LOGGER.error("Error updating sensor %s: %s", self._name, error)

class GuntamagicConfigFlow(config_entries.ConfigFlow, domain="guntamagic"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Guntamagic", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_IP_ADDRESS): str,
                vol.Required(CONF_KEY): str,
            }),
            errors=errors,
        )
