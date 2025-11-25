import os
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectOptionDict

from .const import DOMAIN, CONF_NAME, CONF_IP_ADDRESS, CONF_KEY, CONF_MAPPING, CONF_MAPPING_OPTIONS

_LOGGER = logging.getLogger(__name__)


class GuntamagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Guntamagic."""

    VERSION = 1

    def _get_mapping_options(self) -> list[SelectOptionDict]:
        """Lade die verfügbaren Mapping-Dateien und erstelle Optionen für den Selector."""
        mapping_files = [
            f for f in os.listdir(os.path.dirname(__file__))
            if f.startswith("modbus_mapping_") and f.endswith(".json")
        ]
        
        _LOGGER.debug("Mapping-Ordner: %s", os.path.dirname(__file__))
        _LOGGER.debug("Gefundene Mapping-Dateien: %s", mapping_files)
        
        # Erstelle Optionen für SelectSelector: value=Dateiname, label=Anzeigename
        options = []
        for f in mapping_files:
            label = CONF_MAPPING_OPTIONS.get(f, f.replace("modbus_mapping_", "").replace(".json", "").replace("_", " ").title())
            options.append(SelectOptionDict(value=f, label=label))
        
        return options

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        mapping_options = self._get_mapping_options()

        if not mapping_options:
            return self.async_abort(reason="no_mapping_files_found")

        if user_input is not None:
            # Validierung
            if not user_input.get(CONF_MAPPING):
                errors[CONF_MAPPING] = "no_mapping_selected"
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
            vol.Required(CONF_MAPPING): SelectSelector(
                SelectSelectorConfig(
                    options=mapping_options,
                    mode="dropdown",
                )
            ),
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

    def _get_mapping_options(self) -> list[SelectOptionDict]:
        """Lade die verfügbaren Mapping-Dateien."""
        mapping_files = [
            f for f in os.listdir(os.path.dirname(__file__))
            if f.startswith("modbus_mapping_") and f.endswith(".json")
        ]
        
        options = []
        for f in mapping_files:
            label = CONF_MAPPING_OPTIONS.get(f, f.replace("modbus_mapping_", "").replace(".json", "").replace("_", " ").title())
            options.append(SelectOptionDict(value=f, label=label))
        
        return options

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        errors = {}

        mapping_options = self._get_mapping_options()

        if user_input is not None:
            return self.async_create_entry(title="", data={CONF_MAPPING: user_input[CONF_MAPPING]})

        current_mapping = self.config_entry.data.get(CONF_MAPPING)

        schema = vol.Schema({
            vol.Required(CONF_MAPPING, default=current_mapping): SelectSelector(
                SelectSelectorConfig(
                    options=mapping_options,
                    mode="dropdown",
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )
