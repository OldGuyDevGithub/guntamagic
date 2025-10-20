import os
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_NAME, CONF_IP_ADDRESS, CONF_KEY, CONF_MAPPING, CONF_MAPPING_OPTIONS


class GuntamagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Guntamagic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        # Mapping-Dateien dynamisch im Component-Ordner suchen
        mapping_files = [
            f for f in os.listdir(os.path.dirname(__file__))
            if f.startswith("modbus_mapping_") and f.endswith(".json")
        ]

        if not mapping_files:
            return self.async_abort(reason="no_mapping_files_found")

        # Schöne Labels statt Dateinamen anzeigen
        mapping_labels = {CONF_MAPPING_OPTIONS.get(f, f): f for f in mapping_files}

        if user_input is not None:
            if user_input[CONF_MAPPING] not in mapping_labels:
                errors["base"] = "invalid_mapping"
            else:
                mapping_file = mapping_labels[user_input[CONF_MAPPING]]
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS],
                        CONF_KEY: user_input[CONF_KEY],
                        CONF_MAPPING: mapping_file,
                    },
                )
            
        import logging
        _LOGGER = logging.getLogger(__name__)

        _LOGGER.warning("Mapping-Ordner: %s", os.path.dirname(__file__))
        _LOGGER.warning("Gefundene Mapping-Dateien: %s", mapping_files)

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required(CONF_KEY): str,
            vol.Required(CONF_MAPPING): vol.In(mapping_labels.keys()),
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
    """Optionen nachträglich ändern."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        mapping_files = [
            f for f in os.listdir(os.path.dirname(__file__))
            if f.startswith("modbus_mapping_") and f.endswith(".json")
        ]
        mapping_labels = {CONF_MAPPING_OPTIONS.get(f, f): f for f in mapping_files}

        if user_input is not None:
            mapping_file = mapping_labels[user_input[CONF_MAPPING]]
            return self.async_create_entry(title="", data={CONF_MAPPING: mapping_file})

        # Standardwert als Label ermitteln
        current_file = self.config_entry.data.get(CONF_MAPPING)
        default_label = next((label for label, file in mapping_labels.items() if file == current_file), None)

        schema = vol.Schema({
            vol.Required(CONF_MAPPING, default=default_label): vol.In(mapping_labels.keys())
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )
