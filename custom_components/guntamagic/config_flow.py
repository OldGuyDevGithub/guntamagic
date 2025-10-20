import os
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_NAME, CONF_IP_ADDRESS, CONF_KEY, CONF_MAPPING

class GuntamagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Guntamagic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Zeigt das Konfigurationsformular an."""
        errors = {}

        # Mapping Files im Component-Ordner dynamisch finden
        mapping_files = [
            f for f in os.listdir(os.path.dirname(__file__))
            if f.startswith("modbus_mapping_") and f.endswith(".json")
        ]

        if not mapping_files:
            errors["base"] = "no_mapping_files"
            return self.async_abort(reason="no_mapping_files_found")

        if user_input is not None:
            # Sicherstellen, dass ein Mapping ausgewählt wurde
            if user_input.get(CONF_MAPPING) not in mapping_files:
                errors["base"] = "invalid_mapping"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS],
                        CONF_KEY: user_input[CONF_KEY],
                        CONF_MAPPING: user_input[CONF_MAPPING],
                    },
                )

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required(CONF_KEY): str,
            vol.Required(CONF_MAPPING): vol.In(mapping_files),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GuntamagicOptionsFlowHandler(config_entry)


class GuntamagicOptionsFlowHandler(config_entries.OptionsFlow):
    """Optionaler Options-Flow zum Ändern des Mappings nachträglich."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        mapping_files = [
            f for f in os.listdir(os.path.dirname(__file__))
            if f.startswith("modbus_mapping_") and f.endswith(".json")
        ]

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_MAPPING, default=self.config_entry.data.get(CONF_MAPPING)): vol.In(mapping_files)
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )
