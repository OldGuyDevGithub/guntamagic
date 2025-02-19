import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_KEY

_LOGGER = logging.getLogger(__name__)

class GuntamagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Guntamagic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
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
