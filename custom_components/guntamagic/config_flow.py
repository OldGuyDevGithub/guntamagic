import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant import config_entries
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_KEY, CONF_NAME, CONF_MAPPING, CONF_MAPPING_OPTIONS

_LOGGER = logging.getLogger(__name__)


class GuntamagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    "Handle a config flow for Guntamagic."

    VERSION = 1

    async def async_step_user(self, user_input=None):
        "Handle the initial step."
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): cv.string,
                    vol.Required(CONF_IP_ADDRESS): cv.string,
                    vol.Required(CONF_KEY): cv.string,
                    vol.Required(CONF_MAPPING): vol.In(CONF_MAPPING_OPTIONS)
                }
            ),
            errors=errors,
        )
